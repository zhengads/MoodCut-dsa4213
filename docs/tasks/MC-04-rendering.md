# MC-04 生成视频与本地检查

[Issue #24](https://github.com/zhengads/MoodCut-dsa4213/issues/24) · [团队协作](../TEAM.md) · [文档状态](../README.md)

本卡说明模块责任，具体认领与增量以 Issue / PR 为准。旧分期清单与验收日志见[历史任务卡](https://github.com/zhengads/MoodCut-dsa4213/blob/18c19a2f36cef2820acb747299b83b58eea5ffc7/docs/tasks/MC-04-rendering.md)。

## 已有能力

三条件请求编译、原始音视频拼接、来源绑定、抽帧/ffprobe 与空人工检查表已交付；静态 animatic 和旧开发对仍为独立入口。真实开发试跑已有成片，人工质量验收仍独立进行。

## 后续工作

- 工程交付已关闭；维护具体编译/媒体故障及已批准的后端适配。
- 对选定实际成片检查人物、台词/说话人、口型和连续性；音轨存在、文件解码与实际质量分别记录，不自动填写通过。

## 修改范围与依赖

`src/moodcut/video_generation.py`、`renderer.py`、`prompts/video_generated.txt`；`configs/video.json`；`scripts/inspect_generated_video.py`；对应视频/渲染测试和 `docs/rendering.md`。

消费 P2 共同动作，规划前冻结实际模板哈希；使用 P1 传输、账目、执行器和 P5 资格工具。仅台词随条件变化，不为单组加强动作/滤镜/音色，不以静态图替代失败生成。

## 验证入口

```powershell
.venv/Scripts/python -m pytest tests/test_video_generation.py tests/test_renderer.py tests/test_video.py -q
```

按实际改动选择相关检查；上述命令不代表本次重新跑过测试。视频测试需要 FFmpeg/ffprobe 和字体，模型响应使用 FakeClient/受控替身。协议与验收边界见[模块文档](../rendering.md)；默认离线，不由任务卡授权付费、实验或合并。

历史试跑只在[试跑索引](../pilots/README.md)维护，不复制到本卡，不把软件测试或媒体完成当作方法效果。
