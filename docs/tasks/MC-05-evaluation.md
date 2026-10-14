# MC-05 配对对照、盲评导出与统计

认领模块：P5 评估，账号以 Issue 为准。依赖：MC-01 PR1 的记录契约；先用合成记录开发。首个 Draft PR：10/15；10/21 前完成协议工具。

## 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

## 交付

能列出三条件的配对任务、输出匿名观看材料、导入人工评分、报告识别结果和失败覆盖；不负责新增Agent，不把评价脚本变成自动付费跑数工具。

## 修改范围

`src/moodcut/evaluation.py`、`configs/pilot.json`、`tests/test_evaluation.py`、`docs/evaluation.md`。分配、盲评导出和指标汇总先作为 evaluation.py 内的函数实现。后续已确认实验的配置也放 configs；不修改模型/渲染公共配置、初稿、提示词、reviewer 或 renderer。

## PR 1 实验分配与盲评

- [ ] 实现build_assignments，按scene×tone×replicate形成block，每block包含baseline/generic_review/moodcut。记录列表顺序稳定、run_id唯一。
- [ ] 对同一block三个记录检查initial_plan_sha256一致；发现不一致直接拒绝出比较报告。
- [ ] 导出blind_items.csv：item_id、匿名video_file；private_key.csv单独保存condition、target_tone、block_id，不进入观看者页面。随机种子可复现。
- [ ] 评分CSV字段：rater_id（匿名）、item_id、perceived_tone、confidence、naturalness、story_clarity、overstatement。tone可选三类或uncertain；自然度/清楚度/过度表达1–5，confidence1–5。uncertain单列并按主识别口径计为未命中。
- [ ] 组内先用mock CSV验证流程，不把自己知道答案的调试评分当盲评。真实分配应避免同一观看者连续看到同一故事的多个版本。

## PR 2 指标、覆盖与报告

- [ ] 对有评分的可播放clip先计算该clip的tone命中比例，再报告按clip等权平均与混淆计数；显示clip数、rating数、独立scene数。不能让多评分的clip自动获得更大权重。
- [ ] 单列计划运行总数、render成功数、review失败/拒绝数、有人工评分clip数、缺失评分数。识别结果只说明被评价子集，不把失败视频算正确。
- [ ] 自然度、清楚度和过度表达分别汇总，不合成一个“总分”。Agent的verification不作为人工评分。
- [ ] 比较M/G时列出共同可评价block，并报告共同覆盖；若coverage不同，不把共同成功子集结论说成所有运行的无条件提升。
- [ ] 零样本/零分母输出null并显示N/A；重复rater-item或缺字段拒绝，不静默去重。写入出错行号。
- [ ] 实际calls/token/elapsed与费用按所有尝试汇总；null价格不当0。正式统计与代码mock结果分目录并标source_kind。
- [ ] 正式规模在10/21由组内根据pilot成本和人工能力确认；本Issue只实现可配置工具，正式数据集与运行规模由团队批准后执行。

## 验收

目标命令：`python -m pytest tests/test_evaluation.py -q`、`python -m moodcut evaluate --config configs/pilot.json --dry-run`。

测试用合成记录覆盖：一正确、一错误、一失败、一uncertain、一无评分、重复评分、初稿hash不一致、零样本。预期数值人工手算写在测试中。报告能看到失败与分母，不预写“我们方法更好”。

## 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
