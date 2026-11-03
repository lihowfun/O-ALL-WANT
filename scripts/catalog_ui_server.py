"""Local web page (`catalog.py ui`) and terminal menu (`catalog.py menu`) for the OAW catalog.

Both front ends call the same action layer, which calls only the catalog
engine (catalog.py, catalog_core.py); both display `.oaw/catalog/view.json`
with the display rules in oaw_status.py. Their main screen is the intake
pipeline of docs/SKILL_INTAKE.md: the stage table and each food's stage and
current-stage actions come from view.json, so the page's stage buttons and the
menu's lettered stage actions are the same engine calls.

The page server binds 127.0.0.1 on a free port. Every API call needs the
per-session token header and a Host header naming that address; no CORS
headers are ever sent, actions are JSON POSTs only, and the static files carry
a strict Content-Security-Policy. Food-derived strings are data: JSON responses
escape <, > and & so no payload is ever markup, and the page sets text with
textContent only. Owner confirmation codes live only in this process's memory
and are printed on the interactive terminal that runs `ui` or `menu`; they
never appear in an API response or on disk, and a session stops accepting codes
after three wrong ones. Without an interactive terminal no code is issued.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hmac
import http.server
import json
from pathlib import Path
import re
import secrets
import sys
import threading
import traceback
import webbrowser

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import catalog  # noqa: E402
import catalog_core as core  # noqa: E402
import oaw  # noqa: E402
import oaw_status  # noqa: E402

UI_DIR = SCRIPTS / "catalog_ui"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
TOKEN_HEADER = "X-OAW-Token"
MAX_BODY = 256 * 1024
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
SECURITY_HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                    "X-Frame-Options": "DENY", "Cross-Origin-Opener-Policy": "same-origin",
                    "Cross-Origin-Resource-Policy": "same-origin", "Content-Security-Policy": CSP}
JOB_WAIT_SECONDS = 0.6
KEEP_JOBS = 40


class ActionError(ValueError):
    """A request whose parameters do not fit the action."""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def encode_json(value) -> bytes:
    """JSON whose bytes never contain markup characters, whatever the strings hold."""
    text = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    for raw, escaped in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        text = text.replace(raw, escaped)
    return text.encode("utf-8")


def split_urls(text: str) -> list:
    return [part for part in re.split(r"[\s,]+", str(text or "")) if part]


# --------------------------------------------------------------------------- parameters

def _text(params, key, *, limit=512, required=True, default=""):
    value = params.get(key)
    if value is None or value == "":
        if required:
            raise ActionError(f"{key} is required.")
        return default
    if not isinstance(value, str) or len(value) > limit:
        raise ActionError(f"{key} must be text of at most {limit} characters.")
    return value


def _flag(params, key):
    value = params.get(key, False)
    if not isinstance(value, bool):
        raise ActionError(f"{key} must be true or false.")
    return value


def _whole(params, key):
    value = params.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ActionError(f"{key} must be a whole number.")
    return value


def _texts(params, key, *, limit=512, most=50):
    value = params.get(key)
    if not isinstance(value, list) or not value or len(value) > most:
        raise ActionError(f"{key} must be a list of 1-{most} items.")
    if not all(isinstance(item, str) and item and len(item) <= limit for item in value):
        raise ActionError(f"Each {key} item must be text of at most {limit} characters.")
    return value


def _code(params):
    code = params.get("confirm")
    if code in (None, ""):
        return None
    if not isinstance(code, str) or not re.fullmatch(r"\d{6}", code):
        raise ActionError("The confirmation code has 6 digits.")
    return code


# --------------------------------------------------------------------------- actions (engine calls only)

def _pick_keys(target: Path, keys) -> dict:
    """Scout picks by canonical key, mapped to the current queue order right before picking."""
    pool = catalog.load_json(catalog.catalog_path(target, "scout.json"), {"candidates": {}})
    ranks = {c.get("key"): index for index, c in enumerate(catalog.scout_order(pool), 1)}
    missing = [k for k in keys if k not in ranks]
    if missing:
        raise catalog.CatalogError(f"Not in this week's scout list: {core.sanitize_text(missing[0], 80)}")
    return catalog.cmd_scout_pick(target, [ranks[k] for k in keys])


def act_add(target, params, progress):
    result = catalog.add_foods(target, _texts(params, "urls"))
    catalog.update_view(target)
    return result


def act_feed(target, params, progress):
    """送去試吃: add (or pick from the scout list), then taste every food not tasted yet."""
    if "scout_keys" in params:
        added = _pick_keys(target, _texts(params, "scout_keys", limit=200))
    else:
        added = act_add(target, params, progress)
    registry = catalog.load_registry(target)
    ids = list(dict.fromkeys(added["added"] + [e["id"] for e in added["existing"]]))
    queue = [fid for fid in ids if registry.get("foods", {}).get(fid, {}).get("lifecycle") == "found"]
    tasted, failed = [], []
    for index, fid in enumerate(queue):
        progress(f"試吃 {index + 1}/{len(queue)}：{fid}（封存在專案外 → 免費靜態檢查）", index, len(queue))
        try:
            tasted.append(catalog.cmd_taste(target, fid))
        except catalog.CatalogError as exc:
            failed.append({"food": fid, "error": core.sanitize_text(str(exc), 300), "error_zh": core.zh_error(exc)})
    lines = list(added["lines"]) + [line for result in tasted for line in result["lines"]]
    lines += [f"taste failed: {item['food']}: {item['error']}" for item in failed]
    return {"status": "fed", "added": added["added"], "merges": added["merges"], "existing": added["existing"],
            "errors": added["errors"], "already_tasted": [fid for fid in ids if fid not in queue],
            "tasted": [{k: r.get(k) for k in ("food", "verdict", "files", "integrity", "commit", "components")} for r in tasted],
            "failed": failed, "lines": lines}


def act_taste(target, params, progress):
    food = _text(params, "food", limit=200)
    progress(f"試吃 {food}（封存在專案外 → 免費靜態檢查）")
    return catalog.cmd_taste(target, food)


def act_scout(target, params, progress):
    progress("在 GitHub 搜尋本週的 skill／harness repo（只看、不下載）")
    return catalog.cmd_scout(target)


def act_scout_pick(target, params, progress):
    return _pick_keys(target, _texts(params, "scout_keys", limit=200))


def act_import_report(target, params, progress):
    """An empty food lets the engine register the food named in the folder's scout.json."""
    return catalog.cmd_import_report(target, _text(params, "food", limit=200, required=False),
                                     _text(params, "directory", limit=1024))


def act_plan(target, params, progress):
    return catalog.cmd_plan(target, _text(params, "food", limit=200))


def act_absorb(target, params, progress):
    apply = _flag(params, "apply")
    if apply:
        progress("存還原點 → 安裝 → 產生新版本 → 評估和預設的差異")
    return catalog.cmd_absorb(target, _text(params, "food", limit=200), _texts(params, "components", limit=200, most=100),
                              _text(params, "reason", limit=300, required=False), apply)


def act_remove(target, params, progress):
    """`food: true` names a food id; otherwise the name is egm, a bundled skill or an absorbed skill."""
    apply = _flag(params, "apply")
    if apply:
        progress("存還原點 → 移除 → 產生新版本 → 評估和預設的差異")
    return catalog.cmd_remove(target, _text(params, "name", limit=200), _text(params, "reason", limit=300, required=False), apply,
                              food=_flag(params, "food"))


def act_readd(target, params, progress):
    apply = _flag(params, "apply")
    if apply:
        progress("存還原點 → 備份 → 經 oaw.py migrate 加回 → 產生新版本 → 評估和預設的差異")
    return catalog.cmd_readd(target, _text(params, "name", limit=200), _text(params, "reason", limit=300, required=False), apply)


def act_forget(target, params, progress):
    return catalog.cmd_forget(target, _text(params, "food", limit=200), _text(params, "reason", limit=300, required=False),
                              _flag(params, "apply"))


def act_builds(target, params, progress):
    return catalog.cmd_builds(target)


def act_restore(target, params, progress):
    apply = _flag(params, "apply")
    if apply:
        progress("存目前的還原點 → 還原 OAW 安裝層 → doctor → 重新評估和預設的差異")
    return catalog.cmd_restore(target, _text(params, "build", limit=120), apply)


def act_effect(target, params, progress):
    progress("在 LAB_HOME 裝一份預設 2.0.0，靜態比較兩者")
    return catalog.cmd_effect(target)


def act_policy_show(target, params, progress):
    return catalog.cmd_policy(target, argparse.Namespace(policy_command="show"))


def act_policy_set(target, params, progress, confirmer=None):
    sandbox = _texts(params, "sandbox", limit=40, most=len(core.SANDBOX_CONDITIONS))
    args = argparse.Namespace(policy_command="set", per_food_tokens=_whole(params, "per_food_tokens"),
                              weekly_tokens=_whole(params, "weekly_tokens"), sandbox=",".join(sandbox), confirm=_code(params))
    return catalog.cmd_policy(target, args, confirmer=confirmer or catalog.ConfirmationChannel())


def act_triage(target, params, progress, confirmer=None):
    outcome = _text(params, "outcome", limit=20)
    if outcome not in core.TRIAGE_OUTCOMES:
        raise ActionError("outcome must be benign, allergen or confirm-toxic.")
    args = argparse.Namespace(food=_text(params, "food", limit=200), flag=_text(params, "flag", limit=400),
                              benign=outcome == "benign", allergen=outcome == "allergen", confirm_toxic=outcome == "confirm-toxic",
                              reason=_text(params, "reason", limit=300), confirm=_code(params))
    return catalog.cmd_triage(target, args, confirmer=confirmer or catalog.ConfirmationChannel())


def act_view(target, params, progress):
    return catalog.cmd_view(target)


ACTIONS = {"add": act_add, "feed": act_feed, "taste": act_taste, "scout": act_scout, "scout-pick": act_scout_pick,
           "import-report": act_import_report, "plan": act_plan, "absorb": act_absorb, "remove": act_remove,
           "readd": act_readd, "forget": act_forget,
           "builds": act_builds, "restore": act_restore, "effect": act_effect, "policy-show": act_policy_show,
           "policy-set": act_policy_set, "triage": act_triage, "view": act_view}
# Actions that need the owner's code get the front end's in-memory confirmation channel.
CONFIRMED_ACTIONS = ("policy-set", "triage")


def run_action(target: Path, name: str, params=None, progress=None, confirmer=None) -> dict:
    """One engine action as an envelope: ok, code (0 done, 2 refused/failed, 4 waiting for the owner's code).

    `error` keeps the engine's English text (the 動作紀錄 log shows it); `error_zh` is the
    Traditional Chinese message for a known error, or None.
    """
    handler = ACTIONS.get(name)
    if handler is None:
        return {"ok": False, "code": 2, "status": "error", "error": f"Unknown action {core.sanitize_text(name, 40)!r}.",
                "error_zh": "沒有這個動作。", "lines": []}
    progress = progress or (lambda *_args: None)
    params = params if isinstance(params, dict) else {}
    try:
        if name in CONFIRMED_ACTIONS:
            result = handler(target, params, progress, confirmer=confirmer)
        else:
            result = handler(target, params, progress)
    except catalog.NeedsConfirmation as exc:
        return {"ok": False, "code": 4, "status": "needs-confirmation", "error": str(exc), "error_zh": core.zh_error(exc), "lines": [str(exc)]}
    except (ActionError, catalog.CatalogError, oaw.InstallError, core.SourceError, OSError, ValueError) as exc:
        return {"ok": False, "code": 2, "status": "error", "error": core.sanitize_text(str(exc), 600), "error_zh": core.zh_error(exc),
                "lines": [f"catalog error: {exc}"]}
    return {"ok": True, "code": 0, "status": result.get("status"), "error": None,
            "result": {k: v for k, v in result.items() if k != "lines"}, "lines": list(result.get("lines", []))[:300]}


# --------------------------------------------------------------------------- jobs

class Job:
    def __init__(self, action: str, params: dict):
        self.id = secrets.token_hex(8)
        self.action, self.params = action, params
        self.state, self.envelope = "running", None
        self.progress = {"label": None, "done": None, "total": None}
        self.started_at, self.finished_at = now_iso(), None
        self.done = threading.Event()

    def update(self, label, done=None, total=None):
        self.progress = {"label": core.sanitize_text(label, 200), "done": done, "total": total}

    def finish(self, envelope: dict):
        self.envelope, self.finished_at = envelope, now_iso()
        self.state = "done" if envelope.get("ok") else "needs-confirmation" if envelope.get("code") == 4 else "error"
        self.done.set()

    def public(self, target: Path) -> dict:
        data = {"id": self.id, "action": self.action, "state": self.state, "progress": self.progress,
                "started_at": self.started_at, "finished_at": self.finished_at, "result": self.envelope}
        if self.state == "running" and self.action in ("feed", "taste"):
            raw, _note = oaw_status.load(target / oaw_status.STATUS_FILE)
            data["digest"] = oaw_status.digest_summary(raw) if raw else None
        return data


class UiApp:
    """Runs one engine action at a time in a background thread."""

    def __init__(self, target: Path, token: str):
        self.target, self.token = target, token
        self.lock = threading.Lock()
        self.jobs, self.current = {}, None
        self.confirmer = catalog.ConfirmationChannel()

    def submit(self, action: str, params: dict):
        with self.lock:
            if self.current is not None and self.current.state == "running":
                return None
            job = Job(action, params)
            self.current, self.jobs[job.id] = job, job
            for old in list(self.jobs)[:-KEEP_JOBS]:
                del self.jobs[old]
        threading.Thread(target=self._run, args=(job,), name=f"oaw-ui-{action}", daemon=True).start()
        return job

    def _run(self, job: Job):
        try:
            envelope = run_action(self.target, job.action, job.params, job.update, confirmer=self.confirmer)
        except Exception as exc:  # an engine bug must not kill the server or leak a traceback to the page
            traceback.print_exc()
            envelope = {"ok": False, "code": 2, "status": "error", "error": f"internal error: {type(exc).__name__}",
                        "error_zh": "內部錯誤（細節在啟動 ui 的終端機）。", "lines": []}
        job.finish(envelope)

    def busy(self):
        job = self.current
        return job.public(self.target) if job is not None and job.state == "running" else None

    def view_payload(self) -> dict:
        view, note = oaw_status.load_view(self.target)
        return {"view": view, "note": note, "stale": oaw_status.view_stale(self.target) if view else False, "busy": self.busy()}

    def meta(self) -> dict:
        return {"release": core.RELEASE, "project": str(self.target), "project_name": self.target.name,
                "installed": (self.target / oaw.MANIFEST_PATH).is_file(), "sandbox_conditions": list(core.SANDBOX_CONDITIONS),
                "token_label": core.TOKEN_LABEL, "token_label_zh": core.TOKEN_LABEL_ZH, "egm_skills": list(oaw.EGM_SKILLS), "bundled_skills": list(oaw.BUNDLED_SKILLS),
                "actions": sorted(ACTIONS), "paid_runs_enabled": False}


# --------------------------------------------------------------------------- HTTP

class UiHandler(http.server.BaseHTTPRequestHandler):
    server_version = "oaw-catalog-ui/0"
    sys_version = ""
    timeout = 30

    def log_message(self, format, *args):  # noqa: A002 - quiet: the terminal shows only the URL and codes
        return

    def _send(self, status: int, body: bytes, content_type: str, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in {**SECURITY_HEADERS, **(extra or {})}.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, value, extra=None):
        self._send(status, encode_json(value), "application/json; charset=utf-8", extra)

    def _guard(self, api: bool) -> bool:
        server = self.server
        if self.headers.get("Host", "") not in server.allowed_hosts:
            self._json(403, {"ok": False, "error": "This page only answers on its own 127.0.0.1 address."})
            return False
        if not api:
            return True
        supplied = self.headers.get(TOKEN_HEADER, "")
        if not supplied or not hmac.compare_digest(supplied.encode("utf-8", "replace"), server.app.token.encode("utf-8")):
            self._json(403, {"ok": False, "error": "Missing or wrong session token."})
            return False
        site = self.headers.get("Sec-Fetch-Site")
        origin = self.headers.get("Origin")
        if (site and site not in ("same-origin", "none")) or (origin and origin not in server.allowed_origins):
            self._json(403, {"ok": False, "error": "Cross-site requests are refused."})
            return False
        return True

    def _path(self) -> str:
        return self.path.split("?", 1)[0].split("#", 1)[0]

    def do_GET(self):  # noqa: N802
        path, app = self._path(), self.server.app
        if path.startswith("/api/"):
            if not self._guard(api=True):
                return
            if path.startswith("/api/action/"):
                return self._json(405, {"ok": False, "error": "Actions are POST-only."}, {"Allow": "POST"})
            if path == "/api/view":
                return self._json(200, app.view_payload())
            if path == "/api/meta":
                return self._json(200, app.meta())
            if path.startswith("/api/job/"):
                job = app.jobs.get(path[len("/api/job/"):])
                if job is None:
                    return self._json(404, {"ok": False, "error": "Unknown job."})
                return self._json(200, {"job": job.public(app.target)})
            return self._json(404, {"ok": False, "error": "Unknown API path."})
        if not self._guard(api=False):
            return
        if path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        entry = STATIC.get(path)
        if entry is None:
            return self._send(404, "Not found".encode(), "text/plain; charset=utf-8")
        self._send(200, (UI_DIR / entry[0]).read_bytes(), entry[1])

    def do_POST(self):  # noqa: N802
        path, app = self._path(), self.server.app
        if not path.startswith("/api/action/"):
            if self._guard(api=False):
                self._json(405, {"ok": False, "error": "Only /api/action/NAME accepts POST."}, {"Allow": "GET"})
            return
        if not self._guard(api=True):
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold() != "application/json":
            return self._json(415, {"ok": False, "error": "Send application/json."})
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._json(411, {"ok": False, "error": "Content-Length is required."})
        if length < 0 or length > MAX_BODY:
            return self._json(413, {"ok": False, "error": "Request body is too large."})
        try:
            params = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except (ValueError, UnicodeError):
            return self._json(400, {"ok": False, "error": "Body is not JSON."})
        if not isinstance(params, dict):
            return self._json(400, {"ok": False, "error": "Body must be a JSON object."})
        name = path[len("/api/action/"):]
        if name not in ACTIONS:
            return self._json(404, {"ok": False, "error": "Unknown action."})
        job = app.submit(name, params)
        if job is None:
            return self._json(409, {"ok": False, "error": "Another action is still running.", "busy": app.busy()})
        job.done.wait(JOB_WAIT_SECONDS)
        self._json(200 if job.state != "running" else 202, {"job": job.public(app.target)})

    def _refuse(self):
        if self._guard(api=False):
            self._json(405, {"ok": False, "error": "Method not allowed."}, {"Allow": "GET, POST"})

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = do_TRACE = do_CONNECT = _refuse


class UiServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, app: UiApp, port: int = 0):
        super().__init__(("127.0.0.1", port), UiHandler)
        self.app = app
        bound = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{bound}", f"localhost:{bound}"}
        self.allowed_origins = {f"http://127.0.0.1:{bound}", f"http://localhost:{bound}"}
        self.url = f"http://127.0.0.1:{bound}/#t={app.token}"


def start_server(target: Path, *, port: int = 0, token: str | None = None, auto_effect: bool = True) -> UiServer:
    """Bind 127.0.0.1 and serve in a background thread; the caller stops it with shutdown()."""
    try:
        catalog.refresh_view(target)
    except (catalog.CatalogError, OSError, ValueError) as exc:
        print(f"catalog warning: view.json not refreshed: {exc}", file=sys.stderr)
    app = UiApp(target, token or secrets.token_urlsafe(32))
    server = UiServer(app, port)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.25}, name="oaw-ui-http", daemon=True).start()
    if auto_effect and (target / oaw.MANIFEST_PATH).is_file():
        view, _note = oaw_status.load_view(target)
        effect = ((view or {}).get("my_oaw") or {}).get("effect")
        if not effect or effect.get("stale"):
            app.submit("effect", {})
    return server


def cmd_ui(target: Path, *, open_browser: bool = True, port: int = 0) -> dict:
    server = start_server(target, port=port)
    print(f"OAW 消化系統：{server.url}", flush=True)
    print("只接受本機 127.0.0.1；網址裡是這次的通行碼，不要分享。確認碼會印在這個終端機。按 Ctrl+C 結束。", flush=True)
    if open_browser:
        try:
            webbrowser.open(server.url)
        except (webbrowser.Error, OSError):
            print("無法自動開啟瀏覽器：請手動打開上面的網址。", flush=True)
    stop = threading.Event()
    try:
        while not stop.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return {"status": "stopped", "lines": ["OAW 消化系統網頁已結束（ui stopped）"]}


# --------------------------------------------------------------------------- terminal menu

class MenuExit(Exception):
    """End of input or the owner chose to leave."""


# Letters for the stage actions on the menu's main screen; q stays "quit".
STAGE_KEYS = "abcdefghijklmnoprstuvwxyz"


class Menu:
    """Terminal menu with the same pipeline, stage actions and display rules as the page (no curses).

    The main screen prints the intake pipeline (one line per food, from view.json), then every food's
    current-stage actions as letters, then the numbered screens.
    """

    def __init__(self, target: Path, read=None, write=None):
        # input()/print() are looked up at call time, so a wrapper or a test can replace them.
        self.target = target
        self._read = read or (lambda prompt: input(prompt))
        self.write = write or (lambda text: print(text, flush=True))
        # Codes live in this menu's memory and are shown on its terminal, like the page's.
        self.confirmer = catalog.ConfirmationChannel()
        self.items = (("1", "我的 OAW（版本、skill、和預設比）", self.my_oaw), ("2", "入口：你點名（貼 GitHub 網址，送去試吃）", self.feed),
                      ("3", "入口：每週偵查 → 相關性過濾 → 你確認", self.scout), ("4", "食物卡（送去試吃、忘掉）", self.cards),
                      ("5", "核准：吸收選中的成分", self.absorb), ("6", "版本：移除 skill／EGM", self.remove),
                      ("7", "計畫：系統的測試計畫", self.plan), ("8", "計畫：匯入 🐘 Elephant／🐟 Goldfish 紀錄", self.import_report),
                      ("9", "版本：時間線／還原到這版", self.restore), ("10", "版本：重新評估和預設的差異", self.effect),
                      ("11", "實測：常設預算", self.policy), ("12", "靜態：分流旗標", self.triage),
                      ("13", "版本：加回 EGM／內建 skill", self.readd))

    # ---- io
    def ask(self, prompt: str) -> str:
        try:
            return self._read(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            raise MenuExit() from None

    def yes(self, prompt: str) -> bool:
        return self.ask(prompt + " [y/N]：").casefold() in ("y", "yes", "是", "好")

    def numbers(self, text: str, size: int) -> list:
        picks = []
        for part in split_urls(text):
            if not part.isdigit() or not 1 <= int(part) <= size:
                self.write(f"  沒有第 {core.sanitize_text(part, 10)} 項")
                return []
            if int(part) not in picks:
                picks.append(int(part))
        return picks

    def view(self) -> dict:
        view, _note = oaw_status.load_view(self.target)
        if view is None or oaw_status.view_stale(self.target):
            catalog.refresh_view(self.target)
            view, _note = oaw_status.load_view(self.target)
        return view or {"foods": [], "release": core.RELEASE}

    def do(self, action: str, params=None) -> dict:
        envelope = run_action(self.target, action, params or {}, lambda label, *_rest: self.write(f"  … {label}"),
                              confirmer=self.confirmer)
        for line in envelope.get("lines", []):
            self.write("  " + line)
        if envelope["code"] == 2:
            self.write("  沒有完成：" + (envelope.get("error_zh") or "（原文見上一行）"))
        return envelope

    def reason(self, prompt: str = "原因（必填，會記進決定紀錄）：") -> str:
        """D6: a removal or re-add records why; an empty answer cancels."""
        text = self.ask(prompt)
        if not text:
            self.write("  沒有原因：已取消。")
        return text

    # ---- loop
    def loop(self) -> None:
        try:
            while True:
                view = self.view()
                funnel = view.get("funnel") or {}
                self.write("")
                self.write(f"OAW 消化系統（終端選單） · {self.target}")
                self.write(oaw_status.my_oaw_lines(view)[0] + f" · 食物 {funnel.get('submitted', 0)} · 已試吃 {funnel.get('tasted', 0)}"
                           f" · 實測 {funnel.get('measured', 0)} · 已吸收成分 {funnel.get('absorbed_parts', 0)}")
                for line in oaw_status.pipeline_lines(view):
                    self.write(line)
                actions = self.stage_choices(view)
                for key, label, _handler in self.items:
                    self.write(f"{key:>3}  {label}")
                self.write("  0  離開")
                choice = self.ask("請選擇（字母 = 這一站的動作，數字 = 畫面）：")
                if choice in ("0", "q", "quit", "exit"):
                    break
                if choice.casefold() in actions:
                    food, action = actions[choice.casefold()]
                    handler = lambda food=food, action=action: self.stage_action(food, action)  # noqa: E731
                else:
                    handler = next((h for key, _label, h in self.items if key == choice), None)
                if handler is None:
                    self.write("沒有這個選項。")
                    continue
                try:
                    handler()
                except (catalog.CatalogError, OSError, ValueError) as exc:
                    self.write(f"錯誤：{core.sanitize_text(str(exc), 300)}")
        except MenuExit:
            self.write("")

    # ---- stage actions (the same ones the page puts on the pipeline)
    def stage_choices(self, view) -> dict:
        """Print every food's current-stage actions with a letter; return letter -> (food, action)."""
        pairs = oaw_status.stage_actions(view)
        if not pairs:
            return {}
        self.write("這一站可以做：")
        choices = {}
        for key, (food, action) in zip(STAGE_KEYS, pairs):
            stage = oaw_status.clean((food.get("pipeline") or {}).get("stage_label_zh"), 8)
            where = "（終端確認碼）" if action.get("where") == "terminal" else ""
            self.write(f"  {key}. {oaw_status.clean(food.get('id'), 64)} · {stage} · {oaw_status.clean(action.get('label_zh'), 60)}"
                       + ("" if "終端" in str(action.get("label_zh")) else where))
            choices[key] = (food, action)
        if len(pairs) > len(STAGE_KEYS):
            self.write(f"  還有 {len(pairs) - len(STAGE_KEYS)} 個動作沒有列出：用 4 食物卡。")
        return choices

    def stage_action(self, food: dict, action: dict) -> None:
        """Run one pipeline action through the same engine calls as the page's stage buttons."""
        kind, fid = action.get("id"), food["id"]
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        if kind == "taste":
            if self.do("taste", {"food": fid})["ok"]:
                self.write("  試吃完成：看上面的流程。")
        elif kind == "forget":
            self.forget(food)
        elif kind == "absorb":
            self.absorb(food)
        elif kind == "remove-food":
            if self.do("remove", {"name": fid, "food": True, "apply": False})["ok"] and self.yes(f"確定移除 {fid} 已安裝的部分？會先存還原點"):
                reason = self.reason()
                if reason:
                    self.do("remove", {"name": fid, "food": True, "apply": True, "reason": reason})
        elif kind == "restore" and isinstance(params.get("build"), str):
            self.restore_to(params["build"])
        elif kind == "triage":
            self.triage(food)
        else:
            self.write("  這個動作不在終端選單裡。")

    def forget(self, food: dict) -> None:
        if self.do("forget", {"food": food["id"], "apply": False})["ok"] and self.yes(f"確定忘掉 {food['id']}？"):
            self.do("forget", {"food": food["id"], "apply": True, "reason": "由終端選單忘掉"})

    # ---- helpers
    def choose_food(self, view=None):
        foods = [f for f in (view or self.view()).get("foods", []) if isinstance(f, dict)]
        if not foods:
            self.write("還沒有食物：先選 2 投食，或 3 本週覓食。")
            return None
        for index, food in enumerate(foods, 1):
            self.write(f"  {index}. {oaw_status.headline_label(food.get('verdict'))} · {oaw_status.clean(food.get('display'), 60)} [{food.get('id')}]")
        picks = self.numbers(self.ask("選食物編號："), len(foods))
        return foods[picks[0] - 1] if picks else None

    def confirm_code(self, action: str, params: dict) -> dict:
        envelope = self.do(action, params)
        if envelope["code"] == 4:
            code = self.ask("輸入這個終端上剛顯示的 6 位數確認碼：")
            envelope = self.do(action, {**params, "confirm": code})
        if envelope["ok"]:
            self.write("  完成。")
        return envelope

    # ---- screens
    def my_oaw(self):
        for line in oaw_status.my_oaw_lines(self.view()):
            self.write(line)

    def feed(self):
        urls = split_urls(self.ask("貼上一個或多個 GitHub 網址（空白或逗號分隔；重複的會自動合併）："))
        if not urls:
            return
        envelope = self.do("feed", {"urls": urls})
        if envelope["ok"]:
            self.write(f"  試吃完成 {len(envelope['result']['tasted'])} 樣；結果在「4 食物卡」。")

    def scout(self):
        view = self.view()
        for line in oaw_status.scout_lines(view):
            self.write(line)
        candidates = ((view.get("feeding") or {}).get("scout") or {}).get("candidates") or []
        answer = self.ask("s = 立即覓食（連網搜尋 GitHub）；輸入編號 = 送去試吃；Enter = 返回：")
        if answer.casefold() == "s":
            if self.do("scout")["ok"]:
                for line in oaw_status.scout_lines(self.view()):
                    self.write(line)
        elif answer:
            picks = self.numbers(answer, len(candidates))
            keys = [candidates[i - 1]["key"] for i in picks if candidates[i - 1].get("status") != "picked"]
            if keys:
                self.do("feed", {"scout_keys": keys})
            elif picks:
                self.write("  這些已經送去過了。")

    def cards(self):
        view = self.view()
        food = self.choose_food(view)
        if not food:
            return
        for line in oaw_status.food_lines(food, detail=True):
            self.write(line)
        tasted = bool(food.get("tasted"))
        installed = any(c.get("in_current_build") for c in food.get("components") or [] if isinstance(c, dict))
        choices = (["t = 送去試吃（免費、封存在專案外）"] if not tasted else []) + (["f = 忘掉這樣食物"] if not installed else [])
        if not choices:
            return
        answer = self.ask("；".join(choices) + "；Enter = 返回：").casefold()
        if answer == "t" and not tasted:
            if self.do("taste", {"food": food["id"]})["ok"]:
                self.write("  試吃完成；再選 4 看結果。")
        elif answer == "f" and not installed:
            self.forget(food)

    def absorb(self, food=None):
        food = food or self.choose_food()
        if not food:
            return
        options = [(c["id"], c.get("name"), "靜態量測") for c in food.get("components", [])
                   if c.get("disposition") == "absorb" and not c.get("decision")]
        options += [(c["id"], c.get("name"), "歷史證據，只記成待辦") for r in food.get("historical", []) for c in r.get("components", [])
                    if c.get("disposition") == "absorb" and not c.get("decision")]
        if not options:
            self.write("  這樣食物目前沒有可以吸收的成分（只有 🟢 吸收 的成分能選）。")
            return
        for index, (cid, name, basis) in enumerate(options, 1):
            self.write(f"  {index}. 🟢 {cid} · {oaw_status.clean(name, 60)} · {basis}")
        picks = self.numbers(self.ask("選要吸收的成分編號（可多個）："), len(options))
        if not picks:
            return
        params = {"food": food["id"], "components": [options[i - 1][0] for i in picks]}
        preview = self.do("absorb", {**params, "apply": False})
        if not preview["ok"]:
            return
        creates = preview["result"].get("creates_build")
        if self.yes("確定吸收？會先存還原點，再產生新版本" if creates else "確定記成待辦？不改程式，也不產生新版本"):
            reason = self.ask("原因（可空白）：")
            done = self.do("absorb", {**params, "apply": True, "reason": reason})
            if done["ok"] and done["result"].get("build"):
                doctor = (done["result"].get("doctor") or {}).get("status")
                self.write(f"  已吸收：新版本 {done['result']['build']} · doctor：{doctor} · 品質：未量測（沒有實測證據）。")
            elif done["ok"]:
                self.write("  已記成待辦（未改程式）。")

    def remove(self):
        view = self.view()
        rows = oaw_status.installed_skills(view)
        names = []
        if rows:
            present = [name for name, tag in rows if tag != "比預設少"]
            if any(name in oaw.EGM_SKILLS for name in present):
                names.append("egm")
            names += [name for name in present if name not in oaw.EGM_SKILLS]
        if not names:
            name = self.ask("要移除的 skill 名稱（或 egm）：")
            if not name:
                return
        else:
            for index, name in enumerate(names, 1):
                self.write(f"  {index}. {name}" + ("（整組 EGM skill）" if name == "egm" else ""))
            picks = self.numbers(self.ask("選要移除的編號："), len(names))
            if not picks:
                return
            name = names[picks[0] - 1]
        if self.do("remove", {"name": name, "apply": False})["ok"] and self.yes(f"確定移除 {name}？會先備份和存還原點"):
            reason = self.reason()
            if reason:
                self.do("remove", {"name": name, "apply": True, "reason": reason})

    def readd(self):
        rows = oaw_status.installed_skills(self.view()) or []
        missing = [name for name, tag in rows if tag == "比預設少"]
        names = (["egm"] if any(name in oaw.EGM_SKILLS for name in missing) else []) + [n for n in missing if n not in oaw.EGM_SKILLS]
        if not names:
            name = self.ask("要加回的內建 skill 名稱（或 egm；Enter 返回）：")
            if not name:
                return
        else:
            for index, name in enumerate(names, 1):
                self.write(f"  {index}. {name}" + ("（整組 EGM skill）" if name == "egm" else ""))
            picks = self.numbers(self.ask("選要加回的編號："), len(names))
            if not picks:
                return
            name = names[picks[0] - 1]
        if self.do("readd", {"name": name, "apply": False})["ok"] and self.yes(f"確定加回 {name}？會先備份和存還原點；加回的 skill 要重新測試"):
            reason = self.reason()
            if reason:
                self.do("readd", {"name": name, "apply": True, "reason": reason})

    def plan(self):
        food = self.choose_food()
        if food and self.do("plan", {"food": food["id"]})["ok"]:
            self.write("  實測還是規劃中：原型 v0 只顯示系統規劃的測試和預估花費，不執行付費實測。")

    def import_report(self):
        directory = self.ask("報告資料夾路徑（digest.json、goldfish-*.json、components.json…）：")
        if not directory:
            return
        foods = [f for f in self.view().get("foods", []) if isinstance(f, dict)]
        for index, food in enumerate(foods, 1):
            self.write(f"  {index}. {oaw_status.clean(food.get('display'), 60)} [{food.get('id')}]")
        answer = self.ask("屬於哪樣食物？輸入編號；Enter = 依資料夾裡的 scout.json 判斷：")
        ident = ""
        if answer:
            picks = self.numbers(answer, len(foods))
            if not picks:
                return
            ident = foods[picks[0] - 1]["id"]
        if self.do("import-report", {"food": ident, "directory": directory})["ok"]:
            self.write("  已匯入成 歷史證據：只顯示，不計入判定。")

    def restore(self):
        view = self.view()
        timeline = list(reversed(((view.get("my_oaw") or {}).get("timeline")) or []))
        for line in oaw_status.timeline_lines(list(reversed(timeline))):
            self.write(line)
        if not timeline:
            return
        for index, build in enumerate(timeline, 1):
            self.write(f"  {index}. {build.get('name')}" + ("（目前）" if build.get("current") else ""))
        picks = self.numbers(self.ask("還原到第幾版（Enter 返回）："), len(timeline))
        if picks:
            self.restore_to(timeline[picks[0] - 1]["name"])

    def restore_to(self, name: str) -> None:
        if self.do("restore", {"build": name, "apply": False})["ok"] and self.yes(f"確定還原到 {name}？只動 OAW 安裝層"):
            self.do("restore", {"build": name, "apply": True})

    def effect(self):
        if self.do("effect")["ok"]:
            for line in oaw_status.effect_lines((self.view().get("my_oaw") or {}).get("effect")):
                self.write(line)

    def policy(self):
        self.do("policy-show")
        if not self.yes("要設定常設預算嗎？"):
            return
        try:
            per_food = int(self.ask("每樣食物的付費上限（tokens）：").replace(",", ""))
            weekly = int(self.ask("每週的付費上限（tokens）：").replace(",", ""))
        except ValueError:
            self.write("  請輸入整數。")
            return
        for index, condition in enumerate(core.SANDBOX_CONDITIONS, 1):
            self.write(f"  {index}. {condition}")
        picks = self.numbers(self.ask("試跑的隔離條件（編號，可多個）："), len(core.SANDBOX_CONDITIONS))
        if picks:
            self.confirm_code("policy-set", {"per_food_tokens": per_food, "weekly_tokens": weekly,
                                             "sandbox": [core.SANDBOX_CONDITIONS[i - 1] for i in picks]})

    def triage(self, food=None):
        food = food or self.choose_food()
        if not food:
            return
        static = catalog.latest_static(catalog.load_evidence(self.target, food["id"]))
        decided = {d.get("flag") for d in catalog.load_decisions(self.target) if d.get("food") == food["id"] and d.get("kind") == "triage"}
        flags = [f for f in (static or {}).get("flags", []) if f.get("id") not in decided and f.get("severity") in ("high", "medium")]
        if not flags:
            self.write("  沒有待分流的旗標。")
            return
        flags.sort(key=lambda f: (f.get("severity") != "high", f.get("id")))
        for index, flag in enumerate(flags[:40], 1):
            self.write(f"  {index}. [{flag.get('severity')}] {flag.get('rule')} {oaw_status.clean(flag.get('path'), 80)}:{flag.get('line')} · {flag.get('meaning')}")
        picks = self.numbers(self.ask("選旗標編號："), min(len(flags), 40))
        if not picks:
            return
        outcome = {"b": "benign", "a": "allergen", "t": "confirm-toxic"}.get(self.ask("b = 良性、a = 過敏原、t = 確認有毒：").casefold())
        reason = self.ask("原因（必填）：")
        if outcome and reason:
            self.confirm_code("triage", {"food": food["id"], "flag": flags[picks[0] - 1]["id"], "outcome": outcome, "reason": reason})


def cmd_menu(target: Path, *, read=None, write=None) -> dict:
    Menu(target, read, write).loop()
    return {"status": "menu", "lines": ["已離開選單（menu closed）"]}
