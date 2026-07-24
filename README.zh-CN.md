# orchestration — Claude 与 Codex 的双 host 编排工作流

[English](README.md) · [繁體中文](README.zh-TW.md) · **简体中文** · [日本語](README.ja.md)

Version: **0.7.0**

本 repository 提供一份 governance-neutral 编排契约和两个 active-host
adapter。Claude Desktop／Claude Code 可通过 Claude-native agents 执行工作流；
Codex Desktop 则使用 Desktop-controlled host-local CLI scout 与 native
worker／executor。任一 host 都可把冻结后的候选内容
交给对方 provider 的 CLI，进行 fresh、read-only 对抗式审查。

核心分离如下：

```text
governance authority
!= active execution host
!= host-local scout / worker / executor tier
!= external adversarial reviewer
```

Governance 不固定为 ChatGPT、Claude、Codex 或任何产品。每张 task packet 都必须
明确 governance authority、authorization issuer、acceptance owner、finding
adjudicator 和 final ratifier；host、model 或 reviewer 都不能从角色自行推导权力。

## Host modes 与三层同构

| Host mode | Active host | Host-local tiers | External reviewer |
|---|---|---|---|
| `claude_hosted` | Claude Desktop／Claude Code | Claude-native `scout` / `worker` / `executor` | Codex CLI / `codex_read_only` |
| `codex_hosted` | Codex Desktop | scout＝`host_local_cli` Codex CLI／Luna；worker／executor＝native Terra／Sol | Claude CLI / `claude_read_only` |

`scout` 负责只读 inventory 与窄范围 feasibility；`worker` 负责单一 invariant
或 defect family 的已规格化 implementation；`executor` 负责跨模块或高风险契约
closure。更高档位不会增加文件、Git、acceptance、adjudication、ratification 或
governance authority。

Codex-hosted feasibility 固定走单独授权的 Desktop-controlled
`host_local_cli / codex_cli / codex_read_only / gpt-5.6-luna`；worker／executor
仍为 native Desktop Terra／Sol。scout 不是 external reviewer 或 fallback。
Implementer 不得启动 reviewer，也没有 automatic
reviewer dispatch、retry、fallback、model switching 或 role chaining。
`headless_cli` implementation 是非默认 opt-in，必须单独授权。

## Claude-hosted 安装

从 Claude plugin marketplace 安装：

```text
/plugin marketplace add letitia-chiu/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

开发模式：

```bash
claude --plugin-dir /path/to/claude-orchestration-plugin
```

Claude-hosted 正式 surface 是 namespaced commands：
`/orchestration:kickoff`、`/orchestration:go`、`/orchestration:dispatch`、
`/orchestration:wrapup`、`/orchestration:init-playbook`，以及
`agents/scout.md`、`agents/worker.md`、`agents/executor.md`。

Claude model 可通过同名 agent shadowing 做 update-safe 覆盖；优先级是项目
`.claude/agents/`、用户 `~/.claude/agents/`、plugin，示例在
`examples/agents/`。Claude-hosted adversarial review 使用单独授权的 fresh
Codex CLI read-only session。

## Codex-hosted 安装

Plugin checkout 内的文件不会自动出现在其他 repository。请把 Codex-host
adapter materialize 到明确的 target Git root：

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository
```

只读检查：

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository \
  --check
```

Target 必须是已存在、absolute path 的 Git repository。Materializer 安装恰好
20 个 repository-local 文件：`AGENTS.md`、两个 native `.codex/agents`
（worker／executor）、Codex-host
skill 与 references、shared playbook／routing／schema／task packets，以及
Claude reviewer runner。

安装具有 transactional no-overwrite 语义：missing 文件会复制、identical 文件
完全不动；任何 existing different file 都使整次操作以零写入失败。已有且不同的
`AGENTS.md` 必须由 repository owner 手动合并。Plugin 更新后可安全重跑；
未改文件是 no-op，project-local customization 会形成 conflict，不会被覆盖。

Materializer 不修改 global Codex／Claude config、不调用 provider、不做 Git
write。这是 repository-local materializer，不是 native Codex Plugin Directory
package。Codex-hosted reviewer 使用 target 内的
`scripts/orchestration_agent.py`、`docs/playbook/agent-routing.json` 和
`examples/schemas/orchestration-result.schema.json`。

## Safety 与 evidence contract

每张已授权 packet 都分别包含 authoritative plan SHA、release／implementation
candidate SHA、target repository HEAD 与 dirty-state evidence、明确的 governance
identity、host／tier／model、allowed／forbidden files、acceptance
commands、stop conditions，以及相互分离的 execution、Git、external-provider
authorization。真实 CLI 调用要求 packet 与 runner command 都携带
`ALLOW_PROVIDER_INVOCATION`；reviewer authorization 始终独立并启动 fresh session。

Canonical schema v3 是唯一 SSOT。Provider 只收到机械抽取的
`provider_result`；runner 注入 controller-owned immutable provenance，并分别
记录 requested／reported model。Reviewer findings 在裁定前都只是 candidate。

## Capability status

Source 与 fake-transport tests 已覆盖 routing schema v2、governance neutrality、
两个 host contracts、三层 static mappings、strict result validation、
authorization preflight、timeout／Git／manifest，以及 transactional
no-overwrite distribution。

已经成立的 real evidence 较窄：先前 Codex CLI probe 已证明 JSONL event 保存，
并跑过 timeout、process-group termination、partial transcript 与 manifest。Luna／
low Codex-host scout formal runner recheck 已在一次 fresh invocation 中通过，
exit 0，且 schema v3、semantic、read-only／mutation 与 manifest validation 均 PASS。

Real smoke 已证明旧 native Codex scout sandbox 在观察到的 embedded runtime
没有形成 read-only 边界，因此该默认已撤除。仍待 real recheck：native
Terra／Sol、两边 schema-v3 reciprocal reviewer，以及 embedded／standalone
Codex runtime version skew。目前没有 native per-file sandbox enforcement，
也没有 native Plugin Directory package。本项目不是 Xinghui Runtime adapter。

## 许可证

[MIT](LICENSE) © 2026 letitia-chiu
