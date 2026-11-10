# 能力型計畫第 4 版：升級審查 gpt-6-astra（2026-11-10）

Codex gpt-6.1-sol 三輪用完後，照 owner 的規則由 gpt-6-astra 和 Fable 5.1 各自獨立判斷第 4 版（records ea791fc）。原文照錄。用量：輸入 459,387（其中快取 390,144）、輸出 4,973 token。

---

先改再做
第 3 輪：#1 open（應修）；#5、#9、#10 closed（計畫層面）。

#1：完整墨跡的基準仍可能已被裁切；既有驗題淘汰規則可擋住，列應修。
#5：已取消全片缺失額度，改為逐剪接點確認及黑場兩側推算。
#9：已加入轉場主畫面的來源殘差檢查，原本「保留幀碼、替換主畫面」的缺口已處理。
#10：已固定亮度正規化、暗幀處理及單調容差，並要求有損編碼替代品驗題。

1. **阻擋；§5「亮度和增益」「畫面內容」：非轉場區也允許任意 gain，會把錯誤調暗判成正確。**  
   **反例：**需求要求保留素材，只在指定區間淡入淡出；成品卻把普通片段的主畫面乘上 `0.5`，幀碼、字幕、音訊和指定轉場全部正確。此時估出的 `g=0.5`，與「素材 × g」的殘差為零，因此通過；實際已違反保留素材的要求。§12 即使確認實作完全符合 §5，也不會排除這個錯誤判準。  
   **最小修法：**只有需求允許的轉場區間可估 gain；其餘區間以 `g=1` 對照素材。低 gain 的豁免同樣限於指定轉場區間，補上「普通片段被調暗」反例。

2. **應修；§5「算繪後完整看得見」：隔離文字框不保證得到完整墨跡。**  
   **反例：**文字被框本身的 clipping 裁掉部分筆畫；隔離後仍保留同一 clipping，基準圖與整頁圖都缺相同筆畫，覆蓋率仍是 `1.0`。§4 已要求裁切反例不通過、偵測不穩就淘汰，因此不另列阻擋。  
   **最小修法：**基準墨跡須來自解除裁切、保留原排版的獨立算繪，並涵蓋頁面外區域；明確加入「基準與成品同時被裁切」反例。

讀過檔案：`CLAUDE.md`、`AI_CONTEXT.md`、`VERSION.json`（指定兩欄）、`docs/knowledge/CURRENT_STATE.md`、`.agents/skills/{read-discipline,harness-evaluator}.md`、`scripts/memory_nudge.py`、`OAW-records/{AGENTS,CLAUDE}.md`、`OAW-records/records/v2.0.1-experiments/capability/{PLAN,review-1,review-2,review-3,CANDIDATES}.md`、`OAW-records/records/v2.0.1-experiments/H1/PREREG.md`、`OAW-records/records/digestion-2026-11-03/ingest/DECISIONS.md`（D21、D26、D28、D35、D38、D41）；另核對指定的 `a2aed61..ea791fc` diff。