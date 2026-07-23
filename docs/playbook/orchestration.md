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
