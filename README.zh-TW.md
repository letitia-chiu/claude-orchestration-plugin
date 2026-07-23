# orchestration — Claude 與 Codex 的雙 host 統籌工作流

[English](README.md) · **繁體中文** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

Version: **0.7.0**

本 repository 提供一份 governance-neutral 統籌契約與兩個 active-host
adapter。Claude Desktop／Claude Code 可用 Claude-native agents 執行工作流；
Codex Desktop 則可用 Codex-native agents。任一 host 都可把凍結後的候選內容，
交給對方 provider 的 CLI 做 fresh、read-only 對抗式覆核。

核心分離如下：

```text
governance authority
!= active execution host
!= host-local scout / worker / executor tier
!= external adversarial reviewer
```

Governance 不固定為 ChatGPT、Claude、Codex 或任何產品。每張 task packet 都要
明示 governance authority、authorization issuer、acceptance owner、finding
adjudicator 與 final ratifier；host、model 或 reviewer 都不能從角色自行推導權力。

## Host modes 與三層同構

| Host mode | Active host | Host-local tiers | External reviewer |
|---|---|---|---|
| `claude_hosted` | Claude Desktop／Claude Code | Claude-native `scout` / `worker` / `executor` | Codex CLI / `codex_read_only` |
| `codex_hosted` | Codex Desktop | `scout` / `worker` / `executor`，預設 Luna / Terra / Sol | Claude CLI / `claude_read_only` |

`scout` 負責唯讀 inventory 與窄範圍 feasibility；`worker` 負責單一 invariant
或 defect family 的已規格化 implementation；`executor` 負責跨模組或高風險契約
closure。較高檔位不會增加檔案、Git、acceptance、adjudication、ratification 或
governance authority。

Feasibility 與 implementation 永遠走 active host 的 native tier；互惠 CLI
路徑只供 reviewer 使用。Implementer 不得啟動 reviewer，也沒有 automatic
reviewer dispatch、retry、fallback、model switching 或 role chaining。
`headless_cli` implementation 是非預設 opt-in，必須另行授權。

## Claude-hosted 安裝

從 Claude plugin marketplace 安裝：

```text
/plugin marketplace add letitia-chiu/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

開發模式：

```bash
claude --plugin-dir /path/to/claude-orchestration-plugin
```

Claude-hosted 正式 surface 是 namespaced commands：
`/orchestration:kickoff`、`/orchestration:go`、`/orchestration:dispatch`、
`/orchestration:wrapup`、`/orchestration:init-playbook`，以及
`agents/scout.md`、`agents/worker.md`、`agents/executor.md`。

Claude model 可用同名 agent shadowing 做 update-safe 覆蓋；優先序是專案
`.claude/agents/`、使用者 `~/.claude/agents/`、plugin，範例在
`examples/agents/`。Claude-hosted 的 adversarial review 使用另行授權的 fresh
Codex CLI read-only session。

## Codex-hosted 安裝

Plugin checkout 內的檔案不會自動出現在別的 repository。請把 Codex-host
adapter materialize 到明示的 target Git root：

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository
```

唯讀檢查：

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository \
  --check
```

Target 必須是既存、absolute path 的 Git repository。Materializer 安裝恰好
21 個 repository-local 檔案：`AGENTS.md`、三個 `.codex/agents`、Codex-host
skill 與 references、shared playbook／routing／schema／task packets，以及
Claude reviewer runner。

安裝具 transactional no-overwrite 語意：missing 檔案會複製、identical 檔案
完全不動；任何 existing different file 都讓整次操作以零寫入失敗。既有且不同
的 `AGENTS.md` 必須由 repository owner 手動合併。Plugin 更新後可安全重跑；
未改檔案是 no-op，project-local customization 會形成 conflict，不會被覆蓋。

Materializer 不修改 global Codex／Claude config、不呼叫 provider、不做 Git
write。這是 repository-local materializer，不是 native Codex Plugin Directory
package。Codex-hosted reviewer 使用 target 內的
`scripts/orchestration_agent.py`、`docs/playbook/agent-routing.json` 與
`examples/schemas/orchestration-result.schema.json`。

## Safety 與 evidence contract

每張已授權 packet 都包含 authoritative plan identity、明示的 governance 與
packet identity、host／tier／model、allowed／forbidden files、acceptance
commands、stop conditions，以及彼此分離的 execution、Git、external-provider
authorization。真實 CLI 呼叫要求 packet 與 runner command 都帶
`ALLOW_PROVIDER_INVOCATION`；reviewer authorization 永遠獨立並啟動 fresh session。

結果共用 strict structured envelope，記錄 role／provider／model／session、
transcript、pre/post Git evidence、changed files、tests 與 artifact manifest。
Reviewer findings 在 packet 指定的 adjudicator 裁定前都只是 candidate。

## Capability status

Source 與 fake-transport tests 已涵蓋 routing schema v2、governance neutrality、
兩個 host contracts、三層 static mappings、strict result validation、
authorization preflight、timeout／Git／manifest，以及 transactional
no-overwrite distribution。

已成立的 real evidence 較窄：先前 Codex CLI probe 已證明 JSONL event 保存，
並跑過 timeout、process-group termination、partial transcript 與 manifest。
C1 已修正兩個 real-CLI contract defect，但修正後尚未用 real CLI recheck。

Real smoke 仍待驗證：Claude-hosted → Codex reviewer、Codex-hosted → Claude
reviewer、Luna／Terra／Sol custom-agent spawn、三個不同 child thread／model
identity、scout sandbox precedence、embedded／standalone Codex runtime parity。
目前沒有 native per-file sandbox enforcement，也沒有 native Plugin Directory
package。本專案不是 Xinghui Runtime adapter。

## 授權

[MIT](LICENSE) © 2026 letitia-chiu
