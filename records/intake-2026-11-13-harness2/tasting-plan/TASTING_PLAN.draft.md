# Harness² 官方 runtime 試吃計畫（draft；尚未執行）

**建議先只資助 LAB 同一 practice area 的 2 題、每題 k=1、parallel、1 個 chronological stream，以 Codex executor 跑官方 loop，另跑獨立 native baseline。** 這是可評分的 operational pilot：檢查官方安裝、完整 loop、跨題 library、隔離及完整計量是否可用；不能據此吸收或排掉 runtime。維護者正式 intake 的預設仍是 12 題各 1 次。依下列**全為猜測**的 token 模型，12 題 expected Claude-model 支出含 1.3 reserve 為 **55.12416M**，已超過 30M；Codex 另計 **98.22384M**。不能用「k=1」當成一次便宜審查。

2 題 pilot 的 Claude-model low／expected／high 是 **2.1944／9.18736／58.7704M**；Codex 另為 **3.874／16.37064／106.4544M**。兩者合計 **6.0684／25.558／165.2248M**。expected 可容於 Claude 30M，但 high 不可；只有配合逐呼叫 reservation 與硬停止，才可核准有限支出，不能保證跑完。這些是規劃情境，既非量測、信賴區間，也非最壞上限。

若連兩題也無法保留足夠 headroom，最便宜付費變體是 **1 題 smoke**：Claude-model low／expected／high 含 1.3 為 **1.0972／4.59368／29.3852M**；Codex 另 **1.937／8.18532／53.2272M**。它只回答單題官方 loop／計量可否運作，不能回答跨題 library 是否有用，亦無採用判詞；Codex 20M 硬額度仍可能使 high 情境中止。

**執行前仍有兩個 funding gate：**（1）現有規範是 subscription-only，而官方 runner／judge 使用 API／Vertex；須有 owner 對這個具體用途的例外，或先交付另案 subscription adapter。（2）完整 Claude Code cell 沒有官方 executor；`claude_cli` 只是 editor channel。不得把 OpenCode+Claude 標成 Claude Code，也不得把 API model alias 可設定說成帳戶確實能用。這份文件不授權安裝、API 消費、adapter 開發或任何實驗。

## 1. 證據範圍與閱讀方法

日期 2026-11-13。Harness² pin：`6868817518876de8fd170c6a8354daca273b6191`。本文的「來源」是靜態讀到的行為；「設計」是 OAW 額外條件；「猜測」是未校準的預算。所有 upstream 檔案／行號連結均固定於此 pin；外部 dataset card 與 paper 另標，不冒充 pinned repository 證據。

已讀既有 [EVALUATION](../EVALUATION.md) §3、§5、[SOURCE](../SOURCE.json)、[IMPLEMENTATION](../IMPLEMENTATION.md)，以及 OAW 的 `docs/SKILL_INTAKE.md`、`docs/SELF_IMPROVEMENT.md`、`docs/EVAL_LEDGER.md`、`docs/EVAL_PROTOCOL.md`。U1 已有工程交付；不是 runtime tasting receipt，也不是模型收益。此輪只產出本計畫與 `COST_MODEL.json`。沒有安裝、匯入／執行 upstream Python、跑 demo、check、dry-run、模型或 benchmark。

OAW 規範引用以文件內標題／節定位：SKILL_INTAKE「一頁版」要求官方 food arm、主場、凍結問題與盲評；EVAL_PROTOCOL「設計」指定 12 題、30M 與 subscription-only；SELF_IMPROVEMENT「Require the mechanism to trigger」「Charge overhead」要求免費 trigger fixture、獨立 usage；EVAL_LEDGER「Bundle contract」要求完整 stage、artifact 與 judge identity。本次不修改這些規範，不推 records；正式執行者須另完成 PREREG 的既有登記程序。

## 2. 官方安裝、相依、授權與隔離

### 2.1 未來執行者的安裝 runbook

以下命令**僅供另次獲准後執行**，在全新的 disposable Linux VM 內、相對於 VM 的專用工作目錄。不要在 OAW checkout 安裝；不要重用任何現有實驗、登入 profile 或原生 transcript。建立目錄前由 controller 將其綁定至已核准的 trial root。保留 OS image digest、architecture、套件版本、uv／Node／gcloud 版本和 install logs。

1. 在 VM image 安裝 git、curl、unzip、ca-certificates、Node.js ≥20、uv；走 Vertex 才加 Google Cloud CLI；LAB 加 pandoc、poppler-utils。使用受信任、固定版本的 OS／uv 官方安裝渠道，記 checksum；本計畫不指定浮動 `curl | sh`。WorkBuddy 才安裝 VM 內專用 Docker Engine。這是 upstream 的 Linux 建議，OAW 主體仍維持 Python 3.10+ stdlib。[S1]
2. 按官方 source-install 路線建立 checkout 與 main venv；Python 套件接受 ≥3.12、<3.14，benchmark setup 固定用 3.12，因此選 3.12：[S2][S3]

   ```bash
   git clone https://github.com/google-research/harness2.git harness2
   cd harness2
   git checkout --detach 6868817518876de8fd170c6a8354daca273b6191
   git rev-parse HEAD
   uv python install 3.12
   uv venv --python 3.12 .venv
   source .venv/bin/activate
   uv pip install -e '.[render]'
   cp .env.example .env
   ```

   只寫 VM 的 private `.env`，不把實值放進公開產物。使用 main venv 執行主命令，不 activate benchmark 自己的 `.venv`。`harness2-demo` 是可選非模型 demo，這次預算設計不需要它；demo 通過不證明模型 cell 可用。
3. 先完成 §3 的 endpoint／model／judge gate。若走 Vertex，在 VM 中配置最小 scope ADC（`gcloud auth application-default login` 或專用短期身分）；若獲准直連 Responses API，設定 §3 的 private 環境。憑證只授予 broker／controller；worker 只取得限定模型 route 的短期 token。[S1][S4]
4. 只安裝 LAB：

   ```bash
   harness2-setup lab --substrate cx --dry-run
   harness2-setup lab --substrate cx
   harness2-check --bench lab --substrate cx
   ```

   setup 會安裝 pinned OpenCode（即使選 cx，editor 仍需要）、Bun 1.3.11、LAB 及官方 patches／overlays、`uv sync --locked --python 3.12`、LAB 額外 `google-auth[requests]`，以及 Codex CLI 0.144.6。必須保留這條官方安裝鏈，不能只挑幾個函式模擬 food arm。check 會執行 dependencies imports、credential／socket probes，**不是純靜態操作**；它不測 model availability，首次 paid call 才能知道模型能否服務。[S5][S6][S7]
5. 封存 `uv pip freeze`、各 dependency revision／lockfile／patch hash、Python 精確 patch version、Codex／OpenCode binary identity、全部資料 hash、`.env` 去密版本、network policy hash。setup 的非 locked 額外 pip 依賴也須記實際 resolution；上游 commit 不會凍結整個軟體供應鏈。先完成無模型 fixture（identity、stage meter、retry、拒絕 grading 存取、kill switch），再凍結 tasks／PREREG，才可跑 §4。

### 2.2 每套 benchmark 需要什麼

| Benchmark | 官方 backends／runtime | Optional 與 benchmark dependencies | Code licence 與 data licence（分開） |
|---|---|---|---|
| LAB | oc 或 cx；兩者的 proposer／selector 預設 OpenCode high | main `[render]` 為官方 quick start；LAB venv `uv sync --locked` 加 `google-auth[requests]`；Pandoc、Poppler；judge 的 anthropic／google／openai／mistral SDK 等由 LAB lock 解決。cx 直連 Responses 不必裝 bridge | Harness² Apache-2.0；harvey-labs code MIT。Tasks 隨 pinned LAB checkout，repository README 將 dataset 與 harness 一同描述為 MIT project；未找到獨立 dataset grant。先按 repo MIT 保存通知，但逐題所附第三方 legal documents 的權利仍須保留／核對，不能宣稱所有來源文件可任意再散布。[S3][S8][L1] |
| JobBench main | oc 或 cx；document extraction、rubric judge | main `[render]`；benchmark locked venv 加 `python-docx`；preflight 查 pandas、openpyxl、docx、mammoth、pdfplumber、pptx、openai。Vertex Gemini judge 或單獨 judge base URL/key；bridge 僅 Gemini→Codex 時需要 | job-bench-eval code Apache-2.0；**data card MIT**，不是 code 的 Apache。card 是另行讀取的浮動 main，未被 Harness² pin 固定；下載時另封存 card／LICENSE／data revision。官方只裝 main，easy 不是官方 setup 的便宜替代。[S5][S9][L2] |
| WorkBuddy office／web／code | oc 或 cx；Harbor、Docker，每 rollout fresh container | locked venv；office main `[render]` 硬需求；web／code 不應因此漏裝其他官方要求。setup 生成 solver/judge routes，**即使 cx，仍要求 Vertex Gemini solver 與 Gemini judge 設定**。`[bridge]` 給 Codex 使用 Gemini Responses bridge；從容器連 bridge 須設 container URL；oc setup 建 harness mounts/image | workbuddy-bench code 是 custom Tencent licence，含 EU territorial limitation；data card 是 `other`／Tencent，不是 Apache/MIT。archive 還可能含第三方 repo／素材 licence。須核對執行地點與服務部署地點，保存 archive SHA256SUMS／通知。此 pilot 不下載 WB。[S10][S11][L3] |

核心 runtime dependencies 為空，不代表整套 benchmark 無 dependencies。`[render]` 是 openpyxl ≥3.1,<4、python-pptx ≥1,<2；`[bridge]` 是 litellm[proxy] 1.95.0、fastapi 0.139.2、google-auth 2.56.3。使用 bridge 時在 main venv 執行 `uv pip install -e '.[render,bridge]'`、另 session 起 `harness2-bridge`；WB 才用 `--host 0.0.0.0`，VM firewall 限定內部容器，不對外公開。[S3][S4]

### 2.3 Network 與 OAW 額外 isolation

來源：setup 需要 GitHub、npm registry、Hugging Face/CDN、Docker registry（WB）、Python/uv distribution；實際 pip／uv 還需 package index／artifact hosts（例如 PyPI 及其 CDN，以 setup log 固定），OS 安裝也需 package mirrors。執行與 judging 需要模型 API、ADC token refresh；setup 與任務 web access 是不同允許範圍。[S12] 上游明記不限制 network；validation 曾有 Codex 主動下載 JobBench rubric；Codex 使用 bypass approvals/sandbox 與 hook trust flags。[S13][S14]

設計：使用兩層邊界，外層 disposable VM，內層每 rollout／editor 的非特權 worker namespace/container。只 mount 該題 sanitized instructions、documents、base/candidate harness、必要 tools；可寫自己的 scratch/output。禁 mount OAW 真實 repository、host home、其他實驗、cloud credential files、Docker socket、benchmark task.json／RUBRICS／verifier／完整 upstream checkout。controller 在另一 trust boundary 擁有原始 dataset、marker、ledger、judge；官方 runner 仍保留原 argv，broker 在 launch 邊界注入唯讀工具與資料，**不改 food 的推理流程／selection pool**。若必須改 adapter 才能安全分開 mount，先保存最小 adapter diff，標記為 isolated official-runtime variant；不得稱 unmodified runtime。

setup 完畢後 worker egress **default deny**：只允許固定的 model broker，不提供一般 HTTP CONNECT／任意 URL proxy；broker 只接受 model API schema。阻擋直接 IP、DNS 外送、IPv6、redirect 繞過及雲端 metadata service；不只靠 HF/GitHub domain denylist。所有 editor、reflection、subagents、generated scripts 同受限制。judge 在另一 namespace 讀 rubric，不能回寫 worker/library。先用無模型 canary 驗證 filesystem／network deny 與 broker allow；只改環境、不得用 prompt「請勿讀 rubric」當隔離。僅 SCRUB_ENV 不足：未列入的變數、local helpers 仍可能承接完整環境。[S1]

本設計選不需 live web 的文件題。需要 research/web 的題無法在此環境公平回答，於**看輸出前**依 §4 排除；不允許跑失敗後補開網路。論文數字使用其他模型／host、任務集／順序／可用網路與較寬權限；因此這裡只能作同隔離條件下的 paired tasting，不能宣稱重現 paper 絕對分數。paper 的三個 shuffled streams 與 200 turns／3,600 秒只是設定，**不是 logical-token 預算**；LAB cx 的實際命令沒有通用 200-turn flag，需外部 controller 控制花費。[P1][S14]

## 3. Hosts、models 與不支援項目

| OAW 目標 cell | upstream 可直接做的部分 | 不可直接做的部分／必要設定 |
|---|---|---|
| Codex CLI + `gpt-6.1-sol`, high | `--substrate cx`；LAB adapter 送 `--model` 與 `model_reasoning_effort="high"`；官方 setup 固定 CLI 0.144.6 | 需要可接受該**確切 ID**的 Responses endpoint。`HARNESS2_CODEX_BASE_URL`、`HARNESS2_CODEX_API_KEY`、`HARNESS2_CODEX_MODEL=gpt-6.1-sol`；setup 生成 `wire_api="responses"` provider config，改 endpoint/model 後重跑 setup。這不是沿用已登入的 subscription Codex profile。精確 alias、quota、high 行為與 0.144.6 相容性未實測；失敗即 stop，不換模型。[S4][S6][S14] |
| Claude Code + `claude-opus-5-5`, high | core 有 `claude_cli` **editor** channel，會呼叫 `claude -p --effort high --output-format json`；可用 bare model ID 建 ChannelSpec | CLI executor 選項只有 oc/cx，沒有 Claude Code substrate。公開 CLI 沒有 proposer-channel 選項；bench specs 固定 `resolve_channel_model(None,None)`，預設 opencode。claude_cli env 強制 Vertex／project／region，並 scrub direct Anthropic tokens；不能只設 `.env` 就得到 subscription Claude Code loop。改 BenchSpec/channel 或新增 substrate 都是 adapter fork，需獨立實作／fixture／計量；**本輪未交付**。[S15][S16][S17] |

官方試吃建議的配置 profile 為：LAB cx executor `gpt-6.1-sol` high；editor 為 OpenCode `anthropic/claude-opus-5-5` high（或已核准 Vertex 對應 ID，但要獨立 condition），`HARNESS2_SOLVER_MODEL=openai/gpt-6.1-sol` 仍必填以滿足 generic validation，`HARNESS2_IMPROVER_MODEL=anthropic/claude-opus-5-5`。direct Anthropic editor 要獲准的 API key；另一方案是官方 Vertex Claude route，但精確 ID／access 未確定，不能自動替換。LAB 官方 judge 使用 `HARNESS2_JUDGE_MODEL=claude-opus-5-5` 時 config 會加 `vertex/`，因此還需要 Vertex ADC 與 access；單設 Anthropic key不會使這條 judge route 變成 subscription。[S18]

第二家盲評使用獨立 Codex CLI `gpt-6.1-sol` high，讀匿名成品、相同 rubric 與 task sources；不看任何 solver/editor trace、候選名稱或成本。這是 OAW grading wrapper，不是 upstream 新 substrate。官方 LAB judge 先在隔離 sidecar 收到匿名 run-ID／artifact 副本；保留 `base_judged.json`／`judged.json` 與 artifact hash 映射，跨家族評分只在全部 outputs 凍結後執行。此方案有額外 wrapper 工程，需在無模型 fixture 證明 identity 一致；若原 judge 的 prompt 暴露 arm labels，先用 sidecar 轉匿名，不直接將該次當盲評證據。

官方只有 OpenCode improver、沒有 Codex CLI improver channel；`openai/gpt-6.1-sol` 可以是 OpenCode provider/model 設定，仍不是 Codex editor host。WorkBuddy setup 的 Gemini route 限制也不能被「cx 支援 Responses」這一句繞過。模型 ID 可通過字串檢查不證明 provider 已上架或本帳戶獲授權。[S5][S10][S16]

OAW EVAL_PROTOCOL 的「只用訂閱計費（apiKeySource 為 none）」沒有被本任務撤銷。owner 可選：資助明確限定的 API/Vertex 例外；或另案資助 subscription adapter，並同時承認它不是 as-is 官方 cell。若兩者皆不允許，**零付費停止、狀態未試吃，沒有 runtime verdict**。不得借用現有 host token／subscription credentials 偽裝成 API key。

## 4. 最小主場設計與未來執行順序

### 4.1 選 LAB 的理由與題目凍結

LAB 是 upstream 主場之一；資料隨 pinned checkout、免 Docker 與即時 search，文件題較容易設封閉環境。缺點是沒有可執行正確性 oracle，法務判斷依賴 model rubric，且文件可很長；不是 OAW coding 用途的替代證據。[S8][P1] JobBench main 有 search 情境與公開 rubric；WB-code 雖貼近開發工作，官方 Gemini configuration／Docker／custom data licence 提高這次最小試吃門檻。

**題目選擇規則現在凍結，actual IDs 在官方安裝後、任何 paid call 前實體化。** 不假造目前未安裝的資料清單。由不知道 arm 輸出的獨立 curator 依以下算法選題，不能根據模型成績挑題：

1. 以 LAB dependency pin `b58a28ae9fde5ee4b810e53b4fd0a1915325a35d` 的 `tasks/*/*/task.json` 為 universe；OAW instructions／H1／FIXCHECK 完全不可見。task ID 用 upstream 的 `practice-area/task`。只讀公開 instructions／source inventory；rubric 另由 grading custodian 保存。[S18][S19]
2. eligible = 可用提供文件完成、不要求 live search／外部登入／新增服務；只含可離線解析的文件；source files 加 instructions 合計 ≤80,000 UTF-8 extracted characters。**80,000 是 OAW 設計上限，不是 upstream default，也不是 tokens**。curator 保存每題 inclusion/exclusion reason、extraction tool version；未符合的直接排除，不看 model output。
3. 2 題 operational pilot：`antitrust-competition` eligible IDs 按 SHA256(`h2-taste-v1|` + task ID) 升序取 2。這固定的是集合；實際執行順序採 pinned scheduler 對該集合的 seed=42 排序，以 dry-run manifest 固定。第一題 cold-start，第二題可讀第一題 library。如果此域不足 2 題，零付費停，不自動換域。不是獨立兩樣本的收益檢定，分析單位是 diagnostic stream。
4. 預設 12 題正式 tasting：排除 operational pilot 的整個 practice area，其他至少有 2 題的 eligible domains 按 SHA256(`h2-home12-v1|` + domain) 排序取前 6，每域依同 prefix/task ID 排序取 2。共 6 個 2-task streams；不能把 12 題或 48 rollouts 全當獨立同分布樣本。domain-cluster 推論樣本很少，report 保留未定；若改成獨立 task/cold-start 設計，必須是新 PREREG。此 12 題只對閉網短文件子分布成立。
5. 保存 `tasks.json`、每題 source／instruction hash、ordered stream、private rubric hash、兩家 judge ID/version/effort、base harness hash、完整 conditions、停止規則與本計畫 hash。另產 upstream 格式 split `{"benchmark":"lab","train":[],"test":["<frozen IDs>"]}`；`test` 僅是 upstream selector 名稱，operational pilot 在 OAW ledger 仍是 `split=pilot`、`analysis_unit=diagnostic`。它接受 subset 不必全覆蓋 universe。[S19]

公開 benchmark 不符合「新 agent 全新出題」的字面條件；這是 owner 指定官方主場 tasting 的既有公開題。獨立 curator 凍結抽題、不得知 OAW 實作／arm 結果；OAW 用途的全新題另見 §5。正式登記須明記此範圍，不說成新的 hidden tasks。凍結後不因 baseline 接近滿分而換題；若全數 ceiling，記 no conclusion，另案出題。

### 4.2 Arms、計數與命令

每題固定兩個外部 arms：N = 官方 base harness 的獨立單次 native execution；F = 官方 Harness² k=1 loop，內含 base1、inv1 probe、dom1 probe、agg1 final、兩次 proposal、一個 compose editor、一個 reflection。N 與 F 使用相同 Codex version/model/effort、資料／tools／time／network；不同 fresh workspace。N 不讀 library；F 的 library 按 upstream 更新。**每題共 5 rollouts**，其中 F 本身仍是 4；不能把 F 的 base 又收成第 6 次成本。無 description-only：這是 runtime，不是只放 description 可啟動的 skill。

另外對 F 的 internal base 評分，回答 final 相對「不改」是否退步；external native N 與 F final 是主 paired comparison。對 inv/dom probes 不評分以節省成本；若另要診斷所有候選，須事先加列費用，不能偷偷事後取最高分。所有評分都在 reflection/library 凍結後，不得回流。

F 的未來命令（只跑一種 mode，不跑 both；`--max-tasks` 是**每域**上限）：

```bash
export HARNESS2_RUNS_DIR=runs/home-pilot-cx-r1
harness2 --bench lab --substrate cx --k 1 --mode parallel --workers 1 \
  --split-file splits/home-pilot.json --split test --seed 42 --dry-run
harness2 --bench lab --substrate cx --k 1 --mode parallel --workers 1 \
  --split-file splits/home-pilot.json --split test --seed 42
harness2-judge --bench lab --substrate cx --k 1 --mode parallel --seed 42 --bases
harness2-judge --bench lab --substrate cx --k 1 --mode parallel --seed 42
harness2-report --bench lab --substrate cx --k 1 --mode parallel --seed 42
```

執行前比對 dry-run IDs 與凍結 manifest，不一致就 stop。judge/report 沒有 `--split-file` 旗標，讀該 namespace 的記錄，勿自行加旗標。上列 judge 命令由隔離／匿名 sidecar 包裝，不能使 workers 讀到 rubric。N 沒有 upstream native-only sweep CLI；使用固定 pin 的 `LabAdapter(substrate="cx")`，對每題呼叫 `execute(task_id, None, unique_native_run_id)` 的獨立 controller，需新寫最小 driver（不經 propose/library），並以無模型 fake launcher 驗證。N 先 `preflight`，按相同 task order 執行；預登記用 hash 決定每題 N/F 誰先啟動，避免所有 N 都在較好 quota 時段。N output 凍結後由 sidecar 呼叫 `score(native_run_dir, task_id)`，收進同一 official rubric contract，再送第二家盲評；它不會自動出現在 F 的 `--bases` 報告。這是外部對照 driver，F 的官方 loop 不因此改寫；未交付 driver 前不得花模型 token。[S20][S21][S30]

2 題跑一次 stream（seed 42），不重抽模型輸出；順序 seed 不能宣稱 model seed。正式擴至 12 題前先依 pilot 實測 unit cost 重新估算，沿用 `unit × runs × 1.3`；此為 funding recalibration，不能用 pilot 修改正式 rubric。若擴展到 3 shuffled streams，libraries／roots 獨立，12×3 的開支另乘 3，不能當免費重現。[S22]

## 5. OAW-use pilot：改善 OAW 的 harness 與改善搜尋流程

這是與主場 tasting **分開登記、分開計量**的第二個實驗，不能把 30M 拆成多個名字規避。先有官方 runtime 可運作的證據，再考慮 adapter。只使用獨立 development sandbox 的 OAW snapshot；不讀 held-out H1 題目、rubric、歷史 trace 或目前正在跑的實驗。也不把 FIXCHECK 題目包裝成獨立測試。

**任務與 base harness。** 固定已發布／owner 指定 OAW commit，記 native package、policy、skill payload 及工具版本。任務限 stdlib 開發：D1 修正 source-identity／evidence adapter 的新 synthetic edge case；D2 改善 native skill routing 的重複 context，在不改行為下簡化；每題都有獨立 curator 新建的 toy repository、issue、公開 tests、private assertions，且與 H1 的 task family 不同。兩個新的 validation cases V1（session handoff 的另一 toy repo）／V2（installer customization 保留的另一 toy repo），每個 3 repeats，只在候選凍結後揭露；全都屬此 pilot 開發資料，不構成 H1 留出證據。若 task 其實要求修改程序碼，程序碼是任務交付；Harness² 可編輯 surface 限 harness，不能靠改 checker／private tests 提高分數。

**Adapter contract。** 新增 OAW benchmark adapter：task_prompt/source、base_harness、execute、trajectory、deliverable、score 分離；起點是當前 OAW 的實際 native tree，不拿 upstream empty harness 冒充。Codex surface 能表達 AGENTS.md／skills／scripts；不支援的 OAW memory、session、router semantics 必須逐項列 mapping／loss，不能默認等價。Claude Code 要新增真正 executor substrate；editor `claude_cli` 不解決此缺口。patch 只能碰 sandbox 中的 OAW harness payload／routing policy，不能改 budget controller、permissions、task、grader 或 OAW source baseline。無模型 fixture 先證明機制會觸發、隔離、native discovery 與 usage 封口；schema pass 不證明真 host discovery。

**完整探索性 pilot 的搜尋 arms。** 同起點、同 D1/D2、同模型 host／effort 與 2.948M logical-token expected allowance/題（猜測；硬額度另設），每個搜尋 arm 一次 discovery episode：

| Arm | 實際程序 | 要排除的混淆 |
|---|---|---|
| H | 官方 Harness² loop 經 OAW adapter，k=1，4 rollouts + 3 editors + reflection；D1→D2 chronological library | 官方方法能否產生可凍結候選；每題仍從共同 OAW base 起步，不能自動累積整棵前題 harness |
| O | 現有 `oaw-improve`：具體 diff/hypothesis→fresh review→matched base/candidate probe→compare；1 author + 1 review session、2 executions/題 | 當前改進流程的實際成本與結果；拒絕 proposal／trigger 未發生也保留成本，不能只記最後 accept |
| B | native OAW 不改 harness，4 次 rollout + 匿名 selector；與 H 相同執行次數，另給相同總 token ceiling | 「多花 compute／多選一次就有效」；B 不是新 harness，無法冒充產品候選 |

不是每個 arm 都必須花滿 ceiling；記 time-to-first-eligible、total spend-to-frozen-candidate、failed proposals、quality-vs-spend。O 的比較門檻先固定 `minimum_improvement=0.05`、`maximum_resource_regression=0.1`、`usage_coverage=required`，trigger cases D1/D2，minimum_rate=2/3；符合 fixtures 才開付費。先預定只准一個 focused patch；H 多文件改動也只形成一個 bundle，不把每行都算一次勝利。候選以 D2 最後凍結 tree 為準，不能事後用 validation 分數挑 D1 或 D2；若無有效 tree，記 no candidate，保留 base。H／O 探索結束前不看 private validation grades。

**產品問題：「結果 harness 比當前 OAW 好嗎？」** 凍結 H、O 後，在 V1/V2×3 repeats 配對執行 current OAW、H candidate、O candidate、native/no-OAW 四個 arms，共 24 answers；同 tools/權限/model，base 可保留為部署選擇。mechanical assertions 為主要品質，cross-family blind rubric 補充 source correctness／不支援陳述。量 per-assertion regression、完成／可評分分母、trigger、logical／noncache／USD／latency、tool errors、常駐 context、無關題誤觸發。依 SELF_IMPROVEMENT gate：先前 pass 的任何 assertion 退步即 reject，resource >10% reject；樣本太少時只得 pilot signal，不能宣稱跨任務普遍收益。

**流程問題：「是否較便宜找到同等品質？」** 比較 H/O/B **搜尋全帳＋凍結後 validation 成本**，不能拿 final rollout tokens 作搜尋成本。B 的 delivered-output 品質另與 H final 對照，不能拿 B 當已學到持久 harness。一次 discovery episode 只能校準流程／成本，不能證明 cheaper；若要較強證據，至少 3 個獨立 discovery episodes（獨立 history、相同預先分配開發集與預算），每次產生 tree 後才在新 matched validation bundle 測，按 episode／task family 群聚分析。若沒有同等品質候選，不能說便宜勝出；若成本差來自不同 editor model，也不能歸因於 loop。

**成本與縮案。** 完整探索性 pilot 一個 episode：搜尋 2 development tasks×3 methods，加 24 validation answers，shared work；low／expected／high 含 1.3 為 **8.1744／34.1848／207.584M**（全部猜測）。若全用 Claude cell，expected 已超 30M；3 episodes 為 **24.5232／102.5544／622.752M**。Codex cell 同設計另計，不可替 Claude 超額買單。

最便宜且仍回答一個 OAW 問題的縮案：只做 H 的 D1/D2 搜尋，凍結一個候選，再對 current OAW／H candidate 跑 V1/V2×3，共 12 answers；不做 O／B／native 參考。含 1.3 是 **4.0248／16.6816／100.178M**，expected 在 30M 內。這只問該候選在兩個新 development cases 是否可用，不能回答 H 比 `oaw-improve`／best-of-4 更便宜，不能據此吸收 U2/U3 或替換 runtime。adapter 的工程時間／額外模型 authoring/review 另有 meter；模型 shared placeholder 超額就壓縮／停止，不視為免費。

## 6. 成本依據、口徑與 cap

logical = 每個實際呼叫 input（包括 cache-read/cache-write 對應的 input，依 provider 欄位去重）+ output（含未重複計入的 reasoning）。每 turn 累積；不是 context window 大小、不是 unique text tokens，也不是折扣後帳單。noncache = logical − cache-read，僅在 provider 有完整欄位且語義吻合時計，否則 null。不同模型 tokens 是各 tokenizer 的原生數，不把字元直接當 token。

上游只給 stage 數、step／time 上限與部分 cost 記錄，**沒有這兩個模型的 stage logical-token 實測**。以下全部 token/turn/平均長度/criteria 數都標 **G＝猜測**；「來源」僅支持結構、上限與證據會累積的原因。80k-character eligibility 也不保證後續 trace／library 很短。[S23][S24]

主場每單位 = 一題 N/F paired run，F k=1 + 1 native；每份 artifact 的 grading 在兩家各跑一次。單位：k logical tokens。

| Stage | 次數/單位 | low G | expected G | high G | 生成數字的方法（均為 G） |
|---|---:|---:|---:|---:|---|
| rollout（N、base、INV、DOM、final） | 5 | 280/次 | 1,080/次 | 5,200/次 | turns 20/40/100 × (平均 input 12/24/48k + output 2/3/4k)。paper 的上限不是平均；為 closed-doc 工作保守擴寬，包含 reasoning |
| proposal INV／DOM | 2 | 144/次 | 560/次 | 2,720/次 | turns 8/16/40 × (16/32/64k + 2/3/4k)；讀一份 base trace、來源與 library |
| compose editor | 1 | 260 | 1,020 | 5,000 | turns 10/20/50 × (24/48/96k + 2/3/4k)；讀多份候選 evidence |
| reflection | 1 | 156 | 612 | 3,000 | turns 6/12/30 × 同 compose 的平均長度；可 NO_ENTRY 仍有費用 |
| selector | 0 | 0 | 0 | 0 | **0 是來源事實**：k=1 trivial selection，不呼叫模型；有 controller 工時。k>1 不在本預算 |
| grading（N、F base、F final ×兩家） | 6 | 30/份/家 | 108/份/家 | 432/份/家 | 6/12/24 criteria × (input 4/8/16k + output 1/1/2k)。LAB per-criterion grading 與 16,384 output cap 有 source；criteria 數與平均 tokens 沒有。filename matching 額外 model call 由 retry allowance 暫估，實際獨立列帳。[S25] |
| retry allowance | 一個比例 | 0% | 10% | 50% | 乘上以上所有模型 stages；**猜測，非 upstream retry 機率或最大值**。stage validation 2 attempts 與 transport 2 attempts 可疊加至一 stage 4 calls；judge SDK 還有 retries。[S26] |
| shared authoring/review/controller 模型工作 | 一份 | 50 | 150 | 500 | G placeholder，暫按每題攤提、保守全記 Claude pool；安裝 CPU／人力不以此冒充 tokens |

逐題總額（M）：`(5R + 2P + C + F + 6G) × (1 + retry_fraction) + shared` = **2.334／9.830／63.548**。其中 Claude-model pool = editors/reflection + 三份 Claude grading + 分攤 retry + shared = **0.844／3.5336／22.604M**；Codex pool = 五次 executions + 三份 Codex grading + 分攤 retry = **1.490／6.2964／40.944M**。這是**使用模型分類**，不是聲稱 OpenCode editor 成為 Claude Code cell。未支援的完整 Claude Code official-run estimate 只能作 adapter 後規劃：全單位同額由 Claude cell承擔，實際 calibration 前不能稱測得。

| 設計 | pilot unit × runs × 1.3 | Claude pool M（L/E/H） | Codex pool M（另計 L/E/H） | 判讀 |
|---|---|---:|---:|---|
| operational 2 題 | 上列每題 ×2×1.3 | 2.1944 / 9.18736 / 58.7704 | 3.874 / 16.37064 / 106.4544 | expected 在 cap；high 不在，不能保證完成 |
| intake 預設 12 題 | 每題 ×12×1.3 | 13.1664 / 55.12416 / 352.6224 | 23.244 / 98.22384 / 638.7264 | expected Claude 已超 cap，不建議直接資助 |
| 12 題×3 streams | 每題 ×36×1.3 | 39.4992 / 165.37248 / 1057.8672 | 69.732 / 294.67152 / 1916.1792 | low Claude 已超 cap |

1.3 是**額外 reserve**，10%/50% 是有根據結構但未知頻率的 retry 情境，兩者用途不同；不得事後拿 reserve 當無限重試許可。付費 pilot 後以 observed complete unit 取代猜測重新估 `unit × 剩餘 planned runs × 1.3`。USD 因 endpoint／subscription／cache／price 未核定為 null；不捏造價格或把 subscription 算免費。正式啟動前填 input/output/cache/reasoning 單價、計費幣別、quote 日期與來源，USD = 實際 provider charge；VM/storage/egress/tool API/人工時間另報。未有價格或可接受 spend ceiling 時只核准 token pilot 仍不足以啟動 API 消費。

## 7. 完整 ledger mapping 與獨立計量

upstream `Ledger` 的 Entry 是 kind/label/usd/cached/attempts；R=4k、P=3k 是身份檢查，selection/reflection 在外。`_roll`／`_roll_many` 呼叫 ledger.rollout 時未傳真實 USD，預設可為 0，不能當作免費。USD 小計也不能反推 logical usage。[S23][S27]

| upstream 工作 | OAW stage | artifact／成本處置 |
|---|---|---|
| N native answer、F base1 reference | answer | 各屬自己的 run；produces 指向對應 hash；F base 是診斷 output，不能當第二個 final outcome |
| INV／DOM editor | proposal | 分別記 attempts、diff/tree hash、input evidence identity；自身不 produces deliverable |
| INV／DOM rollout | probe | 各自 produces artifact；全部失敗也保留 planned 分母與支出 |
| composition editor、agg1/c1 final execution | compose | 兩筆 disjoint charge scope，stage attempt 編號唯一；只有 final execution 的 completed record produces 成品 |
| k=1 trivial selection | selection | 模型成本 0；實際 controller elapsed 仍記。若沒有獨立 stage 工作才能 N/A+理由；記 selects=final artifact，不虛構 selector 呼叫 |
| experience distillation／library update | reflection | Reply／audit／EXPERIENCE/tree hash；selection.usd 混含 reflection，不再重複整筆匯入 |
| invalid-tree retry、transport/SDK retry、resume 補跑 | retry | 記 failed/interrupted attempt 與 retry_of 原 stage；若 host 只給聚合，不拆虛構數字，標 unmeasured breakdown。不得同時把聚合總額放 stage 又加 retry |
| official benchmark judge、第二家盲評、matching helper | grading | judges 指向 exact delivered hash；兩家分開 contracts，Mechanical checks 可 0 tokens 但 time/CPU 非零；score null 與 scored 0 分清楚 |
| 新題／checker／rubric／protocol／adapter 撰寫 | shared authoring | run_id=null；模型設計／工程 usage 與人工 hours 分開；不改寫成當前 task 成本 |
| fresh review／grader 校準／資料授權檢視 | shared review | 獨立 meter；候選自填帳不算 observed complete |
| setup、curation、排程、reservation、bridge、分析與報表 | shared controller | setup 非模型 tokens 可 0，elapsed/VM USD 另記；controller 自己模型對話也算；LLM proxy 不另重複 parent 已含的 charge |

meter 在 VM 外的 controller／endpoint broker 擷取每個實際 call 的 model、request/session/parent ID、時間、input/output/cache/reasoning、USD；host trace 抓 subagents、CLI background jobs、bridge、judge SDK。Codex `turn.completed` 可能是 cumulative，依 pinned host event 語義去重，不能把 cumulative snapshots 當增量一直加。Claude input/cache 欄位也先用 fixture 校對。終止／timeout 仍以 provider charge 對帳，來不及回寫的 usage 是 unknown，不填零。OAW U1 的 `meter=independent/host`、complete、subagents_included 與 disjoint charge_ids 必須有 evidence 支持。

manifest 凍結 task input／harness／model/effort/host-version/environment／judge/rubric hash；每個 output/outcome/grade 都綁 exact artifact。N、F 各一個 final outcome；base/probes 以 diagnostic artifacts 保留。兩家 grade 各自產 bundle/contract 再由既有 `agree` 合併，不在一個 outcome 塞兩套不相容 score。operational/development 不送 U1 `compare` 冒充 test；正式 streams 也不能冒用 independent_task 的 task bootstrap。要量產品部署成本，只比 frozen-harness answers；要量 process，完整加 proposals/probes/compose/selection/reflection/retry。grading 依 SELF_IMPROVEMENT 既有欄位語義另列，但**whole-study 支出與本次 cap 包含它**。

## 8. 效度風險、決策與 stop rules

| EVALUATION §3 風險 | 本計畫的處置／仍有限制 |
|---|---|
| network 公開 rubric leakage | worker default-deny＋sanitized mounts＋grading sidecar；全部子程序同邊界。canary／egress log 只支持邊界被測到的部分，不能證明模型預訓練沒見過公開題 |
| final pool 無 base | food arm保留官方 finals-only；k=1 直接 final，無 fallback。另評 F base/N，記 base→final regression；OAW 部署 gate 明確可保留 base，不能暗中把它加進官方 pool 之後仍叫同一方法。[S28] |
| resume marker 缺 input identity 仍可重用 | 全新 roots；外層驗 marker 必須有 expected inputs hash，另綁 data/harness/tool/model/network identity；缺欄就 stop/new run，**不修改舊 marker 補 identity**。保留已花費並新 attempt，不能清帳重跑。[S29] |
| task seeds 不是 model seeds | seed 42 只固定 stream；單題一次仍有 stochasticity。相同題 repeats 是題內變異，streams 是 library 群聚；不能把 rollout 次數當 independent N。未校準 floor_sd 時，12×1 不給等價判詞。[S22] |
| ledger 外成本 | 外部 meter 覆蓋 reflection/selection/retry/grading/authoring/review/controller/children；full-study unknown 就不聲稱 cheaper；失敗、棄用 patch、API 不回 usage 均保留 |
| filtered evidence 仍可洩題 | 不讓 worker讀完整 checkout／task.json；judge 不與 library 共檔案系統。context guard 為額外層，不是安全證明 |
| 不可評分與 ceiling／模型不相容 | planned/started/completed/scored/failed/censored 逐 arm 列；不把 unscored 當 0、不補挑題、不同模型不混格 |

**停止規則先於 paid call 固定：**

1. $0 gate：沒有 owner 的 runtime/API 或 adapter 授權、licence provenance 不清、network/mount canary 失敗、fixture 中 trigger/identity/meter 不能工作、模型 ID/endpoint 未確定，即停止於未試吃。free check 成功不冒充模型 access 成功。
2. worker 每次模型呼叫前向 controller reservation：以當前 input＋configured maximum output 上界記 logical reservation；無法對內部 CLI calls 做上界 reservation 時，必須用可攔截 broker／受控 wrapper，否則不開跑。Claude pool 總額硬上限 30,000,000，任何 background/children/shared model work 都計入；Codex pool separate cap 於 funding 時填，**null 不代表無限**。建議此 2 題 pilot Codex 上限 20M（設計值），達上限即 censored，不再補跑。
3. Claude 在 24M observed+outstanding 觸發 stop-new-work，保留最多 6M 收尾／對帳，不承諾全額可用於重試；任何新 reservation 仍不得使總額 >30M。每題完成後重算剩餘 high-cost forecast；expected+1.3 超 remaining 就暫停後續 paid launches、回 owner 作下一次 funding 決定，不自動追加題數或換題。2 題 expected total25.558M 不是全域 hard cap；分池各自管。
4. 第一個完整 unit若 Claude >5M 或 Codex >8M（設計的校準 stop），停止下一題，保留 partial pilot；這不是「失敗 runtime」判詞。單個 session 3,600 秒沿用官方 timeout；外層 4,500 秒 kill process group 並 reconciliation。每 paid call 另有 token reservation，不靠 wall time 保證 cap。
5. 只准 upstream 既有 validation/transport retry 上限；controller 不另加自動重試。judge 429／quota 可在原 manifest 用新 attempt重試一次且須有 reservation；第二次仍 unscored就停該題評分。auth/unsupported-model 不盲重試、不改 effort；leak canary 命中、worker 取得 rubric、identity mismatch 立即停整個 stream，隔離污染 outputs，不讓其 library 進下一題。
6. 沒有足夠 scored coverage、兩家 disagreement、private assertions/regression 不過、floor_sd 未校準、未出現機制、整池無 deliverable、模型被截斷、成本不完整、只有 adapter 失敗，都保留 **no conclusion**。報完整 planned denominator；缺失超過 0 的主要 paired set不作通過宣告。不得用現在這 2 題補齊 12 題證據。

| 最終證據 | 支持的決定 | 不支持的推論 |
|---|---|---|
| 2 題安裝／loop／meter／isolation 可用，品質可評 | 資助或不資助下一階段；保留 U1 方法；runtime 狀態仍 pilot | 不吸收、不 decline、不宣布比 OAW 好或省 token |
| 充分、獨立的 frozen product test 支持候選品質更好且成本可接受；或品質等價且更省；兩家同結論／機械驗收一致 | 可按 scope 吸收 U2；U3 另需 chronological/cold-start/去 library 消融；寫清替換／移除哪個現有組件 | 不能從整包贏推論每個單位都有貢獻；也不能推論搜尋流程更便宜 |
| runtime 主場有效但 OAW-use 無收益，或收益成本太高／adapter 維護不合算 | 保留方法 U1，runtime 不進預設；有特定用途可另列 optional | 不能說官方方法沒用；也不需因它有效就改 OAW runtime |
| 有公平官方 food arm／主場、完整計量與盲評後，runtime 穩定更差，或品質等價但成本依 gate 太高 | 可 decline 該版本／condition 的 runtime，保留已驗證方法；列局限與可撤回理由 | 未安裝／不相容／額度不足不能用同一 decline 判詞 |
| 單一 episode 顯示 spend較低，或 final被 selector 選中 | 只記 descriptive pilot evidence | 不代表 cheaper process、不代表獨立品質／泛化 |

正式效益 gate 沿用 EVAL_PROTOCOL 的 paired CI／TOST／cost ratio 與跨家族 agree；LAB Partial 是新 metric，**本 draft 不把 coverage ±0.10 直接套成 legal quality margin**。候選 funding 前須以獨立校準定 LAB 的 meaningful margin／floor_sd（不看正式組別結果），否則即使12題跑完仍只報 descriptive tasting；不用假門檻替 owner做採用決定。自我改進 minimum 2 cases×3 repeats 是工程最小 gate，也不保證統計力。[EVALUATION §5]

## 9. 尚不能由靜態閱讀確定、交接與自我檢查

未確定：兩個精確 model aliases 的 API/Vertex/CLI 服務可用性、subscription 可否保留官方路徑、真實 input/cache/reasoning 分布與價格、LAB 安裝後 eligible IDs／criteria 數／來源文件個別權利、adapter/meter/isolation 的實際工程可行性、native discovery、gradering independence、品質變異與 effect size。必須靠獲准後的安裝 inventory／免費 fixtures／有限 paid calibration 解決；不以靜態 schema 或來源閱讀替代。

本次只作一輪撰寫＋一次 self-check；strict JSON、所有 design 成本算式、分池總額、既有 31 個 pinned file/line links 的存在／範圍、fenced blocks 及隱私掃描通過。人工檢查修正了「抽題 hash order」與「scheduler seed order」的區分，並補明 native driver 的 execute/score linkage（新增 S30）、一題 smoke 退路，將 JSON 的 OAW 設計計數與 upstream source facts 分開。平台 Linux／Python 3.10.20；這是文件／成本模型檢查，不是 upstream runtime 或 OAW harness gate 驗證。沒有 code/template/installer 變更，故不執行 `sync_examples.py` 或 `harness_check.py`，也不改寫既有實驗。

## 固定來源索引

連結文字就是 file:line range；均為靜態閱讀，不是執行證據。

- [S1: docs/SETUP.md:7–73](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/SETUP.md#L7-L73)
- [S2: README.md:81–106](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/README.md#L81-L106)
- [S3: pyproject.toml:5–24](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/pyproject.toml#L5-L24)
- [S4: docs/SETUP.md:112–148](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/SETUP.md#L112-L148)
- [S5: harness2/cli/setup.py:46–108](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/cli/setup.py#L46-L108)
- [S6: harness2/install.py:193–247](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/install.py#L193-L247)
- [S7: harness2/preflight.py:46–154](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/preflight.py#L46-L154)
- [S8: docs/BENCHMARKS.md:11–39](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/BENCHMARKS.md#L11-L39)
- [S9: docs/BENCHMARKS.md:41–72](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/BENCHMARKS.md#L41-L72)
- [S10: docs/BENCHMARKS.md:74–124](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/BENCHMARKS.md#L74-L124)
- [S11: third_party/licenses/workbuddy-bench.LICENSE:1–20](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/third_party/licenses/workbuddy-bench.LICENSE#L1-L20)
- [S12: docs/SETUP.md:150–165](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/SETUP.md#L150-L165)
- [S13: docs/EXPERIMENTS.md:93–109](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/EXPERIMENTS.md#L93-L109)
- [S14: third_party/lab_runner/adapt_runs_cx/run_codex_lab.py:285–310](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/third_party/lab_runner/adapt_runs_cx/run_codex_lab.py#L285-L310)
- [S15: harness2/cli/_common.py:30–67](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/cli/_common.py#L30-L67)
- [S16: harness2/core/spec.py:33–86](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/spec.py#L33-L86)
- [S17: harness2/core/proposer.py:95–115 and 201–242](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/proposer.py#L95-L242)
- [S18: harness2/config.py:100–178](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/config.py#L100-L178)
- [S19: harness2/benchmarks/tasks.py:34–88](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/benchmarks/tasks.py#L34-L88)
- [S20: harness2/benchmarks/lab.py:495–547 and 660–755](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/benchmarks/lab.py#L495-L755)
- [S21: harness2/cli/judge.py:158–208](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/cli/judge.py#L158-L208)
- [S22: docs/EXPERIMENTS.md:6–28 and 64–90](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/EXPERIMENTS.md#L6-L90)
- [S23: harness2/core/ledger.py:15–64 and 115–132](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/ledger.py#L15-L132)
- [S24: harness2/core/context.py:15–26 and 105–129](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/context.py#L15-L129)
- [S25: tests/fixtures/harvey-labs/evaluation/scoring.py.txt:1–5 and 135–143](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/tests/fixtures/harvey-labs/evaluation/scoring.py.txt#L1-L143), [judge.py.txt:67–137](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/tests/fixtures/harvey-labs/evaluation/judge.py.txt#L67-L137)（fixtures，不冒充完整 data）
- [S26: harness2/core/recursion.py:36–38 and 150–261](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/recursion.py#L36-L261)
- [S27: harness2/core/recursion.py:280–350](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/recursion.py#L280-L350)
- [S28: harness2/core/selection.py:93–111 and 360–398](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/selection.py#L93-L398), [reflection:402–486](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/selection.py#L402-L486)
- [S29: harness2/core/runmark.py:132–159](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/runmark.py#L132-L159)
- [S30: harness2/benchmarks/lab.py:605–652](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/benchmarks/lab.py#L605-L652), [score:981–1022](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/benchmarks/lab.py#L981-L1022)
- [P1: paper v1 §3.1, §4 Figure 6, Appendix B/D/F](https://arxiv.org/html/2610.14224v1)（讀其方法、成本範圍與限制；沒有可套用這兩個 cell 的逐 stage token 表）
- [L1: pinned LAB README:14–18](https://github.com/harveyai/harvey-labs/blob/b58a28ae9fde5ee4b810e53b4fd0a1915325a35d/README.md#L14-L18), [LICENSE:1–19](https://github.com/harveyai/harvey-labs/blob/b58a28ae9fde5ee4b810e53b4fd0a1915325a35d/LICENSE#L1-L19)
- [L2: JobBench dataset card, metadata license:mit](https://huggingface.co/datasets/JobBench/job-bench/blob/main/README.md)（2026-11-13 靜態讀取；浮動 main，執行時另 pin）
- [L3: WorkBuddy dataset card, metadata other/tencent](https://huggingface.co/datasets/tencent/workbuddy-bench/blob/main/README.md)（同上，不把 code licence 當 data licence）
