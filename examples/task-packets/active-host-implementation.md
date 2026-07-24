# Task Packet — Active-Host Implementation（`implementer`）

> 用途：在 packet 明示的 authorization issuer 另行授權後，由 active host 以自家 worker／executor tier 於指定 worktree 執行單一 implementation batch。
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
| Host-local tier | `<worker（單一 invariant／defect family）或 executor（跨模組、契約、高風險）>` |
| Host-local model | `<該 tier 的 model（預設＝agent 定義釘選；model_override 則明示）>` |
| Invocation path | active_host（headless_cli 是另一張 packet＋另一次授權，不得混用本單） |
| External reviewer provider/profile/model | not applicable（implementer 不得 dispatch reviewer；reviewer 需獨立授權） |
| Role | implementer |
| Provider/profile | `<claude_native 或 codex_native>` / `<tier profile>`（依目標專案 `docs/playbook/agent-routing.json` 解析） |
| Explicit model | `<exact-model-id>` |
| Repository/worktree | `<absolute-authorized-worktree-path>`（只准在此 worktree 內工作） |
| Authoritative plan branch | `<plan-branch>` |
| Authoritative plan commit SHA | `<plan-commit-sha>` |
| Release／implementation candidate SHA | `<plugin-or-release-candidate-sha>` |
| Canonical base SHA | `<canonical-base-sha>` |
| Target repository HEAD | `<target repository 本 batch 開工時的 HEAD>` |
| Target repository status／dirty-state evidence | `<CLEAN，或 controller 對 exact git status --short --untracked-files=all UTF-8 bytes 產生的 sha256:<digest>>` |
| Goal | `<一句話：本 batch 的單一意圖＋可觀察完成狀態>` |
| Allowed files | `<逐一列出 repo-relative path；未列出＝禁止>` |
| Forbidden files | `<明列絕對禁碰檔案>`；另固定：Allowed files 以外的一切路徑 |
| Required evidence | `<驗收命令＋期望輸出；changed files；tests；HEAD；git status>` |
| Stop conditions | `<本單特定停止條件>`；另固定：需要 forbidden／未列入檔案＝停止；plan 與 repository 矛盾＝停止；規格缺漏＝停止 |
| Git authorization | `<NONE（預設）；或 authorization issuer 明文單獨授權，如 COMMIT_ONLY:"<commit-message>"。push／PR／merge 一律需要再另行明文授權，不得由 COMMIT_ONLY 推導>` |
| Host-local execution authorization | NONE（worker／executor 為 native active_host） |
| External-side-effect authorization | NONE（不得 dispatch reviewer 或任何其他 provider；不得對外發布） |
| Report schema | `examples/schemas/orchestration-result.schema.json`（schema v3；active host 回報 substantive result，controller 保有 provenance） |

## 固定行為契約（不可覆寫）

- 本角色屬 active host 的 host-local tier（`active_host_local_tier` binding）；Codex CLI 不是本 host mode 的 implementer。
- 只有本 packet 所載的這一個 batch 被授權；完成即停止，不得自行進入下一 batch，也不得自行授權任何後續工作。
- 只修改 Allowed files 明列的路徑；發現需要動到 forbidden 或未列入的檔案＝立即停止並回報，不得先做再說。
- 依 packet 規格實作，不得自行增加抽象層、generic framework、順手 cleanup 或相鄰重構。
- 遇到 plan 與 repository 事實矛盾、或規格缺漏＝停止並回報，不猜測。
- 可執行 packet 明列的測試命令；測試失敗照實回報，不得掩蓋或改寫驗收標準。
- 不得 dispatch 任何 reviewer——reviewer 的啟動需要 packet 明示的 authorization issuer 另行獨立授權，不在 implementer。
- tier 較高不代表授權較多：executor 與 worker 的 Git／governance authority 完全相同，都以本 packet 明文為限。
- controller 保有 immutable provenance；provider/agent 不得推論、修改、確認
  或裁定 authority／host／invocation metadata。
- Git authorization 欄為 NONE 時：不得 commit、push、開 PR、merge；即使已授權 commit，push／PR／merge 仍需再另行授權。
- 不得使用任何 permission／sandbox bypass 旗標。

## 回報要求

- 依 Report schema 產出 final result（`role=implementer`，`invocation_path=active_host`）。
- substantive result 與 controller-owned provenance 必須分離；agent 不回填
  governance identity。
- 必含：changed files 全清單、每條測試命令與實際結果、resulting HEAD、`git status --short`、殘留 deviations／blockers、session ID。
- active host 執行沒有 external runner manifest＝明確記 `not applicable`，不得虛構。
- 回報後停止，等待 packet 明示的 acceptance owner 驗收與下一步授權。
