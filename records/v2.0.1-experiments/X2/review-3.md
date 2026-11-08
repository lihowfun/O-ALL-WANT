fix first

以下「前1–12、追加1–6」對應 `review-2.md`；已解決項沿用原嚴重度。路徑均相對於 X2。

- **Blocker｜前1：已解決** — `x2_judge.py:214`：最高平均平手且未證明等價時，保持未定。
- **Major｜前2：已解決** — `PREREG.md:24,30`：主分析使用新案例，舊案例只描述。
- **Major｜前3：部分解決** — `x2_grade.py:109`：未知 ID 已拒收，但 `[{}]`、`[""]` 仍算 unsupported claims。修正：要求每項具非空 `claim`、`why` 等完整結構。
- **Major｜前4：已解決** — `x2_run.py:102,145`：Claude 逾時保留輸出，串流用量記為下限。
- **Major｜前5：已解決** — `x2_judge.py:197`：兩家均須確立 unsupported claims 的非劣性。
- **Major｜前6：部分解決** — `x2_build_spec.py:129`、`x2_judge.py:82`：缺作者案例已拒收，但校準案可縮成兩案，缺 `planned_primary` 也照常判定。修正：強制核對原始名單、合法刪案及三分區，校準不足三案即停止。
- **Major｜前7：部分解決** — `PREREG.md:149`：例外透明，但以「否則無法過關」豁免 unsupported 敏感度，規則偏向過關，不能接受為穩健性驗證；上界 0.620 表示精度不足。修正：高 floor 下非劣性失敗也保持未定，或事先增加樣本。
- **Major｜前8：部分解決** — `x2_run.py:261`：無根 rollout 時已補父成本；根檔存在但缺 token_count 時仍漏算，合成資料應為 1,300，實記 200。修正：逐 thread 驗證 usage，根資料不完整時回退串流並標記缺漏。
- **Major｜前9：已解決** — `x2_case_tools.py:110`：普通 `rate limiter` 不觸發 quota 判定。
- **Major｜前10：部分解決** — `x2_run.py:375`、`PREREG.md:70`：wait 已不算 agent，但任意五次啟動仍能冒充完整 EGM。修正：核對必要階段、唯一 reviewer、完成回報與 fresh context。
- **Major｜前11：部分解決** — `x2_judge.py:100,123`、`x2_grade.py:186`：缺 runner/grader hash 仍能選 E；評分來源未重新核對 case digest。修正：建立必填 manifest，涵蓋 prompt、來源、安裝內容、評分 helper、校準及 floor，續跑重驗。
- **Minor｜前12：已解決** — `x2_run.py:363,383`：各次嘗試保留獨立 transcript 與報告 artifacts。
- **Major｜追加1：部分解決** — `x2_build_spec.py:36,46`：空 verdict 已拒收，但 ledger 順序不能證明傳入 verdict 核的是現行案例，重複矛盾 ID 也可通過。修正：將核實呼叫綁定來源與 rubric digest，嚴格驗證 schema 和唯一 ID。
- **Major｜追加2：部分解決** — `x2_calibrate.py:40,52`：完整唯一身份格已檢查，但舊 spec、不同報告的評分仍成功產生 floor。修正：核對 report/spec/case/version 綁定，並讓 judge 驗證 floor 的來源。
- **Major｜追加3：已解決** — `x2_judge.py:178,180`：每主機三組比較採校正區間；主機各自下結論的家族範圍已寫明。
- **Major｜追加4：已解決** — `x2_judge.py:218`：跨供應商 token 不再直接競價，成本結論已限制。
- **Major｜追加5：部分解決** — `x2_grade.py:193`、`x2_case_tools.py:128`：評分失敗新增 deviation，但 usage 記成 null、原始輸出遺失；出題／核實仍直接退出。修正：所有呼叫在退出前保存完整輸出、可得 usage 與失敗列。
- **Minor｜追加6：已解決** — `x2_judge.py:8,23`：說明與範例已同步非劣性門檻及 `floor-final.json`。
- **Major｜新增** — `x2_build_spec.py:96,102`：乾淨案的 trap 被判 `correct:false` 時，只刪 rubric，案例仍保留為乾淨；合成測試確認。修正：修正來源後重核，或剔除該案例。
- **Major｜新增** — `x2_run.py:282`：timeout 分支先於零 token 檢查，從未開始的零用量逾時也算有效作答，違反 D30。修正：先拒絕零 token，再處理有效作答逾時。
- **Minor｜新增** — `PREREG.md:168,191`：檢定力未涵蓋強制敏感度判定；x1.5 時等價區間半寬約 0.115，超過 0.10，八成檢定力所需改善約 22.6%。修正：更新完整決策程序的檢定力與限制。

驗證：Linux x86_64、Python 3.10.20；唯讀、記憶體內合成測試，未呼叫模型。凍結 `eval_stats.py` 的 SHA-256 與登記相符。