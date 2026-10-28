# MoodCut 团队协作

[文档入口与当前状态](README.md) · [分支规则](BRANCHES.md) · [AI 开工模板](usage.md#用-ai-开发一个任务)

P1–P5 表示模块责任，不是审批等级或固定人员。以 Issue 中的认领和活动 PR 为准，一项增量由一位成员负责；任务卡不代替实际认领，也不自动授权付费运行或合并。

## 模块与文件边界

| 模块 | Issue / 任务卡 | 维护内容 |
| --- | --- | --- |
| P1 基础与集成 | [#8](https://github.com/zhengads/MoodCut-dsa4213/issues/8) · [任务卡](tasks/MC-01-foundation.md) | contracts、client、validation、pipeline、CLI、video_client、公共夹具与 CI |
| P2 输入与规划 | [#22](https://github.com/zhengads/MoodCut-dsa4213/issues/22) · [任务卡](tasks/MC-02-planning.md) | importer、planner、planning 提示词、素材清单与准备 |
| P3 台词审查 | [#23](https://github.com/zhengads/MoodCut-dsa4213/issues/23) · [任务卡](tasks/MC-03-review.md) | reviewer、patches、review 提示词及相应测试 |
| P4 生成与检查 | [#24](https://github.com/zhengads/MoodCut-dsa4213/issues/24) · [任务卡](tasks/MC-04-rendering.md) | video_generation、renderer、video_generated 提示词、video 配置与媒体检查 |
| P5 评价 | [#9](https://github.com/zhengads/MoodCut-dsa4213/issues/9) · [任务卡](tasks/MC-05-evaluation.md) | evaluation、评价测试、实验配置与报告 |

#22/#23/#24 的工程交付已关闭；维护时检查是否已有新 Issue，不重新认领已交付功能。#8/#9 的后续工作涉及实际来源交接、质量检查与评价。具体状态见 Issue。

公共接口和共享夹具由 P1 维护，其他模块直接复用；公共文件或跨模块修改先与受影响成员协调。代码按功能平铺在 `src/moodcut/`，提示词集中于 `prompts/`，配置集中于 `configs/`，测试使用 `tests/fixtures/`。

## 工作顺序

1. 阅读 AGENTS、相关任务卡、公共契约及模块实现，核对 Issue 和活动 PR。
2. 复用已有增量和分支；新任务从最新 main 开始，按[分支规则](BRANCHES.md)命名。
3. 明确文件范围和验收问题，使用已有客户端、验证器、编排及评价工具。
4. 运行相关离线检查，审阅 diff 和实际产物；报告失败、未验证项和费用未知状态。
5. 每个可验收增量走 PR，自查结论、测试和遗留项写入描述。验收及所需检查通过后，按已有授权合并。

作者可以自行评审，无需固定评审人；自查记录不等于 GitHub Approve。保留 `.gitmessage` 的姓名与日期格式，不直接 push main，不强推共享分支。同步已推送分支优先 merge，保留共同历史。

团队日常进度在 Issue 更新已交付项、下一步和阻塞；原约定为每天北京时间 21:00 前更新。阻塞超过半天时附报错、最小复现和尝试过的方案，协调接手。旧课程里程碑见[历史计划](history/README.md)，不作为新的执行授权。

## 对照与费用

三条件共享故事、素材、初稿、场景/动作/镜头和生成设置；生成式审查只能改台词。两组使用相同的模型分工、轮数上限和修改权限，协议差异以[演员方法](ACTOR_REVIEW_METHOD.md)为准，不把旧全局审查的一轮限制套到 actor-negotiation。

默认 mock/offline。团队原共享额度为 $15，历史额度不等于可用余额或新调用授权。真实请求需明确模型、规模和预算；未知费用保留 null，规划和合法请求复用不重复计费，失败不静默剔除。

固定 seed 不保证不同台词生成相同画面。Agent 自评、软件验收、实际媒体完成与独立人工评分分别记录；新实验条件、正式样本和评价规则须另行确认。
