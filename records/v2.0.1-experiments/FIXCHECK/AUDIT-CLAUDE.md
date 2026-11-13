# Claude cell 機制事件稽核

- 範圍：12 個 counted row，僅採各 row.root 指定的 attempt；重讀 FIXCHECK.md「機制事件稽核」凍結文字與 EVENTS.json 格式。
- passing-1-b1 僅稽核 a2；a1 為使用者指明的 service error 未計入 attempt，未檢視／稽核其 raw。t01 也依 counted root 採 a2。
- 所有證據均指向原始 JSONL 的 1-based 行號，SHA-256 是原始整檔 bytes；摘要去識別，不複製 raw transcript。
- 配對依 tool_use.id／tool_result.tool_use_id；review 子事件另核 parent_tool_use_id 與 completed 結果。skill 名稱、agent 統計及最終自述不作單獨證據。

## A：小改動
- t01、t04、t09、t12 的前後 suggest 都是 light；無 required review、無額外 deep。
- t09 最後有 type-ignore 拼寫修改及測試，未再次 suggest；如實記為最後已見 mode=light，沒有捏造最終 mode 呼叫。
- 五種機制皆 unverified：非 B／非 design、無額外觸發；各列 scope_evidence 保存實際 mode 呼叫與結果。

## B：記憶
- explicit：M1 observed；s1 memory add 含兩項完整事實，成功寫入 OAW primary memory，tail 與 s2 實際讀回吻合。
- explicit：M2 absent；s1 有空 recall，但餘下只有 OAW memory tail/status，沒有 host 記憶／歷史查詢。s2 的 host 目錄查詢跨 session，不能補算。
- passing：M1 observed；s1 成功 memory add，cat 與 s2 讀回均含兩項完整事實。s2 合併命令最後 host 目錄查詢 exit 1，不影響前一 session 的成功寫入。
- passing：M2 unverified；兩個 session 都沒執行 memory recall；直接讀檔／查 host 不能憑空建立空 recall 觸發。
- superseded：M1 absent；s1、s2 都確實用 Write 保存到 Claude host memory 的同一 maintenance note 並更新 MEMORY.md 索引，沒有執行 OAW memory add。
- 本稽核將凍結條件讀為「成功執行指定 memory add」；host 保存是真實寫入，但不是符合 M1 的寫入，故不擴張 observed，也不稱完全沒寫。
- superseded s1 舊 header／maintenance 值有保存，但舊 body 少了需求的末尾句點；s2 讀回可證。s2 新 body 含句點並明示取代舊規格，s3 確實讀回新值。
- superseded：M2 unverified；s2、s3 直接讀 host note，但沒有任何 memory recall，故無空 recall 觸發。
- handoff：M1 absent；完整 s1 只有第一部分實作／測試／changelog／mode 檢查，沒有保存兩項未來事實，亦無其他記憶寫入。
- handoff：M2 unverified；s2 先查 host 目錄，再執行空的 OAW search --include-memory／memory show；它們不是凍結條件所稱的空 recall，順序也不能倒算。
- Bash 成功判讀：M1 的 add 沒有獨立數字 exitCode=0 欄，依配對結果 is_error=false、interrupted=false、無非零 returnCodeInterpretation、成功訊息及寫入 diff／讀回，判為 exit 0。
- 不將 is_error=false 一律當每個子命令成功：pipeline、分號串接與 grep 的 benign 非零解讀分開記錄；尤其不把最後 exit 1 套到 earlier memory add。
- B 各 session 的實際 suggest 都是 light，沒有 required review 或額外 deep。

## C：審查
- design-1：R2 observed；獨立設計 review 與一輪 code review 均完成，有子工具活動及 completed 結果。設計快照方向等修正在 source 實作前完成。
- design-1：code reviewer 重現 root_path 未還原及無效測試；後續 source／test／doc 修改、最終類別讀回及 515 tests 通過可配對。
- design-1 的同一設計 reviewer 讀了 design 與 plan；稍後補登 plan 的 reviewed 記錄不另算一輪，也不當 code review。
- design-3：R2 observed；設計 review 的 host-error／authority 規則修正與登記先於 source 實作；另有完成的一輪 code review。
- design-3：code review 後實際修正畸形 host label、無效斷言與測試缺口；新增測試一度失敗，修正後 589 tests 通過。修復／重測不算第二輪獨立 code review。
- large-2：實際 diff 與最終 suggest 為 standard；一輪 Claude code review 完成且有對應修復／回歸測試，546 tests 通過。保留普通 JSON equality 是 log 明示的取捨，未宣稱所有建議都採納。
- large-3：path-list light 之後 actual diff 轉 standard；一輪 Claude code review 完成，修正 typing、增強賦值 identity 與空 list 重複迴圈；628 tests 通過，mypy 成功。
- large-3 review 修復後未再 suggest；最後測試風格修改後 628 tests 通過，log 無 deep／design 流程。pyright 仍有既存錯誤，不能宣稱全部檢查通過。
- 兩個 large 題沒走 deep，故 R2 unverified；兩個 design 的 deep 屬原定範圍，故 12 列 extra_deep 與 extra_required_review 全為 false。

## 無法確認與界線
- Claude 全列未實際執行 Codex-only M3／R1，均 unverified 且 evidence=[]；Claude 的一般 Agent review 不冒充 Codex R1。
- B 以外沒有 memory recall 觸發；除 explicit 的空 recall 外，不將未知 M2 當 observed／absent。
- raw 可證明 native Agent 呼叫、子工具活動及回覆，未獨立揭露 runtime 內部 context isolation／effort 設定；不以名稱或數量替代。
- 不判 token 是否下降、隱藏 assertion、CLI 空結果引導的離線測試或發佈通過；本次不重跑模型／實驗，也未執行 git 操作。
- 按要求完成一次機制核對後，只做一次輸出自檢：重新計算 counted row SHA、每個 evidence 原檔 SHA，驗證所有 locator 行範圍、12 列及狀態結構。
