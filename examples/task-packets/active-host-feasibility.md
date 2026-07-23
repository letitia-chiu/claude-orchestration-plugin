# Task Packet — Active-Host Feasibility（`feasibility_verifier`）

> 用途：由 active host 以自家 host-local tier 對 authoritative plan 做 repository-local 可行性查證。唯讀、fresh session、不開始實作、**不走 external CLI**。
> `<...>` 佔位欄位由 packet 明示的 governance identity／統籌填入；「固定行為契約」不得由填單者覆寫或刪除。

## Common header（27 欄缺一不可）

| 欄位 | 值 |
|---|---|
| Governance authority | `<本次授權的 governance authority identity>` |
| Authorization issuer | `<本次授權簽發者>` |
| Acceptance owner | `<驗收 owner>` |
| Finding adjudicator | `<finding 裁定者>` |
| Final ratifier | `<最終批准者>` |
| Host mode | claude_hosted 或 codex_hosted（一次只能一個；codex_hosted adapter 未實作＝fail closed） |
| Active execution host | `<claude_code 或 codex_desktop>` |
| Host-local tier | `<scout 或 executor：依風險選 active host 自家唯讀查證檔位>` |
| Host-local model | `<該 tier 的 model（預設＝agent 定義釘選；model_override 則明示）>` |
| Invocation path | active_host（本角色固定；external CLI feasibility 不在 dual-host 契約內） |
| External reviewer provider/profile/model | not applicable（本 packet 不授權任何 reviewer dispatch） |
| Role | feasibility_verifier |
| Provider/profile | `<claude_native 或 codex_native>` / `<tier profile>`（依目標專案 `docs/playbook/agent-routing.json` 解析） |
| Explicit model | `<exact-model-id>` |
| Repository/worktree | `<absolute-repo-path>`（既有 checkout；本角色不得建立 branch／worktree） |
| Authoritative plan branch | `<plan-branch>` |
| Authoritative plan commit SHA | `<plan-commit-sha>` |
| Canonical base SHA | `<canonical-base-sha>` |
| Target SHA or batch base SHA | `<target-sha；不適用則明寫 N/A（＝canonical base）>` |
| Goal | `<一句話：要查證什麼可行性、對哪份 plan>` |
| Allowed files | 無——唯讀角色，不得修改、新增或刪除任何檔案 |
| Forbidden files | 全部檔案（任何 repository 寫入＝違規） |
| Required evidence | `<必查項清單：exact file/symbol/command 證據要求>` |
| Stop conditions | `<本單特定停止條件>`；另固定：缺規格＝停止；plan 與 repository 矛盾＝回報而非自行修正 |
| Git authorization | NONE（不得 branch、worktree、commit、push、PR、merge） |
| External-side-effect authorization | NONE（不得對外寫入、不得 dispatch 任何 provider 或角色） |
| Report schema | `examples/schemas/orchestration-result.schema.json`（schema v2 envelope，role=feasibility_verifier） |

## 固定行為契約（不可覆寫）

- 本角色屬 active host 的 host-local tier（`active_host_local_tier` binding）；不得改派 external CLI 執行。
- 唯讀；fresh session——不得 resume 任何既有 session，也不得與 implementation 共用 session。
- 不建立 branch／worktree；不修改、不新增、不刪除任何檔案。
- 不開始 implementation；實作建議不得以 implementation result 的形式呈現。
- 依本機實際狀態查證，不得只憑記憶或 plan 內示例；指出 repository 事實與 plan 的矛盾，附 exact file／symbol／command 證據。
- 缺少規格＝停止並回報缺什麼，不猜測、不發明替代方案。
- governance identity 只作追溯；本角色不得改寫 authority fields，也不因執行而取得任何 governance authority。
- verdict 只能是下列三者之一：

```text
PASS_FOR_IMPLEMENTATION_AUTHORIZATION
PLAN_CHANGE_REQUIRED
EVIDENCE_INSUFFICIENT
```

## 回報要求

- 依 Report schema 產出 final result（`role=feasibility_verifier`，`invocation_path=active_host`）。
- governance_identity／host_mode／execution_host／host_tier 逐欄照 packet 填寫，不得改寫。
- `changed_files` 必須為空；`repository_state.pre/post` 必須零 delta。
- `evidence` 逐項對應 Required evidence 清單；查不到的列入回報而非省略。
- active host 執行沒有 external runner manifest＝明確記 `not applicable`，不得虛構。
- 回報後停止，等待 packet 明示的 authorization issuer 決定下一步。
