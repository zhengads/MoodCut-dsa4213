# MC-01 公共契约、客户端与集成

[Issue #8](https://github.com/zhengads/MoodCut-dsa4213/issues/8) · [团队协作](../TEAM.md) · [文档状态](../README.md)

本卡说明模块责任，具体认领与增量以 Issue / PR 为准。旧分期清单与验收日志见[历史任务卡](https://github.com/zhengads/MoodCut-dsa4213/blob/18c19a2f36cef2820acb747299b83b58eea5ffc7/docs/tasks/MC-01-foundation.md)。

## 已有能力

公共协议、模式验证、一次规划与条件隔离、缓存和共享身份、离线请求准备、回执/费用装配、真实任务执行/恢复已实现。角色路由、actor-negotiation 来源重检及私有 JSON 诊断已接入。默认 animatic 和历史协议继续兼容。

## 后续工作

- 为选定实际运行交接完整最终 records、冻结输入、请求、回执与媒体，保留原相对关系；公开结果摘要不能替代最终 block。
- 与 P5 重检真实来源和费用，区分工程成功、导出资格与正式纳入；不补造缺失回执或把未知费用填零。

## 修改范围与依赖

`src/moodcut/contracts.py`、`client.py`、`validation.py`、`pipeline.py`、`__main__.py`、`video_client.py`；`scripts/generate_video.py`；公共配置、夹具、CI 和对应测试。P1 维护公共契约与项目基础文件；具体增量仍只修改 Issue 认领范围，不因此获得修改所有模块的权限。

`contracts.py` 的白名单/共享哈希供全模块复用；P2/P3 提示、P4 编译器与 video 配置变更先协调。P5 资格和评分工具直接复用，不再另建账目或状态框架。

## 验证入口

```powershell
.venv/Scripts/python -m pytest tests/test_contracts.py tests/test_validation.py tests/test_pipeline.py tests/test_cli.py -q
```

按实际改动选择相关检查；上述命令不代表本次重新跑过测试。视频测试需要 FFmpeg/ffprobe 和字体，模型响应使用 FakeClient/受控替身。协议与验收边界见[模块文档](../CONTRACTS.md)；默认离线，不由任务卡授权付费、实验或合并。

历史试跑只在[试跑索引](../pilots/README.md)维护，不复制到本卡，不把软件测试或媒体完成当作方法效果。
