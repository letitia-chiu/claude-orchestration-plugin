# Task Packet — Active-Host Feasibility（`feasibility_verifier`）

> 用途：由 active host 以 host-local tier 對 authoritative plan 做 repository-local 可行性查證。Claude-hosted 走 native tier；Codex-hosted scout 走 Desktop 明確控制的 `host_local_cli`。
> `<...>` 佔位欄位由 packet 明示的 governance identity／統籌填入；「固定行為契約」不得由填單者覆寫或刪除。

## Common header（C2 identity fields included；缺一不可）

| 欄位 | 值 |
|---|---|
| Governance authority | `<本次授權的 governance authority identity>` |
| Authorization issuer | `<本次授權簽發者>` |
| Acceptance owner | `<驗收 owner>` |
| Finding adjudicator | `<finding 裁定者>` |
| Final ratifier | `<最終批准者>` |
| Host mode | `claude_hosted` 或 `codex_hosted`（一次只能一個；兩者均已實作） |
| Active execution host | `<claude_code 或 codex_desktop>` |
| Host-local tier | `<scout；codex_hosted 走 host_local_cli，claude_hosted 走 active_host>` |
| Host-local model | `<該 tier 的 model（預設＝agent 定義釘選；model_override 則明示）>` |
| Invocation path | Claude-hosted：active_host；Codex-hosted scout：host_local_cli |
| External reviewer provider/profile/model | not applicable（本 packet 不授權任何 reviewer dispatch） |
| Role | feasibility_verifier |
| Provider/profile | Claude-hosted：`claude_native / <tier>`；Codex-hosted scout：`codex_cli / codex_read_only` |
| Explicit model | `<exact-model-id>` |
| Repository/worktree | `<absolute-repo-path>`（既有 checkout；本角色不得建立 branch／worktree） |
| Authoritative plan branch | `<plan-branch>` |
| Authoritative plan commit SHA | `<plan-commit-sha>` |
| Release／implementation candidate SHA | `<plugin-or-release-candidate-sha>` |
| Canonical base SHA | `<canonical-base-sha>` |
| Target repository HEAD | `<target repository 實際 HEAD；不得以 plan/candidate SHA 代替>` |
| Target repository status／dirty-state evidence | `<CLEAN，或 controller 對 exact git status --short --untracked-files=all UTF-8 bytes 產生的 sha256:<digest>>` |
| Goal | `<一句話：要查證什麼可行性、對哪份 plan>` |
| Allowed files | 無——唯讀角色，不得修改、新增或刪除任何檔案 |
| Forbidden files | 全部檔案（任何 repository 寫入＝違規） |
| Required evidence | `<必查項清單：exact file/symbol/command 證據要求>` |
| Stop conditions | `<本單特定停止條件>`；另固定：缺規格＝停止；plan 與 repository 矛盾＝回報而非自行修正 |
| Git authorization | NONE（不得 branch、worktree、commit、push、PR、merge） |
| Host-local execution authorization | Codex-hosted scout 必須為 `ALLOW_HOST_LOCAL_CLI_INVOCATION`；其他情況 `NONE` |
| External-side-effect authorization | NONE（不得對外寫入、不得 dispatch 任何 provider 或角色） |
| Report schema | `examples/schemas/orchestration-result.schema.json`（schema v3；runner依`feasibility_verifier`機械選擇role-specific provider transport） |

## 固定行為契約（不可覆寫）

- Codex-hosted scout 固定為 `host_local_cli / codex_cli /
  codex_read_only / gpt-5.6-luna`；這是 active host local tier，不是 external
  reviewer。其他 external CLI feasibility 一律禁止。
- 唯讀；fresh session——不得 resume 任何既有 session，也不得與 implementation 共用 session。
- 不建立 branch／worktree；不修改、不新增、不刪除任何檔案。
- 不開始 implementation；實作建議不得以 implementation result 的形式呈現。
- 依本機實際狀態查證，不得只憑記憶或 plan 內示例；指出 repository 事實與 plan 的矛盾，附 exact file／symbol／command 證據。
- 缺少規格＝停止並回報缺什麼，不猜測、不發明替代方案。
- controller 已提供 immutable provenance；provider 不得推論、修改、確認或
  裁定 authority／host／invocation metadata。
- Report feasibility and repository inventory through `summary` and
  `evidence`. Do not produce review `findings`, `observations`, `suggestions`,
  or `evidence_gaps`. Those collections are not part of the feasibility
  transport schema.
- verdict 只能是下列三者之一：

```text
PASS_FOR_IMPLEMENTATION_AUTHORIZATION
PLAN_CHANGE_REQUIRED
EVIDENCE_INSUFFICIENT
```

## 回報要求

- Provider只產出feasibility transport的`verdict`、`summary`、`evidence`、
  `stop_reason`、`tests`與`repository_state`。Runner驗證成功後才為canonical
  result補入`changed_files: []`與四個空review collections，再組合immutable
  provenance。
- `repository_state.pre/post`必須零delta。
- `evidence`逐項對應Required evidence清單；無法取得的證據在`summary`與
  `evidence`中明示，必要時使用`EVIDENCE_INSUFFICIENT`，不得改用review
  collections。
- active host 執行沒有 external runner manifest＝明確記 `not applicable`，不得虛構。
- 回報後停止，等待 packet 明示的 authorization issuer 決定下一步。
