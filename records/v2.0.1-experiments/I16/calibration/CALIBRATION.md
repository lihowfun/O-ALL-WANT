# I16 校準結果（2026-11-09，主分析之前）

照 `PREREG.md`「校準和天花板」跑：每格只跑 N，6 條缺陷流程各 3 次，機械重播後由兩家評分。spec sha256 `08c7cefa…`，和凍結版相同。

## 天花板：沒有

天花板的定義是 N 在兩格、兩家評分、3 次都抓到。沒有任何一條流程符合，所以不換題，主分析用凍結的 12 條流程。

偵測次數（3 次中抓到幾次，Opus 評分 / Codex 評分）：

| 流程 | 類別 | Claude 格 | Codex 格 |
|---|---|---|---|
| manage-only-own-skills | B8 嚴重 | 3 / 3 | 0 / 0 |
| estimate-review-budget | B2 | 1 / 1 | 0 / 0 |
| review-saved-plan | B4 | 3 / 3 | 1 / 1 |
| find-project-code | B1 | 1 / 1 | 0 / 0 |
| remove-bundled-skill | B3 嚴重 | 0 / 0 | 0 / 0 |
| annotate-project-topic | B6 | 3 / 3 | 2 / 2 |

- 兩家評分在 36 份報告的「抓到」上完全一致。
- Claude 格有 3 條在本格滿分，但 Codex 格沒有，所以都不算天花板。
- 每份報告「沒根據的回報」平均：Claude 格 2.56（Opus 評）/ 2.17（Codex 評），Codex 格 0.33 / 0.11。

## 下限（`floor-final.json`）

| 格 | 評分 | 偵測 | 沒根據的回報 |
|---|---|---|---|
| Claude | Opus | 0.333 | 1.054 |
| Claude | Codex | 0.333 | 0.850 |
| Codex | Opus | 0.333 | 0.527 |
| Codex | Codex | 0.333 | 0.615（借來的 X2 值，實測 0.333 較低） |

偵測下限都是實測值，比借來的 0.132 高。

## 紀錄

- 36 次作答都正常結束，Claude 計費 apiKeySource none，Codex 用 ChatGPT 方案。評分 72 筆全部有效，評分者工具呼叫數都是 0。
- 黑箱：3 次作答各有 1 個讀原始碼的工具呼叫（Claude 格 manage-only-own-skills 第 2 次；Codex 格 remove-bundled-skill 第 1 次、annotate-project-topic 第 3 次）。校準不進主分析，只記下。
- 輸入摘要（sha256）：`floor-final.json` 的 `inputs` 欄記了作答列和兩份評分。原始作答、重播和評分事件串留在本機，不推上 records。

## 成本和預算重估

| 項目 | Claude logical token | Codex logical token |
|---|---|---|
| 校準作答 18 次 | 13,862,593（平均 0.77M） | 5,486,623（平均 0.30M） |
| 校準評分 | 605,475 | 700,426 |

- Claude 單次作答是試跑估計（0.44M）的 1.75 倍。最貴的是 remove-bundled-skill 和 manage-only-own-skills，每次 1.0–1.6M。
- Claude 累計約 23.2M（D35 上限 30M）。
- 主分析 Claude 格 48 次（12 流程 × N、C、D、F），以每次 0.8M 估約 38M，評分約 2M。
- 完整做完 Claude 累計估約 63M，可能範圍 55–70M。PREREG 原本估的 44M 不夠，所以要重新請 owner 決定。
- Codex 格的主分析不佔 Claude 上限，先開跑。評分要等兩格作答都完成才開始，因為評分順序要跨格打亂。
