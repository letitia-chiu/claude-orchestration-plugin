# playbook（統籌–執行分層工作流：方法層）

> 本目錄由 `/orchestration:init-playbook` 生成骨架，內容由本專案逐步長出。

| 欄位 | 內容 |
|---|---|
| 適用場景 | 本專案的任何開發、除錯、審查、交班工作 |
| 不適用場景 | 純聊天、與專案無關的問答 |
| 必讀前置 | 本專案的 CLAUDE.md（若有，通常是每 session 自動載入的現況與規範 SSOT） |
| 不能違反的約束 | 本目錄**不重複**專案主文件（如 CLAUDE.md）內容：現況/進度以主文件為準，本目錄只放「方法與教訓」；兩邊重疊處以引用代替複寫 |
| 例外處理 | 兩邊矛盾時以較常更新的現況文件為準，並同一個 commit 修正本目錄 |
| 驗收方式 | 新開的統籌 session 只讀本目錄＋專案主文件，就能：正確選驗證電池、開工先跑盲區清單、收尾產出合規交班 |

## 檔案地圖（按需載入，別一次全讀）

| 時機 | 讀什麼 |
|---|---|
| 開工（非瑣碎＝預估 ≥15 分鐘**或碰行為/資料**） | `unknowns-interview.md`（盲區自答＋提問門檻）＋`architecture-constraints.md` §鐵律 |
| 統籌窗運作（派工/分層/成本） | `orchestration.md`（統籌七律＋八件派工單格式＋判準表；SOP 命令＝`/orchestration:kickoff` `/orchestration:dispatch` `/orchestration:wrapup`） |
| 設計新功能 | `architecture-constraints.md` 全文＋`known-failures.md` §架構級 |
| 動手寫 code 前後 | `review-rubric.md`（風險分級＋驗證電池決策表） |
| 修 bug | `debug-playbook.md`（症狀速查）→ `known-failures.md`（別踩回舊坑）；動手修之前補跑盲區 pass |
| 委派或覆核（governance／host／tier／reviewer 四層路由） | `task-routing.md`＋`agent-routing.json`＋`handoff-template.md` §工單；派工單用 plugin 附帶範本 `examples/task-packets/`（active-host-feasibility／active-host-implementation／codex-adversarial-review／claude-adversarial-review／headless-codex-implementation），回報對照 `examples/schemas/orchestration-result.schema.json`（schema v2） |
| 大案子執行中 | `implementation-notes-template.md` |
| 收尾/交班/換機 | `handoff-template.md`＋`review-rubric.md` §完成定義 |

> 註：`agent-routing.json`（schema v2）是 governance-neutral、host-aware、tier-aware 路由的 SSOT：governance identity 由每次 task packet 明示；host mode（claude_hosted／codex_hosted）一次一個；兩個 adapter 均已實作，feasibility／implementation 走 active host 自家 scout／worker／executor；external reviewer 用對方 CLI（經 bounded runner：timeout、transcript、Git 證據、allowlist 驗證）。Codex-host surface 必須先用 `scripts/init_codex_host.py --target /absolute/path/to/target-repository` materialize 到 target Git repository；headless CLI implementation 為非預設 opt-in。

## 日常工作流

### 開工前（預估 ≥15 分鐘、或碰行為/資料的任務都適用）
1. 讀專案現況文件相關條目＋上表對應文件。
2. **盲區 pass**：照 `unknowns-interview.md` 第一步自答；答不出的老實列成 unknowns，不腦補。
3. **提問**：門檻與類別以 interview 檔為準、最多 3 個、每個附推薦選項。使用者不在場時：記錄假設、先做可逆的部分，不空等。
4. **計畫**：先寫最可能變動、最需要人確認的部分；標出風險門（什麼情況必須停下來，不可以猜）。

### 執行中
- 非瑣碎案子照 `implementation-notes-template.md` 記取捨。
- 每完成一階段輸出一行進度；斷線重連第一句先報進度。

### 收尾（缺一不算完成）
1. `review-rubric.md` 驗證電池跑完、記指紋。
2. `known-failures.md` 快掃：有沒有踩回舊坑？產生新坑就**當場同 commit 入館**。
3. 對照 `architecture-constraints.md` 鐵律自查。
4. 照 `handoff-template.md` 更新交班快照＋commit。
5. 完成回報三段式（見下方慣例）、**用使用者的語言**回報（見 `orchestration.md` §語言律）＋告訴使用者「怎麼體驗」的確切路徑。

## 維護規則（這是活文件）

- 新坑 → 修好當下**同一個 commit** 補 `known-failures.md`；新鐵律 → `architecture-constraints.md`；新驗證手法 → `review-rubric.md`。
- 過時就改、不要累積。誰發現誰改。
- 本目錄的品質就是本專案協作品質的下限。
