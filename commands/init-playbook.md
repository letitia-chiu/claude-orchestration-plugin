---
description: Generate the docs/playbook/ skeleton in the current project (the methodology-layer docs for the orchestrate-and-delegate workflow)
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Generate skeleton files under `docs/playbook/` in the **current (target) project**.

**Rules**: for each file below, first check whether `docs/playbook/<filename>` already exists in the target project. **Exists = skip, don't overwrite** (list skipped filenames in the final report); **doesn't exist = create it verbatim with the content attached below**. Never overwrite, replace, merge, append, or auto-repair an existing target file — not even when its content has drifted from the template. The same no-overwrite rule applies to `docs/playbook/agent-routing.json`: if the target project already has its own routing file, the result is `SKIP — existing file preserved`; never replace it with the plugin default.

11 files total: `README.md`, `orchestration.md`, `architecture-constraints.md`, `unknowns-interview.md`, `review-rubric.md`, `debug-playbook.md`, `known-failures.md`, `handoff-template.md`, `implementation-notes-template.md`, `task-routing.md`, `agent-routing.json`.

What the generated playbook provides: governance-neutral, host-aware, tier-aware routing contracts (`agent-routing.json` schema v2 — governance identity comes from each task packet; feasibility/implementation belong to the active host's scout/worker/executor tiers; the adversarial reviewer is the opposing provider's read-only CLI; headless CLI implementation is a non-default opt-in), pointers to this plugin's task-packet templates (`examples/task-packets/`) and result schema (`examples/schemas/orchestration-result.schema.json`, schema v2), and the contract surface for the bounded external-agent runner integration. Do not claim more than that: the Codex-host adapter is not implemented (codex_hosted active-host execution fails closed), no real Codex/Claude smoke test has been passed by generating these files, network isolation is not thereby verified against real CLIs, arbitrary providers are not supported, and no runner is installed into the target project. This command never modifies the target project's Claude settings or hooks.

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
| 委派或覆核（governance／host／tier／reviewer 四層路由） | `task-routing.md`＋`agent-routing.json`＋`handoff-template.md` §工單；派工單用 plugin 附帶範本 `examples/task-packets/`（active-host-feasibility／active-host-implementation／codex-adversarial-review／claude-adversarial-review／headless-codex-implementation），回報對照 `examples/schemas/orchestration-result.schema.json`（schema v2） |
| 大案子執行中 | `implementation-notes-template.md` |
| 收尾/交班/換機 | `handoff-template.md`＋`review-rubric.md` §完成定義 |

> 註：`agent-routing.json`（schema v2）是 governance-neutral、host-aware、tier-aware 路由的 SSOT：governance identity 由每次 task packet 明示；host mode（claude_hosted／codex_hosted）一次一個；feasibility／implementation 走 active host 自家 scout／worker／executor；external reviewer 用對方 CLI（經 bounded runner：timeout、transcript、Git 證據、allowlist 驗證）。Codex-host adapter 尚未實作＝fail closed；headless CLI implementation 為非預設 opt-in。

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
| 必讀前置 | `README.md`＋`task-routing.md`＋`agent-routing.json`（schema v2：governance-neutral、host-aware、tier-aware） |
| 不能違反的約束 | governance authority ≠ active host ≠ host-local tier ≠ external reviewer；驗收歸屬 packet 明示的 acceptance owner；規格不清不准派工；同一不變量只准一個實作 owner |
| 例外處理 | 止血可統籌親手做＋事後補審；同一 defect family 在外部覆核重現兩次＝停止逐點修補，升級方法或 owner |
| 驗收方式 | 不只看測試全綠：必須同時有 inventory、class closure、adversarial probe、valid-path regression |

## 架構一張圖

```text
Explicit governance authority（每次 packet／流程明示，不固定為任何產品）
│  authoritative plan / authorization / acceptance / adjudication / final ratification
│
└─ selected active host（一次一個：claude_hosted 或 codex_hosted）
   │
   ├─ Claude-host adapter（本 plugin；已實作）
   │   ├─ 統籌（主窗，當下可用的最高智慧模型 + high effort）
   │   ├─ scout / worker / executor ＝ Claude-native model tiers（既有 agents，模型釘選不變）
   │   ├─ feasibility_verifier／implementer ＝ active Claude host 自家 tier（Task path）
   │   └─ adversarial_reviewer ＝ Codex CLI（codex_read_only；獨立授權後經 bounded runner 派）
   │
   └─ Codex-host adapter（尚未實作；等本機唯讀 feasibility）
       ├─ scout / worker / executor ＝ Codex-native model tiers
       └─ adversarial_reviewer ＝ Claude CLI（claude_read_only）
```

- 四層分離：**governance authority ≠ active host ≠ host-local tier ≠ external reviewer**；細節見 `task-routing.md`，SSOT＝`agent-routing.json`（schema v2）。
- 統籌模型：當下可用的最高智慧模型＋effort high。
- Claude-native tier 成本權重（API 定價比例，訂閱額度同方向）：**Haiku : Sonnet : Opus ≈ 1 : 3 : 15**。effort：統籌自選（/effort）；executor/worker＝medium（釘在 agents frontmatter）；scout（Haiku 4.5）不支援 effort 參數＝不設。
- 執行者一律**開工第一行自報模型 ID**（釘選探針的指紋機制，防「以為派了便宜的、其實跑到貴的」）；外部 CLI provider 另以工單的 Explicit model 欄位釘住；高風險覆核另驗 model＋effort。
- `codex_workspace_write` headless implementation 保留為明示 opt-in（`headless_cli_implementation`），非任何 host mode 的預設。

## 角色與四層分離

governance identity **不固定、不可路由、由每次 packet 明示**：

```text
Governance authority
Authorization issuer
Acceptance owner
Finding adjudicator
Final ratifier
```

執行角色只有三個：`feasibility_verifier`（唯讀查證，active host 自家 tier）、`implementer`（單一 batch 實作，active host 自家 tier）、`adversarial_reviewer`（fresh-context 只審不改，對方 CLI）。行為契約與 host 無關，換 host mode 不換契約。

不可越權的硬邊界：

- implementer 不得 dispatch reviewer；reviewer 不得修 code；reviewer 必須來自 active host 的對方 provider 家族（fail closed）。
- feasibility 與 implementation 不共用 session；reviewer 永遠 fresh session。
- 任何 Git 寫入需 packet 明示的 authorization issuer 另行明文授權。
- reviewer 產出的是 candidate findings；成立與否由 packet 明示的 finding adjudicator 裁定，統籌只做整理與轉呈。
- tier 較高不代表授權較多：scout／worker／executor 只改能力與成本，不改 Git 或 governance authority。
- active host 不因負責 implementation 就自動取得 acceptance 或 final-ratification authority。

可逆性：換 host mode 只改 packet 的 `Host mode` 與 host-local model mapping（`model_override`）；shared methodology、packet 與 finding 語意不動。Codex-hosted adapter 未經本機 feasibility 證明前一律 fail closed。

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
| 現況／檔案／surface 盤點 | scout（active host 自家快速唯讀檔位；Claude-hosted＝Haiku tier） | 唯讀；回傳結論＋證據，不貼大段原文 |
| 對 authoritative plan 的 repository-local 可行性查證 | feasibility_verifier（→ active_host_local_tier；Claude-hosted＝自家 tier 唯讀查證） | 唯讀、fresh session；verdict 只有三種；工單用 active-host-feasibility packet；**不走 external CLI** |
| 規格明確、已授權的實作 batch | implementer（→ active_host_local_tier；Claude-hosted＝worker（邊界獨立；不得與其他 agent 共用同一 invariant owner）／executor（跨模組、精密；production＋共用 validator＋inventory＋boundary tests 同一 context）） | 限授權 worktree＋allowed files；工單用 active-host-implementation packet；headless_cli_implementation（codex_workspace_write）為非預設 opt-in，工單用 headless-codex-implementation packet＋獨立授權 |
| 高風險第二雙眼 | adversarial_reviewer（→ 對方 CLI：claude_hosted＝codex_cli / codex_read_only；codex_hosted＝claude_cli / claude_read_only） | fresh context、只審不改、凍結候選集合；需獨立 reviewer authorization；工單用 codex-adversarial-review／claude-adversarial-review packet；覆核模型依風險分級且由 packet 明示；finding 成立由 packet 明示的 finding adjudicator 裁定；外部 reviewer 不可用＝lens 加倍（rubric 有明文） |
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
# 模型分工與任務路由（governance-neutral、host-aware、tier-aware）

| 欄位 | 內容 |
|---|---|
| 適用場景 | 統籌把工作派給執行角色時的路由決策：查證可行性、實作、對抗式覆核 |
| 不適用場景 | governance 決策本身（plan／授權／驗收／裁定——那是 packet 明示的 governance identity 的事，不路由給執行角色） |
| 必讀前置 | `orchestration.md`＋本專案 `agent-routing.json`（schema v2） |
| 不能違反的約束 | governance authority ≠ active execution host ≠ host-local execution tier ≠ external reviewer；四層分離不得混同；唯讀角色不得映射到可寫 profile |
| 例外處理 | routing 無法解析、host adapter 未實作、provider 不可用、或 profile 能力缺失＝停止派工並回報，不得靜默降級、fallback 或換用未授權 provider |
| 驗收方式 | 換 host mode 只改 packet 的 `Host mode`＋host-local model mapping；shared methodology、packet 與 finding 語意不複製、不漂移 |

## 四層分離（核心不變量）

```text
governance authority ≠ active execution host ≠ host-local execution tier ≠ external reviewer
```

| 層 | 是什麼 | 由誰決定 |
|---|---|---|
| governance authority | plan／授權／驗收／裁定的權責 identity | 每次 task packet／流程明示，**不由 plugin 固定** |
| active execution host | 本次 Gate 的執行宿主（`claude_hosted` 或 `codex_hosted`，一次只能一個） | packet 的 `Host mode` 欄 |
| host-local execution tier | active host 自家的 `scout`／`worker`／`executor` 模型檔位 | active host 依 task risk 選擇，packet 記錄 |
| external reviewer | 對方 provider 的 CLI，fresh、read-only 對抗式覆核 | 獨立 reviewer authorization 後才派 |

## Governance identity（不固定產品）

routing 檔**不含**任何固定 owner。每個正式 Gate／task packet 必須明示：

```text
Governance authority
Authorization issuer
Acceptance owner
Finding adjudicator
Final ratifier
```

- 這些 identity 可由使用者、ChatGPT、Claude-host、Codex-host 或其他明確控制流程持有；可同一 identity，也可分開；但必須在本次 authorization 中明示並可追溯。
- external reviewer 不得自行取得 governance authority；active host 不因負責 implementation 就自動取得 acceptance 或 final-ratification authority。
- routing 驗證必須 fail closed 拒絕：routing 檔內出現固定 authority owner（舊 schema v1 的 `authority` block）、或 packet 缺任何 governance identity 欄位。
- provider 不得改寫 packet 的 authority fields；result 內的 governance identity 與 packet 不一致＝INVALID_OUTPUT。

## Host modes（兩種正式 host）

| host_mode | active host | host-local tiers | external reviewer |
|---|---|---|---|
| `claude_hosted` | Claude Desktop／Claude Code | Claude-native `scout`／`worker`／`executor`（既有 plugin agents，模型釘選不變） | `codex_cli` / `codex_read_only` |
| `codex_hosted` | Codex Desktop | Codex-native `scout`／`worker`／`executor`（**adapter 尚未實作**：exact agent／model mapping 需先本機唯讀 feasibility） | `claude_cli` / `claude_read_only` |

- 每個 Gate 只能有一個 active host（`one_active_host`）；host 偵測、fallback、session migration 一律不做。
- active host 負責：讀 plan 與 authorization、repository-local feasibility、implementation、host 內部 tier 派工、acceptance commands、Git／test／diff evidence、回報；衝突、越界或缺 authority 時停止。
- `codex_hosted` 的 `adapter_status = not_implemented`：在 Codex-host adapter 以本機 feasibility 證明前，任何 codex_hosted 的 active-host 執行請求必須 fail closed，不得假裝可用。shared runner 的 `claude_cli` reviewer transport 本身已存在且可測。

## Host-local tiers（兩種 host 語意一致）

| tier | 行為契約 |
|---|---|
| `scout` | 快速、低成本、優先 read-only；reconnaissance、inventory、定位與窄範圍 feasibility；不做跨模組高風險寫入；不持有 shared invariant 的 implementation ownership |
| `worker` | 平衡成本與能力；一般已規格化 implementation；可持有單一 invariant／defect family；必須完成 authorized tests 與 closure evidence |
| `executor` | 高能力／高成本；跨模組、契約、安全、持久化或高風險 implementation；承擔完整 invariant ownership 與 adversarial closure |

- tier 語意是 shared contract；exact model ID 是 host-local 設定。
- **tier 不得因能力較高而取得額外 Git 或 governance authority**——tier 只改能力與成本，不改授權。
- Claude-hosted mapping：`scout`→Haiku 檔位、`worker`→Sonnet 檔位、`executor`→Opus 檔位（SSOT＝`agents/*.md` frontmatter 的模型釘選）。
- model mapping 可覆寫且 update-safe：每個 tier 的 `model_override`（`agent-routing.json` 內，預設 `null`＝用 agent 定義的釘選模型）屬 project-local 設定；`/orchestration:init-playbook` 對既有 routing 檔一律 no-overwrite，plugin 更新不得覆蓋。model 不存在＝fail closed，不自動替換。
- 不得用單一全域 model 設定假裝完成三檔位能力；三層不得共用同一模型／同一 session 假裝 tier separation。

## External adversarial reviewer

reviewer 一律用 active host 的**對方** CLI：

```text
claude_hosted → codex_cli / codex_read_only
codex_hosted  → claude_cli / claude_read_only
```

reviewer 契約：fresh session；read-only；不屬於 active host 的 tier chain；不修改 repository；不修 code；不啟動 active host 或下一角色；只產生 candidate findings／observations／suggestions／evidence gaps；不自動成為 finding adjudicator 或 final ratifier。review model 可依風險選對方 provider 的平衡／最高檔位，但必須由 packet 明示，不得自動升降級。

**Claude CLI 不是 Claude-hosted 的 reviewer；Codex CLI 不是 Claude-hosted 的 implementer。** routing 驗證 fail closed 拒絕同 provider 家族自審。

## Workflow roles（role_bindings）

| role | binding | 行為契約 |
|---|---|---|
| `feasibility_verifier` | `active_host_local_tier` | 由 active host 以自家 tier（通常 scout／executor 唯讀）對照 authoritative plan commit 查證 repository-local 可行性；verdict 只有 PASS_FOR_IMPLEMENTATION_AUTHORIZATION／PLAN_CHANGE_REQUIRED／EVIDENCE_INSUFFICIENT 三種；**不走 external CLI** |
| `implementer` | `active_host_local_tier` | 由 active host 以自家 worker／executor 於指定 worktree 做單一授權 batch；只碰 allowed files；遇 forbidden-file dependency 或規格矛盾＝停止；不得 dispatch reviewer；未經另行授權不得 commit／push／PR／merge |
| `adversarial_reviewer` | `external_reviewer` | 獨立 reviewer authorization 後，經 bounded runner 派對方 CLI；fresh session、唯讀；findings 為 candidate，由 packet 明示的 finding adjudicator 裁定 |

## Invocation paths

| invocation_path | 語意 | 誰可用 |
|---|---|---|
| `active_host` | active host 自家 Task／agent 派工路徑（Claude-hosted＝Claude Code Task tool → scout／worker／executor） | feasibility_verifier、implementer |
| `external_cli` | bounded runner 派對方 CLI（read-only reviewer） | adversarial_reviewer 專用 |
| `headless_cli` | `codex_workspace_write` headless implementation——**非預設、明示 opt-in、需獨立授權**；不是 Desktop-hosted mode 的一部分，不得與 Codex Desktop host 混稱 | implementer（僅在 packet 明示 headless 授權時） |

packet 的 `Invocation path` 欄必須明示；runner 對未明示或不合法的組合 fail closed。

## Supported provider kinds

| provider kind | 說明 |
|---|---|
| `claude_native` | active Claude host 自家 tier（走 Claude Code Task 派工路徑，用本 plugin agents scout／worker／executor） |
| `codex_native` | active Codex host 自家 tier（adapter 未實作；等 Codex-host feasibility） |
| `codex_cli` | 非互動 `codex exec`，經 bounded external-agent runner 呼叫（reviewer 預設；headless implementation 為 opt-in） |
| `claude_cli` | 非互動 `claude -p`，經 bounded external-agent runner 呼叫（codex_hosted 的 reviewer） |

host-local tier 不得映射到 external CLI provider；新增其他 provider kind 需要另一個 work package。

## Supported profiles

| profile | provider | 權限語意 |
|---|---|---|
| `codex_read_only` | codex_cli | read-only sandbox；非互動；無 approval escalation；repository mutation 由 runner 獨立偵測 |
| `codex_workspace_write` | codex_cli | workspace-write sandbox（絕不 danger-full-access）；限授權 worktree；network 預設關閉；**只作 headless_cli_implementation opt-in 用** |
| `claude_read_only` | claude_cli | fresh `claude -p`；plan／read-only permission mode；機械禁用 Bash／Edit／Write／NotebookEdit／Task／MCP／slash commands；不 resume |
| `scout`／`worker`／`executor` | claude_native | 既有 plugin agents，語意見 `orchestration.md` 派誰表；模型釘選不變、可被 project-local shadowing／`model_override` 覆寫 |

唯讀角色（feasibility_verifier、adversarial_reviewer）映射到可寫 profile＝routing 驗證失敗。

## Session separation

- feasibility 與 implementation 絕不共用 session ID。
- adversarial review 永遠是 fresh session，絕不 resume——尤其不得接續 implementation session。
- implementation resume 僅限：呼叫者明示提供已記錄的 implementation session ID，且 role／provider／worktree 三者一致。
- reviewer resume 與 cross-role resume 一律拒絕；session resume 永遠不自動發生。

## Read-only／write boundaries

- 唯讀角色：零 repository 寫入。prompt 措辭不是保證；由 runner 以 pre/post Git 證據（HEAD、index、tracked diff、untracked paths）獨立偵測，任何 delta＝違規。
- implementer（含 headless）：只准動 packet 明列的 allowed files；changed paths 由 runner 事後獨立比對，forbidden 或未列入路徑＝違規。
- 任何角色都不得使用 permission／sandbox bypass 旗標。

## Git authorization boundary

- 一切 Git 寫入（branch／worktree／commit／push／PR／merge）預設 NONE，需 packet 明示的 authorization issuer 逐項明文授權。
- commit 權可被單獨授權；push／PR／merge 各自需要再另行授權，不得由 commit 權推導。
- implementer 不得自行授權下一 batch；reviewer 的啟動權不在 implementer——需要獨立的 reviewer authorization。
- execution authorization ≠ Git authorization；tier 高低不改變 Git authorization。

## Task packet requirements

每張正式派工單使用 `examples/task-packets/` 對應範本，common header 缺一不可：

```text
Governance authority
Authorization issuer
Acceptance owner
Finding adjudicator
Final ratifier
Host mode
Active execution host
Host-local tier
Host-local model
Invocation path
External reviewer provider/profile/model
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

回報一律對照 `examples/schemas/orchestration-result.schema.json`（schema v2 envelope）；result 必須能分辨 governance identity／host mode／execution host／host tier／role／provider／profile／model／invocation path／session ID。reviewer 結果必須分列 findings／observations／suggestions／evidence_gaps；active host implementation report 與 external reviewer result 共用 evidence vocabulary；active host 沒有 external runner manifest 時明確記 `not applicable`。

## Stop conditions（路由層）

任一發生＝停止派工並回報 packet 明示的 authorization issuer：

- routing 檔缺失、無效、或內含固定 governance owner（任何把 authority 寫死為 ChatGPT／Claude／Codex 的形狀）；
- packet 缺 governance identity 或 host/tier identity 欄位；
- host mode 未明示、一次多個 active host、或 host adapter 未實作（codex_hosted active-host 執行）；
- 未知 role／provider／profile／tier／invocation path；
- host-local tier 映射到 external CLI、或同 provider 家族自審（claude_hosted 配 claude_cli reviewer）；
- 唯讀角色映射到可寫 profile；
- headless_cli_implementation 被設為預設、或未經獨立授權被要求執行；
- packet 的 `External-side-effect authorization` 缺欄、值非 `ALLOW_PROVIDER_INVOCATION`、歧義、或與 runner 的 `--external-authorization` 旗標不一致（由 runner 機械驗證後才 spawn，prompt 措辭不是授權；implementer 授權不涵蓋 reviewer，每次 external review 都要獨立 packet 授權）；
- profile 所需 CLI 能力在本機版本不存在；
- 派工單缺 common header 欄位；
- 任何一方要求繞過 sandbox、approval、session separation 或自動 role chaining。
````

---

## File 11/11: `docs/playbook/agent-routing.json`

````json
{
  "schema_version": 2,
  "governance": {
    "binding": "task_packet",
    "explicit_identity_required": true,
    "provider_agnostic": true
  },
  "host_modes": {
    "claude_hosted": {
      "active_host": "claude_code",
      "adapter_status": "implemented",
      "local_tiers": {
        "scout": {
          "provider": "claude_native",
          "profile": "scout",
          "model_override": null
        },
        "worker": {
          "provider": "claude_native",
          "profile": "worker",
          "model_override": null
        },
        "executor": {
          "provider": "claude_native",
          "profile": "executor",
          "model_override": null
        }
      },
      "external_reviewer": {
        "provider": "codex_cli",
        "profile": "codex_read_only"
      }
    },
    "codex_hosted": {
      "active_host": "codex_desktop",
      "adapter_status": "implemented",
      "local_tiers": {
        "scout": {
          "provider": "codex_native",
          "profile": "scout",
          "model_override": null
        },
        "worker": {
          "provider": "codex_native",
          "profile": "worker",
          "model_override": null
        },
        "executor": {
          "provider": "codex_native",
          "profile": "executor",
          "model_override": null
        }
      },
      "external_reviewer": {
        "provider": "claude_cli",
        "profile": "claude_read_only"
      }
    }
  },
  "role_bindings": {
    "feasibility_verifier": "active_host_local_tier",
    "implementer": "active_host_local_tier",
    "adversarial_reviewer": "external_reviewer"
  },
  "headless_cli_implementation": {
    "enabled_by_default": false,
    "requires_separate_authorization": true,
    "provider": "codex_cli",
    "profile": "codex_workspace_write"
  },
  "constraints": {
    "one_active_host": true,
    "tier_must_be_explicit": true,
    "host_may_auto_dispatch_reviewer": false,
    "implementer_may_dispatch_reviewer": false,
    "reviewer_may_modify_repository": false,
    "reviewer_may_dispatch_host": false,
    "external_git_writes_require_separate_authorization": true,
    "automatic_fallback": false,
    "automatic_retry": false,
    "automatic_role_chaining": false
  }
}
````

---

## Post-run report format

Report each of the 11 files as `CREATED` or `SKIPPED — already exists`; a skipped file is never a failure. Then report the created count, the skipped count, and the total = 11. If the processing state of any file is unclear, do not claim completion. Lead with one sentence of conclusion (created N new files, skipped M existing files) → then the per-file list.
