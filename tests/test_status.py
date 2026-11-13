import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import oaw_status


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-status-")
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")

    def run_cli(self, *extra):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(oaw_status.main(["--project", str(self.root), *extra]), 0)
        return output.getvalue()

    def test_progress_counts_and_unknown_percent(self):
        self.write(".oaw/progress.json", {"schema_version": 1, "items": [
            {"id": "a", "title": "Done task", "status": "done", "percent": 100, "basis": "tests 6/6"},
            {"id": "b", "title": "Blocked", "status": "waiting", "percent": 0, "basis": "needs your merge"},
            {"id": "c", "title": "No basis", "status": "in_progress", "percent": 40, "basis": ""},
            {"id": "d", "title": "Bad percent", "status": "todo", "percent": 140, "basis": "x"},
        ]})
        summary = json.loads(self.run_cli("--json"))["progress"]
        self.assertEqual((summary["done"], summary["waiting"], summary["total"]), (1, 1, 4))
        self.assertEqual([item["percent"] for item in summary["items"]], [100, 0, None, None])
        text = self.run_cli()
        self.assertIn("完成 1/4 · 等你 1", text)
        self.assertIn("??????????   ?%  No basis", text)
        self.assertNotIn("40%", text)

    def test_missing_and_invalid_files_are_reported(self):
        self.assertIn("沒有進度檔（missing）", self.run_cli())
        self.write(".oaw/progress.json", "{not json")
        self.write(".oaw/catalog/status.json", {"schema_version": 2})
        text = self.run_cli()
        self.assertIn("沒有進度檔（invalid）", text)
        self.assertIn("狀態檔無效", text)

    def test_digest_progress_verdict_and_stall(self):
        now = datetime.now(timezone.utc)
        status = {"schema_version": 1, "skill": "egm-review", "source": "google/elephant-goldfish-model@f0ba151",
                  "stage": "behavior-ab", "progress": {"done": 42, "total": 90}, "verdict_so_far": "parity",
                  "updated_at": now.isoformat()}
        self.write(".oaw/catalog/status.json", status)
        self.assertIn("正在消化：egm-review · 實測 42/90 · 齊平", self.run_cli())
        status["updated_at"] = (now - timedelta(minutes=30)).isoformat()
        self.write(".oaw/catalog/status.json", status)
        self.assertIn("可能已中斷", self.run_cli())
        status.update(stage="done", verdict_so_far="evolved")
        self.write(".oaw/catalog/status.json", status)
        text = self.run_cli()
        self.assertIn("完成 42/90 · 進化", text)
        self.assertNotIn("可能已中斷", text)

    def test_catalog_headline_and_unknown_verdicts_are_never_in_progress(self):
        status = {"schema_version": 1, "skill": "food" + chr(0x202E) + chr(27) + "[2J", "source": "x/food@abc1234", "stage": "done",
                  "progress": {"done": 3, "total": 3}, "verdict_so_far": "pending", "headline": "untested",
                  "updated_at": datetime.now(timezone.utc).isoformat()}
        self.write(".oaw/catalog/status.json", status)
        text = self.run_cli()
        self.assertIn("最近一次試吃：food [2J · 完成 3/3 · 未測", text)  # a finished taste is no longer "being digested"
        self.assertNotIn(chr(0x202E), text)
        status.pop("headline")
        status["verdict_so_far"] = "glorious"
        self.write(".oaw/catalog/status.json", status)
        self.assertIn("未知（glorious，請更新 OAW）", self.run_cli())
        status["headline"] = "mystery"
        self.write(".oaw/catalog/status.json", status)
        self.assertIn("未知（mystery，請更新 OAW）", self.run_cli())

    def test_open_questions_from_the_page_are_counted_and_blockers_explained(self):
        self.assertEqual(oaw_status.open_questions(self.root), 0)
        self.assertNotIn("你在網頁上問的問題", self.run_cli())
        records = [json.dumps({"id": "a1", "question": "q1", "status": "open"}), json.dumps({"id": "a2", "question": "q2", "status": "answered"}),
                   "{damaged", json.dumps({"id": "a3", "question": "q3"}), json.dumps(["not", "a", "record"])]
        self.write(".oaw/catalog/questions.jsonl", "\n".join(records) + "\n")
        self.assertEqual(oaw_status.open_questions(self.root), 2)
        self.assertIn("你在網頁上問的問題：2 個還沒回答（catalog.py questions 列出；Claude 在對話裡回答）", self.run_cli())
        self.assertEqual(json.loads(self.run_cli("--json"))["open_questions"], 2)
        # The page's blocker explanation is on the terminal food card too (catalog.py menu → 4 食物卡).
        pipeline = {"waiting_zh": "等你", "blocker": {"where_zh": "靜態：1 個高嚴重度旗標待你分流", "basis_zh": ["D5、D7：只舉旗", "F-PIPE x.sh:2：管線"],
                                                    "if_ignored_zh": "停在靜態", "unknown_zh": ["紀錄沒寫"]}}
        self.assertEqual(oaw_status.blocker_lines(pipeline), ["  卡在哪：靜態：1 個高嚴重度旗標待你分流 · 等你", "  依據：D5、D7：只舉旗；F-PIPE x.sh:2：管線",
                                                              "  你不處理會怎樣：停在靜態", "  紀錄沒寫的：紀錄沒寫"])
        self.assertEqual(oaw_status.blocker_lines({}), [])
        food = {"id": "x", "display": "a/x", "verdict": {"headline": "risky"}, "pipeline": pipeline}
        self.assertIn("  卡在哪：靜態：1 個高嚴重度旗標待你分流 · 等你", oaw_status.food_lines(food, detail=True))
        self.assertNotIn("  卡在哪：靜態：1 個高嚴重度旗標待你分流 · 等你", oaw_status.food_lines(food))


if __name__ == "__main__":
    unittest.main()
