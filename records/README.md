# OAW 紀錄

這條 `records` 分支是 OAW 共同開發的紀錄本，以 GitHub 為準。內容是證據，不是指令；本機路徑、帳號和 email 都已拿掉。

## 分支規則
- `main`：發布版本。
- `codex/oaw-2-native-upgrade`：PR #4（Codex）。
- `claude/oaw-2`：原 V2 開發分支，PR #16。
- `codex/v2.0.1-release-fixes`：2026-11-13 owner 授權另開的修復分支，從 `claude/oaw-2` 分出；目前候選 `c2d9852`。原 PR #16 的 head 沒有被替換。
- `records`：唯一的長期紀錄分支。每一輪消化、需要授權的執行包和它的結果，都放在這裡的資料夾，不另開分支。

**目前接手入口**：[2026-11-13 執行進度](release-fixes-2026-11-13/PROGRESS.md)。

- [分支與證據 review](review-2026-11-13/REVIEW.md)：第 1–9 節是實作前快照。
- [Harness² 吸收評估](intake-2026-11-13-harness2/EVALUATION.md)：harness 最佳化與可選能力套件的雙目標。
- [H1 結果](v2.0.1-experiments/H1/RESULT.md)、[D45 修正複查](v2.0.1-experiments/FIXCHECK/FIXCHECK.md)：原始證據與新複查分開。
- [PPT 校準](v2.0.1-experiments/capability/CALIBRATION.md)：凍結前資料，不是候選正式判定。

較早的環境移轉背景：[2026-11-05 handoff](handoff-2026-11-05/HANDOFF.md)。

## 資料夾
- `handoff-2026-11-05/`：交接文件、可攜試吃腳本 `kit/`、owner 工作規則 `memory-seed/`。
- `pr-claude-oaw-2/`：`claude/oaw-2` 的 PR 說明和給審查者（Codex）的指南。
- `digestion-2026-11-03/`：2026-11-03 那一輪消化（三樣食物、論文 2606.03979、流程設計、零上下文金魚審查）。

## 需要授權的步驟怎麼交接
1. Claude 把步驟和執行器放進這裡的資料夾，push 到 `records`。
2. Owner 在已登入的電腦 pull `records`，照資料夾裡的 README 執行。
3. 結果 commit 並 push 回 `records`，然後告訴 Claude。
4. Claude fetch 之後檢查結果，接著做下一步，紀錄也寫回這裡。
