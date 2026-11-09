# X2 結果（2026-11-09）

## 結論

**兩格（Opus 5.5、Codex gpt-6.1-sol）都維持 N**：deep 工作的設計審查用一次原生、全新 context 的審查。判定由 Codex gpt-6.1-sol 照凍結規則做出，全文見 `results/DECISION.md`。敏感度分析也是 N。依 PREREG，D37 的暫時做法因此成為正式結論。使用者仍可把開關撥到「開」，強制跑 EGM。

為什麼是 N：

1. **偵測率碰到天花板。** 埋了 48 個缺陷，N 在兩格都抓到 47 個（97.9%）。R、E 最多多抓 1 個（+2.1 個百分點）。登記的「更好」門檻大約要多 11 個百分點，這次根本沒有這個空間。
2. **乾淨案例都有誤報。** 4 個沒有缺陷的案例上，每個替代組至少有一案被兩家評分者都判成誤報（沒根據的指控，或把刻意的設計當成缺陷）。依規則，這一條就足以否決。
3. **成本差很多。** 每次 E 的 logical token 中位數：Claude 是 N 的 27 倍（1.66M 對 61k），Codex 是 29 倍（2.93M 對 100k）。秒數是 12 倍和 7 倍。

這次不能說什麼：案例很小（每案 7k 字元以內），缺陷都經過核實、確定找得到，而審查者是高 effort 的強模型。N 已經抓到幾乎全部，E 的好處在這裡沒有空間顯現。所以這不代表 EGM 在大型、較難的設計文件上沒用，只代表在這類工作上，多花 27–29 倍的成本，看不出可量到的好處。

## 主要數字（20 個主分析案例，其中 16 案有缺陷，共 48 個缺陷）

| 格 | 組 | 偵測率 | 每份報告沒根據的指控（Opus / Codex 評分） | 乾淨案例誤報（兩家都判） | token 中位數 | 秒數中位數 |
|---|---|---|---|---|---|---|
| claude | N | 47/48 | 0.20 / 0.20 | registry | 60,599 | 64 |
| claude | R | 48/48 | 0.55 / 1.70 | registry、sessions、dashboard | 62,723 | 74 |
| claude | E | 48/48 | 0.45 / 1.65 | registry、supplier、sessions | 1,661,316 | 752 |
| codex | N | 47/48 | 0.05 / 0.05 | sessions | 100,408 | 75 |
| codex | R | 48/48 | 0.35 / 0.30 | registry、sessions、dashboard | 126,247 | 101 |
| codex | E | 47/48 | 0.05 / 0.05 | registry | 2,934,812 | 537 |

- 四個評分者（Opus、Codex、luna、Haiku）在偵測率上給的數字完全相同。
- 漏掉的那一個缺陷都是 `payouts` 的 M1（`HoldPolicy` 從未定義）。漏掉它的報告都有提到，只是沒有判成缺陷。
- 相對 N 的差和區間（Bonferroni 校正，floor 已套用）列在 `results/DECISION.md`。所有替代組的偵測下界都不大於 0。
- 「不比 N 差」（沒根據的指控）兩家都過的只有 claude X 和 codex E。Claude 格的 R、E 在 Codex 評分下，每份報告多出約 1.5 個沒根據的指控。
- 兩格的 N 本身各有一個乾淨案例誤報，所以維持 N 不等於 N 沒有誤報。

## 只描述、不進判定

- **有提到率**（抓到加只提到）：所有組都是 100%。
- **依出題家族**：兩格的 N 和 codex E 在 Opus 出的案例是 23/24，在 Codex 出的案例是 24/24；其他組兩邊都是 24/24。這次看不出偏向出題者自家的審查者。
- **events（重現 V5）**：兩格的 N 都是 2/4，另外 2 個只有提到；R 和 E 都是 4/4。V5「E 比 N 多抓」的方向重現了，但 R（一份清單）也做到，這一案的成本約是 E 的 1/20–1/24。只有一個案例，不進判定。
- **clean**：claude R 被判出 0 和 1 個沒根據的指控（Opus／Codex），codex R 兩家各 1 個，其他組都是 0。
- **E 有沒有照流程跑**：44 次 E（含 events、clean）都啟動了 9–11 個子 agent，沒有一次少於門檻。
  - Claude 的子 agent 名稱固定（egm-zoom-out、comprehension、design、structural、style、implementation-readiness、codebase-details）。有兩次例外：export 多開了一個通用的 `claude`，invites 多開了一個 `statusline-setup`。
  - Codex 的名稱每次自己取（initial_zoom、critic_design、readiness…），逐次清單在 `results/describe.json`。
  - 各階段的內容沒有檢查（PREREG 已寫明的限制）。
- **便宜評分者（D36，Figma I18）**：
  - 判「抓到沒有」：luna、Haiku 和 Opus、Codex 在 288 個缺陷項目上 100% 一致。但這裡大多是一定抓到的缺陷，所以一致很容易。
  - 判「沒根據的指控」：分歧比較大，每份報告的數字完全相同的比率如下表。Opus 和 Codex 彼此也只有 75%。

| 比較 | 每份報告指控數完全相同 | 平均差 |
|---|---|---|
| Opus 對 Codex | 75% | 0.38 |
| Haiku 對 Opus | 82% | 0.22 |
| Haiku 對 Codex | 66% | 0.54 |
| luna 對 Opus | 72% | 0.55 |
| luna 對 Codex | 62% | 0.64 |

便宜評分者拿來判「抓到沒有」可以。判「沒根據的指控」時，它們和兩家的差距，比兩家彼此的差距還大。

## 讀到工作區以外（PREREG 規定的掃描）

`x2_scan.py` 掃了 152 次作答（主分析 132 次、校準 18 次、2 次因用量上限不算數的作答），共 5,760 個工具呼叫，子 agent 的也包含在內。

- 沒有任何一次讀到 records、`spec.json` 或 `frozen/`。也沒有任何工作區以外的絕對路徑。
- Codex 有 42 次照慣例往上層目錄找 `AGENTS.md`。那些檔案都不存在，所以沒有讀到任何東西。
- 3 次 Codex 作答（N-registry、N-invites、R-invites）用 `find ..` 或 `rg .. -g AGENTS.md` 列出了隔壁 E 工作區 `AGENTS.md` 的檔名，但沒有讀內容。Codex 判定：記成偏離，保留，不排除。理由是檔名只透露組別和案例名稱，沒有缺陷、rubric 或其他組的報告。
- 下次改進：每次作答放在互不相鄰的資料夾，例如每次一個隨機路徑。

細節在 `results/scan-summary.json`。

## 偏離和事件

- **用量上限**：Claude 兩個程序在 E-dashboard、E-carts 碰到訂閱的 session 上限（06:30 重置）。那兩次照規則記成「不算數」（`results/claude-deviations.jsonl`），額度重置後從斷點續跑，各自以第 2 次嘗試完成。兩次不算數的作答用掉 1,702,598 token，已計入預算。
- **評分腳本結束碼 2**：四家評分都完整做完（各 132 份，沒有失敗）。結束碼來自最後找偏離檔的 `ls`，因為根本沒有偏離檔。
- **凍結後新增的分析工具**：`x2_scan.py`（掃描）和 `x2_describe.py`（描述統計）是跑完後才寫的。只做描述和掃描，不碰判定。判定只用凍結的 `x2_calibrate.py`、`x2_judge.py`，Codex 核對過它們和 4d7becb 逐位元組相同。
- **Codex 的疑點**（給 owner，原文在 `results/DECISION.md`）：
  1. 天花板：維持 N 是規則的回退，不能推論到大型文件。
  2. 指控下限的敏感度：Codex 仍認為借來的下限不該豁免。全部乘 1.5 時，codex E 的指控門檻也會失敗（上界 0.62）。不影響這次判定。
  3. 流程和核實的證據較弱：只看審查者啟動數，核實沒有綁定內容 digest。
  4. 判定程式沒有自己重算提示雜湊和案例 digest，Codex 另外核過。

## 花費

- **Claude**（D36 上限 60M）：合計 47,237,230。
  - 凍結前 2,533,567。
  - 校準 522,781。
  - 主分析 38,821,743。
  - 不算數的作答 1,702,598。
  - Opus 評分 1,282,243。
  - Haiku 評分 2,374,298。
- **Codex**（ChatGPT 方案，不計入上限，另外記錄）：作答和評分合計 75,616,387。
  - 校準 944,117。
  - 主分析 68,909,071。
  - Codex 評分 2,968,832。
  - luna 評分 2,794,367。
  - 另有判定 1,240,587（輸入 1,223,950，其中快取 1,144,448；輸出 16,637）。
- 兩家的 token 計法不同，不能互相比較。

## 檔案

`results/` 存放以下檔案，本機路徑都已遮蔽。原始 transcript 和工作區只留在本機。

- **作答列**：`claude-rows.jsonl`、`codex-rows.jsonl`、`cal-*-rows.jsonl`。報告內容沒有改動，`report_sha256` 綁定仍然成立。
- **評分**：`main-grades-*.jsonl`、`cal-grades-*.jsonl`。
- **Codex 判定**：
  - `floor-final.json`、`judge.json`：凍結程式的輸出。
  - `integrity.json`、`sensitivity.json`、`judge-descriptive.json`：Codex 的核對和補充明細。
  - `DECISION.md`。
- **描述和掃描**：`describe.json`、`scan-summary.json`。
