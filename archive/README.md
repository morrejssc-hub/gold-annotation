# archive/ — 已弃方案的代码与中间物

这里是 **Pivot 0（富标注多标签）** 和 **Pivot 1（单次归属评测）** 的全部代码与派生文件。
保留是为了可追溯、可复用片段，**不是当前 pipeline**。转向原因见上一级 [`../DESIGN-PIVOTS.md`](../DESIGN-PIVOTS.md)。

> 注意：这些脚本里的相对路径（`aliases.json`、`../sw-sft/jsons`、`sheet.tsv`）是按**原 `gold-annotation/` 根目录**写的。
> 若要重跑，需调整路径或把脚本临时放回上级目录。`focalizers.py`/`pool.py` 依赖 `prepare.py`（同在本目录，组内可跑）。

## Pivot 0：富标注多标签方案（type/bucket/focalizer/target/FID/心理-推测/置信度）
- `prepare.py` — 一章 → 待核对表（对话/动作/无主语 FID 单元 + 难度桶 + 置信度 + target）
- `pool.py` — 多篇 → 大候选池（依赖 prepare）
- `sample.py` — 分层取样（`--mode eval/sft`）
- `merge.py` — 增量并表，保人工列
- `health.py` — 建集进度体检
- `score.py` — 分桶准确率 + 置信度校准
- `focalizers.py` — 生成视角待填表（依赖 prepare；产物 `../focalizers.tsv` 保留在上级）
- `review_dump.py` / `apply_review.py` — 复核工作流
- `example.tsv` — 17 个已核对单元的演示集

## Pivot 1：单次归属评测
- `build_eval.py` — 从对话单元建"单次 (±3上下文,台词)→说话人"评测集（启发式 baseline）
- `eval_candidates.tsv` — 取样后的待标候选（其人工标注版 `../eval.tsv` 保留在上级）

## 中间/派生物（可再生成）
- `pool.tsv`、`sheet.bak*.tsv`、`*.report*`、`*.err`、`err.log`
- `README.old.md` — 旧版 README（描述上述已弃 pipeline 的完整工作流）
