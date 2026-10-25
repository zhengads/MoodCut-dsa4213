# 试跑与协议修订记录

[文档入口](../README.md) · [当前方法](../ACTOR_REVIEW_METHOD.md) · [公开观看页](https://zhengads.github.io/MoodCut-dsa4213/)

本目录是带日期和版本的开发证据。原记录中的 Draft、未合并、尚未试跑等文字描述当时状态；合并状态以对应 PR 为准。后续成功不覆盖较早失败，技术成片不等于人工质量或独立效果评价。

## 实际试跑

| 记录 | 协议 / 输入 | 实际结果 |
| --- | --- | --- |
| [还伞技术试跑及早期失败](umbrella-single-shot.md) | 手写三组台词；cn-02/cn-04 | HeyGen 三段完成，$0.75；原 Wan/Seedance/MIME 失败和未知费用保留 |
| [Anna/Elsa 全局审查](anna-elsa-agent.md) | global_v1 | 9 次文本、3 段视频；$0.75376126，保留模型未解决意见 |
| [Anna/Elsa 双演员](anna-elsa-actor.md) | actor_self_review_v1 | 8 次文本、2 段不同视频覆盖三条件；$0.50248398，通用组复用 baseline，保留 Elsa 未采纳意见 |
| [Anna/Elsa v3 首轮](anna-elsa-actor-v3.md) | v3 / issue_patch_v1 | 重复 edit，视频未提交 |
| [Anna/Elsa 按镜头接口](anna-elsa-actor-v3-shot.md) | v3 / dialogue_by_shot_v1 | JSON 失败；当时缺失原文，具体子型未知 |
| [Anna/Elsa 原文留存版](anna-elsa-actor-v3-captured.md) | v3 / dialogue_by_shot_v1 | 三段视频完成，$0.75277694 |
| [S06 JSON 尾部失败](s06-actor-v3.md) | v3 / dialogue_by_shot_v1 | 坏响应原文保留，视频未提交 |
| [S06 演员错引行号](s06-actor-v3-schema.md) | v3 / dialogue_by_shot_json_schema_v1 | 错引行号，视频未提交 |
| [S06 演员引用约束版](s06-actor-v3-index.md) | v3 / dialogue_by_shot_json_schema_v2 | 三段视频完成，$0.75421676；人工检查待完成 |

每份 Agent 试跑 Markdown 链接对应的 `*.results.json`、执行版本及媒体来源。不要跨协议混合为同一组配对样本，也不要把复用视频计成新的独立生成。真实 v2 集成证据另见 [P1 历史报告](../p1-integration-verification.md)。

## 为解决失败而做的协议修订

| 说明 | 解决的边界 |
| --- | --- |
| [按镜头输出契约](anna-elsa-v3-shot-contract.md) | 每镜头一份完整台词，避免按意见重复 edit |
| [原始响应与 JSON 诊断](text-response-diagnostics.md) | 私有留存原文，区分解析失败；不修复模型输出 |
| [S06 编剧 Schema](s06-structured-writer.md) | 结构化 writer 请求与版本身份 |
| [S06 演员引用约束](s06-actor-index-constraints.md) | 按角色所属台词限定全局行号 |

这些修订记录中的离线验收与后续实际试跑分开阅读。当前协议的统一说明在[方法](../ACTOR_REVIEW_METHOD.md)及[契约](../CONTRACTS.md)，不再复制各次测试日志。

## 媒体与来源

[原视频交付索引](anna-elsa-videos.md)记录观看/下载入口；[合成人物署名](umbrella-sigils-credits.md)保留 cn-02/cn-04 的来源及许可条件。MovieAgent 角色图的使用权状态见[素材库](../../assets/library/README.md)。

公开观看页展示条件和预期台词，不能直接用作盲评材料。历史结果、原始 JSON、失败、费用及图片身份保持原样。
