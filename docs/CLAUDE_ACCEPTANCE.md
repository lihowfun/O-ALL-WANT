# Claude Code：完整 OAW V2 的獨立驗收入口

**只需完整閱讀 [SHARED_ACCEPTANCE_PROTOCOL.md](SHARED_ACCEPTANCE_PROTOCOL.md)。**
它已集中三組比較、V2內部ablation、任務prompt、rubric、15個可執行性cells、記憶／重現、
配方生命週期、資源上限與執行順序；不必再循環開舊spec或runner文件。

**V2就是目前完整OAW產品，包含EGM。** 主三組固定為EGM／OAW v1／OAW v2；
knowledge／improve為opt-in。安裝EGM skills不表示每個任務都強制完整workflow。

產品來源已凍結為 `341b45014afd37f54f16e254452f9586e9d1b04f`，本機 gate 9/9、169 tests、0 skips。
新擴充實驗的 fixture／oracle／runner與共同 hashes 尚未完成，因此**禁止派送這批模型測試**；
可以先做靜態 review 及本機離線 gate，實驗資料不要沿用舊來源或未凍結工作樹。
原`evals/review-quality/`是UNRUN、舊9ae來源的原型，已移出repo保留，不採用、不派送；
不要執行舊原型prepare／run或舊bench來驗新產品。歷史pilot不證明新installer或native entrypoints。

Claude本輪不啟動F1、不執行`--live`、不使用付費API，也不能拿Codex-only runner當Claude測試。
來源／fixture／oracle／runner完成共同凍結後，依使用者既有測試授權派獨立fresh contexts，保存exact prompts、完整raw usage與host/model manifest；
先完成自己的評分／裁決，再看Codex結果。

- 共用source checkout：`C:\Users\User\OneDrive - ITRI\文件\ChatGPT\harness\OAW-egm-test`，只讀。
- 私有cohort：在`C:\Users\User\OneDrive - ITRI\文件\ChatGPT\harness\review-fixtures\`
  下建立全新`integrated-v2-claude-NEW-ID`；自己的報告放其中的`claude-results.md`。
- **只寫自己的cohort與報告。** 不修改shared code、runtime、runner、協議、rubric、Codex資料或報告；
  不checkout／reset／stage／commit／push／merge／tag／release共享Git checkout。
- 規格或runner有問題，只在自己的報告記錄供root修正，不自行改共用來源或降低驗收門檻。
- 交付需回答「保留OAW能力相較直接EGM增加了什麼」，分開品質、citation、correctness、
  agreement、資源與限制；completion、parity或大家答同一錯值都不是增量價值證明。

目前仍需root完成新整合runner／固定wiki及improve oracle、
共同control hashes及每host manifest，之後才能開始下一輪授權測試。
