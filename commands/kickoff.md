---
description: 開工儀式：盲區 pass → 提問 → 計畫（照 playbook）
argument-hint: 任務描述
---
任務：$ARGUMENTS

讀「目標專案的」`docs/playbook/README.md`；不存在＝提示先跑 `/orchestration:init-playbook`。照其開工流程執行：

1. 讀專案交班快照（若有）最新條目＋`docs/playbook/unknowns-interview.md`＋`docs/playbook/architecture-constraints.md` §鐵律（依任務類型照 README 檔案地圖補讀對應文件）。
2. **盲區 pass**：interview 第一步清單逐格自答（機器/環境、任務形狀、行為矩陣、使用者體驗），答不出的老實列成 unknowns。需要查 code 現況的疑問派 scout 去查，不要自己大量讀檔。
3. **提問**：只問五類、最多 3 個、每個附推薦選項（interview 第二步門檻）。
4. **計畫**：先寫最可能變動、最需要確認的部分；標風險門（遇到就停的情況）；標**派工切分**（哪些自己做、哪些派 scout/worker/executor/外部模型覆核，判準見 `docs/playbook/orchestration.md`）。

輸出以上四項後等確認再動手；任務明顯很小且可逆時可直接開做，但假設要寫出來。
