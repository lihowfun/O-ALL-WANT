# 離線重算

在本資料夾執行；只需 Python 3.10+ standard library。所有輸入皆為既有本機檔案，沒有 API／model／EGM invocation。不要把 transcript、credential 或完整本機位置放進此資料夾。

由操作者在 shell 設定 `TRACE_ROOT`（含 x2、plan-review 的歷史 scratchpad）、`RECORDS_ROOT`（records 目錄）、`PRODUCT_ROOT`（含舊 product commits 的 checkout）、`H1_REVIEW_ROOT`（含 H1 v2 snapshots 的歷史 review 目錄）。這四個值不寫進報告或 JSON。可以依 `anatomy.json` 的短 locators 尋找資料；移動輸入後仍可使用同一套命令。

```sh
export PYTHONDONTWRITEBYTECODE=1
/usr/bin/python3 anatomy.py --scratch "$TRACE_ROOT" --records "$RECORDS_ROOT" > /dev/null
/usr/bin/python3 reconcile_claude.py --scratch "$TRACE_ROOT"
/usr/bin/python3 summarize.py --records "$RECORDS_ROOT" > summary.txt
/usr/bin/python3 finding_provenance.py --scratch "$TRACE_ROOT" --records "$RECORDS_ROOT"
/usr/bin/python3 sanitize_outputs.py
/usr/bin/python3 quality_extract.py --records "$RECORDS_ROOT" > /dev/null
/usr/bin/python3 event_summary.py --scratch "$TRACE_ROOT" > /dev/null
/usr/bin/python3 inspect_bank.py "$RECORDS_ROOT" > /dev/null
/usr/bin/python3 local_bank_inventory.py --h1-review "$H1_REVIEW_ROOT" > /dev/null
/usr/bin/python3 cost_design.py --product "$PRODUCT_ROOT" > /dev/null
/usr/bin/python3 render_tables.py
/usr/bin/python3 validate_outputs.py --scratch "$TRACE_ROOT" --records "$RECORDS_ROOT"
```

`anatomy.py` 先產生去重的 stream／rollout 數字；`reconcile_claude.py` 必須接著執行一次，補 completion 與 root turn 用量，並移除尚未修補的 interim summaries。不要對已修補 JSON 重複執行 reconciliation。最終 summaries 在 `summary.json`。所有 output 都寫在目前分析資料夾，請勿在其他 checkout 的 cwd 執行。

`finding_anchors.json` 是人工挑的 provenance anchors，不是新 rubric／grader。`finding_provenance.py` 僅將已有 final grades 對照到最早 S5 回報；regex 命中不代表自動判對錯。摘錄先移除本機路徑，raw line 仍可回查。`improve_anchors.py` 是本次縮窄 anchor 的操作紀錄；目前 JSON 已含其結果，不必再跑。

`TABLES.generated.md` 是 ANATOMY 數字附錄的來源；報告本文的解釋／限制是人工撰寫。重新產表後若數字改變，要同步檢查本文，不應默默覆寫歷史結論。`design-costs.json` 列 unit、within-cell 縮放、未量測 allowances、unique runs 與 1.3 multiplier；它不是新 pilot 的量測資料。各候選文件沿用 reference envelope 的條件與不可用項見 DESIGN。

其他 `inspect_*.py`、`trace_probe.py`、`probe_usage.py`、`rollout_probe.py`、`findings_probe.py` 是保留的唯讀探索腳本。它們可以將原始內容／本機位置印到終端；**不要把這些診斷輸出另存為公開 artifact**。本次保留的 JSON／Markdown 已由 privacy check 檢查。

`validation.json` 記錄實際平台、Python、來源 hash／總額核對數。這些檢查不能證明 host discovery、自然 bank 的真實品質或候選 trim 的效果。
