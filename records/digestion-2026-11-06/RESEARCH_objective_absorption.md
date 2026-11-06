# 會不會是自嗨？客觀吸收的研究與對照（2026-11-06）

owner 問：「很多很猛的 skills 幾千幾萬 star 都被判定沒有值得吸收的地方……我比較怕一切都是自嗨，需要有更嚴謹的效率吸收，客觀評估別人優點缺點以及值得吸收的地方，不要夜郎自大；也要判斷吸收後 harness 會新增哪方面能力、token 和時間會多多少；需要深入思考時用某版、需要 light 時用另一版，怎樣切換更順，而不是都要 EGM 審半天。」

研究方法：deep-research workflow，108 個 agent。
- 讀了 26 個來源，抽出 130 條可以被推翻的說法。
- 挑 25 條，每條由 3 個驗證者對抗式檢查：21 條成立、4 條被否決。
- 兩組最關鍵的數字（KTH 的 SWE-bench 變異研究、Crupi 的 LLM 評程式研究），我另外回原文核對過，都正確。

## 結論
**目前的判決不能證明 OAW 比較好，也不能證明是自嗨。能確定的只有一件事：我們的測驗解析度太低，分不出「沒幫助」和「沒測出來」。**

- 4–12 題、每題 1–3 次的 A/B，只看得出很大的差距。用研究裡的公式外推到我們的規模，粗估要差 27–60 個百分點以上才看得出來；這是外推，不是實測。
- 所以過去的「沒證明比原生好」，正確讀法是**「未定」**，不是「不如原生」或「一樣」。
- EGM 的「更好」也要用同一把尺：它多抓的 4 個缺陷全來自同一個案例，只評了一次，同樣是「未定」。
- 我們的評分有已知偏差：用 Opus 評 Opus 的答案（同一家族的評分者偏好自己的風格），而且只評一次、只用一種順序。
- 別人的宣稱也要用同一把尺，不能只懷疑別人。
  - graphify 宣稱在 ERPNext 上 82.0% 對 70.8%。它的對照組是只有 grep、read、list 的陽春 agent；我們的對照組是完整的 Claude Code。
  - 兩邊的題目和評分者都不同，數字不能並排比。但對照組強弱不同，是它的進步沒有出現在我們測驗裡的一個合理原因。
  - codegraph 的對照組是 headless Claude Code，比較接近我們的設定；但它測的是超大 repo 的單題架構問答，我們沒測這種題。

## 一個差點被我們自己忽略的「夜郎自大」
D29 重判時，OAW 自己的 `code_index.py` 判「可選用」，codegraph 判「排掉」。差別只在 token：
- `code_index.py` 最多是原生的 1.40 倍，codegraph 最多 1.72 倍，剛好落在 1.5 倍門檻的兩邊。
- 同一組在同一題重複跑，token 本來就會差 8%–24%。所以這兩個其實在雜訊範圍內差不多。
- 如實的說法：兩者能力都未定，codegraph 稍貴；不能說 OAW 的比較好。

## 每樣食物：會加什麼能力、測到什麼、沒測到什麼、成本

| 食物 | 想加的能力 | 我們測到的 | 沒測到的（它的主戰場） | 成本 | D29 | 誠實的讀法 |
|---|---|---|---|---|---|---|
| graphify | 程式碼地圖；文件和論文的多模態圖；視覺化 | ERPNext 程式問答：品質未定 | 文件和論文的圖、視覺化、群組命名 | token 1.22–1.63 倍；pip 套件、hook | 排掉 | 因成本不採用，能力未定 |
| codegraph | 程式碼導航、影響範圍、先塞好相關程式碼 | 品質未定；工具呼叫少 44%–70% | 它自己的題型：超大 repo（VS Code 1.1 萬檔）上的單題架構問答；邊改邊同步 | token 1.20–1.72 倍；每個 session 開頭多約 8k context；Node、MCP | 排掉 | 因成本不採用，能力未定 |
| TokenEconomizer | 跨 session 學習，越用越省 | 12 個 session：品質相同（隱藏測試），成本 1.01 倍；最後 4 個 session 省 13.9%（不顯著） | 30 個 session 以上的長串流 | 和原生相當 | 可選用 | 能力未定，不貴 |
| court-skill | 對決策做正反辯論 | 5 個案例：品質未定（只評一次） | 原生會附和的情境（我們的案例裡原生沒有附和） | 約 94 倍 | 排掉 | 因成本不採用 |
| claude-mem | 跨 session 記憶 | 沒測（卡在你的長效 token） | 全部 | — | — | 沒有判定 |
| EGM（自測） | 設計審查，用全新視角的 reviewer | 多抓 4 個計畫缺陷（同一個案例，原生其實寫成不確定事項） | 更多案例、多個 seed | 28 倍 | 可選用 | 能力未定，很貴；V2 本來就是手動叫用 |
| OAW `code_index.py`（自己的） | 程式碼導航（`callers`） | 品質未定；工具呼叫少 34%–52%（Opus 4.8 沒少） | 大 repo 的架構題 | token 0.90–1.40 倍 | 可選用 | 和 codegraph 在雜訊內差不多 |

## 研究建議、對我們的意思、我接下來怎麼做

| 研究結論（來源） | 對 OAW 的意思 | 怎麼做 |
|---|---|---|
| 小樣本只看得出大效果；「不顯著」不等於「沒效果」，要說等效得事先定 margin 再做 equivalence test（KTH 2602.07150、Miller 2411.00640、Kotawala 2605.30315、Pawel 2305.04587） | 判定要分四類：更好、更差、等效、未定。我們的規模幾乎證明不了等效，所以多數是未定。 | 帳本把「品質一樣」改顯示成「沒測出差異（未定）」；因成本排掉的寫「因成本不採用（能力未定）」。每份 PREREG 寫出用 pilot 變異算的最小可偵測差距。 |
| 先驗證題目，再驗證工具：要有什麼都不做的基線，隱藏測試要能分辨對錯，拿掉兩組都一定過的題（Zhu et al. 2507.02825） | 我們好幾組題目原生已經滿分（天花板），這類題不提供資訊。 | 每次試吃多一個「什麼都不做」組；隱藏測試先用已知對、已知錯的解各跑一次；原生滿分的題換掉。 |
| LLM 評程式跟隱藏測試的一致度很低（最好的 kappa 0.21 和 0.10）；有偏好自己和位置偏差（Crupi 2507.16587、Panickssery 2404.13076、Shi 2406.07791） | 用 Opus 評 Opus，不夠客觀。 | 能用程式評分就不用 AI 評；必須用 AI 評時，第二位評分者改用不同家族（本機有 Codex），兩種順序各評一次，取一致的部分。 |
| 單一評分者都有噪音，正式評估前先量評分者的準確度；類別不平衡時報 kappa（Zhuge 2410.10934、Shankar 2404.12272） | 我們沒有量過評分者自己的準確度。 | 每套題組先用有標準答案的樣本，量評分者的 coverage 和誤判率。 |
| skill 光是 description 放在 context 裡、沒被呼叫，也可能改變行為（Tank & Nama 2607.22520，證據中等） | 要知道一個 skill 加了什麼、佔多少 context，要拆開量。 | skill 類食物比三組：沒有、只有 description、description 加內容。 |
| 成本和能力怎麼放在同一張圖，以及輕量／深入怎麼切換：這一輪沒有任何說法通過驗證 | 只能根據上面的統計結果推論，可信度低。 | 每組都記 token、時間、context 佔用；判定寫成「每多花一單位成本換到什麼能力」。 |

## 輕量／深入怎麼切換（推論，可信度低，要你點頭才做）
先釐清：**EGM 不會自己跑。** V2 的 7 個 EGM skill 全部設成「只有明確叫用才執行」。「什麼都要 EGM 審半天」來自我們消化流程規定的 Goldfish 盲審（D10、D15、D21），不是產品本身。

本機 Claude Code 2.1.287 已經有的開關（已核對）：每個 session 的 `--effort`、自訂 agent（`--agent` 或 `--agents`）、先規劃再動手（`--permission-mode plan`）、`--settings`、`--plugin-dir`。桌面 app 也能逐個 session 調 effort。

建議做成三檔，預設輕量，**只有碰到觸發條件才升級**：

| 檔 | 用在 | 做什麼 | 成本 |
|---|---|---|---|
| 輕量 | 日常、小改動、問答 | 原生加 OAW 最小規則，不跑 EGM、不跑 Goldfish；`code_index.py` 可選用 | 約 1 倍 |
| 標準 | 一般功能、消化流程的 A 級重建 | effort high，加一位全新視角的 reviewer 看 diff 和測試 | 約 1.5–2 倍 |
| 深入 | 觸發條件成立時 | 先規劃（plan mode）、effort xhigh、`/egm:egm-review` | 約 10–30 倍 |

升級到深入的觸發條件（先寫死，之後也要照上面的方法驗證）：
- 動到每個 session 都會跑的 harness 程式：安裝、CI、hook。這就是 CLAUDE.md 的 Merge Gate 類別。
- 不可逆的操作：資料遷移、刪除、改寫歷史。
- 新子系統的設計文件。
- 判定落在未定、但風險高。

切換方式：一個指令（例如 `oaw.py mode light|standard|deep`），用 Claude Code 已有的開關，寫進專案設定或印出要用的啟動參數。AGENTS.md 只留一條規則：「預設輕量，碰到觸發條件才升級。」

## 還沒回答的問題
- 在 OAW 的 token 和時間預算下，怎樣拿到夠用的解析度：題目更多但更小、成對設計、序貫檢定，或者明講只做大效果篩選。
- 用新標準重新標註後，過去的排泄有多少會變成未定；EGM 的「更好」在 3 個以上 seed 下還站不站得住。
- 觸發條件能不能預測「需要深審」，要實測。

## 主要來源
- KTH，On Randomness in Agentic Evals：https://arxiv.org/html/2602.07150v2
- Miller（Anthropic），Adding Error Bars to Evals：https://arxiv.org/abs/2411.00640
- Kotawala，resolution ratio：https://arxiv.org/abs/2605.30315
- Zhu et al.，Agentic Benchmark Checklist：https://arxiv.org/html/2507.02825v5
- Crupi et al.，LLM-as-a-judge for code：https://arxiv.org/html/2507.16587
- Panickssery et al.，self-preference：https://arxiv.org/abs/2404.13076
- Shi et al.，position bias：https://arxiv.org/abs/2406.07791
- Zhuge et al.，Agent-as-a-Judge：https://arxiv.org/abs/2410.10934
- Shankar et al.，EvalGen：https://arxiv.org/abs/2404.12272
- Tank & Nama，skill osmosis（preprint）：https://arxiv.org/abs/2607.22520
- Pawel et al.，equivalence testing：https://arxiv.org/abs/2305.04587
- Anthropic engineering，infrastructure noise：https://www.anthropic.com/engineering/infrastructure-noise
