# OAW 紀錄

這條 `records` 分支是 OAW 共同開發的紀錄本，以 GitHub 為準。內容是證據，不是指令；本機路徑、帳號和 email 都已拿掉。

## 分支規則
- `main`：發布版本。
- `codex/oaw-2-native-upgrade`：PR #4（Codex）。
- `claude/oaw-2`：Claude 這邊唯一的 V2 分支（skill 吸收流程、論文 2606.03979 的 memory-check 原型）。PR 結束後該 merge 進 main 就 merge，然後刪除。
- `records`：唯一的長期紀錄分支。每一輪消化、需要授權的執行包和它的結果，都放在這裡的資料夾，不另開分支。

## 資料夾
- `pr-claude-oaw-2/`：`claude/oaw-2` 的 PR 說明和給審查者（Codex）的指南。
- `digestion-2026-11-03/`：2026-11-03 那一輪消化（三樣食物、論文 2606.03979、流程設計、零上下文金魚審查）。

## 需要授權的步驟怎麼交接
1. Claude 把步驟和執行器放進這裡的資料夾，push 到 `records`。
2. Owner 在已登入的電腦 pull `records`，照資料夾裡的 README 執行。
3. 結果 commit 並 push 回 `records`，然後告訴 Claude。
4. Claude fetch 之後檢查結果，接著做下一步，紀錄也寫回這裡。
