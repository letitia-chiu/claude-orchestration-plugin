# Orchestration Dual-Host Architecture Recovery Plan

- **文件性質**：docs-only architecture recovery plan／待使用者確認
- **文件起草者**：目前 recovery 控制窗口（不代表產品內固定 governance owner）
- **Repository**：`letitia-chiu/claude-orchestration-plugin`
- **Canonical main**：`2d531112e25735bd88e85a3d4ebe6cc9339deca9`
- **被取代的原 plan**：`d1e1332adf947a513ef0f216e3f86197cdd33ed0`
- **目前可回收 candidate**：`bf2f2cbb56fedca1559c6497917d2bb2e889f6be`
- **建議新 planning branch**：`plan/orchestration-dual-host-recovery`
- **建議新 plan path**：`docs/ORCHESTRATION_DUAL_HOST_ARCHITECTURE_RECOVERY_PLAN.md`
- **建議 recovery implementation branch**：`feat/orchestration-dual-host-recovery`
- **狀態**：**PLANNING ONLY — NO IMPLEMENTATION／REAL-CLI／PUSH／PR／MERGE AUTHORIZATION**

> 本文件修正兩項架構誤解：第一，orchestration plugin 不應把 governance authority 固定為 ChatGPT 或任何單一產品；第二，Codex CLI implementer 不等於 Codex Desktop host。目標是建立 Claude-hosted 與 Codex-hosted 兩種對稱的正式工作模式，各自具備 host-native `scout`／`worker`／`executor`，並可派對方 CLI 做 fresh adversarial review。

---

## 1. Recovery trigger 與已成立問題

原 plan 正確建立了 bounded CLI transport、task packet、result schema、Git evidence 與安全邊界，但錯把：

```text
Claude plugin command surface 統籌
→ Codex CLI feasibility／implementation
→ Claude CLI adversarial review
```

視為「可切換到 Codex 統籌」。

真正需求是：

```text
Claude-hosted
→ Claude Desktop／Claude Code 作為 active host
→ 使用 Claude 自家的 scout／worker／executor 模型檔位
→ 必要時派 Codex CLI 做 fresh、read-only 對抗審查

Codex-hosted
→ Codex Desktop 作為 active host
→ 使用 Codex 自家的 scout／worker／executor 模型檔位
→ 必要時派 Claude CLI 做 fresh、read-only 對抗審查
```

根因是將四個概念混在一起：

1. governance authority；
2. active execution host；
3. host-local execution tier；
4. external reviewer provider。

因此目前 candidate 不可直接 ratify，但共用 CLI transport與證據層可回收。

---

## 2. Target invariants

### 2.1 Governance authority 不由 plugin 固定

orchestration plugin **不決定誰是最高治理者**，也不把 owner 寫死為 `chatgpt`、`claude` 或 `codex`。

每個正式 Gate／task packet 必須明示：

```text
Governance authority
Authoritative plan identity
Authorization issuer
Acceptance owner
Finding adjudicator
Final ratifier
```

這些 identity：

- 可以由使用者、ChatGPT、Claude-host、Codex-host或其他明確控制流程持有；
- 可以是同一 identity，也可以依專案規範分開；
- 必須在本次 authorization 中明示並可追溯；
- external reviewer 不得自行取得 governance authority；
- active host 不得因為負責 implementation 就自動取得 acceptance 或 final-ratification authority。

plugin 的責任是：

- 驗證 authority fields 存在且未在執行途中被 provider 篡改；
- 執行已授權 packet；
- 保存 evidence；
- fail closed。

plugin 不是 governance framework，也不建立任意 authority registry。

### 2.2 Active execution host

每個 Gate 必須明示一個且只能一個 active host：

```text
claude_hosted
codex_hosted
```

active host 負責：

- 讀取 authoritative plan與 authorization；
- repository-local feasibility／readiness；
- 規劃 host 內部的 scout／worker／executor 派工；
- implementation；
- 執行 acceptance commands；
- 回報 Git、test、diff與 evidence；
- 在衝突、越界或缺 authority 時停止。

active host 可以同時是 governance authority，但只有 packet 明示時才成立；不能由 host 身分自動推導。

### 2.3 Host-local execution tiers

兩種 host 都必須提供語意一致的三層：

```text
scout
worker
executor
```

共同角色契約：

#### `scout`

- 快速、低成本、優先 read-only；
- repository reconnaissance、inventory、定位與窄範圍 feasibility；
- 不做跨模組高風險寫入；
- 不持有 shared invariant 的 implementation ownership。

#### `worker`

- 平衡成本與能力；
- 一般已規格化 implementation；
- 可持有單一 invariant／defect family；
- 必須完成 authorized tests與 closure evidence。

#### `executor`

- 高能力／高成本；
- 跨模組、契約、安全、持久化或高風險 implementation；
- 承擔完整 invariant ownership與 adversarial closure；
- 不因能力較高而取得額外 Git 或 governance authority。

host adapter 將三層映射到自家模型檔位：

```text
Claude-hosted:
  scout    -> Claude 快速／低成本檔位
  worker   -> Claude 平衡檔位
  executor -> Claude 最高能力檔位

Codex-hosted:
  scout    -> Codex 快速／低成本檔位
  worker   -> Codex 平衡檔位
  executor -> Codex 最高能力檔位
```

Claude 現有 `scout`／`worker`／`executor` agent 與 model customization 機制保留。

Codex Desktop 的 exact agent／model identifiers、subagent 支援方式及覆寫位置，必須先做本機 feasibility；plan 只固定 tier semantics，不預猜版本相依的 model 名稱。

### 2.4 External adversarial reviewer

reviewer 使用 active host 的對方 CLI：

```text
claude_hosted → codex_cli / codex_read_only
codex_hosted  → claude_cli / claude_read_only
```

reviewer：

- fresh session；
- read-only；
- 不屬於 active host 的 scout／worker／executor chain；
- 不修改 repository；
- 不修 code；
- 不啟動 active host或下一角色；
- 只產生 candidate findings、observations、suggestions與 evidence gaps；
- 不自動成為 finding adjudicator或 final ratifier。

review model可依風險選擇對方 provider的平衡／最高檔位，但必須由 packet明示，不得自動升降級。

---

## 3. Target architecture

```text
Explicit governance authority
│
├── authoritative plan / authorization / acceptance / adjudication
│
└── selected active host
    │
    ├── Claude-host adapter
    │   ├── Claude Desktop／Claude Code
    │   ├── scout / worker / executor → Claude native model tiers
    │   └── Codex CLI → external adversarial reviewer
    │
    └── Codex-host adapter
        ├── Codex Desktop
        ├── scout / worker / executor → Codex native model tiers
        └── Claude CLI → external adversarial reviewer

Shared orchestration core
├── authority identity fields（不固定產品）
├── host-mode／tier routing contract
├── task packet／result contract
├── bounded external-review runner
├── transcript／manifest／Git evidence
└── acceptance／defect-closure／review-loop methodology
```

核心分離：

```text
governance authority ≠ active host ≠ host-local tier ≠ external reviewer
```

---

## 4. Routing contract v2

取代現行「Codex CLI 固定 implementer」的 routing v1。

建議概念形狀：

```json
{
  "schema_version": 2,
  "governance": {
    "binding": "task_packet",
    "explicit_identity_required": true,
    "provider_agnostic": true
  },
  "host_modes": {
    "claude_hosted": {
      "active_host": "claude_desktop",
      "local_tiers": {
        "scout": {
          "provider": "claude_native",
          "model_tier": "scout"
        },
        "worker": {
          "provider": "claude_native",
          "model_tier": "worker"
        },
        "executor": {
          "provider": "claude_native",
          "model_tier": "executor"
        }
      },
      "external_reviewer": {
        "provider": "codex_cli",
        "profile": "codex_read_only"
      }
    },
    "codex_hosted": {
      "active_host": "codex_desktop",
      "local_tiers": {
        "scout": {
          "provider": "codex_native",
          "model_tier": "scout"
        },
        "worker": {
          "provider": "codex_native",
          "model_tier": "worker"
        },
        "executor": {
          "provider": "codex_native",
          "model_tier": "executor"
        }
      },
      "external_reviewer": {
        "provider": "claude_cli",
        "profile": "claude_read_only"
      }
    }
  },
  "role_bindings": {
    "feasibility_verifier": "active_host.local_tier",
    "implementer": "active_host.local_tier",
    "adversarial_reviewer": "external_reviewer"
  },
  "constraints": {
    "one_active_host": true,
    "tier_must_be_explicit": true,
    "host_may_auto_dispatch_reviewer": false,
    "reviewer_may_modify_repository": false,
    "reviewer_may_dispatch_host": false,
    "external_git_writes_require_separate_authorization": true,
    "automatic_fallback": false,
    "automatic_retry": false,
    "automatic_role_chaining": false
  }
}
```

最終欄名可在 feasibility 後微調，但不得退回：

- governance owner 固定某產品；
- implementer固定某 CLI；
-只有 Claude host具備 scout／worker／executor。

### 4.1 Host-local model mapping

model mapping 與 role routing 分開。

建議每個 host adapter有自己的 model mapping檔或 update-safe override：

```text
scout_model
worker_model
executor_model
review_model_balanced
review_model_high
```

規則：

- tier語意為shared contract；
- exact model ID是host-local設定；
- plugin update不得覆蓋使用者自訂 mapping；
- model不存在時fail closed，不自動替換；
-不得用一個全域 model env var假裝完成三檔位能力。

### 4.2 Optional headless mode

現有 `codex_workspace_write` runner 能力可保留為明示 opt-in：

```text
headless_cli_implementation
```

但：

-不是兩種 Desktop-hosted mode的預設；
-不列入本次 dual-host success condition；
-不得在文件中與 Codex Desktop host混稱；
-需要獨立 authorization。

---

## 5. Host adapters

### 5.1 Claude-host adapter

回收現有 Claude plugin surface並修正語意：

- `kickoff／go／dispatch／wrapup／init-playbook` 保留；
- governance identity由 packet輸入，不固定 ChatGPT；
- active Claude host執行 feasibility與implementation；
- host內部依task risk派 `scout／worker／executor`；
-三層分別映射Claude自家模型檔位；
-只有新的 reviewer authorization後，才透過 shared runner派 Codex CLI；
-不得再把 Codex CLI設為Claude-hosted預設implementer；
-不得再把 Claude CLI設為Claude-hosted預設reviewer。

既有 Claude agents、模型 pin與 shadowing／override 文件必須保留。

### 5.2 Codex-host adapter

Codex Desktop是正式 execution host，不是 manual pilot。adapter必須提供與Claude-host adapter等價的：

- kickoff／go／dispatch／wrapup semantics；
- governance／plan identity verification；
- host-local `scout／worker／executor`；
-三層對應Codex自家模型檔位；
- allowed／forbidden files與stop conditions；
- invariant owner與defect-class closure；
- Git authorization separation；
- task packet materialization；
- Claude CLI reviewer dispatch；
- receipt／evidence／handoff格式。

候選承載面：

```text
repo-local AGENTS.md
+ Codex skill／instruction bundle
+ host-local model-tier mapping
```

但以下必須先由本機唯讀 feasibility確認：

- Codex Desktop是否有穩定的host-native subagent／agent tier承載方式；
- scout／worker／executor如何映射到不同Codex模型檔位；
- skill／instruction bundle的可靠解析與安裝位置；
-本機Claude CLI dispatch的sandbox／approval與artifact回收；
- Codex Desktop與CLI是否共享必要設定，且不需daemon／hook／全域侵入式修改。

不得在feasibility前預猜exact path或model ID。

### 5.3 Shared external-review runner

`orchestration_agent.py` 的dual-host預設責任收斂為：

- Codex CLI read-only reviewer；
- Claude CLI read-only reviewer；
- strict schema preflight；
- timeout／interrupt；
- stdout／stderr與final result；
- pre/post Git evidence；
- read-only mutation detection；
-manifest。

現有 workspace-write implementation profile保留為headless mode，不是active host adapter。

---

## 6. Task packet與result contract

所有正式packet新增：

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
Invocation path (active_host | external_cli | headless_cli)
External reviewer provider/profile/model
```

必要不變欄位仍包括：

```text
Authoritative plan branch／SHA
Canonical base
Repository／worktree
Goal
Allowed files
Forbidden files
Required evidence
Acceptance commands
Stop conditions
Git authorization
External-side-effect authorization
Report schema
```

Result envelope必須能分辨：

```text
governance_identity
host_mode
execution_host
host_tier
role
provider/profile/model
invocation_path
session_id
```

規則：

- active host implementation report與external reviewer result共用evidence vocabulary；
- active host沒有external runner manifest時明確記`not applicable`；
- external reviewer不得回報host-local tier execution；
- authority identity只作追溯，不作provider自我授權。

---

## 7. Salvage／amend／add matrix

### 7.1 直接保留

- C1 strict-compatible result schema與local preflight；
- Codex CLI／Claude CLI transport；
- timeout／process-group；
- transcript、manifest與Git evidence；
- read-only mutation／forbidden-path detection；
- no retry／fallback／automatic chaining；
- finding七欄、candidate-finding分離與explicit adjudicator。

### 7.2 必須修改

- `docs/playbook/agent-routing.json`：升級governance-neutral、dual-host、tier-aware schema；
- playbook docs：明示governance／host／tier／reviewer四層；
- task packets與result envelope：加入authority、host與tier identity；
- Claude commands：active Claude host＋Claude三層＋Codex CLI review；
- `init-playbook` embedded templates與drift tests；
-四語README、CHANGELOG、plugin metadata；
-單向smoke strategy與acceptance scripts。

### 7.3 必須新增

- Codex-host adapter bundle；
- Codex host的scout／worker／executor definitions或等價host-native機制；
- Codex host model-tier mapping與update-safe override；
- Codex-host adapter tests；
- dual-host tier parity tests；
- host-mode fixtures；
-兩種host的disposable smoke fixtures與reports。

### 7.4 保留但降級為非預設

- external Codex CLI implementer／workspace-write profile；
- headless implementation task packet。

### 7.5 不做history rewrite

不rebase、不amend、不force push。舊plan與錯誤實作保留為歷史證據；新recovery plan commit明確supersede舊plan。

---

## 8. Recovery branch strategy

1. 讓目前 `bf2f2cbb56fedca1559c6497917d2bb2e889f6be` 保持clean並停止使用。
2. 從該SHA建立 `plan/orchestration-dual-host-recovery`。
3. 只加入本recovery plan，建立docs-only commit。
4. 執行兩份唯讀feasibility：
   - Claude-host feasibility：驗證Claude三層保留、命令修正與Codex CLI review path；
   - Codex-host feasibility：驗證Codex Desktop三層、模型檔位mapping、instruction／skill承載與Claude CLI dispatch。
5. governance由此次planning authorization明示，不寫死於產品架構。
6. feasibility findings回到明示的plan owner／adjudicator裁定。
7. 從核准plan commit建立 `feat/orchestration-dual-host-recovery`。
8. 舊 `feat/orchestration-codex-enablement` 保留到新分支merge後再退休。

---

## 9. Pre-implementation feasibility gates

### 9.1 Claude-host feasibility

必須驗證：

-現有 `scout／worker／executor` agent與model override行為；
- active host能自行完成feasibility／implementation，不需被CLI取代；
- Codex CLI reviewer能由Claude host透過shared runner啟動；
- reviewer authorization不能由implementer自動推導；
- existing command surface可在不固定governance owner下工作。

### 9.2 Codex-host feasibility

必須以Codex Desktop實際版本唯讀確認：

-可用的repo-local instructions／skills；
-是否存在穩定的host-native agent/subagent機制；
-如何提供scout／worker／executor三層；
-三層是否能各自選擇不同Codex模型檔位；
-若沒有host-native subagent，能否以正式、可追溯的session/task機制達成等價tier contract；
-是否能受控呼叫本機Claude CLI；
-能否回收structured result、transcript、manifest與Git evidence；
-是否需要不被允許的daemon／hook／全域設定。

若Codex Desktop無法提供三層等價能力，必須回 `PLAN_CHANGE_REQUIRED`，不得用三個名稱包裝同一模型／同一session假裝完成。

---

## 10. Implementation gates（硬上限四批）

除非feasibility證明plan有矛盾，實作最多四批。

### R1 — Shared contract recovery

- governance-neutral routing v2；
- host／tier identity fields；
- packet／result contract；
- shared model-tier semantics；
- shared tests；
-不修改host adapter實作。

### R2 — Claude-host adapter correction

-修正Claude commands與init template；
- active Claude host feasibility／implementation；
- Claude `scout／worker／executor` tier routing；
- Codex CLI reviewer dispatch；
-保留model customization。

### R3 — Codex-host adapter implementation

-依本機feasibility裁定的Codex instruction／skill／agent承載方式；
- active Codex host feasibility／implementation；
- Codex `scout／worker／executor` tier routing；
- Claude CLI reviewer dispatch；
-與Claude-host等價的authority、authorization與evidence semantics。

### R4 — Parity、documentation與release candidate

- dual-host host/tier parity tests；
-四語文件與metadata；
-template sync；
-完整fake suite；
-建立新的未發佈release candidate。

完成R4後另行授權real smoke，不算implementation batch。

---

## 11. Acceptance matrix

| Contract | Claude-hosted | Codex-hosted |
|---|---|---|
| governance identity明示且可追溯 | 必須 | 必須 |
| governance不固定產品 | 必須 | 必須 |
| active host完成feasibility | Claude host | Codex host |
| active host完成implementation | Claude host | Codex host |
| host-native scout | Claude快速檔位 | Codex快速檔位 |
| host-native worker | Claude平衡檔位 | Codex平衡檔位 |
| host-native executor | Claude最高檔位 | Codex最高檔位 |
| external reviewer | Codex CLI | Claude CLI |
| reviewer fresh/read-only | 必須 | 必須 |
| reviewer不進入host tier chain | 必須 | 必須 |
| implementation不得自動啟reviewer | 必須 | 必須 |
| execution auth ≠ Git auth | 必須 | 必須 |
|同一packet/report語意 | 必須 | 必須 |
| allowed/forbidden enforcement | 必須 | 必須 |
| no fallback/retry/chaining | 必須 | 必須 |
| host切換不改方法論 | 必須 | 必須 |
| model mapping可覆寫且update-safe | 必須 | 必須 |

Parity test必須證明：

-只切換 `host_mode`、host adapter入口與host-local model mapping；
- shared methodology、packet、finding與authorization語意不複製、不漂移；
-兩邊不是用相同模型／相同session假裝三層。

---

## 12. Real smoke strategy

### 12.1 CLI compatibility gate

先各做一個最小external-review call：

- Claude-hosted → Codex CLI reviewer；
- Codex-hosted → Claude CLI reviewer。

### 12.2 Host-tier capability smoke

每種host分別驗證：

- scout：read-only inventory；
- worker：一般allowed-file implementation；
- executor：高風險但可控的cross-file contract task；
-三層實際model/session identity；
- tier不得取得額外Git／governance authority。

### 12.3 Positive workflow smoke

每種host各一個disposable repo：

1. governance packet明示owner與plan identity；
2. active host依risk選tier；
3.只改allowed files並跑tests；
4. controller驗證Git evidence；
5.新授權external reviewer；
6. reviewer產生有效candidate finding或PASS evidence；
7.明示adjudicator裁定。

### 12.4 Negative probes

每種host至少驗證：

- forbidden-file lure；
- Git commit／push lure；
-自動reviewer dispatch lure；
- tier越權 lure；
- reviewer repair／closed-Gate lure；
- authority impersonation lure；
-無越界且證據完整。

CLI timeout／manifest已由真實Codex CLI驗證通過；除非runner再改process layer，不重跑完整timeout probe。

---

## 13. Release與版本策略

- 現有 `0.6.0` 尚未發布，不得merge或tag。
- recovery完成前，文件稱其為blocked candidate。
-最終沿用`0.6.0`或升`0.7.0`，在R4依實際public surface裁定。
- repo名稱暫不更動。
-本次不建立generic governance framework、arbitrary provider SDK或Xinghui Runtime adapter。

---

## 14. Hard stop conditions

任一發生即停止並修訂plan：

-文件或routing仍把governance寫死為ChatGPT、Claude或Codex；
- Codex Desktop無可靠repo-local adapter／skill承載面；
- Codex Desktop無法提供可證明的scout／worker／executor三層等價能力；
-三層只能共用同一模型／同一session且無法證明tier separation；
- Codex Desktop無法在受控approval下呼叫本機Claude CLI；
- adapter必須安裝daemon、hook或侵入式修改全域設定；
-兩host無法共享同一packet／result／routing語意；
-需要自動host偵測、fallback或session migration；
-需要修改`dream-home`或Xinghui Runtime production code；
-需要抹除、rebase或force-push既有證據；
-需要把active host降格為CLI child process；
-文件必須宣稱尚未real-smoke的能力。

---

## 15. 使用者確認項目

在建立planning commit前確認：

1. governance authority由每次packet／流程明示，plugin不固定為ChatGPT或任何模型；
2.正式host為Claude Desktop／Claude Code與Codex Desktop；
3.兩種host都具備語意一致的`scout／worker／executor`，各自對應自家模型檔位；
4. active host負責feasibility＋implementation，對方CLI只做fresh adversarial review；
5. external CLI implementation保留為非預設headless能力；
6. recovery採新planning branch＋新implementation branch，不重寫舊歷史。

確認後，下一步只建立docs-only planning branch與commit，不直接授權implementation。
