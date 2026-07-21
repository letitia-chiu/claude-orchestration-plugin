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

安裝完成後，命令會以 plugin 命名空間出現：`/orchestration:kickoff`、`/orchestration:go`、`/orchestration:dispatch`、`/orchestration:wrapup`、`/orchestration:init-playbook`。

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
└─ executor = Opus 4.8    難活執行（已規格化的大型重構／精密
                          修改——第一行自報模型 ID，讓你
                          不會不小心用錯層級）
```

五個 slash command 對應工作流的各階段：

| 命令 | 作用 |
|---|---|
| `/orchestration:kickoff` | 開工儀式：盲區 pass → 提問 → 計畫（包含如何拆分派工）——**停在計畫、不開工** |
| `/orchestration:go` | 開工令：使用者下這個指令才開始執行（授權在使用當下才注入，不會被長對話稀釋） |
| `/orchestration:dispatch` | 把任務轉成六欄位的派工單，送到正確的層級 |
| `/orchestration:wrapup` | 收尾儀式：驗證電池 → 舊坑檢查 → 交班 |
| `/orchestration:init-playbook` | 在目標專案生成 `docs/playbook/` 骨架（不會覆蓋既有檔案） |

各層級背後的成本直覺（API 定價比例，訂閱制的額度消耗趨勢相同）：**Haiku : Sonnet : Opus ≈ 1 : 3 : 15。** Orchestrator 花的每一個 token 都是系統裡最貴的 token——所以它把單純的閱讀與機械性修改往下派，自己只保留判斷力。

## 依層級自訂模型（不怕更新覆蓋）

各層級出貨時釘了預設值：`scout` = `claude-haiku-4-5-20251001`、`worker` = `claude-sonnet-5`、`executor` = `claude-opus-4-8`。這是合理的起點，不是鎖死。

想讓某一層跑別的模型，**別去改 plugin 的 `agents/*.md`**——plugin 一更新就會被覆蓋，你的改動就沒了。Claude Code 的 `settings.json` 也沒有「per-agent 指定模型」的開關。唯一不怕更新的機制是**同名覆蓋（agent shadowing）**：在你自己的 scope 放一個同 `name:` 的子代理，就會整份取代 plugin 版本，而且放在更新永遠碰不到的地方。優先序由高到低：專案 `.claude/agents/` → 使用者 `~/.claude/agents/` → plugin。

可直接複製的覆蓋檔放在 [`examples/agents/`](examples/agents/)——挑你要改的層複製過去，只改 `model:` 那一行：

```
# 全域套用（使用者 scope）……
cp examples/agents/executor.md ~/.claude/agents/executor.md
# ……或只套用單一專案（專案 scope）
cp examples/agents/worker.md   .claude/agents/worker.md
# 接著打開檔案，改 `model:` 那一行
```

兩個注意事項，範例檔開頭的註解也都寫了：

- 覆蓋是**整份取代 plugin 的 agent**（連本體一起），所以 plugin 之後對 agent 指令的改進不會流到你的拷貝——要的話請手動同步。
- `executor` 帶了「開工自報模型 ID、不符就停」的指紋探針；改它的 `model:` 時，記得把本體裡對應的 model ID 一起改，否則會被自己的檢查擋下。

若你只是想暫時把**所有層**一次壓到同一個模型（非依層級），可用環境變數 `CLAUDE_CODE_SUBAGENT_MODEL` 一次覆蓋所有子代理。

## 引擎，而非領域知識

這個 plugin 提供的是**引擎**：角色分工（scout/worker/executor——它們的模型釘選與職責邊界）、工作流（kickoff / dispatch / wrap-up 儀式），以及一份去專案化、通用的 `orchestration.md` 方法論。

它刻意**不**提供你專案的領域知識：特定 codebase 的鐵律、它踩過的坑、驗證電池的細節、自己的交接慣例。這些是每個專案要自己養成的東西；若烤進 plugin 裡，換到下一個專案時就只會變成過時的假設、反而礙事。

這份領域知識的入口是 `/orchestration:init-playbook`：它會在目標專案生成一份空的 `docs/playbook/` 骨架（包含通用的 `orchestration.md`、作為 `known-failures.md` 起點的一組中性通用工程教訓種子，以及待填欄位的範本檔案），該專案再透過自己的開發過程一筆一筆填進去。引擎可以裝到任何地方；領域知識則只能在專案自己內部養成。

## 授權

[MIT](LICENSE) © 2026 letitia-chiu
