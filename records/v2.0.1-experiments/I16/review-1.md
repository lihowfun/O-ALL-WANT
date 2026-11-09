先修再凍結

1. **阻擋｜[i16_judge.py:129](i16_judge.py:129)**：BASH 通過條件被放寬。`quality()` 接受 unsupported「未定」；成本「未定」也能進預設。記憶體反例中，unsupported 上界為 **0.658＞0.5**，品質仍是 better。保留 D29 分類，但另計 BASH 通過旗標，強制兩家偵測更好、unsupported 通過預先定義的不劣門檻、critical 零漏失、成本上界 ≤1.5；不得把 D29 預設直接當成 BASH 通過。

2. **阻擋｜[categories.json:6](categories.json:6)、[catalog-local-paper/oracle.sh:20](frozen/cases/catalog-local-paper/oracle.sh:20)**：凍結測試明列「1,000 emoji」，目前卻放寬為任一非 ASCII；實際 oracle 只有四個中文字。補入明確的 1,000 emoji 情境與機械驗證，使用合法欄位／內容，避免只測到作業系統的檔名長度限制。

3. **阻擋｜[author_prompt.md:12](author_prompt.md:12)、[categories.json:4](categories.json:4)**：作者被指示讀取的分類檔直接寫出 N／D／F、配方消融方式與模型，與「看不到組別」的宣稱衝突。補存實際交付作者的去組別版本及雜湊；若交付的就是此檔，須重新盲出題，不能僅以新 session 證明盲性。

4. **阻擋｜[i16_run.py:89](i16_run.py:89)、[x2_case_tools.py:133](../X2/x2_case_tools.py:133)**：測試者仍能讀完整 `~/.claude`／`~/.codex`，包含歷史對話與其他組狀態；Codex 評分呼叫也只有 read-only sandbox，並未禁用工具或遮蔽 records。改用每次獨立的主機狀態，只提供必要認證；評分者另做檔案隔離，並以事件紀錄強制確認零工具呼叫。

5. **應修｜[i16_grade.py:84](i16_grade.py:84)**：`anonymous()` 只挑頂層欄位，沒有移除其中的組別、方法或 skill 路徑；`notes` 寫「followed full recipe」會原樣進評分。對報告與重播文字統一遮蔽明確的 treatment／host 標記，保存遮蔽前後雜湊。

6. **應修｜[i16_grade.py:165](i16_grade.py:165)**：對整份雙版本重播直接切前 9,000 字，會切斷 JSON，並優先刪掉後面的 clean build；四步的大輸出反例已重現。改成逐步、逐版本對稱裁切，保留每步結束碼與截斷標記。另將重播的 25 步／每步 60 秒限制寫進所有組的 TASK。

7. **阻擋｜[i16_run.py:377](i16_run.py:377)、[i16_replay.py:79](i16_replay.py:79)**：runner 未驗 `case_digests`；改掉 goal／fixture、但不改 OAW 原始碼，仍能被當成同一凍結案例。重播也未綁定 spec、來源及建置 digest，續跑只看 key/index。執行與重播前驗全部輸入；重播續跑須同時核對 report、spec、案例及建置雜湊。

8. **應修｜[i16_grade.py:127](i16_grade.py:127)**：grader 雜湊漏掉實際重用的 X2 `call()`／`cheap_call()`；replayer 雜湊也漏掉匯入的建置與環境函式。修改依賴後仍可混接舊結果。建立包含執行依賴的版本清單，續跑時連同 family、cell 與輸入雜湊一起核對。

9. **應修｜[i16_run.py:52](i16_run.py:52)**：`python3 ./oaw/scripts/oaw.py --help` 被算成 source read；`cat project/scripts/oaw_mode.py` 或先 `cd oaw` 再讀則漏算。因此排除分析會排掉正常黑箱操作，留下真正讀碼者。改按工具行為與解析後路徑分類，涵蓋安裝後副本；`tool_changed` 也應涵蓋實際執行的 `project/scripts`。

10. **應修｜[i16_judge.py:107](i16_judge.py:107)**：PREREG 允許換題一次後仍碰天花板就保留，但 judge 遇任何非空 `ceiling` 都拒判。記錄換題沿革及已用次數，明確接受第二次仍飽和的登記狀態，保留天花板警示。

11. **應修｜[i16_grade.py:91](i16_grade.py:91)**：檢查器接受 `valid_report=false` 同時 `planted_detected=true`，也接受 detected 與 mentioned-only 同時成立；前者會真的進偵測分數。加入交叉欄位約束，並將非物件項目等格式錯誤一致轉成 `NotGraded`，不得崩潰或留下矛盾評分。

12. **應修｜[i16_run.py:254](i16_run.py:254)**：先按 `cwd == work` 篩 rollout，再追父子關係，會漏算在子目錄工作的子 agent 及其後代，低估成本。先建立完整 thread ancestry，再依 root 歸屬計費；或明確禁用子 agent，並驗證沒有啟動。

13. **應修｜[remove-bundled-skill/oracle.sh:27](frozen/cases/remove-bundled-skill/oracle.sh:27)**：oracle 會把「exit 0 且已刪除使用者編輯的 skill」判成 PASS，也會接受不相關的非零失敗。成功條件須同時要求預期的拒絕結束碼／錯誤、編輯內容逐位元保留；其他執行錯誤回傳 2，不能視為乾淨通過。

驗證平台：Linux x86_64、Python 3.10.12；僅唯讀檢查與記憶體反例，未重跑會寫檔的 oracle。