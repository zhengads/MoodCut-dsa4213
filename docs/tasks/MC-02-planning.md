# MC-02 输入素材与共同规划

[Issue #22](https://github.com/zhengads/MoodCut-dsa4213/issues/22) · [团队协作](../TEAM.md) · [文档状态](../README.md)

本卡说明模块责任，具体认领与增量以 Issue / PR 为准。旧分期清单与验收日志见[历史任务卡](https://github.com/zhengads/MoodCut-dsa4213/blob/18c19a2f36cef2820acb747299b83b58eea5ffc7/docs/tasks/MC-02-planning.md)。

## 已有能力

director→scene→shot 规划、梗概导入、显式 1.1/generated 共同动作与时长、P4 实际编译消费均已交付。可选规划 JSON Schema 支持由独立配置启用，不改变旧默认。

## 后续工作

- 维护与新输入有关的明确故障或适配需求；该 Issue 的工程交付已关闭，不重新实现既有规划。
- 新增素材或故事必须保留原来源、使用权状态和显式角色映射；研究输入变化须按已确认范围处理。

## 修改范围与依赖

`src/moodcut/importer.py`、`planner.py`、`prompts/planning_*.txt`；`assets/manifest.json`、`assets/selection.example.json`、`scripts/prepare_assets.py`；相应测试及 `docs/upstream-reuse.md`。

使用 P1 的验证器、共同输入与缓存。三条件只规划一次，不为 moodcut 单独加强动作/镜头；不代写 reviewer 或媒体编译器，不另建 normalizer。

## 验证入口

```powershell
.venv/Scripts/python -m pytest tests/test_planner.py tests/test_importer.py tests/test_prepare_assets.py -q
```

按实际改动选择相关检查；上述命令不代表本次重新跑过测试。视频测试需要 FFmpeg/ffprobe 和字体，模型响应使用 FakeClient/受控替身。协议与验收边界见[模块文档](../CONTRACTS.md#610-生成式共同规划适配)；默认离线，不由任务卡授权付费、实验或合并。

历史试跑只在[试跑索引](../pilots/README.md)维护，不复制到本卡，不把软件测试或媒体完成当作方法效果。
