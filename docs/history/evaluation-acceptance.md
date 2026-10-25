# P5 历史验收记录

[历史索引](README.md) · [当前评价说明](../evaluation.md)

以下是 2026-10-24 的原验收快照，保留各自基线、署名、真实摘要资格拒绝及软件结果；旧 PR 状态不代表当前状态。原始完整发展记录可由历史索引中的固定版本追溯。

## 当前优先：一键验证代码流程

2026-10-24，按用户收敛后的范围，优先验收代码流程，不以历史真实运行包
交接作为本轮软件验收的前提。安装开发依赖并将 FFmpeg/ffprobe 加入 PATH，
在仓库根目录运行（输出目录必须新建）：

```powershell
.venv/Scripts/python scripts/verify_workflow.py --output runs/workflow-check-01
```

该入口复用原 CLI 和现有集成测试，不重写任何模块。实际 Windows 验收通过：

- 三条件 mock 规划/审查 → 3 段 animatic → 3 段匿名导出 → 无评分覆盖统计。
- 任务分配 dry-run 通过。
- generated 跨模块集成 12 项通过（47.27 秒）：请求准备、软件音视频装配、
  资格、匿名导出、评分算术、来源变化拒绝、失败及未知费用保留。

查看输出的 `verification.json`、各步骤日志和 `generated-tests.xml`。
`blind/public/` 含匿名视频和空评分表，`blind/PRIVATE/` 不向观看者分发；
`coverage.json` 为 3 条已渲染、3 条缺评分，主观均值全部 null。
`generated-software-cases/` 保存生成式集成产物，测试中的视频、回执和评分
均为软件夹具。本轮没有付费 API 调用，不把此结果声明为真实模型效果验证。

历史真实运行的严格 6.14/6.15 认证保留为独立后续项，不影响上述代码验收；
现有门禁保持原样。本轮完成人：FANXUYANG；保留原 P5 及各模块作者贡献。



## 最新 main 上的 P5 起步验收（2026-10-24）

本轮基于 main `ba692a7`，继续 `feat/issue-9-evaluation-acceptance`，保留
chessloverr 的原 P5 实现、团队接线及 FAN XUYANG 的覆盖计数增量。
七项要求的工程核对如下；“已实现”不代表真实样本已通过资格或方法效果已证实。

| Issue #9 要求 | 当前实现及验收依据 | 真实执行边界 |
| --- | --- | --- |
| 三条件输入适配、来源与账目 | P1 `recheck_generated_records` 和 P5 `qualify_generated_records` 消费完整最终 1.1 block；保留原 source_kind、失败、模型、哈希和账目 | 新公开 v3 结果是试跑摘要，不能代替最终 block |
| 共同初稿、共享身份和导出资格 | `validate_generated_comparison` 加 P1/P4 来源重算；身份、非台词、回执或媒体变化有拒绝回归 | 真实摘要只验证了公开计划及媒体，尚不能独立重算全部共同输入 |
| 复用导出/评分，匿名和状态分列 | `export_generated_blind_items` / `summarize_generated_records` 复用原复制器/算术；覆盖 applied、unchanged、失败、无渲染及缺评分 | 真实匿名包尚未发布；不使用低层旧接口绕过门禁 |
| 统计及费用口径 | clip 等权、uncertain 未命中、M/G 共同可评块及覆盖分报；unknown 为 null，规划/合法复用各计一次 | 公开费用算术一致不等于独立认证提供商账单 |
| 合成软件回归 | `tests/test_evaluation_paired.py` / `tests/test_evaluation.py` 覆盖三条件、身份篡改、失败、unknown、零分母、复用、匿名副本与评分映射 | 测试回执、软件视频和合成评分不是模型效果数据 |
| 待确认协议 | 本文保留协议表；当前故事候选为 PR #56 的[明显情绪 v2 输入](../studies/six-story-clear-emotions-20261024/README.md) | 6 故事/18 条目是当前设计范围；正式冻结、观看者、排除/复用规则和执行预算仍需确认 |
| 报告边界 | 检验情绪专项台词审查相对通用审查的端到端价值；不归因为更多 Agent、动作规划或面部表情机制；VBench imaging_quality 不衡量情绪 | 人工质量、独立盲评、正式统计和效果结论尚未完成 |

新版 main 已支持独立 `tense` 标签；保留 `suspicious` 兼容历史记录，不将
二者重命名或混计。旧开发 `configs/experiment.json` 仍是软件示例，不据此启动
六故事实验。PR #52 的新 writer 合约/提示词尚未合入本轮 main，不将新摘要
改标为旧协议或强行拼成可比较记录。

### 新真实视频预检和正式资格结果

从 [v3 Release](https://github.com/zhengads/MoodCut-dsa4213/releases/tag/pilot-anna-elsa-v3-20261024)
下载三段原片及 manifest；原模型结果来自
`feat/issue-8-actor-v3-live` 的 `docs/pilots/anna-elsa-actor-v3-captured.results.json`，
执行代码为 `7817623`。三段不同原片共 3,326,698 字节，均 1344×768、24fps、
约 5.258344 秒并含音轨；大小/SHA-256、完整解码、初稿/最终计划哈希及
非台词一致性检查通过。审查状态为 baseline not_applicable，其余两组 applied。

公开账目分项按 8 位小数核对：文本 $0.00277694、视频 $0.75、合计
$0.75277694；原浮点尾差及 unknown token/estimated 字段保留，不补零。
没有访问提供商账户认证这些金额，没有新模型或视频调用。

随后实际运行既有资格函数、匿名导出函数及 README CLI。资格诊断为
`expected a final 1.1/generated record block`，导出拒绝非完整最终 block；
这份公开 JSON 的 kind 为 `actual_actor_v3_captured_text_and_video_trial`。
这说明当前可取得的输入尚不能进入正式接线，不说明原生成执行失败。
未补造回执、run_id、来源文件或人工评分，未绕过门禁发布匿名材料。

实际程序结果为：真实条件条目 3、不同原片 3，真实匿名导出 0、人工评分 0；
情绪准确率、自然度、剧情清楚度和过度表达均无可报告数值。
下一步为定位/交付该次执行的原最终 records 及其引用来源，检查迁移路径和
writer 合约兼容性后重跑 6.14/6.15。单独的公开摘要不能认证完整来源和费用。
人工听看及独立评分随后进行；不需要为此次离线核对重新生成视频。

本轮整理与预检：FAN XUYANG。运行证据保存在忽略的 `runs/` 中；不提交
原视频、参考图片、私人响应或观看者身份。后续小节保留各自历史基线和验收时间。

本轮 Windows / PowerShell 验收：`python -m pytest tests/test_evaluation_paired.py
tests/test_evaluation.py -q --tb=short -p no:cacheprovider` 为 101 项、92 个子测试
通过（153.94 秒）；`tests/test_cli.py -k 'evaluate or rating'` 为 4 项通过。
33 份固定参考校验、evaluate dry-run 和 `git diff --check` 通过。
上述软件成功与真实摘要资格未通过分别报告，不用软件结果替代真实接入认证。




## 覆盖计数增量的原始验收与署名

本次增量：FAN XUYANG。原 P5 及团队集成贡献见文末记录，署名保持。

本次离线验收（Windows / PowerShell，FFmpeg/ffprobe 7.1.1 已加入测试进程 PATH）：

- `python -m pytest tests/test_evaluation_paired.py tests/test_evaluation.py -q`：
  100 项测试、92 个子测试通过，145.05 秒；包含合成音视频、实际资格/导出/评分链路。
- `python -m pytest tests/test_cli.py -k 'evaluate or rating' -q`：4 项通过。
- 三条件 `smoke --mock`、对其 block 的 `evaluate` 和 experiment `--dry-run` 通过；
  实际 smoke 汇总为 2 applied、1 not_applicable、3 no_rendered_video、3 missing_ratings，
  tone_accuracy 为 null。合成输入与评分不作为真实方法效果。
- `prepare_references.py --check`：33 份缓存通过、0 下载；`git diff --check` 通过。

本轮不调用模型/API/GPU，不运行 VBench 推理，不产生真实视频或人工评分。
