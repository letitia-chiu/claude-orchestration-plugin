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
