# V6 補登記：加上 Skill 工具（2026-11-07，任何有效作答之前）

- **發現**：照 PREREG「工具和權限和第一輪相同」，第一次開跑沿用第一輪的工具清單 `Read,Write,Edit,Glob,Grep,Bash,Agent`。
  - 這個清單沒有 `Skill` 工具。init 有列出 `court`，但 D 組第一回合的 context 和 N 組逐字相同（c1 8,912 對 8,912、c2 8,930 對 8,930、c3 8,846 對 8,846）。
  - 也就是說，skill 的 description 根本沒送進模型，模型也不可能自己叫用 court。
  - 第一輪的 C 組沒有碰到這個問題，因為它用 `/court` 直接展開 skill，不需要 `Skill` 工具。
- **和 PREREG 的衝突**：PREREG 要測的是「不打 `/court`，要不要叫用由模型自己決定」和「只放 description 會不會改變行為」。沒有 `Skill` 工具時兩者都測不到，所以照 PREREG 的目的修正工具清單。
- **修正**：
  - 三組都加上 `Skill` 工具。N 也加，讓工具集合相同。
  - runner 多一道檢查：D 或 F 在同一案的第一回合 context 沒有比 N 大，就停下。
- **作廢的資料**：
  - 第一次的 6 筆（N、D 各 3 筆）原樣留在本機的 `out-invalid-no-skill-tool/`，不計分。
  - 它們的 68,115 token，加上被中止的那一次（不知道用量，以該組最大值 13,604 估），共 81,719，算進 court-skill 的預算。
- 其他設定、次數、順序、判定規則都不變。
