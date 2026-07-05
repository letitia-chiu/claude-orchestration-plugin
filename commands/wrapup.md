---
description: 收尾儀式：驗證電池 → 舊坑檢查 → 交班（快照＋commit）
---
讀「目標專案的」`docs/playbook/README.md`；不存在＝提示先跑 `/orchestration:init-playbook`。照其收尾清單執行（缺一不算完成）：

1. `docs/playbook/review-rubric.md` 驗證電池依變更類型跑完，記指紋（測試總數＋bundle 名等，依專案而定）。
2. `docs/playbook/known-failures.md` 快掃：有沒有踩回舊坑？產生新坑＝同 commit 入館。
3. `docs/playbook/architecture-constraints.md` 鐵律自查。
4. 若專案有交班慣例，照其 `docs/playbook/handoff-template.md` 更新交班快照（新條目插最上；收官條目過多＝把舊的搬歷史檔）＋（若有）其他隨交班同步的狀態檔案，commit（工單則依專案的狀態蓋章慣例標記完成）。
5. 完成回報三段式：①改了什麼 ②在哪驗過（附實跑輸出）③請使用者驗什麼＋**怎麼體驗（確切路徑）**。
