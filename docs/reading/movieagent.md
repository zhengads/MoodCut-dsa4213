# MovieAgent 阅读笔记

论文：[Automated Movie Generation via Multi-Agent CoT Planning，2503.07314v1](https://arxiv.org/abs/2503.07314v1)。作者：Weijia Wu、Zeyu Zhu、Mike Zheng Shou。本文为项目阅读摘要，原文以论文和固定版本源码为准。

MovieAgent 使用分阶段规划连接故事、场景、镜头与后续生成。MoodCut 采用这一规划组织方式，并将输出约束到自己的 ShotPlan；该适配不包含原系统的视频生成后端。

## 源码证据

固定版本：`d84041bed8bc8be460664528d9e9924cdde384ba`。

- `movie_agent/run.py` 中 `ScriptBreakAgent.__init__` 调用 `init_videogen`。该文件涉及生成工具依赖，不作为 MoodCut 的直接 import 入口。
- `ScriptBreak`、`ScenePlanning`、`ShotPlotCreate` 提供规划阅读顺序。`system_prompts.py` 保存相应提示词。
- `scriptsupervisor-sys` 提示存在，但所核对的 `init_agent` 中 supervisor 初始化行被注释。不能仅凭提示词存在认定执行了评审闭环。
- FrozenII 梗概 JSON 包含 `MovieScript` 与 `Character`；角色目录中的图片是参考输入，不是可直接拼接的动态镜头。

## MoodCut 适配

P2 负责输入适配、规划提示与字段归一化；调用统一经过 P1 的 client。三种实验条件使用同一初稿。素材固定，不引入上游 GPU 生成依赖。归一化后用公共 validator 验证结构，保留原始响应与来源。

本地阅读入口：`references/upstream/movieagent/`。精确文件、下载 URL 与校验值见 `references/sources.lock.json`。
