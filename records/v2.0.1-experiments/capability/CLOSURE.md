# PPT 校準收束：停止，候選未判定

2026-11-13。依照本次「按 review 規劃開始動工」的指示，採用
[進度 review 第 5 節](../../review-2026-11-13/REVIEW.md#p1-bppt-選題被-checker-的限制主導)
的收束建議。這一輪停在凍結前，不進正式候選比較。原始
[CALIBRATION.md](CALIBRATION.md)、題目、checker、選題與帳本原樣保留。
本頁是後續狀態，不回寫先前的「等待決定」。

## 為什麼停止

12 題原生 Codex 校準有 6 題通過。其餘 4 題只因 checker 拒收
`LINE_MARKERS`，題目卻沒有禁止折線圖的資料標記點；另 2 題只因
`word-out` 行框檢查，其受影響標題的既有紀錄皆為筆畫 outside=0、
coverage=1.0。選出的四題中三題屬於前者。這些區分不足以支持本輪
原想量測的簡報能力改善，不能把 checker 的偏差當作候選可改善空間。

本次只重讀並核對既有結構化紀錄：12 筆、6 過、5,019,891 Codex tokens；
選題為 p2-t2、p2-t5、p3-t1、p3-t2。三位出題名額已用完，p1 作廢仍占名額。
本機與 records 均無此輪 FREEZE，state 無 main starts／rows。沒有重新評分、
補題、改題或新模型作答。逐題摘要與來源 SHA-256 見
[CLOSURE_EVIDENCE.json](CLOSURE_EVIDENCE.json)。

## 清單狀態與成本

| 候選 | 本輪評估狀態 | 本次安裝變更 |
|---|---|---|
| OfficeCLI | 未判定：校準停止，未進正式比較 | 無 |
| huashu-design | 未判定：校準停止，未進正式比較 | 無 |
| professional-pptx | 未判定：校準停止，未進正式比較 | 無 |

這不是 decline，也不改為 adopt。使用者仍可按自己的需求選裝能力套件；
這份紀錄只約束本輪的測量結論，不代表已證明它們沒有價值。

已記錄的成本分開保留：Codex 出題 2,303,470 tokens（包含作廢 p1）、
校準 5,019,891；Claude 探針／暖機 712,093（含 spent_before）；原文件另報
實驗外 Fable code review 1,195,171。它們不是完整研究成本；controller 工程
與本次收束 review 未另行計量。本次新增實驗作答為 0，沒有把預估續跑
13–23M Claude tokens 當成已支出，也沒有把它算成量測過的節省。

## 重啟條件

由實際 PPT 交付需求提出可觀察的能力缺口，再寫清凍結前 amendment：
題目與 checker 一致、可見溢出與行框的關係、平台／算繪範圍，以及作者名額
與既有校準如何處理。先重新確認可量測空間與 pilot 成本，再取得需要的
預算授權；不沿用本輪四題悄悄改規則或直接凍結。美感沒有在本輪量測。

影片仍保留原先 ffmpeg 與實際能力需求的條件；本次停止不代表取得 PPT
能力，更不自動啟動下一個實驗。發佈仍先完成 FIXCHECK、CI 與 owner gate。

## 獨立核對

Fresh-context reviewer `ppt_closure_review`：**4/4 PASS**。它從原始 state
重算校準／成本，核對 7 個私有來源、5 個原始文件及 12 個 grade 摘要的
hash；確認三候選未判定、重啟限制與原始文件未變。本輪僅審查 PPT 收束，
不包含同批 FIXCHECK 進度更新，也不是產品收益或發佈 review。
