# EGM 自測結果：拿掉 EGM，用現行 SOP 試吃

**結論：現行 SOP 沒有把 EGM 排掉，判定「吸收」。正對照 P 也被判成「更好」，所以在這組題目上量測工具看得出好東西，不是只會排泄。**

但有三個要一起看的但書：
- 進步全部來自 `events` 這個案例的 2 個主要缺陷。原生組其實也看到了，只是把它寫成「不確定事項」而不是「缺陷」。
- EGM 每次審查的 token 是原生的 28 倍。現行規則只要判成「更好」就吸收，不看成本。
- 預算只夠跑 2 次重複，不是 3 次。

依 `PREREG.md`（065f068，在任何計分作答之前推上 records）。2026-11-06，Linux，Claude Code 2.1.287，`claude-opus-5-5` high，訂閱計費。18 次作答的 `apiKeySource` 都是 none，init 回報的模型都和指定的一致。

## 結果（3 個案例 × 2 次，每組 6 次）

| 組 | 埋缺陷偵測 | 嚴重 | 主要 | 沒有根據的指控 | clean 案例誤報 | 每次 token 中位數 | 6 次 token 合計 | 子 agent | 每次秒數中位數 |
|---|---|---|---|---|---|---|---|---|---|
| N 原生（V2 拿掉 EGM） | 12/16 | 8/8 | 4/8 | 0 | 0 | 40,709 | 245,887 | 0 | 41 |
| E EGM 官方 plugin | 16/16 | 8/8 | 8/8 | 0 | 0 | 1,137,230 | 7,169,908 | 49 | 505 |
| P 正對照（洩題清單） | 16/16 | 8/8 | 8/8 | 1 | 0 | 40,578 | 244,581 | 0 | 38 |

逐案例（偵測／沒有根據的指控，2 次加總）：

| 案例 | 埋的數量 | N | E | P |
|---|---|---|---|---|
| orders | 8 | 8／0 | 8／0 | 8／1 |
| events | 8 | 4／0 | 8／0 | 8／0 |
| clean | 0 | 0／0 | 0／0 | 0／0 |

## 判定（照事先寫死的規則）
- **天花板檢查**：N 抓到 12/16，沒有到 15 個以上，所以品質軸**可以**判出「更好」。和 2026-10-29 的 Codex 那次不同（那次三組都是滿分）。
- **E：更好**。偵測比 N 多 4 個，嚴重缺陷沒有少，沒有根據的指控一樣是 0。
  - 現行試吃規則：**吸收（absorb）**。
  - D21 B 級字面（齊平以上才吸收）：**可以出貨**。
- **P：更好**。偵測多 4 個，嚴重缺陷沒有少。
  - 現行試吃規則：**吸收**。
  - D21 B 級字面：**不能出貨**。P 有 1 個沒有根據的指控，N 是 0，不算「齊平」。

兩種讀法在 E 上一致，在 P 上不一致：D21 對「沒有根據的指控」是零容忍，多 1 個就不出貨；現行試吃規則要多 3 個才算變差。

回答 owner 的問題：照 PREREG 寫好的對應，「E 判成更好 → 現行 SOP 能吸收 EGM」。這次沒有「都被排泄」。

## 進步從哪裡來（讀報告看到的，不計分）
- 多出來的 4 個偵測，全部是 `events` 的兩個主要缺陷，兩次都一樣：「Flux shim 沒有定義」（M1）和「實作計畫沒有可執行的範圍和完成條件」（M2）。
- 原生兩次都看到了 `design.md:16` 的「Flux shim」和「production ready」沒有定義，但寫在 `uncertainties` 裡。凍結的評分規則規定不確定事項不算偵測，所以 N 沒拿到分。
- E 的「implementation readiness」階段（第 9 階段）專門檢查計畫能不能動手做，所以把它列成缺陷。P 的清單直接點名「每個元件都要有定義、計畫要有範圍和完成條件」。
- 所以這不是「原生看不到、EGM 看得到」，而是 **EGM 把計畫的缺口當成缺陷來報**。這是 EGM 宣稱的用途，rubric 也這樣算；但差距只有一類缺陷、一個案例。
- `orders` 三組都全中。P 在 `orders` 第 2 次多出一個「計畫沒有完成條件」的指控，評分者判定這是拿範本要求套在不需要的地方，算沒有根據。洩題清單讓 P 在不該報的地方也報了，這是正對照預期會有的副作用。
- `clean` 三組都沒有誤報。E 的不確定事項最多（每次 11–12 個，N 8–9、P 6–7）。

## 機制有沒有真的跑
- E 每次的 init 都有 `egm` plugin 和 `egm:egm-review` 指令。6 次共開了 49 個真的子 agent，都是 Opus 5.5：
  - `egm-zoom-out` 12、`egm-style` 10、`egm-comprehension` 6、`egm-design` 6、`egm-structural` 6、`egm-implementation-readiness` 4、`egm-codebase-details` 4，另外有 1 次一般子 agent。
  - `clean` 的設計沒有「Implementation Plan」段落，EGM 依它自己的規則只跑第 5–8 階段，所以每次 6 個子 agent。
- E 每次都寫出五個階段的報告（`clean` 是四個）、合併報告和 `review_out/report.json`。三組都沒有被拒的權限、沒有改到原始檔。
- N、P 的 init 沒有 `egm`，也沒有讀到任何 EGM 路徑（污染 0）。N 和 P 都沒有開子 agent。
- 每一組的 init 都另外有 4 個主機內建的 `cc-plugin-*`，三組相同。

## 拿掉 EGM 時發現的事（給 OAW 本身）
- 兩條支援的移除路線都沒把 EGM 拿乾淨：
  - 一條是安裝時只選 `oaw-evidence`，另一條是 `catalog.py remove egm --apply`（在試吃區先試過）。
  - 兩條都會留下 `.oaw/integrations/egm`（66 個檔案的執行檔）。
  - `AGENTS.md` 也還寫著「OAW v2 includes the complete pinned EGM runtime」。
  - `catalog.py remove egm` 另外在 `.oaw/backups/` 留一份 EGM skill 的備份（這是還原點，預期中）。
- 這次手動刪掉 `.oaw/integrations/egm`。D6 說「任何 skill（含 EGM）都能移除」，但移除後的政策文字和執行檔都沒有跟著變。這要另外修。

## 不能這樣解讀
- **不能說 EGM 一般而言比原生好。** 只有 3 個案例、2 次重複、每份報告 1 位評分者。評分者和作答者都是 Opus 5.5（AI 評 AI）。進步集中在一個案例的一類缺陷。
- **不能忽略成本。** 每次 token 是原生的 28 倍，時間約 12 倍。現行試吃規則判成「更好」就吸收，不問值不值得。要不要為了「多報 2 個計畫缺口」付 28 倍，規則裡沒有答案。
- 不能和 2026-10-29 的 Codex 結果並排比：host、模型、評分方式（那次 2 位評分者加仲裁）都不同。
- P 洩題，只用來驗證工具，不代表任何真實食物。
- JSON 報告最多 900 字，E 要把五個階段濃縮進去；E 的合併報告原文留在本機，沒有評分。

## 偏差
- **只跑了 2 次重複。** 原本預計 3 次。第 3 次 `orders` 開始前，預算守門停下：已花 7,951,660，下一組估 1,518,679，會超過合計上限 9.0M。照 PREREG，只比完整的 6 組（3 個案例 × 2 次）。
- **一次 E 作答被用量上限切斷。** 第 1 次的 `orders` E，跑了 248 秒、291,284 token 後，碰到訂閱的 5 小時上限。照 PREREG，這次不算作答、記在 `out/deviations.jsonl`，runner 乾淨停下。owner 升級方案後（15:19）從同一次接著跑。這 291,284 token 算進預算。
- **試跑第 1 次也被同一個上限切斷**（1,054,525 token），第 2 次才完整通過（PREREG 已記）。
- 評分沒有碰到上限，`grades.jsonl.deviations` 沒有產生。
- 分組上限（E 7.0M、N 1.0M、P 1.0M）在 PREREG 推上之前改成合計 9.0M，PREREG 有寫明原因。

## 花費
- 食物（EGM 自測，D13 上限 10M）：作答 7,660,376（E 7,169,908、N 245,887、P 244,581），加上被切斷的 E 291,284，共 **7,951,660**。
- 消化開銷（2026-11-06 這一輪）：試跑 1,987,477（第 1 次被切斷 1,054,525，第 2 次 932,952），盲評 113,361（18 份），共 2,100,838。

## 使用者層的 plugin 狀態
- 已還原。四個 E 工作區（3 個案例和試跑）都以 project scope 解除安裝，移除 `egm` marketplace，刪掉安裝時建立的 plugin cache。
- 之後 `installed_plugins.json`、`known_marketplaces.json`、`settings.json`、`settings.local.json` 的 sha256 都和安裝前一樣，`claude plugin list` 從 HOME 看出去也一樣（`proof.json` 的 `restored` 全部 true）。
- `~/.claude.json` 的 `pluginUsage` 會隨每個 session 變（其他 plugin 的使用計數），裡面沒有 egm。

## 檔案
- `out/rows.jsonl`：每次的報告、工具次數、子 agent 種類、token、init 的 plugin 清單（路徑已遮掉；原始 stream-json 和 E 的階段報告留在本機）。
- `out/grades.jsonl`：盲評結果。
- `out/summary.json`：彙總和兩種讀法的判定。
- `out/deviations.jsonl`：被用量上限切斷的那一次。
- `proof.json`：使用者層 plugin 狀態的前後對照。
- `tasting.json`：`oaw-tasting/1` 紀錄，食物 id `egm-selftest`。`egm` 在 catalog 是保留字，所以沒有記進帳本。
