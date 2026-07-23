# Task Packet — Headless Codex Implementation（`implementer`，headless_cli_implementation opt-in）

> 用途：**非預設能力**。在 packet 明示的 authorization issuer 針對 headless 模式另行獨立授權後，經 bounded runner 以 `codex_cli / codex_workspace_write` 於指定 worktree 執行單一 implementation batch。
> 這不是任何 Desktop-hosted mode 的預設 implementation path，也不得與 Codex Desktop host 混稱；Claude-hosted 的預設 implementation 走 active host 自家 worker／executor（用 active-host-implementation packet）。
> `<...>` 佔位欄位由 packet 明示的 governance identity／統籌填入；「固定行為契約」不得由填單者覆寫或刪除。

## Common header（27 欄缺一不可）

| 欄位 | 值 |
|---|---|
| Governance authority | `<本次授權的 governance authority identity>` |
| Authorization issuer | `<本次 headless authorization 簽發者（獨立授權，不得由一般 implementation 授權推導）>` |
| Acceptance owner | `<驗收 owner>` |
| Finding adjudicator | `<finding 裁定者>` |
| Final ratifier | `<最終批准者>` |
| Host mode | `<發起本次 headless dispatch 的 host mode>` |
| Active execution host | `<claude_code 或 codex_desktop：發起端；headless 執行本身不屬於 host tier chain>` |
| Host-local tier | not applicable（headless 執行不是 host-local tier；result 的 host_tier 必須為 null） |
| Host-local model | not applicable |
| Invocation path | headless_cli（明示 opt-in；未明示＝runner fail closed） |
| External reviewer provider/profile/model | not applicable（implementer 不得 dispatch reviewer） |
| Role | implementer |
| Provider/profile | codex_cli / codex_workspace_write（依目標專案 `docs/playbook/agent-routing.json` 的 headless_cli_implementation 解析） |
| Explicit model | `<exact-model-id>` |
| Repository/worktree | `<absolute-authorized-worktree-path>`（只准在此 worktree 內工作） |
| Authoritative plan branch | `<plan-branch>` |
| Authoritative plan commit SHA | `<plan-commit-sha>` |
| Canonical base SHA | `<canonical-base-sha>` |
| Target SHA or batch base SHA | `<batch-base-sha：本 batch 開工時的 HEAD>` |
| Goal | `<一句話：本 batch 的單一意圖＋可觀察完成狀態>` |
| Allowed files | `<逐一列出 repo-relative path；未列出＝禁止>` |
| Forbidden files | `<明列絕對禁碰檔案>`；另固定：Allowed files 以外的一切路徑（由 runner 事後以 changed-paths 獨立驗證） |
| Required evidence | `<驗收命令＋期望輸出；changed files；tests；HEAD；git status>` |
| Stop conditions | `<本單特定停止條件>`；另固定：需要 forbidden／未列入檔案＝停止；plan 與 repository 矛盾＝停止；規格缺漏＝停止 |
| Git authorization | `<NONE（預設）；或 authorization issuer 明文單獨授權，如 COMMIT_ONLY:"<commit-message>"。push／PR／merge 一律需要再另行明文授權，不得由 COMMIT_ONLY 推導>` |
| External-side-effect authorization | ALLOW_PROVIDER_INVOCATION（僅此一次 Codex CLI 呼叫；不得 dispatch reviewer 或任何其他 provider；不得對外發布） |
| Report schema | `examples/schemas/orchestration-result.schema.json`（schema v2 envelope，role=implementer） |

## 固定行為契約（不可覆寫）

- headless_cli_implementation 永遠不是預設：routing 檔的 `enabled_by_default` 必須為 false；本 packet 需要獨立的 headless authorization。
- 只有本 packet 所載的這一個 batch 被授權；完成即停止，不得自行進入下一 batch，也不得自行授權任何後續工作。
- 只修改 Allowed files 明列的路徑；發現需要動到 forbidden 或未列入的檔案＝立即停止並回報，不得先做再說。
- 依 packet 規格實作，不得自行增加抽象層、generic framework、順手 cleanup 或相鄰重構。
- 遇到 plan 與 repository 事實矛盾、或規格缺漏＝停止並回報，不猜測。
- 可執行 packet 明列的測試命令；測試失敗照實回報，不得掩蓋或改寫驗收標準。
- 不得 dispatch 任何 reviewer——reviewer 的啟動需要 packet 明示的 authorization issuer 另行獨立授權，不在 implementer。
- governance identity 只作追溯；本角色不得改寫 authority fields。
- workspace-write sandbox（絕不 danger-full-access）；network 預設關閉，開啟需另行授權。
- Git authorization 欄為 NONE 時：不得 commit、push、開 PR、merge；即使已授權 commit，push／PR／merge 仍需再另行授權。
- 不得使用任何 permission／sandbox bypass 旗標。

## 回報要求

- 依 Report schema 產出 final result（`role=implementer`，`invocation_path=headless_cli`，`host_tier=null`）。
- governance_identity／host_mode／execution_host 逐欄照 packet 填寫，不得改寫。
- 必含：changed files 全清單、每條測試命令與實際結果、resulting HEAD、`git status --short`、殘留 deviations／blockers、session ID。
- 回報後停止，等待 packet 明示的 acceptance owner 驗收與下一步授權。
