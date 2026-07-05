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
| 統籌窗運作（派工/分層/成本） | `orchestration.md`（統籌五律＋派工單格式＋判準表；SOP 命令＝`/orchestration:kickoff` `/orchestration:dispatch` `/orchestration:wrapup`） |
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
| 不適用場景 | 產品本身的 runtime 行為（app 內部邏輯）；純聊天/一句話問答（直接答，別開儀式） |
| 必讀前置 | `README.md`（工作流）＋`task-routing.md`（模型位置，若已填寫） |
| 不能違反的約束 | 驗收永遠在統籌，執行者的「做完了」不算完成；規格不清不准派工 |
| 例外處理 | 止血當下可統籌親手做＋事後補審（rubric 例外條款）；執行者連續兩次退單＝停止派工、統籌接手或升級階層 |
| 驗收方式 | 統籌窗的產出照舊過 review-rubric 電池；本檔生效的證據＝統籌 context 不再充滿檔案原文、最高階模型只出現在判斷點 |

## 架構一張圖

```
統籌（主窗，當下可用的最高智慧模型 + high effort）
│  只做：理解需求、盲區/提問、拆單、派工、對抗式驗收、整合、交班
│
├─ scout    ＝Haiku 4.5   唯讀偵察（找檔/讀碼/彙整現況，只回結論）
├─ worker   ＝Sonnet 5    預設執行（規格明確的實作/測試/批次改/文檔）
├─ executor ＝Opus 4.6    難活執行（已規格化的大重構/精密修改）
├─ 外部模型覆核（若有）    交叉覆核為主＋可規格化實作
└─ 驗證 lens 子代理        對抗式審查（review-rubric 方法）
```

- 統籌模型：當下可用的最高智慧模型＋effort high。
- 成本權重（API 定價比例，訂閱額度同方向）：**Haiku : Sonnet : Opus ≈ 1 : 3 : 15**。effort 預設：統籌 high、executor/worker medium、scout low。
- 執行者一律**開工第一行自報模型 ID**（釘選探針的指紋機制，防「以為派了便宜的、其實跑到貴的」）。

## 統籌五律

1. **統籌不搬磚**：預估超過約 30 行的機械修改、或跨 3 個以上檔案的批次操作 → 派工。統籌的每個 token 是最貴的。
2. **統籌不吃生資料**：偵察、大量讀檔、log 翻找 → 派 scout，只收結論＋file:line 證據。原文一旦貼進統籌 context 就**永遠佔著**（之後每一輪都重新付費），這是最容易被忽略的漏財孔。大輸出落檔案、不貼對話。
3. **規格不清不派工**：模糊在統籌層解決（盲區 pass、問使用者、讀 code 確認）。中低階模型的品質＝工單品質；把模糊派下去＝把判斷外包給不該判斷的人。
4. **驗收在統籌**：照 `review-rubric.md` 電池，且至少**親手抽驗一項**可機械驗證的項目（跑一次測試/curl/grep）。執行者的回報是線索，不是證據。
5. **該自己做的別硬派**：架構判斷、產品語氣/人格類 prompt、精密單檔手術、寫給人讀的關鍵文檔、10 分鐘內的小事。這些派工開銷（寫單＋驗收）大於自做，直接做。

## 語言律（貫穿全程，凌駕形式）

統籌對使用者的**每一次**對話、提問、進度、回報，一律**鏡射使用者當下的語言**——講繁中回繁中、講日文回日文、講英文回英文。

分清兩層、別混：
- **產出物內容**（檔名、程式碼、frontmatter 值、刻意以英文為基準的命令／agent 腳本）維持原文。
- **你對使用者說的話**（結論、標題、分段、提問）跟著使用者走。

命令／agent 腳本英文化，只是「給模型讀的指令」用英文，不是你的輸出語言。長 session 尤其容易漂成英文——這是明確失敗模式，收尾回報時務必自檢。

## 派誰（判準表）

| 任務長相 | 派 | 為什麼 |
|---|---|---|
| 「X 在哪／現況是什麼／哪些檔案相關」 | scout | 唯讀、便宜、答案是結論不是原文 |
| 規格明確的實作/重構/測試撰寫/批次修改/文檔整理 | worker | 預設執行層；Sonnet 遵循指令佳 |
| 已規格化但難（大重構、跨模組、精密度高） | executor | 難度值得高階模型，但規格仍由統籌給足 |
| worker 覺得需要規格外決定 | 退回統籌 → 補規格或升 executor | 不讓執行層做判斷 |
| 高風險變更的第二雙眼 | 外部模型覆核（若專案有委派範本則照其格式） | 跨模型視角；外部模型不可用＝lens 加倍（rubric 有明文） |
| 判斷/語氣/審美/小事 | 統籌自己 | 五律第 5 條 |

## 內部派工單格式（比外部委派工單輕，但六件缺一不可）

```
【目標】一句話＋「完成的樣子」（可觀察的結果）
【範圍】動哪些檔案（精確路徑）；工作目錄
【禁區】不碰什麼：依任務指定；目標專案 CLAUDE.md／playbook 鐵律為準（正式服務、敏感資料、git push 等）
【規格】關鍵決定統籌已做好，逐條列（不留給執行者猜）
【驗收】可機械驗證的命令＋期望輸出（例：測試全綠記總數／curl 200／grep 應有 N 處）
【回報】先結論一句 → ①改了什麼（檔案清單）②驗了什麼（附實跑輸出）③殘留/偏離/blocker；不貼大段檔案內容
```

派法＝Task/Agent 工具選對應 agent 類型（scout/worker/executor），工單全文當 prompt。可平行派（互不依賴的單一次派齊）。

## 統籌窗的 context 節食（自己的紀律）

- 開場稅要控管：現況文件只留現況（歷史搬歸檔檔案，考古才讀）。
- playbook 按需載入（README 檔案地圖），不一次全讀。
- 長 session 察覺 context 臃腫（大量已完成話題）＝照 `handoff-template.md` 交班、開新窗接力，比拖著整車歷史便宜。

## 新統籌窗開機儀式

1. `git pull`（換機/新窗必做）→ 讀現況文件快照最新條目。
2. 有指紋疑慮就跑測試對總數。
3. `/orchestration:kickoff 任務描述` → 盲區 → 提問 → 計畫（含派工切分）→ 開做。
4. 收尾 `/orchestration:wrapup`。

## 與既有規範的關係

- 驗證標準完全不變：`review-rubric.md` 電池、對抗式審查、專案自身的行為規範照舊。本檔只改「誰動手」，不改「怎麼算完成」。
- 外部模型覆核（若專案採用）仍有效；額度或方案調整時可能改變覆核與實作的比重，實作重心會移到 worker/executor。
- 執行者（worker/executor）受目標專案 CLAUDE.md 慣例與 `architecture-constraints.md` 鐵律約束，工單禁區欄是第二道保險。
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
11. Python sqlite3 的 with ≠ close；「偶發性全掛」先查資源洩漏。
12. 掃描式背景迴圈必配 in-flight 標記，且標記要在入列瞬間、不是開始處理才標。
13. 節流／冷卻／每日上限一律持久化；設計時直接問「重啟會怎樣」。
14. schema-gated 的寫入路徑，每個新欄位都是三件套（schema＋normalize＋round-trip）；驗證走真入口、不走捷徑。
15. 行動裝置 PWA 版面問題先在模擬器 standalone 重現再動手；「數字剛好對了」的 hack 會在別處爆。
16. API 層型別照後端真回應寫；型別謊言的代價是整頁崩潰。
17. 前端多層快取先分清改動落在哪層、用對應的重載儀式。
18. flex 對齊怪＝先查 inline-block 基線；用截圖＋像素量測驗證，不靠目測。
19. 跨模型協作要有「對到同一版」的握手信物（測試總數／commit hash）。
20. 自動化工具會動你腳下的地；收工檢查分支是慣例不是偏執。
21. 功能的終點是使用者實際能用，不是 merge；順口提的小需求當場落檔。
22. 有參考碼＝逐屬性移植；交付前並排截圖自比，不像不交。
23. 外部 API 以實測回應為準；寫 code 前先 curl 一發存證。
24. 改動有調節器（moderator／clamp）的系統前，先讀清它的實際作用域；用「事前推算最終顯示值」做 guard。
25. 便宜模型需要剛性輸出契約；parser 永遠假設對面會答非所問。
26. 依賴模型自標的協定，都要有後端 backstop 接「它最自然的寫法」；範例文檔裡的寫法就是模型最會寫的寫法。
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
