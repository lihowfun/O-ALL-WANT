# Harness² 論文怎麼驗證（arXiv:2610.14224，2026-11-17 讀）

由一個讀網頁的 agent 抽取，lead 沒有另外逐字核對。來源：`https://arxiv.org/html/2610.14224`。
正文到第 5 節與附錄 H 的 prompt 是逐字讀到的；附錄 B–G 只有模型摘要，下面標「摘要」的都要再核對才能對外引用。

## 設定
- 題庫：WorkBuddy-Bench（Code／Web／Office）、JobBench、LAB。測試題數（摘要）：WorkBuddy 40／35／25，JobBench 34，LAB 100。
- 執行的模型：Gemini 3.5 Flash、GLM-5，各在 OpenCode 與 Codex 下，權重不動。編輯者：Claude Opus 4.8。
- 每個數字：「means and standard deviations over three runs, each with a shuffled task order」。沒有信賴區間或檢定。
- 「open world」的操作定義：方法拿不到正確答案或有標註的驗證回饋，只看一次參考執行與各改法之間的行為差異。

## 主要結果（k=1，一步）
- WorkBuddy 平均：GLM-5/OpenCode 64.2 → 75.7（+11.5，標題數字）；Gemini/OpenCode 72.4 → 77.5。
- JobBench：Gemini/OpenCode 31.5 → 36.0（+4.5）；GLM-5/OpenCode 20.6 → 24.2。
- LAB Partial：GLM-5/OpenCode 59.6 → 71.4（+11.8）；Gemini/OpenCode 79.9 → 81.9。
- 對照方法有變差的：ReasoningBank 在寫程式題比原樣低最多 6.6 分；Harness Scaling 12 組裡 7 組低於原樣。

## 拿掉零件
- 表 3（k=1，WorkBuddy／JobBench）：完整 77.5／36.0；沒有 library 74.4／34.2；沒有分工 74.6／32.3；沒有組合 75.9／34.1。各只跑一次，沒有標準差。
- 表 6（摘要）：從改好的 harness 拿掉提示類 79.3、拿掉 skill 75.5、拿掉腳本 77.1（完整 80.8）。作者說這不代表效果可以相加。
- 不看執行紀錄直接改：Code 73.4 → 63.2、Web 69.9 → 65.0（變差）。
- 加大預算（k=1→5）：增益 JobBench 4.5 → 7.5、WorkBuddy 5.1 → 8.4。「Increasing test-time exploration alone therefore does not ensure better performance.」

## 轉移
- 用 JobBench 得到的 library 去做 WorkBuddy：+0.6、+0.5、+2.9。作者標明是事後分析。
- 編輯者與執行者用同一個模型（k=2）：五個模型在每個題庫都有進步；Opus 5 是 +3.3、+5.5、+3.0，GLM-5 在 LAB +13.7。
- 跨執行者（摘要）：增益隨執行者與領域差很多。

## 成本
- 圖 6 把交出成果前花的所有 token 都算進去，包含改進的花費。沒有找到每題金額、也沒有找到「同樣次數的多跑幾次挑最好」的等成本對照。

## 作者自己講的限制
- 「execution stochasticity and shared model biases limit the reliability of the evidence.」被採用「not verified optimality」。
- 失敗分析（摘要）：9 個變差的案例，分三類：挑選者挑了較弱的、錯的前提被帶下去、執行變動與缺判定。

## 哪些零件最常被改（摘要）
- skill 與腳本約佔每個題庫一半的修改。拿掉後平均掉分：skill 5.3、腳本 3.7、提示類 1.5。

## 讀的人自己的觀察
- JobBench 的評分者與編輯者都是 Claude Opus 4.8，可能有共同的偏好；讀到的範圍內論文沒有討論。
