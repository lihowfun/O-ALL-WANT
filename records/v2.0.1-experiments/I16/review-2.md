先修再凍結

1. **阻擋｜`i16_grade.py:60`**：`planted` 可僅憑報告自述得分，即使重播失敗；`real_other` 卻必須有重播證據。猜中缺陷的無根據回報可能同時增加 detection、避開 unsupported。改成兩者都須成功重播，或提供經核實的原始工具輸出。

2. **阻擋｜`i16_grade.py:278`、`i16_judge.py:53`**：版本綁定仍未貫通。grader 不核對重播的程式／建置版本，也未把重播摘要綁進評分；judge 接受不同 runner 的列。記憶體反例已確認混版可通過 `bind()`。各階段須核對 runner、replayer、案例與建置版本，評分續跑也須核對報告及重播內容摘要。

3. **應修｜`i16_grade.py:35`**：第一輪遮蔽問題仍在；`followed full recipe`、`F arm`、`Claude Code`、`codex` 均原樣保留，已用函式反例確認。補齊明確組別、方法及主機標記的遮蔽，保存遮蔽前後摘要與評分事件紀錄。

4. **應修｜`i16_run.py:62`、`i16_run.py:415`**：第一輪黑箱紀錄只修了一部分。`cd oaw/scripts && cat oaw.py`、`cat project/scripts/*.py` 仍記為零；`tool_changed` 仍只比對 `./oaw`。依工具工作目錄解析讀取路徑與 glob，掃描子 thread，並比對安裝進專案的受測腳本。

5. **應修｜`i16_judge.py:111`、`PREREG.md:169`**：第二次校準後才寫入 `ceiling_kept`，會改變 spec 摘要，隨即使該次 floor 被拒；程式也未驗證確實只換過一次題。將保留結果寫進綁定凍結題庫摘要的校準產物，並驗證換題沿革與次數。

6. **應修｜`i16_grade.py:173`**：重播截斷已修，但報告仍直接切前 24,000 字。反例中，第一個缺陷的長 evidence 會截掉後續缺陷並破壞 JSON，grader 卻仍須評完整缺陷數。改為逐欄位、逐缺陷裁切，保留所有項目、合法 JSON 與截斷標記。

7. **應修｜`frozen/cases/remove-bundled-skill/oracle.sh:31`**：B3 首輪僅驗非零、錯誤字串及檔案存在，沒有確認預期 exit 2 或逐位元回滾；檔案被截斷後，第二輪成功刪除仍可能得到 0。要求精確結束碼、解析錯誤 JSON，並比對失敗前後受保護檔案及備份內容。

8. **應修｜`PREREG.md:112`；尺度 `docs/EVAL_PROTOCOL.md:8`**：尺度要求偵測實驗另設正對照與不洩題的便宜做法，目前只有 N／D／F；description 消融尚未被定義為該便宜基線。補上固定的正對照與便宜基線，預先寫明用途、成本及失敗時如何解讀。

驗證平台：Linux x86_64、Python 3.10.12；完成唯讀檢查與記憶體反例，未重跑會寫檔的 oracle。