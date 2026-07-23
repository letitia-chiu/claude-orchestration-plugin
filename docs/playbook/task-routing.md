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
| `codex_hosted` | Codex Desktop | Codex-native `scout`／`worker`／`executor`（預設 Luna／Terra／Sol；SSOT＝`.codex/agents/*.toml`） | `claude_cli` / `claude_read_only` |

- 每個 Gate 只能有一個 active host（`one_active_host`）；host 偵測、fallback、session migration 一律不做。
- active host 負責：讀 plan 與 authorization、repository-local feasibility、implementation、host 內部 tier 派工、acceptance commands、Git／test／diff evidence、回報；衝突、越界或缺 authority 時停止。
- 兩個 host mode 的 `adapter_status = implemented`。Codex-hosted target 必須先用 `scripts/init_codex_host.py --target /absolute/path/to/target-repository` 安裝 21 個 repository-local 檔案；缺檔、衝突或未安裝時 fail closed，不得把 plugin source checkout 內可讀誤當成 target 已安裝。

## Host-local tiers（兩種 host 語意一致）

| tier | 行為契約 |
|---|---|
| `scout` | 快速、低成本、優先 read-only；reconnaissance、inventory、定位與窄範圍 feasibility；不做跨模組高風險寫入；不持有 shared invariant 的 implementation ownership |
| `worker` | 平衡成本與能力；一般已規格化 implementation；可持有單一 invariant／defect family；必須完成 authorized tests 與 closure evidence |
| `executor` | 高能力／高成本；跨模組、契約、安全、持久化或高風險 implementation；承擔完整 invariant ownership 與 adversarial closure |

- tier 語意是 shared contract；exact model ID 是 host-local 設定。
- **tier 不得因能力較高而取得額外 Git 或 governance authority**——tier 只改能力與成本，不改授權。
- Claude-hosted mapping：`scout`→Haiku 檔位、`worker`→Sonnet 檔位、`executor`→Opus 檔位（SSOT＝`agents/*.md` frontmatter 的模型釘選）。
- Codex-hosted mapping：`scout`→Luna、`worker`→Terra、`executor`→Sol（SSOT＝`.codex/agents/*.toml`；actual model 與 child-thread UUID 必須在 runtime evidence 記錄）。
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
| `codex_native` | active Codex host 自家 tier（Codex Desktop child task；不以 PATH Codex CLI 冒充 active host） |
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
- host mode 未明示、一次多個 active host、或 target repository 缺少對應 host adapter；
- 未知 role／provider／profile／tier／invocation path；
- host-local tier 映射到 external CLI、或同 provider 家族自審（claude_hosted 配 claude_cli reviewer）；
- 唯讀角色映射到可寫 profile；
- headless_cli_implementation 被設為預設、或未經獨立授權被要求執行；
- packet 的 `External-side-effect authorization` 缺欄、值非 `ALLOW_PROVIDER_INVOCATION`、歧義、或與 runner 的 `--external-authorization` 旗標不一致（由 runner 機械驗證後才 spawn，prompt 措辭不是授權；implementer 授權不涵蓋 reviewer，每次 external review 都要獨立 packet 授權）；
- profile 所需 CLI 能力在本機版本不存在；
- 派工單缺 common header 欄位；
- 任何一方要求繞過 sandbox、approval、session separation 或自動 role chaining。
