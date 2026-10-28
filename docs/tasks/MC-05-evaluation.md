# MC-05 配对评价、盲评与统计

[Issue #9](https://github.com/zhengads/MoodCut-dsa4213/issues/9) · [团队协作](../TEAM.md) · [文档状态](../README.md)

本卡说明模块责任，具体认领与增量以 Issue / PR 为准。旧分期清单与验收日志见[历史任务卡](https://github.com/zhengads/MoodCut-dsa4213/blob/18c19a2f36cef2820acb747299b83b58eea5ffc7/docs/tasks/MC-05-evaluation.md)。

## 已有能力

三条件输入验证、媒体/来源/回执重检、离线资格、匿名导出/评分、覆盖与生成状态分列、单指标 VBench 及可恢复批量入口已实现。软件接线完成不等于真实样本合格。

## 后续工作

- 接收 P1 完整真实来源包并重跑资格/导出检查；失败或未知费用保留，公开摘要不补造成最终记录。
- 由团队确认正式样本、复用/失败纳入规则、方法版本、评价者分配与预算，再收集独立人工评分。
- PR #58 的历史视频审计/图像质量与定性案例已合入；使用这些记录时保留协议与版本，不能视为当前发布包的独立效果结论。

## 修改范围与依赖

`src/moodcut/evaluation.py`、`tests/test_evaluation_paired.py`、`tests/test_evaluation.py`；`configs/experiment.json`、`configs/pilot.json`；评价与 VBench 文档。

P1 提供原始账目，P4 提供媒体证据；复用当前资格、导出与评分算术，不代填主观分。只向评价者分发 public，PRIVATE 映射独立保存。

## 验证入口

```powershell
.venv/Scripts/python -m pytest tests/test_evaluation_paired.py tests/test_evaluation.py -q
```

按实际改动选择相关检查；上述命令不代表本次重新跑过测试。视频测试需要 FFmpeg/ffprobe 和字体，模型响应使用 FakeClient/受控替身。协议与验收边界见[模块文档](../evaluation.md)；默认离线，不由任务卡授权付费、实验或合并。

历史试跑只在[试跑索引](../pilots/README.md)维护，不复制到本卡，不把软件测试或媒体完成当作方法效果。
