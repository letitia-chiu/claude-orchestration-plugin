# orchestration — 為 Claude Code 打造的統籌與派工工作流

[English](README.md) · **繁體中文** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

一組跨專案的 slash command 與 subagent，包裝了一個簡單的想法：**主 session 用的是你最貴的 token，所以它應該只負責思考——規劃、拆解任務、驗證、交接——而機械性的偵察、實作、粗重工作則交給三個釘選模型的 subagent。** 把它裝到任何專案上，你的主 session 就不再做苦力活。

> 🌐 **用你的語言工作。** 這些命令與 subagent 是用英文撰寫以利維護，但每一個都會指示 Claude *以你的語言回應*。用日文對話，Claude 就會用日文規劃、提問、回報；用繁體中文對話，它就用繁體中文回答。把內部機制英文化**不會**讓助理變成只懂英文。

## 安裝

從 plugin marketplace 安裝（公開 repo）：

```
/plugin marketplace add letitia-chiu/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

若想在開發階段不透過 marketplace 流程直接試用：

```
claude --plugin-dir /path/to/claude-orchestration-plugin
```

安裝完成後，命令會以 plugin 命名空間出現：`/orchestration:kickoff`、`/orchestration:dispatch`、`/orchestration:wrapup`、`/orchestration:init-playbook`。

## 三層架構

```
Orchestrator (主 session — 可用的最強模型 + 高投入)
│  只做：理解需求、盲區／提問、拆解任務、
│  派工、對抗性驗證、整合、交接。
│
├─ scout    = Haiku 4.5   唯讀偵察（找檔案／讀 code／彙整
│                          現況——只回傳結論；工具鎖定在
│                          Read/Glob/Grep）
├─ worker   = Sonnet 5    預設執行（規格明確的實作／測試／
│                          批次修改／文件）
└─ executor = Opus 4.6    難活執行（已規格化的大型重構／精密
                          修改——第一行自報模型 ID，讓你
                          不會不小心用錯層級）
```

四個 slash command 對應工作流的四個階段：

| 命令 | 作用 |
|---|---|
| `/orchestration:kickoff` | 開工儀式：盲區 pass → 提問 → 計畫（包含如何拆分派工） |
| `/orchestration:dispatch` | 把任務轉成六欄位的派工單，送到正確的層級 |
| `/orchestration:wrapup` | 收尾儀式：驗證電池 → 舊坑檢查 → 交班 |
| `/orchestration:init-playbook` | 在目標專案生成 `docs/playbook/` 骨架（不會覆蓋既有檔案） |

各層級背後的成本直覺（API 定價比例，訂閱制的額度消耗趨勢相同）：**Haiku : Sonnet : Opus ≈ 1 : 3 : 15。** Orchestrator 花的每一個 token 都是系統裡最貴的 token——所以它把單純的閱讀與機械性修改往下派，自己只保留判斷力。

## 引擎，而非領域知識

這個 plugin 提供的是**引擎**：角色分工（scout/worker/executor——它們的模型釘選與職責邊界）、工作流（kickoff / dispatch / wrap-up 儀式），以及一份去專案化、通用的 `orchestration.md` 方法論。

它刻意**不**提供你專案的領域知識：特定 codebase 的鐵律、它踩過的坑、驗證電池的細節、自己的交接慣例。這些是每個專案要自己養成的東西；若烤進 plugin 裡，換到下一個專案時就只會變成過時的假設、反而礙事。

這份領域知識的入口是 `/orchestration:init-playbook`：它會在目標專案生成一份空的 `docs/playbook/` 骨架（包含通用的 `orchestration.md`、作為 `known-failures.md` 起點的一組中性通用工程教訓種子，以及待填欄位的範本檔案），該專案再透過自己的開發過程一筆一筆填進去。引擎可以裝到任何地方；領域知識則只能在專案自己內部養成。

## 貢獻

歡迎貢獻——尤其是 README 翻譯與修正。詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。核心規則：命令與 agent 一律用英文撰寫，且**必須保留語言鏡射指令**，讓助理永遠用使用者自己的語言與使用者對話。

## 授權

[MIT](LICENSE) © 2026 letitia-chiu
