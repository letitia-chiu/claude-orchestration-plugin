# Task Packet — Codex Implementation（`implementer`）

> 用途：在 ChatGPT 另行授權後，於指定 worktree 內執行單一 implementation batch。
> `<...>` 佔位欄位由授權 owner／統籌填入；「固定行為契約」不得由填單者覆寫或刪除。

## Common header（16 欄缺一不可）

| 欄位 | 值 |
|---|---|
| Role | implementer |
| Provider/profile | codex_cli / codex_workspace_write（依目標專案 `docs/playbook/agent-routing.json` 解析；claude_subagent worker／executor 為可逆 fallback） |
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
| Git authorization | `<NONE（預設）；或 ChatGPT 明文單獨授權，如 COMMIT_ONLY:"<commit-message>"。push／PR／merge 一律需要再另行明文授權，不得由 COMMIT_ONLY 推導>` |
| External-side-effect authorization | NONE（不得 dispatch reviewer 或任何其他 provider；不得對外發布） |
| Report schema | `examples/schemas/orchestration-result.schema.json`（common envelope，role=implementer） |

## 固定行為契約（不可覆寫）

- 只有本 packet 所載的這一個 batch 被授權；完成即停止，不得自行進入下一 batch，也不得自行授權任何後續工作。
- 只修改 Allowed files 明列的路徑；發現需要動到 forbidden 或未列入的檔案＝立即停止並回報，不得先做再說。
- 依 packet 規格實作，不得自行增加抽象層、generic framework、順手 cleanup 或相鄰重構。
- 遇到 plan 與 repository 事實矛盾、或規格缺漏＝停止並回報，不猜測。
- 可執行 packet 明列的測試命令；測試失敗照實回報，不得掩蓋或改寫驗收標準。
- 不得 dispatch Claude 或任何 reviewer——review 的啟動權在 authorization owner（ChatGPT），不在 implementer。
- Git authorization 欄為 NONE 時：不得 commit、push、開 PR、merge。ChatGPT 可在該欄單獨授權 commit（不預設允許）；即使已授權 commit，push／PR／merge 仍需再另行授權。
- 不得使用任何 permission／sandbox bypass 旗標。

## 回報要求

- 依 Report schema 產出 final result（`role=implementer`）。
- 必含：changed files 全清單、每條測試命令與實際結果、resulting HEAD、`git status --short`、殘留 deviations／blockers、session ID。
- 回報後停止，等待 acceptance owner（ChatGPT）驗收與下一步授權。
