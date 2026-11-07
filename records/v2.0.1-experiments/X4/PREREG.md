# X4：每個 session 開頭多花多少 context（2026-11-07，跑之前登記）

依 `claude/oaw-2` 的 `docs/plans/v2.0.1-execution.md` 第 6 節 X4。

## 問題
2.0.1 的預設安裝讓一個 session 的第一回合比 2.0.0 多花多少 context？

## 設計

**三種專案**，都是新的 git repo，裡面只有一個 README：
- **bare**：沒有 OAW。
- **v200**：用 OAW 2.0.0 的程式安裝。來源是 `claude/oaw-2` 的 332c585；這個 commit 只有計畫文件，程式和 8e607f0 相同。
- **v201**：用目前 `claude/oaw-2` HEAD 的程式安裝。

兩個版本都用 `oaw.py init --host both`，也就是預設配方。

**主機**
- **Claude Code 2.1.287**：`claude -p "Reply with OK." --output-format stream-json --verbose --no-session-persistence`，只用訂閱，apiKeySource 必須是 none。
- **Codex CLI 0.167.0**：`codex exec --json --skip-git-repo-check "Reply with OK."`。

**次數**：每種專案、每個主機各跑 3 次，順序輪替。

## 量什麼
- **Claude**：第一則 assistant 訊息的 `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`，也就是整份 prompt 的大小。
- **Codex**：第一個 `turn.completed` 的 `usage.input_tokens`。

## 判定（事先寫死）
- **通過**：Claude 上 v201 的中位數減 v200 的中位數，不超過 600 token。
- Codex 只報告數字，不拿來判定。

## 預算
少於 0.3M Claude token。Codex 用 owner 的 ChatGPT 方案。
