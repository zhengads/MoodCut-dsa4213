# MoodCut 文档

先看[项目首页](../README.md)了解研究问题与快速开始。本目录将当前用法、接口、团队协作和历史证据分开维护。

## 当前状态（2026-10-25）

- 生成式脚本编排、三条件请求编译、任务执行、媒体检查、资格重检和匿名导出已实现。默认 CLI 仍是离线 animatic；演员 v3 需显式选择。
- 当前演员协议为 `actor_self_review_v3`，新请求使用 `dialogue_by_shot_json_schema_v2`。两组共用协商上限，仅审查准则不同。
- S06 v3 已完成三段真实视频，支出 $0.75421676；[原始试跑记录](pilots/s06-actor-v3-index.md)保留具体设置、费用及结果。技术成功不等于人工质量或独立效果验收。
- [六故事 v2](studies/six-story-clear-emotions-20261024/README.md)是下一轮候选输入，共 18 个条件条目，不是 18 个已完成结果。`configs/experiment.json` 仍为开发夹具。
- #8、#9 仍开放。评价结果补充见待合并的 [PR #58](https://github.com/zhengads/MoodCut-dsa4213/pull/58)；其历史 Anna/Elsa 结果不能改称 S06 或六故事结果。独立人工评分和正式纳入仍需完成。

## 按任务阅读

| 目的 | 主文档 |
| --- | --- |
| 安装、命令、API 配置、素材准备 | [使用指南](usage.md) |
| 理解三组对照与演员协商 | [演员方法](ACTOR_REVIEW_METHOD.md) |
| 接入字段、函数、状态和账目 | [公共契约](CONTRACTS.md) |
| 维护报告验证、原子补丁和旧全局审查 | [审查实现](review.md) |
| 生成请求、视频检查与静态渲染 | [渲染](rendering.md) |
| 资格、盲评、人工评分与统计分母 | [评价](evaluation.md) |
| VBench 安装、单指标调用与续跑 | [VBench 工具](vbench.md) |
| 模块分工、文件边界与交付流程 | [团队协作](TEAM.md) · [分支规则](BRANCHES.md) |
| 上游阅读路径与采用范围 | [参考索引](REFERENCES.md) · [复用说明](upstream-reuse.md) |

## 证据与历史

- [试跑索引](pilots/README.md)：按协议和实际结果查找成功、失败、费用及原始 JSON。
- [历史记录索引](history/README.md)：早期实施计划、软件验收与原始文档版本。
- [P1 集成报告](p1-integration-verification.md)：带日期的集成与真实 v2 证据，不作为当前待办。
- [六故事 v1](studies/six-story-20261024/README.md)保留原输入与身份；后续设计使用独立的 v2 目录。

当前状态只在本页维护；操作放使用指南，公共规则放契约，实验结果进入各自带日期的记录。任务卡列模块责任和仍需处理的事项，不再复制试跑日志。已有结果、失败和原始数据不得为更新叙述而改写。
