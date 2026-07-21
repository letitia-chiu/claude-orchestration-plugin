---
description: Generate the docs/playbook/ skeleton in the current project (the methodology-layer docs for the orchestrate-and-delegate workflow)
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Generate skeleton files under `docs/playbook/` in the **current (target) project**.

**Rules**: for each file below, first check whether `docs/playbook/<filename>` already exists in the target project. **Exists = skip, don't overwrite** (list skipped filenames in the final report); **doesn't exist = create it verbatim with the content attached below**. After processing all of them, report "which files were created, which were skipped."

10 files total: `README.md`, `orchestration.md`, `architecture-constraints.md`, `unknowns-interview.md`, `review-rubric.md`, `debug-playbook.md`, `known-failures.md`, `handoff-template.md`, `implementation-notes-template.md`, `task-routing.md`.

---

> NOTE: The playbook skeleton content below is currently authored in Traditional Chinese; multilingual generation is planned (see CHANGELOG).

## File 1/10: `docs/playbook/README.md`

```markdown
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
| 委派或覆核外部模型 | `task-routing.md`＋`handoff-template.md` §工單 |
| 大案子執行中 | `implementation-notes-template.md` |
| 收尾/交班/換機 | `handoff-template.md`＋`review-rubric.md` §完成定義 |

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
```

---

## File 2/10: `docs/playbook/orchestration.md`

```markdown
# 統籌–執行分層（orchestration：主窗當腦、分身動手）

| 欄位 | 內容 |
|---|---|
| 適用場景 | 統籌窗（使用者開的主 session）的日常運作：拆單、派工、驗收、交班 |
| 不適用場景 | 產品本身的 runtime 行為；純聊天／一句話問答 |
| 必讀前置 | `README.md`＋`task-routing.md`（若已填寫） |
| 不能違反的約束 | 驗收永遠在統籌；規格不清不准派工；同一不變量只准一個實作 owner |
| 例外處理 | 止血可統籌親手做＋事後補審；同一 defect family 在外部覆核重現兩次＝停止逐點修補，升級方法或 owner |
| 驗收方式 | 不只看測試全綠：必須同時有 inventory、class closure、adversarial probe、valid-path regression |

## 架構一張圖

```text
統籌（主窗，當下可用的最高智慧模型 + high effort）
│  只做：理解需求、盲區／提問、抽象化 finding、拆單、派工、對抗式驗收、整合、交班
│
├─ scout    ＝Haiku 4.5   唯讀偵察（找檔／讀碼／盤點 surface／彙整現況）
├─ worker   ＝Sonnet 5    規格明確且邊界獨立的實作／測試／批次修改
├─ executor ＝Opus 4.8    已規格化但難、跨模組、精密度高的單一-owner 實作
├─ 外部模型覆核           獨立、只審不改；依風險分級
└─ 驗證 lens              內部對抗式審查；不取代外部獨立覆核
```

- 統籌模型：當下可用的最高智慧模型＋effort high。
- 成本權重（API 定價比例，訂閱額度同方向）：**Haiku : Sonnet : Opus ≈ 1 : 3 : 15**。effort：統籌自選（/effort）；executor/worker＝medium（釘在 agents frontmatter）；scout（Haiku 4.5）不支援 effort 參數＝不設。
- 執行者一律**開工第一行自報模型 ID**（釘選探針的指紋機制，防「以為派了便宜的、其實跑到貴的」）；高風險外部覆核另驗 model＋effort。

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

## 派誰

| 任務長相 | 派 | 附加規則 |
|---|---|---|
| 現況／檔案／surface 盤點 | scout | 唯讀；回傳結論＋證據，不貼大段原文 |
| 規格明確、邊界獨立的實作 | worker | 不得與其他 agent 共用同一 invariant owner |
| 已規格化但難、跨模組契約、精密重構 | executor | production＋共用 validator＋inventory＋boundary tests 同一 context |
| 高風險第二雙眼 | 外部模型 | fresh context、只審不改、凍結候選集合；覆核模型依風險分級（平衡型日常／旗艦關卡／輕量低風險；專案有委派範本則照其格式）；外部模型不可用＝lens 加倍（rubric 有明文） |
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
```

---

## File 3/10: `docs/playbook/architecture-constraints.md`

```markdown
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
```

---

## File 4/10: `docs/playbook/unknowns-interview.md`

```markdown
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
```

---

## File 5/10: `docs/playbook/review-rubric.md`

```markdown
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
```

---

## File 6/10: `docs/playbook/debug-playbook.md`

```markdown
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
```

---

## File 7/10: `docs/playbook/known-failures.md`

```markdown
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
```

---

## File 8/10: `docs/playbook/handoff-template.md`

```markdown
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
```

---

## File 9/10: `docs/playbook/implementation-notes-template.md`

```markdown
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
```

---

## File 10/10: `docs/playbook/task-routing.md`

```markdown
# 模型分工與任務路由

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
```

---

## Post-run report format

Lead with one sentence of conclusion (created N new files, skipped M existing files) → then list each file as "created" or "skipped (already exists)".
