# O-ALL-WANT (OAW)

給 coding agents 的專案證據與原生 skills 套件。**v2.0.0 目前是 PR 中的提案版本，尚未發布 release。**

[English](README.md) · [升級指南](docs/UPGRADING.md) · [CLI](docs/CLI_Reference.md) · [執行計畫](docs/plans/v2.0.0-execution.md)

OAW 保存程式碼無法完整解釋的專案知識：決策原因、外部限制、實驗與來源證據。agent loop、session、compaction、個人記憶、權限與 skills discovery 交給 Claude Code、Codex 或你選擇的 host。

## 最小安裝

需要 Python 3.10+，runtime 只用標準函式庫。在 OAW checkout 執行：

```bash
python3 scripts/oaw.py init --target /path/to/project
python3 scripts/oaw.py doctor --target /path/to/project
```

預設安裝到 Codex skill 目錄。加 `--host claude` 或 `--host both`，即可安裝 Claude Code 或兩者的原生 skill folders。

預設只安裝五個 framework files：短 AGENTS.md、Claude 相容 import、一個原生 evidence skill、Context Hub 與共用 helper。不建立 memory、不塞 placeholder 架構與 roadmap、不改專案 VERSION.json，也沒有每次結束都要做的強制流程。遇到既有不同內容會保留並停止 init。

既有 Bash 入口仍可用；在目標專案執行 `bash /path/to/O-ALL-WANT/install.sh`。

```bash
# 選配 wiki renderer 與 wiki skill
python3 scripts/oaw.py init --target /path/to/project --profile knowledge

# 選配有證據的改善流程，不會啟動背景 agent
python3 scripts/oaw.py init --target /path/to/project --with-improve
```

選配功能會累加，不會隱含降級。[最小範例](example/minimal-project/) · [knowledge 與 improvement 範例](example/public-hybrid-demo/)

## 從 v1 升級

```bash
python3 scripts/oaw.py migrate --target /path/to/project          # 只預覽
python3 scripts/oaw.py migrate --target /path/to/project --apply  # 備份後套用
```

只有可識別且未客製的 framework 檔能直接更新。客製 policy／skill 衝突會產生 proposal；既有 memory、knowledge、raw notes、AI_CONTEXT.md、ROADMAP.md、專案 VERSION.json 都保留。未改動的舊 flat skills／adapters 可移入可回復的備份。衝突未解決時不會宣稱升級完成。細節見 [UPGRADING](docs/UPGRADING.md)。

## 在需要時使用證據

在已安裝的專案執行：

```bash
python3 scripts/context_hub.py memory recall "快取決策" --json --max-chars 12000
python3 scripts/context_hub.py memory add "[DECISION] 保留本機快取 — 證據：docs/experiment.md"
```

recall 有輸出上限、來源位置、截斷與分頁。專案筆記是需要比對目前 code／來源的資訊，不會自動成為更高權限的指令。只保存會影響未來工作的資訊，個人記憶仍由 host 管理。

knowledge profile 提供 `python3 scripts/wiki_sync.py refresh Topic` 與 `lint`。它是 deterministic renderer，不是 LLM 自動摘要或背景知識服務。

## 改善 self-improving

選配流程改為「假設＋候選 diff → 固定案例 A/B → 明確採用或拒絕」。工具會核對 model／effort、host／version、環境、base snapshot、cases、重複次數與 evidence hashes，拒絕品質退步、過大的資源退步、證據缺失或不匹配的 runs。accept 只記錄決定，不會自動套用 patch。

[Self-improvement 指南](docs/SELF_IMPROVEMENT.md) · [Ablation contract](evals/native-ablation/spec.json)

淘汰預設 memory nudge、手動 skills 計數、每三步就 skill-review、每個失敗寫永久記憶，以及強制四段報告。沒有可重用收穫的任務可以直接結束。

## 原生整合與驗證範圍

採用 `<skill>/SKILL.md` 格式；`--host codex` 安裝到 `.agents/skills`，`--host claude` 到 `.claude/skills`，`--host both` 由同一份來源產生兩種目錄。OAW 不暗改 host settings；doctor 將支援能力與是否啟用分開說明。見 [Skill Guide](docs/Skill_Guide.md)。

設計以目前 Claude Code／Opus 5.5 與 Codex／GPT-6.1 Sol 為基準，不把模型名稱寫死在工具裡。本地 schema 測試不等於兩個 host 的實機載入驗證，也尚未宣稱模型 A/B 收益。舊版 86–87% 是「挑選 Markdown」與「全讀」的比較，屬歷史示例。

```bash
python3 scripts/harness_check.py
python3 scripts/harness_check.py --json
```

完整變更見 [CHANGELOG](CHANGELOG.md)，來源沿革見 [Architecture Origins](docs/Architecture_Origins.md)。MIT License。
