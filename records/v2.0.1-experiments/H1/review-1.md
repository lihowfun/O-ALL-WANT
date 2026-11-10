# H1 審查第 1 輪（Codex gpt-6.1-sol，reasoning high，2026-11-10）

審的是第 1 版的 `PREREG.md`、兩份 brief 和當時的 runner；下面的行號指的是第 1 版。原文照錄，只把本機路徑換成 repo 內的相對位置。

---

先修再凍結

1. **阻擋｜`H1/PREREG.md:92`**：suite regression 的扣分太輕，甚至可能獎勵破壞既有功能的實作。例如 N 通過 11/12 個 hidden tests、既有 suite 全過，得 0.9167；O 通過全部 hidden tests、卻弄壞整套 suite，仍得 12/13＝0.9231。C 四題皆如此、其他題同分，主判定仍可「等價」。最小修正：有任何既有測試新失敗，該 unit 記 0；另外列出 regression 數量。

2. **阻擋｜`H1/PREREG.md:97`**：混合平均的等價不能代表「效果與記憶都沒變」。以現有程式驗算：A 同分、B 每題提升 1/8、C 每題下降 1/10，平均差為 0.00833，使用最低 floor 會判「等價」。結果可被叫「雞肋／沒差」，儘管記憶改善、C 全面退步。最小修正：把主結果限定為固定各占三分之一的 composite；記憶另行判定，且達到預登記「較差」條件的類別必須影響總詞，不能只把警語移到最前面。

3. **阻擋｜`H1/PREREG.md:100`**：`cost()` 衡量每題 token ratio 的 geometric mean，不能直接回答完成這批工作的總花費。例如八題 N＝100k、O＝50k，四題 N＝1M、O＝2M：程式回傳 ratio **0.794，95% CI [0.561, 1.122]**，依表可叫「沒差」；總 token 卻由 **4.8M 增至 8.4M，增加 75%**。最小修正：並列整批總 token、總量比與各類成本，事先決定 owner 判定詞採哪個成本意義；保留 `cost()` 作 protocol 指標。

4. **阻擋｜`H1/PREREG.md:101`**：兩格合併的成本與總詞沒有定義。`lowest()` 只接受四種 quality class，不能合併「雞肋／沒差」或成本。例如兩格品質都 equivalent，一格省、一格確實加倍，`lowest()` 仍只回 equivalent，最後用哪格成本未寫死。最小修正：補完整的跨格 decision table，先算每格 quality、cost、owner 詞及 EVAL_PROTOCOL 政策結果，再明定如何合併；不得看結果才選成本來源。

5. **阻擋｜`H1/PREREG.md:79`、`H1/PREREG.md:125`**：目前只有各類題庫的分批 freeze，沒有可驗證的 runner、verifier、scorer、parser、依賴與 launch configuration freeze；A 卻已允許先跑。operator 可以在看到 A 後改成本解析或後續執行方式。最小修正：任何 scored run 前，凍結全部 briefs、題庫及執行依賴 digest，由 Codex 檢查完整 argv、permissions、工具／subagent availability、mount 與環境清單；續跑遇版本不符即拒絕。輸入須固定為 `unit_id → run list`，成本的 N 分母採兩次平均。

6. **阻擋｜`H1/PREREG.md:50`、`H1/PREREG.md:82`**：workspace／home 的隔離 key 少了 replicate 與 attempt。若 runner 按文中的 `(格、臂、unit)` 建目錄，N2 可能讀到 N1 留下的記憶與完成程式，既提高 N 平均，也把 noise estimate 弄錯。最小修正：明定每個 `(cell, arm, unit, replicate, attempt)` 都重建 workspace、home、暫存與工具狀態；只有同一次 attempt 內的 B sessions 共用。另須驗證檔案遮蔽不能經 `/proc` 等 host 路徑繞過。

7. **阻擋｜`H1/PREREG.md:129`**：預算不足時停 C 的 N2，會讓 control 平均與 floor 改成由花費決定的混合設計；停 L 則可能使八題比較缺列。只看成本仍可能選到較容易的題，因為成本與難度相關。27M 的估算檢查也不是 30M hard cap。最小修正：優先保留完整的 N1／N2／O comparison blocks，L 可在開跑前整組取消；缺 primary 題、cell 或必要 replicate 就不出預定主判定。寫死成本估計、預留額度、停止方式及未完成資料的處置。

8. **阻擋｜`H1/PREREG.md:85`**：把有實際作答的 timeout 當成「沒跑」，再給 120 分鐘重做，測到的是 adaptive retry policy；不是一次作答。較慢的臂會獲得額外機會，而且失敗 attempt 的 token 是否計費未定。例如 O 花 59 分鐘後逾時，重跑成功，報告可能只留下成功那次成本。最小修正：所有臂使用同一固定有效作答上限；正常執行到 timeout 記成品質結果並計入全部 token。只有明確的 infrastructure／subscription failure 可重試，另寫死重試耗盡及所有 attempt 的成本處理。

9. **阻擋｜`H1/PREREG.md:90`**：只還原 `tests/`，尚未建立可信的 grading environment。agent 留下的 root `conftest.py`、pytest configuration 或改過的 `.venv` 都可能改變 collection、skip、xfail 或載入內容；collection error、parametrization 與 timeout 的分數也未定。最小修正：在全新 base 中只套入允許的候選 source，再使用固定且不可改的測試環境；核對凍結的 node IDs 與數量，明定每個 function 的所有參數須通過，skip／xfail 不算通過，collection failure 不得變成刪題或縮分母。

10. **阻擋｜`H1/PREREG.md:74`、`AUTHOR_BRIEF_C.md:32`**：reference patch 的允許路徑互相矛盾。plan 只接受 `src/`，C brief 允許 design 題加入 `docs/designs/`。作者照 brief 交出完整設計與實作，會被機械驗題淘汰，補題仍會重複失敗。最小修正：plan 與 verifier 明確允許 design 題指定的 design note，其他路徑繼續拒絕。

11. **阻擋｜`H1/PREREG.md:74`、`AUTHOR_BRIEF_B.md:39`**：B 的驗題只證明「整份測試會失敗／有一個 solver 能全過」，沒有證明 recall tests 必須依靠正確記憶。例如 recall test 只檢查停用功能時沒有 header，base 就能過；另一個 base test 失敗，整題仍符合機械條件。brief 也只要求 base tests 檢查最後 session，可能漏掉被丟棄的前段工作。最小修正：對任意 facts 做錯值／舊值 mutation，確認各 recall test 會失敗；另要求 hidden tests 涵蓋所有 sessions 應保留的成果。full-memory solver 檢查繼續保留，但不能單獨當作有效性證明。

12. **應修｜`AUTHOR_BRIEF_C.md:19`、`AUTHOR_BRIEF_C.md:30`、`H1/PREREG.md:76`**：8–12 條需求、10–14 個 test functions，與 plan 的「每條一個測試」不一致。容易需求拆三個 functions、難需求只放一個，就會改變需求權重；audit 刪除未公開需求的測試，也與「不合格不修」衝突。最小修正：統一需求與計分單位，一個凍結 requirement 對一個計分項，多個 cases 全過才算過；有未公開 requirement 的 unit 整題丟掉。

13. **應修｜`H1/PREREG.md:99`**：N1／N2 可以交給 `pooled_within_sd()`，但借來的 0.1318 是 EGM design-review detection rate 的變異，並非這個 Flask 題庫、這個 grading metric 的 noise estimate；不完全符合 `EVAL_PROTOCOL.md:29` 的來源要求。最低 floor 下，12 題的 SE＝0.05381、MDE＝**0.15066**；等價要求平均差約在 **±0.01150** 內，且 bootstrap interval 不能更寬。floor ≥0.14892 時，12 題連完全同分都不能等價；L 的八題在最低 floor 下也不能等價。最小修正：事先寫出這些限制，補同題庫的獨立 calibration，或把借值明列為 protocol exception／保守 sensitivity；不能承諾八題 L 能證明兩行拿到相同效果。

14. **應修｜`H1/PREREG.md:59`、`H1/PREREG.md:77`**：保留已知 ceiling 的 A、以及 C 不足時補 ceiling 題，均偏離「原生接近滿分要換掉」的 gate。Codex-only calibration 配上新的正式 N，不會單靠 regression-to-mean 製造 O 優勢，但只能建立 Codex 的難度分布；Claude 可能四題全部 ceiling。最小修正：A 保留為獨立的 safety／cost 結果，停止無條件宣稱同一道門；C 若要作兩格能力比較，兩格都校準並固定選題規則，合格題不足就停止補題，不用 ceiling 題補滿後宣稱有足夠鑑別力。

15. **應修｜`H1/PREREG.md:116`**：同四個 units 在兩模型上的八對結果，不能直接當八個獨立 task samples 做 sign test。若四題在兩格都贏，八個獨立樣本的 two-sided p＝0.0078125；四個 task clusters 全贏則為 0.125。淨勝差為 0 也可能是兩贏兩輸，不能叫「一樣」。此外 `eval_stats.py` 沒有 sign test。最小修正：移除這個跨格 p，依四個 unit 描述方向；淨差 0 改成「勝負抵銷，未證等價」，secondary comparison 統一使用 N1／N2 平均。

16. **應修｜`H1/PREREG.md:32`、`H1/PREREG.md:36`**：L 只要求事前 plan review；O 的 standard 要事後 diff／tests review，deep 還有後續 review rounds。若 L 漏掉 implementation bug，不能據此概括「兩行規則拿不到 OAW 效果」。L 在 A 也會增加指令 token，並不等於 N。最小修正：第二行涵蓋事前 plan 與事後 diff／tests，將 `apply what it finds` 改為 `resolve justified findings`，第一行加上 `if NOTES.md exists`；若維持原文，就限定為這份不同 review policy 的比較，並把「A 等於 N」改成「L 的 A 未測」。

已核對無誤：README 的 `--host both` 安裝路線、A 題順序與 SHA-256、舊紀錄的 native 12/12、mechanical grading 可免雙家盲評、`margin=0.10`、`lowest()` 用於跨格品質類別；兩份 brief 文字未直接透露 OAW 或臂別。未改檔、未執行受測 agent 或 Flask 實驗。

驗證平台：Linux 6.8.0-136-generic x86_64、Python 3.10.20；統計反例僅在記憶體中呼叫既有 `eval_stats.py`。
