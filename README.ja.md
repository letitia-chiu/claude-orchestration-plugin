# orchestration — Claude と Codex のデュアルホスト・オーケストレーション

[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · **日本語**

Version: **0.7.0**

この repository は、1つの governance-neutral なオーケストレーション契約と、
2つの active-host adapter を提供します。Claude Desktop／Claude Code は
Claude-native agents、Codex Desktop は Codex-native agents でワークフローを
実行します。どちらの host も、凍結した候補を相手 provider の CLI に渡し、
fresh、read-only の敵対的レビューを受けられます。

中核となる分離は次のとおりです。

```text
governance authority
!= active execution host
!= host-local scout / worker / executor tier
!= external adversarial reviewer
```

Governance は ChatGPT、Claude、Codex、その他の製品に固定されません。各 task
packet が governance authority、authorization issuer、acceptance owner、
finding adjudicator、final ratifier を明示します。host、model、reviewer は、
自分の役割からこれらの権限を推論できません。

## Host modes と三層の同型性

| Host mode | Active host | Host-local tiers | External reviewer |
|---|---|---|---|
| `claude_hosted` | Claude Desktop／Claude Code | Claude-native `scout` / `worker` / `executor` | Codex CLI / `codex_read_only` |
| `codex_hosted` | Codex Desktop | `scout` / `worker` / `executor`、既定は Luna / Terra / Sol | Claude CLI / `claude_read_only` |

`scout` は読み取り専用の inventory と狭い feasibility、`worker` は1つの
invariant または defect family の仕様済み implementation、`executor` は
モジュール横断または高リスク契約の closure を担当します。上位 tier でも、
ファイル、Git、acceptance、adjudication、ratification、governance authority
は増えません。

Feasibility と implementation は常に active host の native tier を使います。
相互 CLI パスは reviewer 専用です。Implementer は reviewer を開始できず、
automatic reviewer dispatch、retry、fallback、model switching、role chaining
もありません。`headless_cli` implementation は、別途認可が必要な非既定の
opt-in です。

## Claude-hosted のインストール

Claude plugin marketplace からインストールします。

```text
/plugin marketplace add letitia-chiu/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

開発モード:

```bash
claude --plugin-dir /path/to/claude-orchestration-plugin
```

Claude-hosted の正式 surface は、namespaced commands
（`/orchestration:kickoff`、`/orchestration:go`、
`/orchestration:dispatch`、`/orchestration:wrapup`、
`/orchestration:init-playbook`）と、`agents/scout.md`、
`agents/worker.md`、`agents/executor.md` です。

Claude model は同名 agent shadowing で update-safe に上書きできます。
優先順位は project `.claude/agents/`、user `~/.claude/agents/`、plugin で、
例は `examples/agents/` にあります。Claude-hosted の adversarial review は、
別途認可された fresh な Codex CLI read-only session を使います。

## Codex-hosted のインストール

Plugin checkout にあるファイルは、別の repository に自動では現れません。
Codex-host adapter を明示した target Git root に materialize します。

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository
```

書き込まずに確認する場合:

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository \
  --check
```

Target は既存の absolute path の Git repository でなければなりません。
Materializer はちょうど21個の repository-local ファイルをインストールします。
対象は `AGENTS.md`、3つの `.codex/agents`、Codex-host skill と references、
shared playbook／routing／schema／task packets、Claude reviewer runner です。

インストールは transactional no-overwrite です。missing file はコピーし、
identical file には触れません。existing different file が1つでもあれば、
実行全体がゼロ書き込みで失敗します。内容の異なる `AGENTS.md` が存在する場合、
repository owner による手動マージが必要です。Plugin 更新後の再実行も安全で、
未変更ファイルは no-op、project-local customization は上書きではなく
conflict になります。

Materializer は global Codex／Claude config を変更せず、provider を呼び出さず、
Git write も行いません。これは repository-local materializer であり、native
Codex Plugin Directory package ではありません。Codex-hosted reviewer は target
内の `scripts/orchestration_agent.py`、`docs/playbook/agent-routing.json`、
`examples/schemas/orchestration-result.schema.json` を使用します。

## Safety と evidence contract

認可済み packet は、authoritative plan identity、明示的な governance と packet
identity、host／tier／model、allowed／forbidden files、acceptance commands、
stop conditions、および分離された execution、Git、external-provider
authorization を持ちます。実際の CLI 呼び出しでは packet と runner command
の両方に `ALLOW_PROVIDER_INVOCATION` が必要です。reviewer authorization は
常に独立し、fresh session を開始します。

結果は strict structured envelope を共有し、role／provider／model／session、
transcript、pre/post Git evidence、changed files、tests、artifact manifest を
記録します。Reviewer findings は、packet が指定した adjudicator の判断まで
candidate のままです。

## Capability status

Source と fake-transport tests は routing schema v2、governance neutrality、
両 host contracts、三層 static mappings、strict result validation、
authorization preflight、timeout／Git／manifest、transactional no-overwrite
distribution を対象にしています。

確立済みの real evidence は限定的です。以前の Codex CLI probe では JSONL
event の保存と、timeout、process-group termination、partial transcript、
manifest を確認しました。C1 は2件の real-CLI contract defect を修正しましたが、
修正後のパスは real CLI でまだ recheck していません。

Real smoke は次の項目で未実施です: Claude-hosted → Codex reviewer、
Codex-hosted → Claude reviewer、Luna／Terra／Sol custom-agent spawn、
3つの別 child thread／model identity、scout sandbox precedence、
embedded／standalone Codex runtime parity。native per-file sandbox enforcement
と native Plugin Directory package はありません。このプロジェクトは
Xinghui Runtime adapter ではありません。

## ライセンス

[MIT](LICENSE) © 2026 letitia-chiu
