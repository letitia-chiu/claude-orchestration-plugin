# orchestration — 統籌–執行分層工作流（Claude Code plugin）

把「統籌拆單、執行者分層動手」打包成可跨專案安裝的 slash 命令與子代理：裝上任何專案後，主 session 只負責理解需求、拆單、驗收、交班；機械性的偵察／實作／難活分別派給三個模型釘選的子代理。

## 安裝

```
/plugin marketplace add /Users/tzuhsuan/code/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

開發時想直接試載（不經 marketplace 安裝流程）：

```
claude --plugin-dir /Users/tzuhsuan/code/claude-orchestration-plugin
```

安裝後命令會以 plugin 名稱為前綴出現：`/orchestration:kickoff`、`/orchestration:dispatch`、`/orchestration:wrapup`、`/orchestration:init-playbook`。

## 三層架構

```
統籌（主 session，當下可用的最高智慧模型 + high effort）
│  只做：理解需求、盲區/提問、拆單、派工、對抗式驗收、整合、交班
│
├─ scout    ＝Haiku 4.5   唯讀偵察（找檔/讀碼/彙整現況，只回結論，tools 鎖 Read/Glob/Grep）
├─ worker   ＝Sonnet 5    預設執行（規格明確的實作/測試/批次改/文檔）
└─ executor ＝Opus 4.6    難活執行（已規格化的大重構/精密修改，開工自報模型 ID 防跑錯階層）
```

四個 slash 命令對應工作流的四個階段：

| 命令 | 作用 |
|---|---|
| `/orchestration:kickoff` | 開工儀式：盲區 pass → 提問 → 計畫（含派工切分） |
| `/orchestration:dispatch` | 把任務轉成六欄派工單、派給對應階層 |
| `/orchestration:wrapup` | 收尾儀式：驗證電池 → 舊坑檢查 → 交班 |
| `/orchestration:init-playbook` | 在目標專案生成 `docs/playbook/` 骨架（已存在的檔案不覆蓋） |

## 引擎 vs 血肉

這個 plugin 打包的是**引擎**：角色分工（scout/worker/executor 的模型釘選與職責邊界）、工作流程（開工/派工/收尾三儀式）、以及一份去專案化的 `orchestration.md` 通用版方法論。

它**不打包血肉**：任何專案的具體鐵律、踩過的坑、驗證電池的細節、交班格式的專屬慣例。這些屬於「這個專案自己長出來的東西」，硬塞進 plugin 只會變成過時的假設，裝到別的專案上反而添亂。

血肉的入口是 `/orchestration:init-playbook`：它在目標專案生成 `docs/playbook/` 的空骨架（含通用版 `orchestration.md`、一份中性的通用工程教訓種子當 `known-failures.md` 開頭，其餘檔案是待填欄位表），之後由該專案自己的開發過程逐條填滿。引擎可以到處裝，血肉只能在自己的專案裡養。

衍生自一個私人 Claude Code 專案裡實際運作的統籌工作流，蒸餾去除專屬脈絡後獨立成 plugin。

## License

TBD
