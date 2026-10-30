# Claude Code：獨立重跑 EGM／OAW v1／OAW v2 驗收

請先讀 [三組驗收規格](plans/egm-oaw-three-way-acceptance.md)，再讀
[protocol.json](../evals/three-way/protocol.json)。**不要先讀 Codex 結果來調題、prompt 或 rubric。**
你是實驗 controller，不是候選或 grader。可看 frozen rubric 以組裝驗收，但不得把 gold
傳給候選。每個候選／reviewer／grader 用新的 Agent context，不 fork controller 歷史。

## 共同輸入與版本

1. 固定 EGM 0.1.0 `f0ba151b252c9abf1318d9fe857a43265d06de89`、OAW v1
   `5df531372330f6b0e1c9a81aee0c1c45f2f283ff`、OAW v2
   `9ae4eba01b948057efb8294df061dd995d03fc6e`。用乾淨 archive，逐檔 hash；不 fetch latest 後悄悄換版本。
2. 用新私有目錄執行 `bench.py prepare` 產生資料（見下方）。這步不呼叫模型。
   v1 應跑自己的 install.sh；v2 使用自己的 Python installer。
   跨 host 時 v2 的 adapter 應以相同來源安裝為 `--host claude`，保留這個必要差異的 manifest；
   不把 Codex skill 目錄缺少 Claude adapter 的情況當成 v2 能力。
3. 主組名稱固定 EGM／OAW v1／OAW v2。EGM 的 Codex adapter 在 Claude 換成同版
   `docs/claude.md` 指示；三名 Stage 9 personas／standards 與任務內容保持相同。
4. 登記你實際使用的 Claude Code version、requested／reported model、effort、tools、
   auth／權限來源、可觀測 memory 設定、價格快照與 quota 上限。
   同一組配對不混模型；未知欄位明列，不猜 Opus 的精確 revision。

```sh
python3 evals/three-way/bench.py prepare \
  --repo /absolute/path/to/O-ALL-WANT \
  --egm-repo /absolute/path/to/EGM-source \
  --out /absolute/private/path/claude-three-way \
  --host claude \
  --bash /path/to/bash
```

Windows 用實際 python 與 Git Bash 路徑。不要覆寫 Codex cohort。
目前 `bench.py run` 是 **Codex CLI adapter**；不要執行後把它冒充 Claude 的結果。
Claude 的 adapter／host manifest 要先登記、免費 smoke-check 後才派模型。

## 實際派送

- Review：讀 manifest 的 12 個 trial，保持 case／repeat／輪序與輸入。
  OAW v1 讀實際啟動 policy，用自己的正常流程。
  EGM／OAW v2 明確指定官方 `implementation` preset，分別派
  implementation-readiness、codebase-details、style 三個全新 Agent；各自讀 persona／standards、
  同一 immutable source 副本，不能看彼此報告。再由第四個新 Agent 按 synthesizer 規則整併。
  三個 Agent 不能由同一 context 角色扮演。產生 traceability，保留 raw findings。
- Memory：兩條 trajectory，各 4 個新 Agent，順序執行；只共享該組實際專案檔案。
  S1 收到 prompt-only ticket；S2 不提供 S1 prompt、controller 摘要或 transcript。
  S3 新增相同 ADR-044；S4 再精確重建。正確值只在 gold／已授權 source，不能偷偷補。
- 同快照重現：依 [獨立 protocol](../evals/three-way/replication-protocol.json)，全部 6 份
  S1 snapshot 各再派 2 位新接手者，使用相同 S2 prompt／獨立 snapshot 副本。
  加上原 S2 共三位；把對 gold 的精準度與彼此一致率分開，不能把共同錯答算準確。
- 最終 JSON 結構、source boundary、read-only review、未知值與 write scope
  使用 bench.py 的同一 prompt；只改必要的 host integration 文字，先保存 exact prompts 與 hashes。
  不以 reviewer 數、token budget 或重試傾斜任一組。

原 spec 的 token 限制可作保守起點；Claude tokens 的 tokenizer／計價與 Codex 不相同。
若你要換上限，**模型執行前**另立 `protocol.claude.json`，列明 host/model/adapter/預算差異；
保留相同 case、rubric、repeats、來源與任務語義。不要直接修改已跑的 Codex protocol。
只有這次使用者授權的範圍才執行；不要啟動舊 `run_pilot.py --live` 或另用付費 API。

## 用量與評分

1. 保存實際 Claude 回合 usage；驗證 parent 是否已包含 child，選一種不重複的加總。
   缺 child usage 就不報全樹 token／成本，不能拿 Agent 數換算。
2. logical input＋output、cache read/write、reasoning 分開；若 reasoning 已含在 output，勿加兩次。
   失敗／timeout／重試與 grading overhead 分列。沒有具體價格就不填美元。
3. 所有報告完成後再匿名化，兩位獨立 fresh graders 看同一原文、完整 method sources 與
   frozen rubric。不要把 OAW／EGM 文件中的真實方法要求判為幻覺，也不要把它當額外產品要求。
4. 真實額外問題可以給分，不只看 gold；重大漏抓與 factual false claim 分歧由第三位裁決。
   不重寫候選報告、不選擇性重跑。修 setup／grader 錯誤時，保留原始檔並說明失效範圍。
5. Memory 精確核對 8 欄值、scope、有效 ADR 與 citation；S2 ticket 要引用真實持久記錄。
   同時算正確率和 agent agreement，避免大家錯得一樣就叫可重現。

## 交付

請輸出一份 `claude-three-way-results.md`，三欄固定 EGM／OAW v1／OAW v2，包含：

- 各 case／repeat 的缺陷偵測、誤判、有效新發現、完整 workflow tokens。
- 每個 session 的 8 欄正確性／引用、prompt-only fact 保存、新舊決策誤用、逐 hop drift。
- 所有 planned／completed／failed／incomplete 數、原始匿名報告、判分分歧與裁決。
- model／host／來源／protocol／prompt／runner hashes、usage 完整性、限制。
- v2 對 EGM、v2 對 v1、v1 對 EGM 的逐項結論；observed parity、regression 或 inconclusive。

先完成你自己的判分再看 Codex 結果。之後做 host 分層對照，不直接比較 token 數就宣稱
某模型更便宜／更強。有限題庫不證明普遍等價；不 merge、不 tag、不改動 main。
