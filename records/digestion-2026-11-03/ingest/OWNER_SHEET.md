# 本輪消化：你要做的決定（一頁）

2026-11-03，修訂 3。沒有實作、沒有安裝、沒有付費測試；**所有效果都是 not measured**，上線一律寫「parity, no improvement claimed」，三份食物對「只用食物」都是「parity vs food alone: not tested」。第 1 節現在就能決定（零上下文審查要靠它）；第 2–4 節等 PRE-02 的零上下文金魚審過修訂 3 再核准（D10）。細節在 `ingest/SUMMARY.md` 和 `ingest/backlog.json`。

## 1. PRE-01 常設政策（只決定一次，D11）

| 欄位 | 建議預設 | 你的決定 |
|---|---|---|
| 每份食物的篩選上限（Stage 0／1；logical tokens，大多是 cache read，不是計費量） | TokenEconomizer 120M、claude-mem 250M、graphify 300M；Stage 2、第二個 host 或任何超過上限的 stage 再問你 | |
| 消化系統開銷上限（金魚審查、probe、fixture） | 30M | |
| 沙箱第 1 級 | 這台機器上的專案副本，重導 host 設定目錄；只給不執行食物程式碼的 run | |
| 沙箱第 2 級 | 拋棄式 Linux 容器或 VM，每次試吃後銷毀；任何執行食物、安裝程式或讀 OS 憑證庫的 run（在 Windows 改 HOME 隔離不了 USERPROFILE 和 Credential Manager） | |
| API key 與金魚設定 | 每次試吃一把專用、有上限、跑完撤銷的 key；金魚用拋棄式設定目錄，canary probe 才驗得了（用你自己的登入只能做較弱的已知內容檢查） | |
| 網路 allowlist | 只開模型供應商 API；第 2 級抓相依時暫開 PyPI／GitHub，抓完就斷 | |
| Codex CLI（PRE-03） | 裝在這台機器和第 2 級映像檔（D8 要兩個 host）；不裝，所有 Codex 一半記 untested | |
| 合併 A/B 的額度分攤 | 共用 baseline 平均分給用它的食物；候選組算給它測的食物 | |

## 2. 提議吸收的批次（逐批核准；每一項目前都是 not measured）

| 批次 | 改了什麼 | 計畫的證據等級 |
|---|---|---|
| 1 | OAW-01 Windows npm shim 解析（永遠不經 cmd.exe）；OAW-02 共用雜湊基準與大小寫路徑 | static-measured（fixture） |
| 2 | 評估工具，不裝進使用者專案：OAW-03 不空轉判定、OAW-04 開銷與覆蓋度、OAW-05 有效 token（只報告）、PRE-10 通過次數比較／容許誤差／parity、PRE-04 允許 shell 的 Claude runner 與計量器、OAW-06 金魚啟動器、OAW-07–09 審查 packet 欄位、OAW-10 計畫文件；OAW-11 migrate 多印一行時機建議 | static-measured；OAW-10、11 為 doc |
| 3 | 寫入守門，預設開啟：OAW-12 拒絕憑證樣式（沒有 override）、OAW-13 拒絕 `<private>` 與 host 包裝標籤（拒絕，不剝除）、OAW-14「跳過驗證」筆記警告（`--strict` 下是錯誤） | static-measured |
| 4a | OAW-15 `recall --index`、OAW-17 超出預算時報出夠用的最小值、OAW-18 `memory add --files`／`recall --file` | static-measured |
| 4b | OAW-19 結束碼：3 需要選擇、4 沒有符合（search 0 → 4、get 1 → 4），見第 4 節 | static-measured |
| 5 | wiki：OAW-20 有證據才升級（選用）、OAW-21 `path::Symbol` 引用 lint、OAW-22 `wiki_sync.py cites`、OAW-23 renderer 版本與重新渲染比對（第一版只警告）、OAW-24 skill 大小 gate（bridge 算進 gate，EGM 記例外） | static-measured |
| 6 | OAW-25 doctor 的 stdlib 遮蔽檢查（FAIL 會讓專案 unhealthy） | static-measured |
| 7 | OAW-27 失敗特徵診斷（只報告）、OAW-28 驗證指令陷阱 fixture；都不安裝 | static-measured |
| 8 | catalog 攝取與掃描規則 OAW-29–34，等 catalog P2–P4 存在才實作 | static-measured（OAW-34 的 Codex 一半 untested） |
| 9 | OAW-35 README 動畫加靜態版（P8） | doc |

要先過 A/B、不在上表的保留項目：OAW-16 recall 資料聲明（修訂 3 改列）、HOLD-01–14、OAW-26。

## 3. 排出清單（整份接受，或指出要改列保留的單位）

| 食物 | 單位 | 元件 | 主要理由 | 建議 |
|---|---|---|---|---|
| TokenEconomizer | 19 | toolprune-auto-default、hooks-on-every-tool-call、background-daemons、windows-job-escape、repo-cwd-module-shadowing、sidecall-model-runtime、sidecall-isolation-gaps、injected-redirect-and-relay、envvalue-secret-capture、distiller-proposer、unpinned-clone-loading、slash-command-shell-args、probe-side-effects、bundled-third-party-text、live-ledger-and-status、pack-or-bundle、non-oaw-host-adapters、codex-skill-consent-pattern、failure-signature/oaw-improve-line | 未經同意改 host 權限、每次工具呼叫都跑 hook、背景程式逃出 job、第二套付費模型 runtime、注入沒有來源的文字、擷取秘密；其餘冗餘或不在範圍 | 整份接受 |
| claude-mem | 21 | capture-all-tool-io、observer-runtime-credentials、worker-daemon-chroma、sessionstart-injection、file-read-gate/hook、mcp-server-loader、bundled-author-skills、telemetry-default-on、launcher-path-edits、supply-chain-install、worker-http-api、my-work-auto-refresh、deliverables-capture、native-memory-bridge、commercial-funnel-license、codex-adapter、knowledge-agent-corpus、observation-type-vocabulary、context-budget-fit、bundled-mixed-license-runtime、capture-exclusion-knobs | 擷取全部工具 I/O 送第三方、讀 OS 憑證庫的第二 runtime、常駐 daemon、每個 session 注入、預設遙測、改 PATH、無法審查的安裝、沒有認證的 loopback API、背景代跑 agent、授權混雜；其餘冗餘 | 整份接受 |
| graphify | 17 | always-on-router、skill-autoinstall、skill-self-refresh、git-hook-installer、pretooluse-guard、host-registration-writes、skill-package、llm-backend-autodetect、repo-controlled-interpreter、semantic-subagent-fanout、wiki-export、memory-reflect-loop、mcp-server、statement-confidence-tags、output-integrity-guards、optional-extra-remote-fetches、pypi-name-and-release-churn | 第二個強制 router、靜默安裝和升級後換掉 skill、git hook、每次工具呼叫的 guard、未經同意寫全域設定並刪使用者段落、過大的 skill、自動把內容送到 8 家 provider、repo 決定要執行的程式、沒有上限的 subagent、會刪頁的 wiki 匯出、沒有認證的 MCP；其餘冗餘或只記錄 | 整份接受 |

## 4. 其他只有你能決定的事

| 決定 | 建議 |
|---|---|
| 目標版本（PRE-07） | 全部批次進還沒打 tag 的 2.0.0。不相容的是 OAW-19、OAW-12／13、OAW-25；只影響 `--strict` 的是 OAW-14、21、23。若 2.0.0 已打 tag：相加性的進 2.x，不相容的等 3.0.0 |
| 移除粒度（PRE-07） | 只用「移除 build」：在目前 build 上撤掉該項和依賴它的項目，不加逐項開關。還原是線性的：還原到舊 build 會連後面的 build 一起退 |
| CLI 契約（OAW-19） | 3 = 需要選擇、4 = 沒有符合；`memory recall` 沒命中維持 0；`get` 在所有 OS 提供唯一的不分大小寫符合並在 stderr 註明；空的 knowledge base 一律 0 |
| 授權路線（OAW-07、12、30） | 附 Apache-2.0 歸屬並標示修改，LICENSE／NOTICE 隨附（比照 EGM 的前例）；clean-room 重寫成本高，也難證明 |
| 流程規則 P1–P4（PRE-09） | 確認。D2 範圍選「整份食物」（D2 原文就是「至少和只用那份食物一樣好」）；但下限組都有條件，可能長期不跑 |
| 延後：OAW-26 `doctor --probe-host` | 只有 Codex 檢查通過才問你；Codex 不可用就依 D8 排出 |

## 5. 政策設好之後，系統自己會做的事（估計，logical tokens）

| 順序 | 工作 | 估計 |
|---|---|---|
| 1 | PRE-06：每個 host 的 init probe 和 canary probe；配方檢查（沒有工具的金魚帶 packet 審第 2 版） | < 0.1M；0.4–1M |
| 2 | PRE-02：零上下文金魚審修訂 3，Elephant 處理意見，再交給你核准批次 | 0.4–1M（配方檢查沒過再加 2.4–3.6M） |
| 3 | PRE-05：fixture W、Q-code、F2（F2 在這裡選定並審查）；所有免費的 Stage 0 | 2.4–3.6M；0 |
| 4 | 你核准後實作批次 1、2（不花模型額度）；每個 build 兩個金魚審 diff | 每個 build 約 1.2–1.8M，全部約 12–20M（沒有工具的金魚應該少很多，未量測） |
| 5 | 批次 1 之後：HOLD-07 第 0 階段；有 Codex 時 HOLD-08a A2 | < 1M；0.6–4.5M |
| 6 | 依 `test_order` 在上限內跑篩選；停止規則會讓多數項目在 Stage 0 或 1 結束；超過上限才問你 | 全部都跑約 610–930M |
| 7 | 每一項回報結果和證據等級；沒有量測證據就寫 not measured，絕不寫「增強」 | 0 |

第 1–3 步合計約 3–6M（配方檢查沒過時約 6–9M）。所有數字都是估計（Claude 校準：每個會用工具的新 agent 約 0.6–0.9M；Codex 未校準）。
