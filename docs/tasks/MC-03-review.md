# MC-03 通用审查、情绪审查与局部修订

[Issue #23](https://github.com/zhengads/MoodCut-dsa4213/issues/23) · [团队协作](../TEAM.md) · [文档状态](../README.md)

本卡说明模块责任，具体认领与增量以 Issue / PR 为准。旧分期清单与验收日志见[历史任务卡](https://github.com/zhengads/MoodCut-dsa4213/blob/18c19a2f36cef2820acb747299b83b58eea5ffc7/docs/tasks/MC-03-review.md)。

## 已有能力

报告验证、原子补丁、全局审查、generated 台词白名单及实际候选复查已交付。演员 v1/v2/v3 与按镜头/Schema 输出在后续增量扩展；当前方法统一见演员协议文档。

## 后续工作

- 工程交付已关闭；后续仅处理明确认领的故障或已批准方法修订。
- 结合真实案例检查自然度、遗漏意见和分歧；保留原模型输出，不根据历史结果静默改写输入、评分或旧协议。

## 修改范围与依赖

`src/moodcut/reviewer.py`、`patches.py`、`prompts/review_*.txt`；`tests/test_reviewer.py`、`tests/test_patches.py`；`docs/review.md` 与方法说明。

导入公共字段白名单与非台词验证。公共 client/pipeline/source 变更与 P1 协调；不改规划/生成提示或评价标准。global_v1 的一次复查与 v3 的有上限协商不可混称。

## 验证入口

```powershell
.venv/Scripts/python -m pytest tests/test_patches.py tests/test_reviewer.py -q
```

按实际改动选择相关检查；上述命令不代表本次重新跑过测试。视频测试需要 FFmpeg/ffprobe 和字体，模型响应使用 FakeClient/受控替身。协议与验收边界见[模块文档](../ACTOR_REVIEW_METHOD.md)；默认离线，不由任务卡授权付费、实验或合并。

历史试跑只在[试跑索引](../pilots/README.md)维护，不复制到本卡，不把软件测试或媒体完成当作方法效果。
