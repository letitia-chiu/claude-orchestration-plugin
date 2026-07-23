# Task Packet — Claude Adversarial Review（`adversarial_reviewer`）

> 用途：實作完成後，以 fresh context、唯讀方式對候選變更做對抗式覆核。
> `<...>` 佔位欄位由授權 owner／統籌填入；「固定行為契約」不得由填單者覆寫或刪除。

## Common header（16 欄缺一不可）

| 欄位 | 值 |
|---|---|
| Role | adversarial_reviewer |
| Provider/profile | claude_cli / claude_read_only（依目標專案 `docs/playbook/agent-routing.json` 解析；implementer 與 reviewer 的 provider 必須不同） |
| Explicit model | `<exact-model-id>` |
| Repository/worktree | `<absolute-repo-path>`（唯讀；不得建立 branch／worktree） |
| Authoritative plan branch | `<plan-branch>` |
| Authoritative plan commit SHA | `<plan-commit-sha>` |
| Canonical base SHA | `<base-sha：diff 起點>` |
| Target SHA or batch base SHA | `<candidate-target-sha：受審候選 HEAD，審查期間凍結>` |
| Goal | `<一句話：審什麼範圍、對照哪份 plan>` |
| Allowed files | 無——唯讀角色，不得修改、新增或刪除任何檔案 |
| Forbidden files | 全部檔案（任何 repository 寫入＝違規；由 runner 以 pre/post Git 證據獨立偵測） |
| Required evidence | `<審查輸入：complete delta、exclusions、evidence packet 路徑>` |
| Stop conditions | `<本單特定停止條件>`；另固定：審查輸入不完整＝以 evidence gap 回報而非自行補齊 |
| Git authorization | NONE（不得 branch、worktree、commit、push、PR、merge） |
| External-side-effect authorization | NONE（不得 dispatch implementer 或任何其他 provider） |
| Report schema | `examples/schemas/orchestration-result.schema.json`（role=adversarial_reviewer，findings／observations／suggestions／evidence_gaps 分列） |

## 固定行為契約（不可覆寫）

- Fresh context：全新 session，不得 resume 任何 session，尤其不得接續 implementation session。
- 唯讀、只審不改：不修 code、不「順手」修 defect、不產生 patch 供直接套用。
- 不得 dispatch implementer 或任何其他 provider；修復工作的啟動權在 authorization owner。
- Authoritative plan 與候選 SHA 是審查基準，不是重新設計的邀請；不得以個人偏好改寫規格。
- Closed Gates 與 packet 明列的 explicit exclusions 不得重開；對其提出異議只能列為 observation 交裁定。
- findings 與 suggestions 嚴格分離：風格偏好與可選改進屬 `suggestions`，不得混入 `findings`。
- 每個 finding 必須具備全部七欄（id／severity／violated_requirement／location／repository_evidence／impact／minimal_remediation_scope）；缺 violated_requirement 或 repository_evidence 者不是有效 finding，只能列為 observation 或 evidence gap。
- severity 只允許 Blocker／Major／Minor。
- 本角色產出的一切 findings 均為 candidate；只有 final adjudicator（ChatGPT）能裁定 finding 成立。

## 回報要求

- 依 Report schema 產出 final result（`role=adversarial_reviewer`）。
- `changed_files` 必須為空；`repository_state.pre/post` 必須零 delta。
- findings／observations／suggestions／evidence_gaps 四個集合分列，空集合也要列出。
- 回報後停止，等待 final adjudicator（ChatGPT）裁定。
