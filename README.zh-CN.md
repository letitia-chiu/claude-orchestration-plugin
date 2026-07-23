# orchestration — 面向 Claude Code 的统筹与派工工作流

[English](README.md) · [繁體中文](README.zh-TW.md) · **简体中文** · [日本語](README.ja.md)

一组跨项目的 slash command 与 subagent，封装了一个简单的想法：**主 session 用的是你最贵的 token，所以它应该只负责思考——规划、拆解任务、验证、交接——而机械性的侦察、实现、繁重工作都交给三个绑定模型的 subagent。** 把它装到任何项目里，你的主 session 就不再干体力活。

> 🌐 **用你的语言工作。** 这些命令与 subagent 是用英文编写的，方便维护，但每一个都会指示 Claude *使用你的语言回应*。用日语聊天，Claude 就会用日语规划、提问、汇报；用简体中文聊天，它就用简体中文回答。把内部机制英文化**不会**让助手变成只懂英文。

## 安装

从 plugin marketplace 安装（公开仓库）：

```
/plugin marketplace add letitia-chiu/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

如果想在开发阶段不走 marketplace 流程直接试用：

```
claude --plugin-dir /path/to/claude-orchestration-plugin
```

安装完成后，命令会以 plugin 命名空间的形式出现：`/orchestration:kickoff`、`/orchestration:go`、`/orchestration:dispatch`、`/orchestration:wrapup`、`/orchestration:init-playbook`。

## 三层架构

```
Orchestrator（主 session — 可用的最强模型 + 高投入）
│  只做：理解需求、盲区／提问、拆解任务、
│  派工、对抗性验证、整合、交接。
│
├─ scout    = Haiku 4.5   只读侦察（找文件／读代码／汇总
│                          现状——只返回结论；工具锁定在
│                          Read/Glob/Grep）
├─ worker   = Sonnet 5    默认执行（规格明确的实现／测试／
│                          批量修改／文档）
└─ executor = Opus 4.8    硬核执行（已完成规格化的大型重构／精细
                          修改——第一行自报模型 ID，让你
                          不会误用错的层级）
```

五个 slash command 对应工作流的各阶段：

| 命令 | 作用 |
|---|---|
| `/orchestration:kickoff` | 开工仪式：盲区排查 → 提问 → 制定计划（包括如何拆分派工）——**停在计划、不开工** |
| `/orchestration:go` | 开工令：先验证 authoritative plan 身份（planning branch／plan commit SHA／canonical base），一次只授权一个 role 或 batch——只靠对话记忆不构成执行授权 |
| `/orchestration:dispatch` | 把任务转成完整 task packet、判定 workflow role，再按 `agent-routing.json` 路由到 Claude subagent 层级或 bounded external runner |
| `/orchestration:wrapup` | 收尾仪式：验证清单 → 历史遗留问题检查 → provider／session／artifact 证据 → 交接 |
| `/orchestration:init-playbook` | 在目标项目生成 `docs/playbook/` 骨架——11 个文件、含 `agent-routing.json`（不覆盖已有文件；内嵌模板有自动化防漂移测试保护） |

各层级背后的成本直觉（API 定价比例，订阅制的额度消耗趋势相同）：**Haiku : Sonnet : Opus ≈ 1 : 3 : 15。** Orchestrator 花的每一个 token 都是系统里最贵的 token——所以它把单纯的阅读与机械性修改下放，自己只保留判断力。

## Role-first 派工路由（0.6.0）

自 0.6.0 起，工作流把**任务是什么**（workflow role）与**由哪个引擎执行**（provider/profile）分开。路由的 SSOT 是目标项目的 `docs/playbook/agent-routing.json`；更换 provider 只需改路由文件＋派工单，不必重写整套 commands 或方法论。

```text
role             ＝ 工作职责（行为契约）
provider/profile ＝ 执行引擎与权限边界
```

**权责留在控制窗口。** ChatGPT／用户控制窗口持有 architecture、authoritative planning、authorization、acceptance、finding adjudication 与 final ratification。可执行的 provider 只执行已明确授权的 task packet——不会成为 plan 或 acceptance 的 owner。

新项目生成的默认路由：

```text
feasibility_verifier -> codex_cli / codex_read_only
implementer          -> codex_cli / codex_workspace_write
adversarial_reviewer -> claude_cli / claude_read_only
```

仅支持三种 provider kind：`claude_subagent`、`codex_cli`、`claude_cli`。不支持任意 provider，没有动态 provider discovery、capability negotiation、automatic fallback，也没有跨 provider 的 session migration。

**Claude 三层完整保留，作为 `claude_subagent` 路径。** `scout`、`worker`、`executor` 原封不动、完整支持——它们是路由上的 fallback（把 `implementer` 改回 worker/executor 只是一行路由变更），不是被删除的旧功能，也不是永远固定的 implementer。

**Bounded external-agent runner。** 外部 CLI provider 一律经 `scripts/orchestration_agent.py` 这个窄版 process-safety wrapper 调用，提供：routing 与 provider/profile 验证、单一 role 的 process invocation、wall-clock timeout 与 interrupt 分类、stdout／stderr 分离保存、按共用 schema（`examples/schemas/orchestration-result.schema.json`）验证 structured result、pre/post Git 证据、只读角色的 mutation 检测、implementation changed-path allowlist 验证、artifact SHA-256 manifest、fail-closed 结果分类。它**不会**自动规划、串接下一角色、自动 retry／fallback、commit／push／PR／merge、清理违规变更——它也不是 generic provider SDK，更不是 Xinghui Runtime 的 provider adapter。

**Git 与 side-effect 边界。** 执行授权不等于 Git 授权：commit、push、PR、merge 必须各自明确授权。真实的外部 CLI 调用需要 task packet 携带 `External-side-effect authorization: ALLOW_PROVIDER_INVOCATION`。implementer 不得自行 dispatch reviewer；reviewer 只读、不得修 code；reviewer 的 findings 在控制窗口裁定前只是 candidate findings。派工单模板在 `examples/task-packets/`。

**Real-CLI 现状。** 自动化测试使用假的（fake）Codex 与 Claude 可执行文件。在正式 implementation Gate 上使用本工作流之前，仍需另行授权的 real-CLI smoke test——真实的 network isolation、schema／stream 兼容性、quota／timeout 行为都尚未验证。本版本改造的是开发用 orchestration plugin，并未实现未来的 Xinghui Runtime Claude/Codex adapter。

## 按层级自定义模型（不怕更新覆盖）

各层级出货时钉了默认值：`scout` = `claude-haiku-4-5-20251001`、`worker` = `claude-sonnet-5`、`executor` = `claude-opus-4-8`。这是合理的起点，不是锁死。

想让某一层跑别的模型，**别去改 plugin 的 `agents/*.md`**——plugin 一更新就会被覆盖，你的改动就没了。Claude Code 的 `settings.json` 也没有「per-agent 指定模型」的开关。唯一不怕更新的机制是**同名覆盖（agent shadowing）**：在你自己的 scope 放一个同 `name:` 的子代理，就会整份取代 plugin 版本，而且放在更新永远碰不到的地方。优先级由高到低：项目 `.claude/agents/` → 用户 `~/.claude/agents/` → plugin。

可直接复制的覆盖档放在 [`examples/agents/`](examples/agents/)——挑你要改的层复制过去，只改 `model:` 那一行：

```
# 全局套用（用户 scope）……
cp examples/agents/executor.md ~/.claude/agents/executor.md
# ……或只套用单一项目（项目 scope）
cp examples/agents/worker.md   .claude/agents/worker.md
# 接着打开文件，改 `model:` 那一行
```

两个注意事项，范例档开头的注释也都写了：

- 覆盖是**整份取代 plugin 的 agent**（连本体一起），所以 plugin 之后对 agent 指令的改进不会流到你的拷贝——要的话请手动同步。
- `executor` 带了「开工自报模型 ID、不符就停」的指纹探针；改它的 `model:` 时，记得把本体里对应的 model ID 一起改，否则会被自己的检查挡下。

若你只是想暂时把**所有层**一次压到同一个模型（非按层级），可用环境变量 `CLAUDE_CODE_SUBAGENT_MODEL` 一次覆盖所有子代理。

## 引擎，而非领域知识

这个 plugin 提供的是**引擎**：角色分工（scout/worker/executor——它们的模型绑定与职责边界）、工作流（kickoff / dispatch / wrap-up 仪式），以及一份去项目化、通用的 `orchestration.md` 方法论。

它刻意**不**提供你项目的领域知识：特定代码库的铁律、它踩过的坑、验证清单的细节、自己的交接惯例。这些是每个项目要自己积累的东西；如果把它们固化进 plugin，换到下一个项目时就只会变成过时的假设、反而碍事。

这份领域知识的入口是 `/orchestration:init-playbook`：它会在目标项目生成一份空的 `docs/playbook/` 骨架（包含通用的 `orchestration.md`、作为 `known-failures.md` 起点的一组中性通用工程教训种子，以及待填字段的模板文件），该项目再通过自身的开发过程一条一条填进去。引擎可以安装到任何地方；领域知识则只能在项目自己内部生长。

## 许可证

[MIT](LICENSE) © 2026 letitia-chiu
