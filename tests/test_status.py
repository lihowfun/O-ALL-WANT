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
        self.assertIn("正在消化：egm-review · A/B 42/90 · 齊平", self.run_cli())
        status["updated_at"] = (now - timedelta(minutes=30)).isoformat()
        self.write(".oaw/catalog/status.json", status)
        self.assertIn("可能已中斷", self.run_cli())
        status.update(stage="done", verdict_so_far="evolved")
        self.write(".oaw/catalog/status.json", status)
        text = self.run_cli()
        self.assertIn("完成 42/90 · 進化", text)
        self.assertNotIn("可能已中斷", text)


if __name__ == "__main__":
    unittest.main()
