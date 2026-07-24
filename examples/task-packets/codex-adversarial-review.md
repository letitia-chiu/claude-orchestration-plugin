# Task Packet — Codex Adversarial Review（`adversarial_reviewer`，claude_hosted）

> 用途：Claude-hosted implementation 完成後，經獨立 reviewer authorization，由 bounded runner 派 Codex CLI 以 fresh context、唯讀方式對候選變更做對抗式覆核。
> `<...>` 佔位欄位由 packet 明示的 governance identity／統籌填入；「固定行為契約」不得由填單者覆寫或刪除。

## Common header（C2 identity fields included；缺一不可）

| 欄位 | 值 |
|---|---|
| Governance authority | `<本次授權的 governance authority identity>` |
| Authorization issuer | `<本次 reviewer authorization 簽發者（獨立於 implementation authorization）>` |
| Acceptance owner | `<驗收 owner>` |
| Finding adjudicator | `<finding 裁定者；reviewer 本身永遠不是>` |
| Final ratifier | `<最終批准者>` |
| Host mode | claude_hosted（本範本固定；codex_hosted 的 reviewer 用 claude-adversarial-review packet） |
| Active execution host | claude_code |
| Host-local tier | not applicable（external reviewer 不屬於 host tier chain；result 的 host_tier 必須為 null） |
| Host-local model | not applicable |
| Invocation path | external_cli |
| External reviewer provider/profile/model | codex_cli / codex_read_only / `<exact-model-id：依風險選對方 provider 的平衡／最高檔位，由本欄明示，不得自動升降級>` |
| Role | adversarial_reviewer |
| Provider/profile | codex_cli / codex_read_only（依目標專案 `docs/playbook/agent-routing.json` 的 claude_hosted.external_reviewer 解析） |
| Explicit model | `<exact-model-id>` |
| Repository/worktree | `<absolute-repo-path>`（唯讀；不得建立 branch／worktree） |
| Authoritative plan branch | `<plan-branch>` |
| Authoritative plan commit SHA | `<plan-commit-sha>` |
| Release／implementation candidate SHA | `<plugin-or-release-candidate-sha>` |
| Canonical base SHA | `<base-sha：diff 起點>` |
| Target repository HEAD | `<target repository 受審 HEAD，審查期間凍結>` |
| Target repository status／dirty-state evidence | `<CLEAN，或 controller 對 exact git status --short --untracked-files=all UTF-8 bytes 產生的 sha256:<digest>>` |
| Goal | `<一句話：審什麼範圍、對照哪份 plan>` |
| Allowed files | 無——唯讀角色，不得修改、新增或刪除任何檔案 |
| Forbidden files | 全部檔案（任何 repository 寫入＝違規；由 runner 以 pre/post Git 證據獨立偵測） |
| Required evidence | `<審查輸入：complete delta、exclusions、evidence packet 路徑>` |
| Stop conditions | `<本單特定停止條件>`；另固定：審查輸入不完整＝以 evidence gap 回報而非自行補齊 |
| Git authorization | NONE（不得 branch、worktree、commit、push、PR、merge） |
| Host-local execution authorization | NONE（reviewer 授權不得外溢到 scout） |
| External-side-effect authorization | ALLOW_PROVIDER_INVOCATION（僅此一次 Codex CLI 呼叫；不得 dispatch 其他 provider 或角色） |
| Report schema | canonical schema v3；runner 機械抽取 `$defs.provider_result` 給 provider |

## 固定行為契約（不可覆寫）

- 本 dispatch 需要**獨立的 reviewer authorization**：不得由 implementer、implementation session、implementation packet 或任何自動 workflow continuation 觸發。
- Fresh context：全新 session，不得 resume 任何 session，尤其不得接續 implementation session。
- 唯讀、只審不改：不修 code、不「順手」修 defect、不產生 patch 供直接套用。
- 不得 dispatch active host、implementer 或任何其他 provider；修復工作的啟動權在 packet 明示的 authorization issuer。
- 不屬於 active host 的 scout／worker／executor chain；不得回報 host-local tier execution（host_tier=null）。
- Authoritative plan 與候選 SHA 是審查基準，不是重新設計的邀請；不得以個人偏好改寫規格。
- Closed Gates 與 packet 明列的 explicit exclusions 不得重開；對其提出異議只能列為 observation 交裁定。
- findings 與 suggestions 嚴格分離：風格偏好與可選改進屬 `suggestions`，不得混入 `findings`。
- 每個 finding 必須具備全部七欄（id／severity／violated_requirement／location／repository_evidence／impact／minimal_remediation_scope）；缺 violated_requirement 或 repository_evidence 者不是有效 finding，只能列為 observation 或 evidence gap。
- severity 只允許 Blocker／Major／Minor。
- 本角色產出的一切 findings 均為 candidate；只有 packet 明示的 finding adjudicator 能裁定 finding 成立。reviewer 不自動成為 adjudicator 或 ratifier。
- The controller has already supplied immutable provenance. Your task is only
  to produce the substantive review result described by the provider_result
  schema. Do not infer, modify, confirm, or adjudicate authority metadata.

## 回報要求

- 只產出 provider_result；runner 驗證後注入 immutable provenance，provider
  不輸出 governance／host／model／session metadata。
- `changed_files` 必須為空；`repository_state.pre/post` 必須零 delta。
- findings／observations／suggestions／evidence_gaps 四個集合分列，空集合也要列出。
- 回報後停止，等待 packet 明示的 finding adjudicator 裁定。
