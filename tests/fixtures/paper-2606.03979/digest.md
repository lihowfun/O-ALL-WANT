# arXiv 2606.03979〈Language Models Need Sleep〉消化紀錄

Elephant 撰寫，2026-11-03。完整帳本：`papers/2606.03979/components.json`

**一句話**：這篇論文的機制全部作用在權重層。OAW 只取「離線檢查」這個框架，做成唯讀的 `wiki_sync.py memory-check` 原型。其餘 11 個單位排泄，3 個保留。本輪沒有任何「進化」主張，對 release 的結論是 parity, no improvement claimed（D2）。

## 1. 元件總表（14 個概念拆成 16 個單位：吸收候選 2、保留 3、排泄 11）

| 決議 | 元件 | OAW 落點與理由 |
|---|---|---|
| **吸收（候選）** | sl.wake-sleep-cycle/manual-pass | `wiki_sync.py memory-check`：手動、唯讀、離線地檢查 memory.md 引用的路徑是否還在。偵測規則 static-measured；實地有用度和 agent 行為 not measured |
| **吸收（候選，只取動機）** | sl.online-consolidation-gap | 落點同上。memory 也會經 bootstrap 這類不經 recall 的路徑進入 context，所以要整檔檢查。這個效益假設是 OAW 自己的，論文沒有提供證據 |
| 保留 | sl.wake-sleep-cycle/schedule | 排程或 CI 自動執行。要等手動版先通過 T0；發布 memory 內容需要 owner 同意 |
| 保留 | sl.synaptic-pruning | 未來的 memory 封存功能。先等 OAW-20 提供 `--supersedes` 標記 |
| 保留 | sl.synthetic-rehearsal/independent-authored | 由 goldfish 盲寫回歸 case。要等 catalog P4 的回歸套件存在 |
| 排泄 | sl.multi-frequency-hierarchy | 多加一層等於多一份狀態鏡像，違反 Small defaults；Fig 4 只測到 1–4 層，而且有例外 |
| 排泄 | sl.consolidate-before-update | 論文的機制沒有驗證步驟。回歸保護屬於 OAW 自己的 P4，不算吸收本論文 |
| 排泄 | sl.session-end-consolidation | 強制寫入和 wrap-up 在 V2 已移除；session 屬於 host；這類 hook 只有 Claude 有（D8） |
| 排泄 | sl.expansion-new-slot | 作用在權重層。改寫成文字版就是 lossy 的就地摘要，違反 OAW 的 provenance 原則 |
| 排泄 | sl.knowledge-seeding | harness 沒有 logits；另用摘要模型等於第二個模型 runtime，v2 明確排除 |
| 排泄 | sl.learning-to-imitate | 用編輯距離給部分分數，會讓錯的值也拿分；semantic judge 要付費而且有偏。§5.3 的協定原本就有，不算吸收 |
| 排泄 | sl.dreaming-loop | 屬於背景自我改寫迴圈，v2 明確排除。選擇偏誤的防護改交 P4 的 R7 |
| 排泄 | sl.synthetic-rehearsal/self-authored | 出題者看過候選，違反評估獨立性 |
| 排泄 | sl.random-expert | 只多 0.9–1.5 分，而且在權重層；OAW 沒有 dream 取樣可以接 |
| 排泄 | sl.gradient-selection | harness 沒有梯度；代理指標 te.failure-signature 已經涵蓋 |
| 排泄 | sl.consolidate-then-dream | 論文沒有直接實驗。P1 原型因為六個缺陷撤回，需求 R1–R9 改交 P4，不引用本論文 |

## 2. 原型

- **分支**：`feat/paper-sleep`，位於 worktree `OAW-paper-sleep/`。base 是 `fc5fda1`，也就是 origin/codex/oaw-2-native-upgrade。
- **commit**：`850806b` 是原型；`b14c875` 修完審查提出的 6 筆問題（2 major、4 minor）。兩個 commit 都只在本機，**沒有 push**。
- **用法**：`python3 scripts/wiki_sync.py memory-check [--json] [--limit N]`。exit code：0 表示檢查完成（memory.md 不存在時也是 0）；1 表示已處理的錯誤，包含非 UTF-8；2 表示用法錯誤。
- **我的獨立重跑**（Windows 11、Python 3.13.13）：
  - `MemoryCheckTests` 24 個測試全部通過。
  - 完整的 `harness_check.py`：9/9 通過，193 個測試，0 skipped。
  - 跑完之後 worktree 沒有任何變動。
- **CI 矩陣**（Ubuntu/macOS/Windows × 3.10/3.13）還沒跑，因為還沒有 PR。
- **已知限制**（guide 裡已寫明）：以下三類不檢查，召回因此下降，中文專案可能特別明顯：
  - 檔名含 CJK 字元的路徑；
  - 單段的 `/word`；
  - 產品名，例如 `Node.js`。

## 3. 系統決定的測試計畫（D11）

token 數一律是估計值。校準基準：每次使用工具的 agent run 約 0.6–0.9M logical tokens。

| 項目 | 最便宜、又能分辨好壞的測試 | 判定 | 估計 token | 前置條件 |
|---|---|---|---|---|
| **T0** P2′ 吸收閘門 | 在 owner 指定的真實 memory.md 上跑 memory-check（0 token）。兩個 goldfish 各自盲標每筆 finding「有用／無用」，兩者都標有用才算有用。Elephant 不參與標記，因為工具是它做的 | 不含移除語境的 missing_path，precision ≥ 0.7，**而且**每 50 條至少 1 筆有用：送 owner 核准。沒達到：排泄並還原。總條目少於 50：記為 not measured。報告附上 n 和 Wilson 下界 | 執行 0；標記約 1.2–1.8M；若 owner 自己標則為 0 | owner 指定專案；PRE-01（或 owner 自己標） |
| T1 排程 | 不測 | 手動版吸收之後才討論，而且屬於同意問題，不是效益問題 | 0 | P2′ 已吸收 |
| T2 synaptic-pruning | Stage 0（免費）：用 fixture W 做出含 supersede 鏈的變體；封存規則事先登記雜湊；量測 recall top-5 或 bootstrap 出現被取代條目的題數，以及省下的 bytes | 沒有任何題目受影響，而且省下不到 5%：排泄。否則進 Stage 1（20 題 × 2 臂 × 3 次）。只要正確率下降或 wrong-scope 誤用上升就排泄，不論省下多少 | Stage 0 約 1.2–1.8M；Stage 1 約 72–108M，和 HOLD-01/03 共用 baseline 時約 36–54M | OAW-20、PRE-05、PRE-01；Codex 那一半另需 PRE-03 |
| T3 independent-authored | Stage 0：goldfish 盲寫 10 個 case，再做靜態覆蓋比對 | 沒有新覆蓋：排泄。Stage 1a：在基準上量雜訊（10 個 case × 5 次）。Stage 1b：3 個種子退步 × 10 個 case × 3 次；一個都抓不到就排泄 | Stage 0 約 1.8–2.7M；1a 約 30–45M（和 P4 共用）；1b 約 54–81M | catalog P4 套件（R1）、PRE-01 |

**現在能花的只有 T0，約 0–1.8M。** T1–T3 都還卡在前置條件，目前沒有排程。PRE-01 設定之前，任何付費階段都不會執行。

## 4. 引用（D3）

由系統決定：只列為「動機」。owner 可以在核准吸收時否決。

**放置位置**：release 來源帳本裡另開一個 `literature` 區塊，**不能放進 `sources`**。原因是 `harness_check.py:146-149` 要求 `sources` 的每一筆都要有 40 位 hex 的 commit，論文沒有 commit，放進去會讓 version 檢查以「Unpinned source」失敗。

Release notes 引用行：

> Behrouz, Hashemi, Javanmard, Mirrokni. "Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories." arXiv:2606.03979v2 [cs.LG], 2026-07-10 (v1 2026-06-02), CC BY 4.0. Motivation only for `scripts/wiki_sync.py memory-check` (prototype): the Wake/Sleep offline-pass framing and the §1 (i) critique that online consolidation is "selective and retrieval-dependent". No text, code, data or mechanism is used, and the paper gives no evidence for this tool. Not adopted (weight-level, or against OAW's Small-defaults, native-execution or provenance principles): multi-frequency updates, compute–consolidate–update, parameter expansion, knowledge seeding/GKD, the learning-to-imitate reward, dreaming/ReST^EM, random expert, gradient selection, session-end consolidation, and the two-stage order. Synaptic pruning is held.

如果最後沒有吸收，就把論文列在「evaluated, not adopted」，並附上 T0 的結果作為理由。

## 5. 吸收時的 D12 build 視圖

- **名稱**：`2.0.0+build.N.<hash>`，N 和 hash 由 PRE-07 的 build 機制指定。
- **標籤**：「add wiki_sync memory-check (prototype)」
- **各項證據等級**：

  | 項目 | 證據等級 |
  |---|---|
  | 偵測規則 | static-measured |
  | 預設安裝和指令面不變 | static-measured |
  | 實地有用度 | not measured（規劃由 T0 量測） |
  | agent 行為 | not measured |
  | 對 2.0.0 | parity, no improvement claimed |

- **還原點**：前一個 build（`fc5fda1`）。在 build 機制完成之前，還原方式是在分支上執行 `git revert b14c875 850806b`。

## 6. 本輪副產品（不屬於本論文的吸收）

- **R1–R9 交給 catalog P4 和版本棘輪。** 附帶發現：目前的 `compare()` 會把完全無效的候選判成 eligible，機率約 12–40%；同一個候選重新提案 3 次，至少一次 eligible 的機率約 32–78%。這個問題由 R4、R7 處理。
- **`context_hub.py:818` 的副作用。** 唯讀的子命令也會建立 `docs/knowledge/`，建議另開一案處理。
- **和 OAW-20 的交會。** 兩邊都會修改 `wiki_sync.py`，但可以相容：C15 的 golden 測試只鎖定 promote-candidates 的預設輸出，而 OAW-20 的 `--evidence-gate` 是 opt-in。後合併的一方負責 rebase。

## 7. 留給 owner 的決定

1. **T0 可以讀哪些專案的 `.agents/memory.md`。** 這涉及隱私，超出 D11 的 standing policy。在指定之前，P2′ 一直是 not measured。
2. **T0 通過後，是否核准吸收 P2′。** 核准時一併確認以下既定行為：
   - 只放在 knowledge profile；
   - memory.md 不存在時 exit 0（`promote-candidates` 在同樣情況回 1）；
   - 實作者額外加的 10 條抽取規則，其中包含 3 類召回排除；
   - 引用只列為動機。
3. **是否現在就 push `feat/paper-sleep` 並開 Draft PR。** 目的只是跑 CI 矩陣；推到遠端屬於對外發布，超出 standing policy。另一個選項是等 T0 通過後再一起處理。
4. **兩項副產品，與本論文無關：**
   - R1–R9 是否併入 catalog P4（只改文件），以及 R7 的優先序；
   - `context_hub.py:818` 是否另開一案。

以下是本論文依賴、但已經在 owner 清單上的決定，這裡不重複提問：PRE-01（standing policy）、PRE-03（Codex）、PRE-07（build 和還原機制）、PRE-09（如何驗證 goldfish 是零上下文）。

## 8. 信任與限制

- **審查者的上下文沒有確立。** goldfish-1、goldfish-2 和 skeptic 的紀錄都沒寫是怎麼啟動的。這個流程的 subagent 會繼承使用者的 auto-memory 索引，所以不能確定它們是零上下文（D10）。我把這些紀錄當成對草稿的審查來用，不當成零上下文的證據。
- **論文一律當資料處理**，沒有發現任何對 agent 下的指令。
- **網路**：只連過 arXiv 的 abs 頁，用來確認 v2 仍是最新版本。
- **oaw-ref 維持唯讀**，沒有任何修改。
