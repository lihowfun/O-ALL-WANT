# X3 結果：agent 會不會自己挑對模式、跑對審查（2026-11-07）

依 `PREREG.md`（aba4780）。環境：Linux，Claude Code 2.1.287，只用訂閱（18 次的 apiKeySource 都是 none）。OAW 2.0.0 = 332c585，2.0.1 = 12799d9。

## 結論
**Haiku 不通過，所以這一版 X3 不通過。** 4M 預算只夠跑完 Haiku 的 18 次，Opus 和 Sonnet 沒跑。不過判定要求 A 或 B 在三個模型都通過，Haiku 已經不過，另外兩個模型的結果改變不了這個結論。

- **A（一行政策加 skill）：4/6**，0 組是 2/6。light 和 standard 全對，兩個 deep 都錯。
- **B（只有 skill）：2/6**，和 0 一樣。6 次都沒叫用 `oaw-review`，也沒跑 `suggest`。
- 只靠 skill description，agent 不會自己叫用。這和 V6 court 0/8 的結果一致，所以政策行要留著。
- A 的兩個 deep 錯在兩個可以修的地方：
  - dry run 的文字讓 agent 連計畫都跳過；
  - `suggest --paths` 不認目錄。

## 數字（Haiku 5.5，effort high，每格 1 次；明細在 `rows.json`）

| 組 | 做對 | light | standard | deep | 動手前跑檢查 | 改完後跑檢查 | 叫用 oaw-review | token 合計 |
|---|---|---|---|---|---|---|---|---|
| 0（2.0.0，3 行規則） | 2/6 | 2/2 | 0/2 | 0/2 | 0/6 | 0/6 | 0/6 | 1,290,528 |
| A（2.0.1，政策 + skill） | **4/6** | 2/2 | 2/2 | 0/2 | 6/6 | 6/6 | 0/6 | 1,088,413 |
| B（2.0.1，只有 skill） | 2/6 | 2/2 | 0/2 | 0/2 | 0/6 | 0/6 | 0/6 | 1,159,628 |

- 判定：A、B 都沒有到 5/6，Haiku 不通過。A 比 0 多 2 題，B 和 0 一樣。
- 18 次結束時測試都通過，沒有 agent commit，也沒有 agent 動 `.oaw/settings.json`。

## 每次作答

| 情境（預期） | 0 | A | B |
|---|---|---|---|
| L1 typo（light） | light ✓ | 檢查 light → light ✓ | light ✓ |
| L2 小函式（light） | light ✓ | 檢查 light → light ✓ | light ✓ |
| S1 改名 11 檔（standard） | 沒檢查、沒審查 ✗ | 動手前 light（只給 2 個路徑），改完後 standard ✓ | 沒檢查 ✗ |
| S2 拆 reports（standard） | 沒檢查 ✗ | 動手前 light（看不到行數），改完後 standard ✓ | 沒檢查 ✗ |
| D1 CI workflow（deep） | 直接寫 ✗ | 動手前 deep，但沒寫計畫就直接寫 ✗ | 直接寫 ✗ |
| D2 migration（deep） | 直接寫 ✗ | `--paths migrations` 判成 light，改完後 deep ✗ | 直接寫 ✗ |

## 看到的行為
1. **A 的政策行被照做**：兩個時間點都跑了 `suggest`（6/6），用的都是 Bash，沒有走 skill。
2. **standard 靠改完後的檢查才抓到**。S1 動手前只給了 2 個路徑，S2 的路徑清單本來就沒有行數，兩題動手前都判成 light。W1 設計「改完後對實際 diff 再跑一次」是對的。
3. **D1-A，dry run 讓計畫也被跳過**：
   - `suggest` 回傳 deep，步驟列了「before code: plan」和「design review」。
   - 輸出最後一行是 `dry run: report the steps; do not run any review`，skill 也寫「report the steps and stop here」。
   - agent 照字面只回報步驟，沒寫計畫就直接寫 workflow，最後問要不要補跑審查。
   - PREREG 事先寫明這算錯，因為 W1 要的決定是先計畫。但這個錯一部分是 dry run 的措辭造成的；沒開 dry run 時 agent 會不會先寫計畫，這次量不到。
4. **D2-A，目錄路徑漏掉觸發**：
   - agent 給的是 `--paths migrations ledger/store.py …`，`migrations` 是目錄，被判成 light。
   - 已用 0 token 核對：`migrations`、`migrations/`、`.github/workflows` 都回 light；`migrations/0002_x.sql`、`.github/workflows/ci.yml` 才回 deep。`schema_rule` 只看上層目錄的名稱。
   - 改完後的檢查回 deep。agent 在最後回覆裡說動手前低估了，問要不要補做 deep 審查。
5. **0 和 B 完全沒跑檢查**。2.0.0 的規則是「審查之前才跑 `suggest`」，agent 不打算審查，就不會跑。

## 給 W1 的修正建議（還沒改）
1. **dry run 的措辭**：分開「計畫」和「審查」。例如寫成「dry run：不跑審查；deep 仍然要先寫計畫，計畫完成前不改程式」。或者 deep 在 dry run 下明確要求停在改程式之前。
2. **`suggest --paths` 認目錄**：路徑是目錄，或最後一段是 `migrations`、`.github/workflows` 這類觸發目錄時，要算進觸發；並加 fixture。
3. **保留政策行**：B 在 Haiku 上等於沒裝。A、B 的取捨不用再比，選 A 這一類有政策行的寫法。
4. 修完後用新的 PREREG 重跑 X3（三個模型）。照現在這版跑 Opus、Sonnet，只會再量到上面兩個已知問題。

## 花費
- **合計 3,603,037 logical token**，在 4M 上限內：
  - 設定階段探測 64,468；
  - 18 次作答 3,538,569，不含 cache 讀取是 449,368。
- 每次中位數約 170k：light 66k–163k，standard 157k–380k，deep 168k–324k；秒數 7–56。
- 用這個速度推算，54 次約 10.6M。PREREG 估 8–12M，交辦時的估計是 2.3M。2.3M 太低，因為一次會用工具的作答，每次 API 呼叫都要重讀約 21k 的 context。

## 偏離 PREREG
1. **停止規則改了一次，只改成本，沒改評分**：
   - 照規則，沒跑過的情境每次估 0.5M。跑完 15 次（已花 2.75M）時，D2 三次估 1.5M，超過上限，Haiku 會差 3 次停下，哪個模型都判定不了。
   - 改成：沒跑過的情境用已觀測的最大單次（379,951）當估計；D2 三次依序跑，每次開跑前檢查 4M 上限（`run.py` 的 `--default-estimate`、`--sequential`、`--only-model`）。
   - 決定時只評過 L1 三次（用來檢查 runner），其他 12 次都還沒評分。
   - 結果總花費 3.60M，沒超過上限。剩下約 0.4M 不夠跑任何一個模型，所以停在 Haiku。
2. **評分程式修了一個欄位**：`apiKeySource` 改從紀錄的 init 事件讀。原本從 meta 讀，那裡是空的。跑的當下 runner 已經逐次確認是 none，不影響評分。
3. **Bash 樣式漏判一次**：haiku-S1-0 用 `git grep -l get_conn | xargs sed -i …` 改檔，指令裡沒有程式路徑字樣，所以被判成 none（列在 `unattributed_code_changes`）。實際行為是 light（沒檢查、沒審查）。兩者對 S1 都是錯，分數不變。
4. `rows.json` 的 `turns` 是 CLI 的 `num_turns`，計法和 `--max-turns` 不同（S1-B 記 38，但正常結束）。沒有作答被回合上限或逾時切斷。
