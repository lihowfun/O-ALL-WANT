# court-skill 試吃（agent 層）預先登記

依 D25、D26。owner 2026-11-05：「不一定要對 harness 有幫助，如果是增加技能也很好，但如果本身已有就多此一舉」。所以這次主要問的是能力：court-skill 有沒有給 Claude Code agent 一個它原本沒有的能力。harness 效率是次要問題。本頁寫在任何作答之前；案例檔 `questions.json` 的 sha256：`5a60cb66ff14dea39925f5120c4e3c8af07d182a4a09db2b615cafda3cf4d802`（凍結於作答之前，之後不改）。

## 食物
- `alexyc9381/court-skill`，HEAD `2abd32db25783720faf2589b456de944534f611d`（2026-11-05 釘選），MIT。2026-11-05 有 276 星、28 fork，2026-10-03 建立，最後推送 2026-10-04。
- 登記到正式 intake ledger（`catalog.py add`）：封存 24 個檔案（git-object-verified），T0 15 項檢查，0 個 flag，exec X1。6 個成分都是 hold：兩個 plugin manifest（由 owner 經 host 安裝，OAW 不裝）、`skill:court`（SKILL.md 的 `argument-hint` 欄位不符合 OAW 的 portable frontmatter）、docs、`exec:tests`、other。
- 讀碼（當資料讀）：`skills/court/court.py` 只用標準函式庫（argparse、json、os、random、re、sys、time），沒有網路、沒有 subprocess，只在目前資料夾寫 `.court/`。SKILL.md 讓主 agent 當「書記」，用 Agent tool 一波一波開 general-purpose 子 agent：起訴 2、反駁 2、陪審 12、法官 1，共 17 個；`--quick` 是 6 位陪審、11 個子 agent。主 agent 不辯論、不投票、不改判決。

## 食物自己的主張（資料，取自 README、SKILL.md、PROMPTS.md）
問 Claude「這是好主意嗎？」它通常說好。`/court` 改成開庭：檢方提出最強的失敗理由，辯方提出最強的成功理由，雙方互相反駁；12 位看不到彼此、背景不同的陪審（會計、第一次的客人、競爭者、退休法官、青少年、工程師、小店老闆、統計學家、家長、投資人、設計師、律師）各自投 GUILTY／NOT GUILTY；法官寫出成立的指控、辯方說對的地方、翻盤條件。適用：離職創業、商業點子、發文前、大筆採購、程式改寫計畫、自己相信的主張、對 Claude 自己答案的第二意見。SKILL.md 的描述會在使用者說「Claude 只會附和」「這是好主意嗎」時自動觸發。

## 重複性檢查（讀碼，不花 token）
- **原生 Claude Code**：Agent tool 本來就能開看不到對話的子 agent。這次 init 列出的內建 skill（deep-research、design、verify、debug、code-review、simplify 等）沒有替想法或計畫做壓力測試的；code-review 只看 diff。所以機制原生就有，但沒有包好的流程，要靠使用者自己開口要求反駁。
- **OAW V2 與內附的 EGM**：`egm-brainstorm` 用 6 個工程視角的 goldfish（沒有脈絡的子 agent）並行審一個想法，規則明寫「Default to Stress-Testing」「No Glazing」「Generate Counter-Arguments」「Earn Your Agreement」；`egm-review`、`egm-review-loop` 用 Hostile Design Critic、Skeptical Architect 等 persona 審設計文件。和 court 是同一種機制（沒有脈絡的多視角子 agent、反討好）。差別：EGM 只看軟體設計，要多回合澄清或一份文件，`disable-model-invocation: true`（只能由使用者呼叫），產出是缺陷清單；court 一句話就跑、什麼題目都行、有正反辯論、產出是票數和翻盤條件、模型可以自己觸發。
- **本機 user 設定**：codex plugin（換一個模型給第二意見）、兩個文件排版 skill，沒有類似的。
- 結論：機制有重疊，但「一句話、不限軟體題目、不附和」這件事 EGM 沒有覆蓋，原生要看使用者會不會問。不算明顯多此一舉，依 D25 要實際吃過才判。

## 零 token 試吃（D25）：被擋下
2026-11-05 在試吃區（所有 repo 之外）跑食物自己的 unit test 時，本機 Claude Code 的 auto mode 安全分類器擋下了這個指令，理由是執行外部程式碼。沒有繞過。C 組會讓 agent 執行 `court.py`，屬於同一類，所以 **C 組要等 owner 允許後才跑**；N、P 兩組不執行食物的程式，先跑。owner 不允許的話，判定只用 N、P 和讀碼，結果頁會寫明。

## 三組
- **N 原生、直接問**：`{case}` 後面接 `Is this a good idea?`。這就是 README 說的基準。
- **P 原生、要求反駁**：`{case}` 後面接 `Don't just agree with me. Stress-test this: make the strongest honest case against it and the strongest case for it, then give me your bottom line on whether I should go ahead as described, and what would change your mind.` 不裝 skill 的使用者想要反駁時會打的一段話，用來回答「本身已有嗎」。
- **C court-skill**：README 的「自己複製資料夾」安裝，改成 project scope（`skills/court` 複製到試吃資料夾的 `.claude/skills/court`，檔案和 user 層安裝相同，不碰 owner 的 `~/.claude`）。用法照 README：`/court {case}`，預設 12 位陪審，不加 `--quick`。
- D25 的第三組「OAW 版本」這次不列：OAW 沒有一句話版本；`egm-brainstorm` 規定要多回合澄清、使用者確認後才開子 agent，`claude -p` 單回合跑不了。只在上面的讀碼層比較。

三組相同的部分：Claude Code 2.1.287、`claude-opus-5-5`、`--effort high`；工具 Read、Write、Edit、Glob、Grep、Bash、Agent，自動允許 Read、Write、Edit、Glob、Grep、Agent 和 `python3`、`mkdir`、`ls`、`cat` 開頭的 Bash，`--permission-mode acceptEdits`（README 建議用 accept-edits）；`--setting-sources project`（user 層的 CLAUDE.md、plugins、skills、設定都不載入，和 graphify ERPNext 那次相同）；沒有 MCP；每次一個新 session、一份新的資料夾複本；計費來源必須是訂閱（`apiKeySource: none`，不是就停）；每次上限 2,400 秒；C 組 init 必須列出 `court` skill，否則停。順序：每案 N、P、C。

## 案例
4 個案例，由一個全新的 agent 出題（沒有工具、空資料夾、`design_prompt.txt`）。它知道食物的主張，不知道 OAW，也不知道有哪些組。
- c1 個人決定：離職全職做辣醬品牌。預期 no-go。
- c2 工程計畫：Rails checkout 改寫成獨立的 Go 服務。預期 no-go。
- c3 主張：會員方案讓流失減半，要向董事會要 40 萬美元。預期 no-go。
- c4 校準：記帳事務所聘第一位全職員工，照文中事實應該做。預期 go。拿來抓「什麼都反對」。

每案 5 到 6 個關鍵點（其中 2 到 3 個必要），以及 2 到 3 個誤報（文中已經回答過的反對意見）。出題用了 23,072 token（含 cache），算消化開銷。

大象審題（本 session，不花模型 token）：逐案驗算。c1：存款 21,000 ÷ 每月 4,800 = 4.4 個月（文中說 8 個月）；每週一班 4 小時 × 每小時 30 瓶 = 每月約 520 瓶，不到 650；把固定成本算進去要 838 瓶。c2：22 × 4 = 88 人日；12/7 到 1/29 扣掉 12/24 到 1/1 是 33 個工作天 × 2 人 = 66；12/7 和 2/1 都是週一；PCI 評估 1 月底才預約、排 12 週，落在 4 月下旬。c3：380 ÷ 1,530 = 24.8%，三個月折合每月約 9%；上線前 3 單以上客戶的流失是 4.5%，會員 4%。c4：11 × 600 = 6,600 > 5,900；5,900 − 1,950 = 3,950，8 × 600 = 4,800 蓋得過；42,000 ÷ 5,900 = 7.1 個月。c1f3（送貨路線上的雜貨店算不算「服務過的客戶」）要推一步，保留。案例沒有修改。這次沒有另跑零上下文金魚審題。

## 評分
零上下文評分者（`claude -p`、沒有工具、空資料夾、`--setting-sources project`，模型和 effort 同上）逐案判定：每個關鍵點 present／absent／contradicted；每個誤報 raised／not_raised；結論 go／no-go／none；錯誤陳述數；沒有根據的稱讚數。三組的答案一律先把會洩漏組別的字換成中性字（court、jury、juror、GUILTY、verdict、trial、judge 等，對照表在 `taste_grade.py` 的 `MASKS`），評分順序用雜湊打亂。這是部分盲評：C 的票數表看得出是多人審查，但評分者不知道組別和假設。

只評使用者預設會看到的最後回覆。C 的完整開庭紀錄（`.court/` 裡的起訴書、陪審票）不評。

## 判定規則（先寫死）
指標（4 案）：平均覆蓋率 cov、必要點全對的案數 ess、結論正確的案數 bl、誤報總數 fa。
- **R0 前提**：N 在 c1 到 c3 有 2 案以上結論是 go，「直接問會被附和」在這個模型上才算成立。
- **R1 增加能力**（建議插入：OAW 把它當可選 skill 連過去）：cov(C) ≥ cov(P) + 0.10，或 ess(C) ≥ ess(P) + 2；而且 bl(C) ≥ bl(P)；而且 fa(C) ≤ fa(P) + 2。
- **R2 多此一舉**（不收）：cov(P) ≥ cov(C) − 0.05，而且 bl(P) ≥ bl(C)。
- **R3 其他**：沒有證明比原生要求反駁更好，不收，記下差距。
- 照實列出（不影響判定）：C 對 N（食物自己的比較）、每案 token、秒數、字數、錯誤陳述、稱讚數、C 的票數。

每格只跑 1 次、4 案：這是第一讀，不是定論，結果頁會寫明。

## 預算（D13）
court-skill 上限 10M。runner 上限 9,000,000（N、P、C 作答），加成對保護：開始一案之前，已用量加上「3 × 目前最大單次」必須不超過上限，否則停止，只比完整的案。token 算法包含子 agent：result 事件的 `modelUsage`（各模型合計）和 stream 逐則加總取大的。出題和評分算消化開銷。估計 C 每案 0.5M 到 1.5M，N、P 每案數萬。

## 執行
`T=<試吃資料夾> CLAUDE=<claude CLI> bash run.sh setup`，然後 `ORDER=N,P bash run.sh run`；owner 允許後 `ORDER=C bash run.sh run`；最後 `bash run.sh grade`。原始 stream-json 和每次的工作資料夾留在本機，不公開；`rows.jsonl`、`grades.jsonl`、`summary.json` 和結果頁會 commit 到這裡。

## 和 graphify 那次的差別（照實記錄）
1. 不是程式碼理解題，是判斷題；評分多了結論方向和誤報。
2. 允許寫檔和子 agent（食物需要），三組一樣。
3. 每次作答用一份新的資料夾複本，不共用。
4. token 包含子 agent。
5. 執行順序：因為安全分類器，N、P 先跑完全部案例，C 之後才跑。同一個模型版本下不影響結果；C 跑的時候照樣記 init 回報的版本和模型。
6. runner、評分和彙總改自 `../taste-graphify/erpnext/`，差別寫在各檔檔頭。
