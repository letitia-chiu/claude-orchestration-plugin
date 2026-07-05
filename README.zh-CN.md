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

安装完成后，命令会以 plugin 命名空间的形式出现：`/orchestration:kickoff`、`/orchestration:dispatch`、`/orchestration:wrapup`、`/orchestration:init-playbook`。

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
└─ executor = Opus 4.6    硬核执行（已完成规格化的大型重构／精细
                          修改——第一行自报模型 ID，让你
                          不会误用错的层级）
```

四个 slash command 对应工作流的四个阶段：

| 命令 | 作用 |
|---|---|
| `/orchestration:kickoff` | 开工仪式：盲区排查 → 提问 → 制定计划（包括如何拆分派工） |
| `/orchestration:dispatch` | 把任务转成六字段的派工单，发送给正确的层级 |
| `/orchestration:wrapup` | 收尾仪式：验证清单 → 历史遗留问题检查 → 交接 |
| `/orchestration:init-playbook` | 在目标项目生成 `docs/playbook/` 骨架（不会覆盖已有文件） |

各层级背后的成本直觉（API 定价比例，订阅制的额度消耗趋势相同）：**Haiku : Sonnet : Opus ≈ 1 : 3 : 15。** Orchestrator 花的每一个 token 都是系统里最贵的 token——所以它把单纯的阅读与机械性修改下放，自己只保留判断力。

## 引擎，而非领域知识

这个 plugin 提供的是**引擎**：角色分工（scout/worker/executor——它们的模型绑定与职责边界）、工作流（kickoff / dispatch / wrap-up 仪式），以及一份去项目化、通用的 `orchestration.md` 方法论。

它刻意**不**提供你项目的领域知识：特定代码库的铁律、它踩过的坑、验证清单的细节、自己的交接惯例。这些是每个项目要自己积累的东西；如果把它们固化进 plugin，换到下一个项目时就只会变成过时的假设、反而碍事。

这份领域知识的入口是 `/orchestration:init-playbook`：它会在目标项目生成一份空的 `docs/playbook/` 骨架（包含通用的 `orchestration.md`、作为 `known-failures.md` 起点的一组中性通用工程教训种子，以及待填字段的模板文件），该项目再通过自身的开发过程一条一条填进去。引擎可以安装到任何地方；领域知识则只能在项目自己内部生长。

## 贡献

欢迎贡献——尤其是 README 翻译与修正。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。核心规则：命令与 agent 一律用英文编写，并且**必须保留语言镜像指令**，让助手始终用用户自己的语言与用户对话。

## 许可证

[MIT](LICENSE) © 2026 letitia-chiu
