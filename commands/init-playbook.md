---
description: Generate the docs/playbook/ skeleton in the current project (the methodology-layer docs for the orchestrate-and-delegate workflow)
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Generate skeleton files under `docs/playbook/` in the **current (target) project**.

**Rules**: for each file below, first check whether `docs/playbook/<filename>` already exists in the target project. **Exists = skip, don't overwrite** (list skipped filenames in the final report); **doesn't exist = create it verbatim with the content attached below**. Never overwrite, replace, merge, append, or auto-repair an existing target file — not even when its content has drifted from the template. The same no-overwrite rule applies to `docs/playbook/agent-routing.json`: if the target project already has its own routing file, the result is `SKIP — existing file preserved`; never replace it with the plugin default.

11 files total: `README.md`, `orchestration.md`, `architecture-constraints.md`, `unknowns-interview.md`, `review-rubric.md`, `debug-playbook.md`, `known-failures.md`, `handoff-template.md`, `implementation-notes-template.md`, `task-routing.md`, `agent-routing.json`.

What the generated playbook provides: role-first routing contracts (workflow roles resolved to provider/profile via `agent-routing.json`), pointers to this plugin's task-packet templates (`examples/task-packets/`) and result schema (`examples/schemas/orchestration-result.schema.json`), and the contract surface for the bounded external-agent runner integration. Do not claim more than that: no real Codex/Claude smoke test has been passed by generating these files, network isolation is not thereby verified against real CLIs, arbitrary providers are not supported, and no runner is installed into the target project. This command never modifies the target project's Claude settings or hooks.

---

> NOTE: The playbook skeleton content below is currently authored in Traditional Chinese; multilingual generation is planned (see CHANGELOG). Each embedded template is wrapped in a **four-backtick** outer fence so that three-backtick fences inside the template stay part of the content.

## File 1/11: `docs/playbook/README.md`

````markdown
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
| 委派或覆核外部 provider（role→provider 路由） | `task-routing.md`＋`agent-routing.json`＋`handoff-template.md` §工單；外部派工單用 plugin 附帶範本 `examples/task-packets/`（codex-feasibility／codex-implementation／claude-adversarial-review），回報對照 `examples/schemas/orchestration-result.schema.json` |
| 大案子執行中 | `implementation-notes-template.md` |
| 收尾/交班/換機 | `handoff-template.md`＋`review-rubric.md` §完成定義 |

> 註：`agent-routing.json` 是角色→provider 對映的 SSOT。外部 CLI provider 的機械化包裝（bounded runner：timeout、transcript、Git 證據、allowlist 驗證）由 orchestration codex enablement 後續 batch 提供，尚非現成能力。

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
````

---

## File 2/11: `docs/playbook/orchestration.md`

````markdown
# 統籌–執行分層（orchestration：主窗當腦、分身動手）

| 欄位 | 內容 |
|---|---|
| 適用場景 | 統籌窗（使用者開的主 session）的日常運作：拆單、派工、驗收、交班 |
| 不適用場景 | 產品本身的 runtime 行為；純聊天／一句話問答 |
| 必讀前置 | `README.md`＋`task-routing.md`＋`agent-routing.json`（角色→provider 路由） |
| 不能違反的約束 | 驗收永遠在統籌；規格不清不准派工；同一不變量只准一個實作 owner |
| 例外處理 | 止血可統籌親手做＋事後補審；同一 defect family 在外部覆核重現兩次＝停止逐點修補，升級方法或 owner |
| 驗收方式 | 不只看測試全綠：必須同時有 inventory、class closure、adversarial probe、valid-path regression |

## 架構一張圖

```text
權責層（不可執行、不可路由）
ChatGPT ＝ architecture／authoritative plan／authorization／acceptance／final adjudication owner
│
統籌（主窗，當下可用的最高智慧模型 + high effort）
│  只做：理解需求、盲區／提問、抽象化 finding、拆單、依 agent-routing.json 路由派工、
│        對抗式驗收整理、整合、交班（驗收與裁定的最終權在權責層）
│
├─ feasibility_verifier ＝唯讀可行性查證（fresh session；預設 codex_cli / codex_read_only）
├─ implementer          ＝主要實作（限授權 worktree；預設 codex_cli / codex_workspace_write）
├─ adversarial_reviewer ＝fresh-context 對抗式覆核（只審不改；預設 claude_cli / claude_read_only）
├─ claude_subagent path ＝scout（Haiku 4.5 唯讀偵察）／worker（Sonnet 5）／executor（Opus 4.8）
│                         既有 agents 完整保留，是隨時可切回的 fallback provider
└─ 驗證 lens            ＝內部對抗式審查；不取代外部獨立覆核
```

- 角色（做什麼）與 provider（用哪個引擎執行）分離；provider 對映以 `agent-routing.json` 為 SSOT，細節見 `task-routing.md`。
- 統籌模型：當下可用的最高智慧模型＋effort high。
- claude_subagent path 成本權重（API 定價比例，訂閱額度同方向）：**Haiku : Sonnet : Opus ≈ 1 : 3 : 15**。effort：統籌自選（/effort）；executor/worker＝medium（釘在 agents frontmatter）；scout（Haiku 4.5）不支援 effort 參數＝不設。
- 執行者一律**開工第一行自報模型 ID**（釘選探針的指紋機制，防「以為派了便宜的、其實跑到貴的」）；外部 CLI provider 另以工單的 Explicit model 欄位釘住；高風險覆核另驗 model＋effort。

## 角色與 provider 分離

權責 owner 固定、不可路由：

```text
architecture_owner        = chatgpt
authoritative_plan_owner  = chatgpt
authorization_owner       = chatgpt
acceptance_owner          = chatgpt
final_adjudicator         = chatgpt
```

執行角色只有三個：`feasibility_verifier`（唯讀查證）、`implementer`（單一 batch 實作）、`adversarial_reviewer`（fresh-context 只審不改）。行為契約與 provider 無關，換 provider 不換契約。

不可越權的硬邊界：

- implementer 不得 dispatch reviewer；reviewer 不得修 code；兩者 provider 必須不同（fail closed）。
- feasibility 與 implementation 不共用 session；reviewer 永遠 fresh session。
- 外部 provider 的任何 Git 寫入需 authorization owner 另行明文授權。
- reviewer 產出的是 candidate findings；成立與否由 final_adjudicator 裁定，統籌只做整理與轉呈。

可逆性：把 implementer 換回 `claude_subagent`（worker／executor）或 reviewer 換回其他已支援 provider，只改 `agent-routing.json`＋工單；commands 與本檔方法論不動。

## 統籌七律

1. **統籌不搬磚**：超過約 30 行機械修改或跨 3 檔批次操作，原則上派工。
2. **統籌不吃生資料**：大量讀檔、log、搜尋交 scout，只收結論＋file:line 證據。
3. **規格不清不派工**：模糊在統籌層解決；不把判斷外包給執行層。
4. **finding 先抽象、再修**：review 指出的行號只是觀測樣本。派工前必須寫出 defect family、同族搜尋範圍與封閉證據。
5. **同一不變量只有一個 owner**：共用契約、validator、inventory、boundary tests 不可拆給不同平行 worker。
6. **驗收在統籌**：執行者回報是線索，不是證據；高風險工作統籌至少親驗一個反例＋一個合法路徑。
7. **同族問題重現就停迴圈**：fresh-context 外部覆核後若同一 defect family 再出現，不再發下一張逐點修補單；重開 family inventory 或更換 owner／方法。

## 語言律（貫穿全程，凌駕形式）

統籌對使用者的**每一次**對話、提問、進度、回報，一律**鏡射使用者當下的語言**——講繁中回繁中、講日文回日文、講英文回英文。

分清兩層、別混：
- **產出物內容**（檔名、程式碼、frontmatter 值、刻意以英文為基準的命令／agent 腳本）維持原文。
- **你對使用者說的話**（結論、標題、分段、提問）跟著使用者走。

命令／agent 腳本英文化，只是「給模型讀的指令」用英文，不是你的輸出語言。長 session 尤其容易漂成英文——這是明確失敗模式，收尾回報時務必自檢。

## 派誰（先選 role，再由 agent-routing.json 解析 provider）

| 任務長相 | role（→ 預設 provider/profile） | 附加規則 |
|---|---|---|
| 現況／檔案／surface 盤點 | scout（claude_subagent） | 唯讀；回傳結論＋證據，不貼大段原文 |
| 對 authoritative plan 的 repository-local 可行性查證 | feasibility_verifier（→ codex_cli / codex_read_only） | 唯讀、fresh session；verdict 只有三種；工單用 codex-feasibility packet |
| 規格明確、已授權的實作 batch | implementer（→ codex_cli / codex_workspace_write） | 限授權 worktree＋allowed files；工單用 codex-implementation packet；fallback＝claude_subagent worker（邊界獨立；不得與其他 agent 共用同一 invariant owner）／executor（跨模組、精密；production＋共用 validator＋inventory＋boundary tests 同一 context） |
| 高風險第二雙眼 | adversarial_reviewer（→ claude_cli / claude_read_only） | fresh context、只審不改、凍結候選集合；工單用 claude-adversarial-review packet；覆核模型依風險分級（平衡型日常／旗艦關卡／輕量低風險；專案有委派範本則照其格式）；finding 成立由 final_adjudicator 裁定；外部 reviewer 不可用＝lens 加倍（rubric 有明文） |
| 判斷／語氣／審美／小事 | 統籌自己 | 派工成本高於自做 |

## finding 泛化規則

收到 bug 或 NO-GO finding 後，統籌先填：

```text
Observed instance:
General defect class:
Authorized same-class search scope:
All matches expected to be inventoried:
Proof required for class closure:
Explicit exclusions:
```

例：

- `success="false"` 被當成成功，不是單一欄位 bug；family 是「外部 bool boundary 使用 truthiness」。
- frozen dataclass 接受 list，不是單一 tuple bug；family 是「contract object 保留 mutable／錯型容器」。
- enum 欄位接受字串，不是單一事件 bug；family 是「字串冒充 discriminator」。

窄 scope 可以限制功能與檔案，但不得禁止在授權 production surface 內搜尋同族問題。

## 不變量 owner 規則

下列內容視為同一 ownership unit，不得平行切碎：

- production contract／schema object
- 共用 runtime validators
- contract inventory／matrix
- boundary／mutation／adversarial tests
- 對該 invariant 的文件宣稱

可平行的前提是彼此沒有共用契約、狀態、validator 或驗收宣稱。若執行中發現 ownership collision，停止其中一單並回統籌重切。

## 內部派工單格式（八件缺一不可）

```text
【目標】一句話＋可觀察完成狀態
【範圍】精確路徑＋workdir
【禁區】不碰什麼
【Invariant owner】單一 owner／context；不適用則明寫
【Defect-class closure】observed → family → search scope → exclusions；不適用則明寫
【規格】關鍵決定逐條列，不留給執行者猜
【驗收】命令＋期望輸出＋inventory＋同族封閉＋adversarial probes＋valid-path regression
【回報】結論 → 檔案 → 分層證據 → 殘留／假設／blocker
```

## 驗收證據四層

高風險契約、信任、持久化、身分、投遞、安全或授權變更，缺一不算完成：

1. **Inventory evidence**：所有授權範圍內的 contract field／external return boundary 已列入。
2. **Class-closure evidence**：finding 已泛化，同族 match 全部修正或明確排除。
3. **Adversarial evidence**：錯型、truthiness、alias、nested mutation、失敗關閉等反例實跑。
4. **Regression evidence**：完整 gate 通過，且合法 end-to-end 路徑仍正常。

測試數量只屬第 4 層，不能單獨證明 invariant。

## Python runtime contract 觸發器

碰到以下任一項，派工與驗收必須使用 `python-runtime-contract-audit` Skill：

- dataclass／`frozen=True`
- Protocol／callback
- bool gate／truthiness
- enum discriminator
- tuple／mapping／nested payload
- receipt、claim、trace、intent、identity、persistence、capability
- reviewer finding 涉及 wrong type、mutable alias 或 runtime validation

核心原則：annotation 不是 runtime enforcement；frozen 不是 deep immutable。

## 外部覆核與止損

1. 實作者先跑內部 adversarial pass。
2. 候選集合凍結並記錄 hash／test fingerprint。
3. 外部模型 fresh context、只審不改。
4. NO-GO 後先分類：新 family，或舊 family 的漏網成員。
5. 舊 family 漏網＝重開整個 inventory，不准再發只修行號的工單。
6. 同一 family 在 fresh-context review 後再次重現＝停止迴圈，升級方法、owner 或使用者裁定。

## 統籌 context 節食

- 大輸出落檔，不貼主窗。
- playbook 按需載入。
- 長 session 以 handoff 開新窗，不拖歷史。
- 外部 reviewer 只吃凍結審查包，不吃整段聊天歷史。

## 新統籌窗開機儀式

1. `git pull`（換機／新窗必做）→ 讀最新 handoff。
2. 有指紋疑慮就跑 gate 對總數／hash。
3. `/orchestration:kickoff`：盲區→提問→計畫→派工切分→**停在計畫**（不開工）。
4. 計畫確認後由使用者下 `/orchestration:go` 才開始執行（沒有 go＝繼續討論；「小且可逆」不是例外）。
5. 收尾 `/orchestration:wrapup`。

## 與專案規範的關係

- 專案 `CLAUDE.md`、architecture constraints、review rubric 優先於通用方法。
- 本檔定義誰負責、finding 如何泛化、證據怎麼分層；具體測試與紅線由目標專案長出。
- 新踩坑應進 `known-failures.md`；同族 finding 重現要記成方法論失敗，而不只是新增一個 bug 條目。
````

---

## File 3/11: `docs/playbook/architecture-constraints.md`

````markdown
# 架構鐵律與約束

| 欄位 | 內容 |
|---|---|
| 適用場景 | （待本專案填寫） |
| 不適用場景 | （待本專案填寫） |
| 必讀前置 | （待本專案填寫） |
| 不能違反的約束 | （待本專案填寫） |
| 例外處理 | （待本專案填寫） |
| 驗收方式 | （待本專案填寫） |

> 本檔內容由本專案長出、過時就改；此為 /orchestration:init-playbook 生成的空骨架。

## （章節待補）
````

---

## File 4/11: `docs/playbook/unknowns-interview.md`

````markdown
# 開工盲區訪談

| 欄位 | 內容 |
|---|---|
| 適用場景 | （待本專案填寫） |
| 不適用場景 | （待本專案填寫） |
| 必讀前置 | （待本專案填寫） |
| 不能違反的約束 | （待本專案填寫） |
| 例外處理 | （待本專案填寫） |
| 驗收方式 | （待本專案填寫） |

> 本檔內容由本專案長出、過時就改；此為 /orchestration:init-playbook 生成的空骨架。

## （章節待補）
````

---

## File 5/11: `docs/playbook/review-rubric.md`

````markdown
# 驗證電池與審查準則

| 欄位 | 內容 |
|---|---|
| 適用場景 | （待本專案填寫） |
| 不適用場景 | （待本專案填寫） |
| 必讀前置 | （待本專案填寫） |
| 不能違反的約束 | （待本專案填寫） |
| 例外處理 | （待本專案填寫） |
| 驗收方式 | （待本專案填寫） |

> 本檔內容由本專案長出、過時就改；此為 /orchestration:init-playbook 生成的空骨架。

## （章節待補）
````

---

## File 6/11: `docs/playbook/debug-playbook.md`

````markdown
# 除錯手冊

| 欄位 | 內容 |
|---|---|
| 適用場景 | （待本專案填寫） |
| 不適用場景 | （待本專案填寫） |
| 必讀前置 | （待本專案填寫） |
| 不能違反的約束 | （待本專案填寫） |
| 例外處理 | （待本專案填寫） |
| 驗收方式 | （待本專案填寫） |

> 本檔內容由本專案長出、過時就改；此為 /orchestration:init-playbook 生成的空骨架。

## （章節待補）
````

---

## File 7/11: `docs/playbook/known-failures.md`

````markdown
# 踩坑博物館

| 欄位 | 內容 |
|---|---|
| 適用場景 | （待本專案填寫） |
| 不適用場景 | （待本專案填寫） |
| 必讀前置 | （待本專案填寫） |
| 不能違反的約束 | （待本專案填寫） |
| 例外處理 | （待本專案填寫） |
| 驗收方式 | （待本專案填寫） |

> 本檔內容由本專案長出、過時就改；此為 /orchestration:init-playbook 生成的空骨架。

## 通用工程教訓（起始種子，來自本 plugin 附帶的 universal-lessons）

> 若本 plugin repo 含 `universal-lessons.md`，以下清單即為其內容；本專案之後在此清單後繼續長出自己的具體條目（症狀→根因→修法→教訓）。

1. 核心能力不可寄生在外部黑盒狀態；外部 session／服務只能當快取，斷了要能無感降級。
2. 建模有狀態的世界時，每個狀態都要解出它的脈絡條件；遇歧義一律往最保守的解讀判。
3. 每條寫入路徑都要盤出對稱的刪除路徑；修一條就立刻盤同族其他路徑；不變量要有 audit 工具常態驗，不靠肉眼。
4. 聚合／合併類功能，先問「所有相關方是否都在裡面」。
5. 注入面一律 allowlist，且類別收窄到能點名；deny-list 對 Unicode 必輸；用對抗式 probe 迭代，不靠想像。
6. 信任判斷不可建立在 basename／正規化這類有損投影上；比對原始 token。
7. 凡 shell 會再處理一次的東西（glob／變數／替換），安全檢查要在字面層做，或假設它已展開成最壞情況。
8. 模型產出的格式永遠比 spec 鬆；parser 要容忍開頭變體，並測「解析失敗時外洩什麼」。
9. 任何「自由 dict」設定欄位都是走私通道；逐鍵 schema、值型別鎖死。
10. URL 會進 log；憑證不走 query string，要走就用短命票。
11. 掃描式背景迴圈必配 in-flight 標記，且標記要在入列瞬間、不是開始處理才標。
12. 節流／冷卻／每日上限一律持久化；設計時直接問「重啟會怎樣」。
13. schema-gated 的寫入路徑，每個新欄位都是三件套（schema＋normalize＋round-trip）；驗證走真入口、不走捷徑。
14. API 層型別照後端真回應寫；型別謊言的代價是整頁崩潰。
15. 跨模型協作要有「對到同一版」的握手信物（測試總數／commit hash）。
16. 自動化工具會動你腳下的地；收工檢查分支是慣例不是偏執。
17. 功能的終點是使用者實際能用，不是 merge；順口提的小需求當場落檔。
18. 外部 API 以實測回應為準；寫 code 前先 curl 一發存證。
19. 改動有調節器（moderator／clamp）的系統前，先讀清它的實際作用域；用「事前推算最終顯示值」做 guard。
20. 便宜模型需要剛性輸出契約；parser 永遠假設對面會答非所問。
21. 依賴模型自標的協定，都要有後端 backstop 接「它最自然的寫法」；範例文檔裡的寫法就是模型最會寫的寫法。
````

---

## File 8/11: `docs/playbook/handoff-template.md`

````markdown
# 交班模板

| 欄位 | 內容 |
|---|---|
| 適用場景 | （待本專案填寫） |
| 不適用場景 | （待本專案填寫） |
| 必讀前置 | （待本專案填寫） |
| 不能違反的約束 | （待本專案填寫） |
| 例外處理 | （待本專案填寫） |
| 驗收方式 | （待本專案填寫） |

> 本檔內容由本專案長出、過時就改；此為 /orchestration:init-playbook 生成的空骨架。

## （章節待補）
````

---

## File 9/11: `docs/playbook/implementation-notes-template.md`

````markdown
# 實作筆記模板

| 欄位 | 內容 |
|---|---|
| 適用場景 | （待本專案填寫） |
| 不適用場景 | （待本專案填寫） |
| 必讀前置 | （待本專案填寫） |
| 不能違反的約束 | （待本專案填寫） |
| 例外處理 | （待本專案填寫） |
| 驗收方式 | （待本專案填寫） |

> 本檔內容由本專案長出、過時就改；此為 /orchestration:init-playbook 生成的空骨架。

## （章節待補）
````

---

## File 10/11: `docs/playbook/task-routing.md`

````markdown
# 模型分工與任務路由（role-first、provider-second）

| 欄位 | 內容 |
|---|---|
| 適用場景 | 統籌把工作派給執行角色時的路由決策：查證可行性、實作、對抗式覆核 |
| 不適用場景 | 權責層決策本身（architecture／plan／授權／驗收／裁定——那是 owner 的事，不路由給執行角色） |
| 必讀前置 | `orchestration.md`＋本專案 `agent-routing.json` |
| 不能違反的約束 | 角色（做什麼）與 provider/profile（用哪個引擎、什麼權限）分離；implementer 與 adversarial_reviewer 的 provider 必須不同；唯讀角色不得映射到可寫 profile |
| 例外處理 | routing 無法解析、provider 不可用、或 profile 能力缺失＝停止派工並回報，不得靜默降級或換用未授權 provider |
| 驗收方式 | 換 provider 只需改 `agent-routing.json`＋工單，不需改 commands 或本 playbook 的方法論 |

## 兩層分離：role 與 provider

```text
role             = 做什麼（行為契約，與引擎無關）
provider/profile = 用哪一個執行引擎、以什麼權限執行
```

角色契約固定不變；provider 由目標專案的 `docs/playbook/agent-routing.json` 決定。這是薄角色層，**不是** generic provider framework——不支援任意 provider、不做 capability negotiation、不做 automatic fallback、不做 session migration。

## Workflow roles

### 權責層（不可路由、不可執行）

| owner | 固定值 |
|---|---|
| architecture_owner | chatgpt |
| authoritative_plan_owner | chatgpt |
| authorization_owner | chatgpt |
| acceptance_owner | chatgpt |
| final_adjudicator | chatgpt |

權責層永遠不是可派工的執行角色；routing 驗證必須 fail closed 拒絕把這些 owner 當成執行目標。

### 執行角色（可路由）

| role | 行為契約 |
|---|---|
| `feasibility_verifier` | 唯讀、fresh session；對照 authoritative plan commit 查證 repository-local 可行性；不得建 branch／worktree、不得改檔、不得開始實作；verdict 只有 PASS_FOR_IMPLEMENTATION_AUTHORIZATION／PLAN_CHANGE_REQUIRED／EVIDENCE_INSUFFICIENT 三種 |
| `implementer` | 僅在另行授權後，於指定 worktree 內做單一 batch；只碰 allowed files；遇 forbidden-file dependency 或規格矛盾＝停止；不得 dispatch reviewer；未經另行授權不得 commit／push／PR／merge |
| `adversarial_reviewer` | fresh session（絕不 resume implementation session）、唯讀；產出 candidate findings／observations／suggestions／evidence gaps；不修 code、不 dispatch implementer；finding 成立與否由 final_adjudicator 裁定 |

## Supported provider kinds（僅此三種）

| provider kind | 說明 |
|---|---|
| `claude_subagent` | 走既有 Claude Code Task 派工路徑，使用本 plugin 既有 agents（scout／worker／executor） |
| `codex_cli` | 非互動 `codex exec`，經 bounded external-agent runner 呼叫 |
| `claude_cli` | 非互動 `claude -p`，經 bounded external-agent runner 呼叫 |

新增其他 provider kind 需要另一個 work package；本檔不得被改寫成宣稱支援任意 provider。

> bounded external-agent runner（含 timeout、transcript、Git 證據、allowlist 驗證）由 orchestration codex enablement 的後續 batch 提供；在其落地前，CLI provider 的呼叫尚無現成的機械化包裝，不得假裝已存在。

## Supported profiles

| profile | provider | 權限語意 |
|---|---|---|
| `codex_read_only` | codex_cli | read-only sandbox；非互動；無 approval escalation；repository mutation 由 runner 獨立偵測 |
| `codex_workspace_write` | codex_cli | workspace-write sandbox（絕不 danger-full-access）；限授權 worktree；network 預設關閉，開啟需另行授權 |
| `claude_read_only` | claude_cli | fresh `claude -p`；plan／read-only permission mode；機械禁用 Bash／Edit／Write／NotebookEdit／Task／MCP／slash commands；不 resume |
| `scout`／`worker`／`executor` | claude_subagent | 既有 plugin agents，語意見 `orchestration.md` 派誰表；模型釘選不變 |

唯讀角色（feasibility_verifier、adversarial_reviewer）映射到可寫 profile＝routing 驗證失敗。

## Default role mapping

```text
feasibility_verifier -> codex_cli / codex_read_only
implementer          -> codex_cli / codex_workspace_write
adversarial_reviewer -> claude_cli / claude_read_only
```

以 `agent-routing.json` 為 SSOT。可逆性要求：把 implementer 改回 `claude_subagent`（worker／executor），或 reviewer 改回 `codex_cli` read-only，只需改該檔＋工單，不得需要重寫 commands 或 playbook。

## Session separation

- feasibility 與 implementation 絕不共用 session ID。
- adversarial review 永遠是 fresh session，絕不 resume——尤其不得接續 implementation session。
- implementation resume 僅限：呼叫者明示提供已記錄的 implementation session ID，且 role／provider／worktree 三者一致。
- reviewer resume 與 cross-role resume 一律拒絕；session resume 永遠不自動發生。

## Read-only／write boundaries

- 唯讀角色：零 repository 寫入。prompt 措辭不是保證；由 runner 以 pre/post Git 證據（HEAD、index、tracked diff、untracked paths）獨立偵測，任何 delta＝違規。
- implementer：只准動 packet 明列的 allowed files；changed paths 由 runner 事後獨立比對，forbidden 或未列入路徑＝違規。
- 任何角色都不得使用 permission／sandbox bypass 旗標。

## Git authorization boundary

- 外部 provider 的一切 Git 寫入（branch／worktree／commit／push／PR／merge）預設 NONE，需 authorization owner 逐項明文授權。
- commit 權可被單獨授權；push／PR／merge 各自需要再另行授權，不得由 commit 權推導。
- implementer 不得自行授權下一 batch；reviewer 的啟動權不在 implementer。

## Task packet requirements

每張外部派工單使用 `examples/task-packets/` 對應範本，common header 十六欄缺一不可：

```text
Role
Provider/profile
Explicit model
Repository/worktree
Authoritative plan branch
Authoritative plan commit SHA
Canonical base SHA
Target SHA or batch base SHA
Goal
Allowed files
Forbidden files
Required evidence
Stop conditions
Git authorization
External-side-effect authorization
Report schema
```

回報一律對照 `examples/schemas/orchestration-result.schema.json` 的 common envelope；reviewer 結果必須分列 findings／observations／suggestions／evidence_gaps。

## Stop conditions（路由層）

任一發生＝停止派工並回報 authorization owner：

- routing 檔缺失、無效、或 authority owner 不是固定的 chatgpt 值；
- 未知 role／provider／profile；
- implementer 與 reviewer 解析到同一 provider（分離約束開啟時）；
- 唯讀角色映射到可寫 profile；
- profile 所需 CLI 能力在本機版本不存在；
- 派工單缺 common header 欄位；
- 任何一方要求繞過 sandbox、approval 或 session separation。
````

---

## File 11/11: `docs/playbook/agent-routing.json`

````json
{
  "schema_version": 1,
  "authority": {
    "architecture_owner": "chatgpt",
    "authoritative_plan_owner": "chatgpt",
    "authorization_owner": "chatgpt",
    "acceptance_owner": "chatgpt",
    "final_adjudicator": "chatgpt"
  },
  "roles": {
    "feasibility_verifier": {
      "provider": "codex_cli",
      "profile": "codex_read_only"
    },
    "implementer": {
      "provider": "codex_cli",
      "profile": "codex_workspace_write"
    },
    "adversarial_reviewer": {
      "provider": "claude_cli",
      "profile": "claude_read_only"
    }
  },
  "constraints": {
    "require_distinct_implementer_and_reviewer_provider": true,
    "implementer_may_dispatch_reviewer": false,
    "reviewer_may_modify_repository": false,
    "external_git_writes_require_separate_authorization": true
  }
}
````

---

## Post-run report format

Report each of the 11 files as `CREATED` or `SKIPPED — already exists`; a skipped file is never a failure. Then report the created count, the skipped count, and the total = 11. If the processing state of any file is unclear, do not claim completion. Lead with one sentence of conclusion (created N new files, skipped M existing files) → then the per-file list.
