# FilmAgent 阅读笔记

论文：[FilmAgent: A Multi-Agent Framework for End-to-End Film Automation in Virtual 3D Spaces，2501.12909v1](https://arxiv.org/abs/2501.12909v1)。官方项目页：[filmagent.github.io](https://filmagent.github.io/)。本文为项目阅读摘要。

FilmAgent 在预设 Unity 环境中组织导演、编剧、演员与摄影角色。论文第 3.3 节给出 Critique–Correct–Verify 和 Debate–Judge；MoodCut 第一版参考前者：对已有分镜提出具体反馈、修改，再复查意见是否解决。

## 源码证据

固定版本：`HITsz-TMG/VideoClaw@16c1ce0b553e30eff90ff1274e8a8a63c1d548a3` 的 `FilmAgent/`。

`FilmAgent/FilmAgent/main.py` 的 `stage1_verify` 包含导演反馈、编剧修订和导演复查；`stage2_verify` 增加演员反馈及导演筛选。对应提示文件位于 `Prompt/`。原实现使用文件状态、上游 client 和宽松文本判断；MoodCut 需要独立实现明确的 JSON 结果与失败状态。

## MoodCut 适配

P3 只做一次 critique→revise→verify，修改限定到允许字段，非法补丁整体拒绝。通用审查与情绪专项审查共用修订器、模型配置及调用上限。复查意见保留为过程记录，不能替代人工盲评。

该机制已有论文先例。项目研究重点是情绪专项反馈相对通用审查的效果；不能把采用 CCV 本身写成原创贡献。原论文使用的 3D 环境、声音与评估条件不同，原论文分数不作为本项目的直接比较结果。

本地阅读入口：`references/upstream/filmagent/FilmAgent/`。实验方法阅读论文第 4 节及附录 B。
