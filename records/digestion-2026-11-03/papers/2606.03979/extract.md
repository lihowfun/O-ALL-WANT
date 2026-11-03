# arXiv 2606.03979 萃取：Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories

- 作者：Ali Behrouz、Adel Javanmard、Vahab Mirrokni（Google）、Farnoosh Hashemi（Cornell）
- 版本：v2，2026-07-10，CC BY 4.0。註記：此工作自 2025-09 起已在 OpenReview 公開（作者以此主張早於 OPSD 系列論文，見 §A.2/A.4）
- 本地檔案：
  - HTML：`papers/2606.03979/paper.html`
  - PDF：`papers/2606.03979/paper.pdf`
  - 純文字：`papers/2606.03979/paper.txt`
  - 從 PDF 抽出的圖檔：`papers/2606.03979/figs/`（Fig 3 = obj855/856/857，Fig 4 = obj858/859/854，Fig 5 = obj860，Fig 6 = obj861）
- 說明：圖表裡的數值是我從 bar/line chart **目測讀出的近似值（誤差約 ±1）**，論文本身沒有附數值表；表格（Table 1–5）的數字則是原文。我在 paper.txt 掃描過，沒有發現針對 LLM 的注入指令。

---

## 1) 問題與動機

- **核心問題**：LLM 部署後是靜態的（knowledge cutoff）。現有更新途徑各有缺陷：(a) re-pretraining 太貴；(b) 反覆 fine-tuning/LoRA 會導致 Catastrophic Forgetting (CF)；(c) In-Context Learning (ICL) 雖然是很有效的 continual learning，但受限於 context window，session 一結束知識就消失（§1）。
- **類比**：anterograde amnesia（順行性失憶），也就是 LLM 只有「當下 context」和「pre-training 結束前的久遠記憶」，沒辦法把短期記憶轉成長期記憶（§1）。
- **兩種 consolidation**（§1、§3.1，承接 Nested Learning / Hope）：
  - *Online consolidation*：清醒時、學習後立即進行。先前的 Hope / Continuum Memory System (CMS) 做的就是這種。作者指出它的不足：(i) 容量不變，知識停在同一抽象層級，沒有額外的 lossy compression；(ii) 是 selective、retrieval-dependent 的，只會強化被反覆 recall 的部分；(iii) 只依賴當前 context，缺乏新舊知識的高階整合。
  - *Offline consolidation（systems consolidation，睡眠）*：這是本文的焦點。
- **人腦啟發**（§1 "The Role of Sleep"）：NREM/slow-wave sleep 對應 synaptic homeostasis 與 hippocampus→neocortex 的 consolidation，作者強調這不是單純 replay raw data，而是重組並抽取 abstraction；REM 對應 dreaming，負責強化新 synapse、和既有網路整合、模擬未來情境。
- **典範主張**：continual learner 沒有 train/test 的區分，應改為週期性的 **Wake（active，接收外部資料）/ Sleep（幾乎不接收外部輸入，專注處理內部知識）** lifecycle（§2.3、§3.1、Fig 1）。
- **背景框架 CMS（§2.2）**：Transformer 被視為兩層記憶。attention 是無限頻率更新（context 結束就遺忘），MLP 是零頻率（pre-training 後不再更新）。CMS 把 MLP 改成一串各有更新頻率 f_ℓ 的 MLP blocks，第 ℓ 個 block 每 C^(ℓ) 步把累積的梯度套用一次（Eq. 1–2）。高頻 block 是短期記憶，低頻 block 是長期記憶。CF 發生在各模組的更新週期剛好對齊的時候，所以作者主張：**每個 memory block 更新之前，都必須先把它的抽象知識 consolidate 到更穩定的參數**。

---

## 2) 方法元件

整體上 Sleep 分兩階段：**(i) Memory Consolidation（對應 NREM）** = Parameter Expansion + Knowledge Seeding；**(ii) Dreaming（對應 REM）** = 以 RL 學習產生自我訓練資料的 self-modifying 過程。

### 2.1 Sleep 觸發時機 / Periodic Parameter (De)Activation（§3.2、Contribution 1）
- Sleep 只在 step 數為 {C^(1)·b, …, C^(k)·b}（b ∈ ℕ）時觸發，也就是某個 faster block 即將更新 base weights 的時候。
- 快 block 在慢 block 更新一次之前可能已更新多次（例如 1K vs 10K 時是 10 次），所以要 consolidate 進慢 block 很多次，這正是 CF 的瓶頸。作者把它歸因為 **容量不足**。
- 解法是 neuroplasticity 式的 gradual parameter expansion：每次 sleep 時，在接收方 block 新增（解鎖）參數，並在發送方 block 停用/重置參數。

### 2.2 Parameter Expansion（§3.2、Fig 2）
- 假設每個 MLP^(f_ℓ) 是 sparse MoE（router R^(f_ℓ)，目前有 s_ℓ 個 experts）。
- 要把 block ℓ*−1 consolidate 進 block ℓ* 時，在 ℓ* **新增一個 low-rank expert {A ∈ ℝ^{d×d_low}, B ∈ ℝ^{d_low×d}}（d_low ≪ d）**，專門存放這次轉移過來的知識，以避免和既有知識互相干擾。每次 sleep 後，部分層的參數量都會增加。
- 實作註記（§3.3 "Note on the Implementation"）：參數事先就配置好，啟用前在 forward/backward 都被 mask 掉，所以不必真的改 tensor 維度。作者把這比喻成大腦容量固定、只解鎖新連結。
- Appendix B：使用「5 個維度 64 的 MLP blocks」作為額外參數，active parameter 數維持與 base model 相同（8B 或 3B）。

### 2.3 Knowledge Seeding (KS) / Self-Knowledge Seeding (SKS)：upward distillation（§3.3）
- **定義**：一個或多個較小的模型把知識 distill 到較大的模型（方向和一般 KD 相反，所以叫 upward）。SKS 則是「較小版本的自己」（部分參數未啟用）distill 到「較大版本的自己」（新參數已啟用）。
- **compute–consolidate–update 協定**：
  - (a) *Compute*：用累積梯度算出發送方 block 的 prospective 新權重 θ_new，**先不套用**。
  - (b) *Consolidate*：Teacher = 更新與擴張前的模型；Student = 套用 θ_new（並重置發送方 block 的 experts）、且在接收方 block 新增 low-rank expert {A,B} 的模型。**只優化 A、B**，其他參數全部凍結。
  - (c) *Update*：套用 θ_new、把發送方 block 先前累積的 low-rank experts 重置（作者類比為 *synaptic pruning*，釋放容量給未來使用）、啟用新的 {A,B}。
- 作者點出兩個挑戰：(1) student 比 teacher 大，直接用 teacher 產生的資料做 sequence-level KD（如 Kim & Rush）會讓參數用得不夠好；(2) 睡眠時拿不到外部資料，所以 Hinton 式需要資料集的 KD 不適用。
- **Generalized Knowledge Distillation (GKD) 部分**（承接 Agarwal et al. 2024）：先從 teacher 取樣建立資料集 D。loss = (1−λ)·E_{(x,y)∼D}[F(teacher‖student)(y|x)] + λ·E_{x∼D} E_{y∼student}[F(teacher‖student)(y|x)]。其中 F 是 divergence，λ 控制 on-policy（student 自己生成）樣本的比例。不對 student 的 sampling 分佈做 backprop（為了穩定與速度）。
- **Learning to Imitate (LTI)，RL-based imitation**：作者觀察到「student 雖然擁有知識，但還不會使用，對 teacher sampling 行為的模仿很弱」。做法是：teacher 生成 dreams D_T = {d^(i)}，隨機截取 prefix，由 student 續寫出 d̂^(i)。reward 為
  - r = γ·r_sem + (1−γ)·r_abs（Eq. 3）
  - r_sem：用**凍結的 reward model** 判斷語意是否相同，給 binary 1/0
  - r_abs：Levenshtein distance z 不超過門檻 z_0 時給 1 − z/max(|d̂|,|d|)，否則給 0（Eq. 4）
- **最終 KS objective**：L_KS = E_x[(1−α)·E_{y∼student}[r(y)] − α·E_{y∼student}[D(teacher‖student)(y|x)]]，α 控制 distillation 與 LTI 的權重。
- 文中未報告的超參數：λ、α、γ、z_0、divergence 的種類、reward model 是哪一個、取樣數量，論文都沒寫。

### 2.4 Replay
- 摘要說 distill 時會「with replay」。實際上方法中**沒有保存 raw wake data 的 replay buffer**，所謂 replay 是讓 teacher（睡前狀態）**自己生成樣本**（D 與 D_T，作者也稱為 dreams），再用這些樣本做 distillation 與 imitation。§3.3 明確表示 consolidation 不應只是 replay raw data，而要 explore 並抽取 abstraction。Dreaming 階段的目的則是「rehearse new knowledge」（摘要、§3.4）。

### 2.5 Dreaming：Self-Modifying Process（§3.4，建構在 SEAL 之上）
- 定位：任何 self-improvement 的 synthetic data 生成方法都可以放進來。本文以 SEAL（Zweiger et al. 2025）作為 proof of concept。
- 作者指出 SEAL 放進 sleep 典範後的問題（文中寫「三個」，列出 (1)(2)(3)）：(1) inner-loop 的 SFT 成本高，因此 self-edit（dream）數量有限；(2) 反覆 self-improvement 會造成 CF；(3) 取樣只能在模型既有的知識空間內，但 dreaming 應該要探索記憶的新組合。
- 流程：給定任務 (C, τ)，C 是相關 context，τ 是下游評估指標。
  1. 把 C 放在 context 中，生成 m 個 dreams：{DREAM^(i)} ∼ LM_θ(·|C)。
  2. **Random Expert Selection**（Contribution 4）：取樣時，每個 MoE router **額外隨機選一個 expert**，把隨機、不相關的知識混進來，讓模型學到平常看不到的潛在模式。
  3. **Gradient-based selection**：每個 dream 的 importance score 依據 g^(i) = ∇_θ L_SFT(DREAM^(i), θ) 計算（參考 LESS 等 gradient-based data selection）。取 **Top-k，再加上 b 個隨機樣本**以維持多樣性。（論文沒有說明如何把梯度向量轉成純量分數，例如 norm 或與目標梯度的 alignment。）
  4. 對每個被選中的 dream，用一個**獨立的模型副本**做 LoRA SFT，得到 θ'^(i)。
  5. Reward：如果 θ'^(i) 在 τ 上比 θ^(i) 進步，reward 為 1，否則為 0（Eq. 5）。
  6. 依照 SEAL，用 **ReST^EM**（rejection-sampling 加 EM 式 SFT）優化 dream 生成策略。
- **Self-modification 的兩層意義**：(a) 結構層，模型在每次 sleep 時自行解鎖/重置參數（擴張與剪除容量）；(b) 資料層，模型透過 RL 學會產生能改善自己的訓練資料（SEAL 式 self-edit），再用這些資料更新自己。
- **兩階段順序的理由**（§3.4、§A.4 "Limitations of OPSD"）：先 consolidation（把新知識穩定到新擴張的低頻參數），再 Dreaming 修改模型，作者主張這樣可以降低 iterative self-training 覆寫既有能力的風險。

### 2.6 附錄中的結構示意
- Fig 7：multi-frequency hierarchy，High→Mid→Low frequency FFN（1k→5k→10k）。updates 經由反覆的 Parameter Expansion 進入高頻 FFN，window 到期時再 consolidate 到中頻、低頻。
- Fig 8：每個 sleep cycle 由 router 選出少量 experts 來更新，其餘維持 inactive，在擴張容量的同時限制干擾。

---

## 3) 實驗

共通設定：照各 benchmark 的原始設定，細節多半指向原論文（Appendix B 開頭）。**所有結果都沒有 error bar、seed 數或統計檢定。**

### 3.1 Class-Incremental Learning（§4.1、Fig 3，只有 consolidation，沒有 dreaming）
- 資料：CLINC150（150 intents、23.7K）、Banking77（77 intents、13,083 筆）、DBpedia（70 類 level-2，抽樣 10K train / 1K test）（§B.1）
- Backbone：Llama-3B、Llama3-8B；metric：Accuracy
- Baselines：ICL（同樣的 continual pre-training，但沒有 sleep）、EWC、InCA（Momeni et al. 2025）、Hope（multi-level in-context updating，沒有明確的 distillation）
- 目測數值（ICL / EWC / InCA / Hope / Sleep）：
  - CLINC：3B 約 58 / 61 / 64 / 69 / 77；8B 約 78 / 80 / 88.5 / 93 / 97
  - Banking：3B 約 51 / 54 / 59 / 64 / 69；8B 約 72 / 75 / 80 / 84 / 92
  - DBpedia：3B 約 35.5 / 39 / 40.5 / 42 / 47.5；8B 約 70 / 71 / 77.5 / 82 / 89
- 命名問題：caption 與正文都寫「Hope 表現最好」，但圖中 Hope 和 Sleep 是兩根不同的 bar，Sleep 最高、Hope 第二。正文中「Hope」看起來指的是「Hope + Sleep consolidation」，用法前後不一致。

### 3.2 記憶層數 / 睡眠排程對 long-context ICL 的影響（§4.1、Fig 4）
- 資料：MK-NIAH（RULER）、LongHealth（20 份病例文件、200 題）、QASPER（以全文為 context，metric 是 perplexity，越低越好）（§B.1）
- Baselines：ICL、DuoAttention、Cartridges
- 變數：memory levels（consolidation 階段數）1–4 × 最低 consolidation 頻率 {512, 2K, 8K}
- 目測數值：
  - MK-NIAH：ICL 約 88.5、Cartridges 約 91、Duo 約 47；Sleep 在 freq=512 時隨 level 1→4 從約 92 升到約 100，8K 時從約 90.7 升到約 95
  - LongHealth：ICL 約 48.7、Cartridges 約 52、Duo 約 39；Sleep 在 512 時 1→4 從約 52.1 升到約 59.1，2K 時從約 50.9 升到約 56.9，8K 時從約 50.7 升到約 55.5。**level 1、freq 2K/8K 的結果低於 Cartridges**
  - QASPER（ppl）：ICL 約 3.53、Cartridges 約 3.32、Duo 約 4.1；Sleep 在 512 時 1→4 從約 2.42 降到約 2.10，8K 時從約 2.49 降到約 2.24（8K 在 level 2 微升到約 2.52，並非單調）
- 作者結論：(1) consolidation 階段越多越好；(2) 提高最低頻率（讓最持久的記憶更容易變動）會損害 retention。

### 3.3 Continual Translation of a Novel Language (CTNL)（§4.1，圖是 Fig 5，正文誤寫成 "Figure 6"）
- MTOB（Kalamang→EN）加 Manchu→EN，兩者都是 pre-training 沒見過的語言；metric 是 ChRF
- 兩種設定：單一語言（紅點），以及依序學兩種語言（continual，藍點）
- 目測（Manchu, MTOB）：
  - ICL：單一語言約 (20.9, 35.4)，**continual 崩到約 (10.1, 15.4)**
  - Sleep-1：單一約 (21.0, 36.2)，continual 約 (21.0, 35.6)
  - Sleep-2：單一約 (22.4, 36.1)，continual 約 (22.6, 37.2)
  - Sleep-3：單一約 (22.7, 36.0)，continual 約 (23.9, 38.1)
- 正文說 Hope-3 在 continual 設定下「接近恢復」單一語言的表現，但圖上 Sleep-2/3 的 continual 結果其實**高於**單一語言，這點反常，作者沒有解釋。Cartridges 和 SFT 被描述成「至少有一種語言 CF、比 ICL 更差」，落在圖外，沒有給數值。

### 3.4 BABILong（§4.1、§B.2、Fig 6）
- 正文說的比較對象：GPT-4、GPT-4o-mini、Llama-8B + RAG、RMT、ARMT、Titans。小模型都依官方 BABILong protocol fine-tune 過。
- **圖上實際只畫了 4 條線**：Llama3+RAG、Llama3.1-8B-Instruct、GPT-4、Llama+Sleep。RMT/ARMT/Titans/GPT-4o-mini 都不在圖中；caption 說的紅點/藍點在圖中也不存在。
- 目測：Llama+Sleep 在 0–16K 約 99，32K–128K 約 95–96，1M 約 93，**10M 約 91**。GPT-4 在 0 時約 87，128K 降到約 36。Llama3.1-8B-Instruct 在 128K 約 45。RAG 從約 48 慢慢降到 10M 時約 37。
- 作者自述的限制：所有小模型（包括 Hope）在沒有 fine-tune 時都會大幅退步（§B.2 最後一段）。
- 正文說「almost perfect score」到 10M，但圖上 10M 約 91%。

### 3.5 數學推理（§4.1 "Memory Consolidation for Reasoning"、Table 2，只有 consolidation）
- Qwen3-1.7B / Qwen3-8B，avg@16，數值如下：

| Model | Method | AIME-24 | AIME-25 | HMMT-25 |
|---|---|---|---|---|
| Qwen3-1.7B | Base (Instruct) | 49.8 | 34.5 | 25.7 |
| | SFT | 47.3 | 36.1 | 22.9 |
| | GRPO | 51.0 | 38.6 | 26.1 |
| | OPSD | 51.6 | 40.0 | 28.1 |
| | **Sleep** | **53.2** | **40.2** | **29.3** |
| Qwen3-8B | Base (Instruct) | 73.8 | 68.1 | 42.4 |
| | SFT | 75.5 | 66.4 | 43.7 |
| | GRPO | 76.4 | 68.1 | 44.9 |
| | OPSD | 76.6 | 67.4 | 45.1 |
| | **Sleep** | **79.2** | **69.0** | **46.1** |

- 訓練設定（Table 5）：LR 5e-6、effective batch 32、steps 為 GRPO 500 / SFT 100 / Sleep 100、LoRA r=64、α=128。**訓練資料是什麼、consolidation 在標準 Transformer（Qwen3）上如何定義高頻與低頻 block，都沒有說明。**

### 3.6 Consolidation 消融（§4.2 正文寫 "Figure 6"，實際是 Table 1，Qwen3-8B）

| Variant | AIME-24 | AIME-25 | HMMT-25 |
|---|---|---|---|
| Sleep（完整） | 79.2 | 69.0 | 46.1 |
| − Imitation Learning | 76.8 | 67.9 | 45.0 |
| − Semantic Reward | 78.9 | **69.2** | 44.5 |
| − w/o Expansion | 78.2 | 67.9 | 44.9 |
| OPSD | 76.6 | 67.4 | 45.1 |
| OPSD + Expansion | 77.9 | 68.2 | 45.9 |

- 作者說「所有元件都有正貢獻」，但在 AIME-25 上拿掉 semantic reward 反而比完整版高 0.2。各元件的效果都在 0.2–2.4 分之間。

### 3.7 Knowledge Incorporation（§4.1、Table 3，正文寫 "Table 4.1"，完整 Sleep 含 Dreaming）
- 照 SEAL 的設定（模型與參數都相同，正文沒有寫明是哪個模型）。SQuAD，無 context 回答，metric 是 accuracy。n=1 為單一 passage；CPT 為 n=200 passages、974 題、每個 passage 取 5 個 dreams 合併訓練。

| Method | n=1 | CPT n=200 |
|---|---|---|
| Base model | 31.9 | 31.9 |
| Fine-tuned, no dreaming | 33.4 | 32.0 |
| SEAL | 46.7 | 43.2 |
| Sleep (Transformer，2-level) | 48.1 | 44.3 |
| Sleep (Transformer + four-level) | **48.9** | **46.2** |
| − gradient-based selection | 47.1 | 45.2 |
| − random expert | 48.0 | 44.7 |
| − Dreaming | 35.7 | 36.2 |

- 解讀：拿掉 Dreaming 會掉 13.2 / 10.0 分，Dreaming（SEAL 式）是主要來源。consolidation 與層數比 SEAL 多 1.4–3.0 分，gradient selection 約貢獻 1.0–1.8 分，random expert 約 0.9–1.5 分（以 four-level 為比較基準）。

### 3.8 Few-shot ARC（§4.1、Table 4、§B.3）
- Llama-3.2-1B；過濾後 11 個訓練 task、**8 個 held-out 評估 task**。每個 task 取樣 60 個 dreams、拒絕 45 個。測試時每個 task 生成 5 個 dreams，各自獨立套用。metric 是「答對的 dreams 比例」。
- ICL 0%、TTT（+synthetic，無 dreaming）10%、SEAL 72.5%、**Sleep 80%**
- 用 8 task × 5 dreams = 40 次推算：80% 約 32/40，72.5% 約 29/40，差距約 3 次。

### 3.9 效率（§B.5）
- 相同 step 數下，SFT 比 Sleep 快 4 倍。作者另外宣稱「要達到相同表現時，SFT 需要 4.3x / 3.6x / 4.8x 的 wall-clock」（AIME-24/25/HMMT-25）。但 Table 2 中 SFT 在部分設定甚至低於 base（例如 1.7B 的 AIME-24 是 47.3），SFT 如何訓練到同等表現沒有說明。

---

## 4) 作者陳述的限制與威脅，以及我觀察到的效度問題

### 4.1 論文本身提到的（沒有專門的 Limitations 章節，以下散見各處）
- iterative self-improvement 在 continual 設定下有 CF 風險（§3.4，引用 Zweiger et al.）。
- SEAL 的 inner-loop SFT 成本高，限制了 dream 數量（§3.4 挑戰 (1)）。
- 直接改變 tensor 維度實作困難，因此改用預先配置加 mask（§3.3 implementation note）。
- OPSD 的失效模式：privileged teacher 會壓抑 epistemic verbalisation，導致 OOD 最多下降 40%（Kim et al. 2026）；naïve iterative self-distillation 會出現 information leakage 與 training collapse（§A.4 "Limitations of OPSD"）。作者把 Sleep 的兩階段設計當成對策，但**沒有直接實驗驗證**。
- 小模型（包括 Hope）在 BABILong 上不 fine-tune 會大幅退步；低頻層需要足夠容量（§B.2）。
- 相同 step 數下計算成本約為 SFT 的 4 倍（§B.5）。
- Fig 4 的 trade-off：最低頻率越低，記憶越持久但適應性越差（§4.1）。

### 4.2 我觀察到的效度威脅
1. **沒有 variance、seed 或信賴區間**；許多結果只有圖、沒有數值表。
2. **圖文不一致**：Hope 與 Sleep 命名混用（Fig 3、Fig 5 legend 寫 Sleep-1/2/3，正文寫 Hope-1/2/3）；CTNL 寫成 "Figure 6"；消融寫成 "Figure 6"（實際是 Table 1）；Table 3 寫成 "Table 4.1"；BABILong 正文列的 baselines 不在圖中，caption 的紅/藍點也不存在；「almost perfect」到 10M，圖上卻約 91%。
3. **規格不足以重現**：λ、α、γ、z_0、divergence、reward model、gradient importance 如何轉成純量、math 的訓練資料、Qwen3/Llama 上 CMS 的層級與頻率如何設定、sleep 次數、dream 數量（除了 ARC 與 SQuAD 之外）都沒有交代。
4. **比較條件不對等**：BABILong 的 Sleep 經過 fine-tune，GPT-4 則是 zero-shot；GRPO 跑 500 steps，Sleep 跑 100 steps，但每步成本不同；baseline 的設定細節多半只「指向原論文」。
5. **小樣本**：ARC 只有 8 個評估 task；LongHealth 只有 200 題。
6. **歸因不清**：Knowledge incorporation 的增益大多來自 SEAL 式 Dreaming；consolidation 本身的邊際貢獻只有 1–3 分。
7. **兩階段設計能抗 CF 的主張缺乏專門實驗**：§3.4 寫「In our evaluation, we show…」，但沒有任何實驗量測多個 sleep cycle 之後舊能力的保留情況（CTNL 最接近，但沒有 dreaming）。
8. CTNL 中 continual 結果優於單一語言，這個反常現象沒有解釋。
9. 生物學類比（NREM/REM、synaptic pruning）只是動機，沒有被檢驗。

---

## 5) 十個最重要的主張：證據位置與強度

（強度分為 強 / 中 / 弱。位置以章節、段落標題、圖表標示。）

| # | 主張（改述） | 證據位置 | 證據強度與理由 |
|---|---|---|---|
| C1 | 只靠 memory consolidation（不含 dreaming）就能在 class-incremental learning 上贏過 ICL、EWC、InCA、Hope | §4.1「Class Incremental Learning」段末三句；Fig 3（三個資料集 × 兩個 backbone） | **中**：6 組設定全部一致，差距明顯（例如 Banking 8B 約 92 vs Hope 約 84）。但沒有 error bar，數值只能從圖讀，Hope/Sleep 命名混淆，baseline 設定外包給 Momeni et al. |
| C2 | consolidation 階段越多，long-context ICL 越好；最低頻率越高（最持久的記憶越易變），retention 越差 | §4.1「The Effect of Levels (#Sleep Phases)」段末 (1)(2)；Fig 4 | **中**：3 個 task × 3 種頻率的趨勢大致單調（QASPER 8K 在 level 2 例外）。但 level 在 backbone 上的實作沒有交代，也沒有 variance。 |
| C3 | Sleep 在 long-context 上優於 ICL、DuoAttention 與 Cartridges | §4.1 同段中段（「consistently outperforms」與 Cartridges 對比句）；Fig 4 | **弱到中**：對 ICL 和 Duo 成立；對 Cartridges 並非一致，LongHealth level 1 在 2K/8K 時約 50.9/50.7，低於 Cartridges 約 52。 |
| C4 | 依序學兩種新語言時，ICL 會 catastrophic forgetting，Sleep 能保留，而且階段越多越好；Cartridges 與 SFT 也會 CF | §4.1「Learning a New Language In-Context」全段；Fig 5（正文誤標為 Fig 6） | **中**：ICL continual 從約 20.9/35.4 崩到約 10.1/15.4，對比非常明顯。但 Sleep 的 continual 優於單一語言很反常；Cartridges 與 SFT 沒有數值；沒有 variance。 |
| C5 | Sleep 在 BABILong 上可擴展到 10M tokens 仍然穩定，優於 RMT/ARMT/Titans 與大模型 | §4.1「BABILong」；§B.2 第二段；Fig 6 | **弱**：圖中沒有 RMT/ARMT/Titans；10M 約 91%，和「almost perfect」不符；fine-tuned 與 zero-shot 的比較不對等；caption 與圖不符。 |
| C6 | Memory consolidation 提升數學推理，優於 SFT、GRPO、OPSD | §4.1「Memory Consolidation for Reasoning」；Table 2；Table 5 | **中到弱**：avg@16 降低了取樣噪音，兩種規模都一致。但幅度小（8B AIME-25 是 69.0 vs GRPO 68.1），訓練資料不明，只有單一 run。 |
| C7 | CF 本質上是容量不足的問題；upward distillation 加上 parameter expansion 能緩解 | §3.2 第二段（CF 歸因於有限容量）；§A.4「Positioning」(i)；Table 1 的「w/o Expansion」與「OPSD + Expansion」 | **弱**：唯一的直接證據是 Table 1。拿掉 expansion 掉 1.0/1.1/1.2 分；OPSD 加上 expansion 提升 1.3/0.8/0.8 分。這是推理任務而非 CF 任務，沒有量測舊能力保留。 |
| C8 | 單靠 on-policy distillation，student「有知識但不會用」；加入 RL 的 Learning-to-Imitate（semantic + Levenshtein reward）才能讓 student 對齊 teacher 的使用方式 | §3.3「Learning to Imitate」首句；§A.4「Positioning」(iv)；Table 1 的「− Imitation Learning」「− Semantic Reward」 | **弱到中**：拿掉 imitation 掉 2.4/1.1/1.1 分，是消融中最大的。拿掉 semantic reward 在 AIME-25 反而更高。「有知識但不會用」這個觀察本身沒有提供量化證據。 |
| C9 | 完整 Sleep（consolidation + 改良版 Dreaming）在 knowledge incorporation 與 few-shot ARC 上優於 SEAL；gradient-based selection 與 random expert 都有幫助 | §4.1「Knowledge Incorporation」第二段、「Few-Shot Learning」；Table 3、Table 4；§B.3 | **中（SQuAD）/ 弱（ARC）**：SQuAD 完全沿用 SEAL protocol，n=1 與 CPT 都一致，但比 SEAL 只多 1.4–3.0 分。ARC 只有 8 task、約 3/40 次的差距。 |
| C10 | 把 consolidation 和 self-improvement 分成兩階段（先 consolidate 再 dream），比直接反覆做 self-improvement / self-distillation 更能抵抗 CF 與 collapse | §3.4 第二段（「In our evaluation, we show…」）；§A.4「Limitations of OPSD and Motivation for the Sleep Paradigm」；§A.4「Positioning」(iii) | **弱（幾乎只是論證）**：沒有專門實驗在多次 sleep cycle 後比較「兩階段」與「只做 dreaming 或 OPSD」的舊任務保留率。Table 3 的「− Dreaming」測的是相反的方向。 |

---

## 6) 哪些只適用於模型訓練層，哪些可以轉譯到不能改 weights 的 harness

### 6.1 只適用於模型訓練層（harness 無法直接使用）
- CMS 的 multi-frequency MLP 梯度更新（Eq. 2），以及 compute 後延遲套用 base-weight update 的機制
- 在 MoE 中新增或解鎖 low-rank expert {A,B}、mask 預先配置的參數、重置舊 LoRA experts（synaptic pruning 的參數版本）
- GKD 的 token-level logit divergence（F、D）、不對 student sampling 做 backprop
- LTI 的 RL 訓練（以 reward 更新 A,B）
- Dreaming 中的 per-dream LoRA SFT、ReST^EM 對 dream 生成策略的 policy update
- MoE router 的 random expert routing（需要 MoE 架構）
- gradient-based importance score ∇_θ L_SFT（需要梯度）
- 所有實驗結果（Fig 3–6、Table 1–4）都是 weight-update 的證據，**不能直接當成 text-memory harness 有效的證據**。論文 §A.3 也特別把自己和 Lin et al. 2025 的「sleep-time compute」（在 text space 做 idle-time 摘要）區分開，而後者其實才是更接近 harness 的先例。

### 6.2 可轉譯到 harness 的概念（只是類比，論文沒有驗證）
1. **Wake/Sleep lifecycle**：把「處理外部任務的 active session」和「不接收新輸入、只整理內部知識的 offline consolidation pass」分開排程。例如在 session 結束、context 快滿、或累積 N 個任務時觸發。
2. **多頻率記憶階層**：context window（最高頻）→ session scratch/notes（高頻）→ project memory（中頻）→ long-term principles/skills（最低頻，極少更新）。每層有各自的更新週期。可直接借用 Fig 4 的方向性結論：**最低頻層要保持穩定，層數多比兩層好**（證據來自 weights，需要自己驗證）。
3. **compute–consolidate–update，也就是「覆寫前先 consolidate」**：任何快層要被清空或壓縮之前（例如 context compaction、清 scratch），必須先把它的抽象知識提煉到下一個較慢的層，**而且要先驗證成功，才能清空快層**。這相當於 synaptic pruning 只在 consolidation 完成之後進行。
4. **Upward distillation 寫進新槽位、凍結舊內容**：consolidation 的產出寫進一個**新的、隔離的記憶條目或區段**（相當於新 expert），不直接改寫既有的長期記憶，以避免 interference。之後再由較低頻的流程做合併。
5. **Teacher/Student consolidation 驗證（LTI 的 harness 版本）**：Teacher 是「持有完整 raw 快層記憶」（例如原始 transcript）的 agent，Student 是「只持有 consolidated 記憶」的 agent。驗證方式：從 teacher 處理過的任務或其自行生成的探針中截取 prefix，讓 student 續寫或回答，再打分：γ × semantic judge（binary）+ (1−γ) × 正規化 edit distance（超過門檻 z_0 記 0）。這是可量化的 **consolidation fidelity gate**；on-policy 的意思是評估 student 自己的輸出，而不只看 teacher 的範本。
6. **Dreaming = 產生候選自我改進的提案，用下游指標做 binary 篩選（ReST^EM 的無梯度版本）**：用近期知識 C 生成 m 個候選（例如新的 skill/規則/範例/自測題），**每個候選在隔離的沙盒副本中套用**，再用任務指標 τ（eval、測試通過率）判斷是否進步，進步記 1、否則記 0。保留 **Top-k，再加上 b 個隨機樣本**以維持多樣性。gradient importance 無法計算，可以改用 eval delta、失敗相關性或新穎度當代理指標。
7. **Random expert injection 的無梯度版本**：生成 dream 或候選改進時，隨機抽一則**不相關的**既有記憶放進 prompt，鼓勵跨領域的新組合。證據很弱（Table 3 只差 0.9–1.5 分），但成本極低。
8. **先 consolidate、再 self-improve 的順序**：self-improvement loop 修改 harness（skills/規則）之前，先把近期知識穩定寫入並驗證。用來防範 §A.4 列出的 iterative self-distillation 失效模式（privileged leakage、collapse、OOD 退化），對應到 harness 就是 self-improvement 侵蝕既有能力。必須搭配**舊能力的 regression eval**，因為論文本身沒有提供這方面的證據，harness 需要自己補上。
9. **容量觀點**：論文把 CF 歸因於容量不足。對應到 harness，記憶衝突或覆寫通常發生在固定大小的記憶檔或 prompt 預算被塞滿時。可以考慮分層擴充（新增條目或檔案），而不是把舊內容硬性改寫成更短的版本。
