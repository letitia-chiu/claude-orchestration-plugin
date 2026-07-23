# Task Packet — Codex Feasibility（`feasibility_verifier`）

> 用途：對 authoritative plan 做 repository-local 可行性查證。唯讀、fresh session、不開始實作。
> `<...>` 佔位欄位由授權 owner／統籌填入；「固定行為契約」不得由填單者覆寫或刪除。

## Common header（16 欄缺一不可）

| 欄位 | 值 |
|---|---|
| Role | feasibility_verifier |
| Provider/profile | codex_cli / codex_read_only（依目標專案 `docs/playbook/agent-routing.json` 解析） |
| Explicit model | `<exact-model-id>` |
| Repository/worktree | `<absolute-repo-path>`（既有 checkout；本角色不得建立 branch／worktree） |
| Authoritative plan branch | `<plan-branch>` |
| Authoritative plan commit SHA | `<plan-commit-sha>` |
| Canonical base SHA | `<canonical-base-sha>` |
| Target SHA or batch base SHA | `<target-sha；不適用則明寫 N/A（＝canonical base）>` |
| Goal | `<一句話：要查證什麼可行性、對哪份 plan>` |
| Allowed files | 無——唯讀角色，不得修改、新增或刪除任何檔案 |
| Forbidden files | 全部檔案（任何 repository 寫入＝違規；由 runner 以 pre/post Git 證據獨立偵測） |
| Required evidence | `<必查項清單：exact file/symbol/command 證據要求>` |
| Stop conditions | `<本單特定停止條件>`；另固定：缺規格＝停止；plan 與 repository 矛盾＝回報而非自行修正 |
| Git authorization | NONE（不得 branch、worktree、commit、push、PR、merge） |
| External-side-effect authorization | NONE（不得對外寫入、不得 dispatch 其他 provider 或角色） |
| Report schema | `examples/schemas/orchestration-result.schema.json`（common envelope，role=feasibility_verifier） |

## 固定行為契約（不可覆寫）

- 唯讀；fresh session——不得 resume 任何既有 session，也不得與 implementation 共用 session。
- 不建立 branch／worktree；不修改、不新增、不刪除任何檔案。
- 不開始 implementation；實作建議不得以 implementation result 的形式呈現。
- 依本機實際狀態查證，不得只憑記憶或 plan 內示例；指出 repository 事實與 plan 的矛盾，附 exact file／symbol／command 證據。
- 缺少規格＝停止並回報缺什麼，不猜測、不發明替代方案。
- verdict 只能是下列三者之一：

```text
PASS_FOR_IMPLEMENTATION_AUTHORIZATION
PLAN_CHANGE_REQUIRED
EVIDENCE_INSUFFICIENT
```

## 回報要求

- 依 Report schema 產出 final result（`role=feasibility_verifier`）。
- `changed_files` 必須為空；`repository_state.pre/post` 必須零 delta。
- `evidence` 逐項對應 Required evidence 清單；查不到的列入回報而非省略。
- 回報後停止，等待 authorization owner（ChatGPT）決定下一步。
