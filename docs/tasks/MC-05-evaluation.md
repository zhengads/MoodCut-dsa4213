# MC-05 配对对照、盲评导出与统计

当前任务：[GitHub Issue #9](https://github.com/zhengads/MoodCut-dsa4213/issues/9)。先做下面未勾选的下一增量；末尾既有交付仅用于复用和回归。

当前具体试跑单增量分支：`docs/issue-9-concrete-pilot`。执行接线已随PR #41合入。先检查认领和活动 PR；[分支命名与迁移](../BRANCHES.md)。不在 `archive/` 继续开发。

### 当前具体候选试跑单（2026-10-23）

[还伞首镜头试跑单](../pilots/umbrella-single-shot.md)选原return-umbrella、4秒、三个手写软件台词版本，列出Seedance/720p共同设置、来源/占位素材缺口、逐字差异、文本/视频/恢复/历史费用与验收标准。首选音视频技术预检不新增文本调用，额度提议$1.10；真实P2/P3扩展另批，总额提议$1.20，不能用手写台词冒充真实审查。#8配合实际编译/报价核对；素材/历史费用/余额未齐，执行开关及批准字段保持false/null，不是付费run-ready材料。#8/#9继续开放。

### 当前试跑协议整理（2026-10-23）

配合#8分支 `feat/issue-8-generated-execution`，扩充docs/evaluation.md已有待确认表：最小单镜头三条件提议、模型/范围/预算冻结、GET恢复/继续与停止、人工质量检查及盲评安排。全部真实试跑选择/规模/费用和正式纳入仍待批准；不新建数据集/配置，不填写评分。执行结果沿用现有资格/导出/统计；只取最终records，不累计父子/preflight快照。接口见CONTRACTS 6.17，#8/#9保持开放。

## 生成式记录评估（离线资格及盲评导出/评分接线已实现）

**目标**：复用现有盲评/统计工具，为真实生成视频补齐输入适配与比较资格校验；VBench 继续仅作视觉质量辅助。

### 当前生成状态细分汇总（2026-10-23）

总体及各条件新增generation状态轴，区分未开始、离线未提交、进行中、待人工检查、失败、中断和未知；镜头轴保留混合失败/中断及原远端状态，另报待拼接与失败原因。复用原P1状态映射、CLI和汇总器，不改费用、评分、资格或正式纳入；旧渲染指标保留。接口见CONTRACTS 6.16，软件夹具/已有产物离线验收，不调用API。整体未完成项和原认领保持，#8/#9继续开放。

### 已有盲评导出和评分接线（6.15）

`export_generated_blind_items` / `summarize_generated_records`复用资格、匿名复制和原评分器，CLI为evaluate加显式`--pricing-config`。复制边界和评分时重检来源/回执/账目，私有清单绑定实际导出字节、匿名映射和完整block（含镜头范围）。公开仅匿名视频/索引/空表，失败块保留全部覆盖与账目；不批准正式纳入。准确接口见CONTRACTS 6.15。以下整体待办含真实任务与后续细分统计，不因软件接线整体勾选。

P1 `recheck_generated_records` 复用已有装配计算和P4编译器；P5 `qualify_generated_records` 输出独立的逐条件资格报告，CLI为 `qualify-generated-records`。源记录/账目/人工表不改，未知费用和失败全部保留，generated盲评/ratings须走6.15的独立重检入口。验收使用现有软件产物，不调用API；整体待办不因本增量自动完成，#8/#9仍保持开放。详见CONTRACTS 6.14。

### 已核实的缺口

旧开发对脚本仍输出 baseline / dialogue_revision；1.1三条件脚本、请求与本地最终记录已有P1/P2/P3/P4实现，PR #37提供前置检查。离线资格报告及盲评/评分接线已实现，当前入口见CONTRACTS 6.15。正式故事/样本数/评价者分配未冻结，也没有真实人工评分；`configs/experiment.json` 仍是软件开发示例。

### 整体待办与验收（含真实试跑，当前工程交付见上节）

- [ ] 与 P1 对齐真实生成记录到 baseline/generic_review/moodcut 的映射，保留源计划/生成输入哈希、实际模型设置、媒体路径、审查与生成失败、费用及 source_kind；不将历史派生投影重命名后冒充正式实验。
- [ ] 在导出比较材料前核对同块初稿及 `shared_generation_sha256` 一致；不一致拒绝可比较导出并显示原因。全部原始记录仍进入覆盖/费用账目，不能删掉违规或失败条件美化分母。
- [ ] 复用 `export_blind_items` 和 `summarize`，不重新实现评分或自动情绪分；公开材料不带方法/目标 tone，私有映射单独保存。单列 `unchanged`、失败回退、无视频和缺失评分，正式纳入规则待团队确认。
- [ ] 保留既有统计口径：clip 等权、uncertain 为未命中、M/G 共同可评 block 的配对差异与覆盖分别报告；费用 unknown 不当零，共享规划/复用镜头不重复计费。
- [ ] 添加生成记录的合成软件回归：三条件、非台词哈希不一致、失败/未知费用、无评分、零分母、请求复用。不把这些记录或分数包装成模型效果数据。
- [x] 在 `docs/evaluation.md` 整理待确认协议表：开发/正式故事划分、条件与冻结配置、样本/重复数、观看者分配、失败/无修改规则、预算及停止条件。6.17配合增量已扩充最小试跑提议；这里只完成文档整理，所有真实选择及正式规则仍未批准，不自行填定、建新数据集或跑数。
- [ ] 报告边界写明：对照检验情绪专项台词审查相对通用审查的端到端价值；不能证明更多 Agent、更好动作规划或单独面部表情机制。VBench imaging_quality 不衡量情绪。

### 写入范围与依赖

接入协议固定为 CONTRACTS 6.3–6.5/6.14/6.15：复用已实现的 validate_generated_comparison 前置核对，重算共享身份而非只比较声明值。GeneratedRunRecord 使用1.1、数字/null消费和独立 generation_status；软件例子见 `tests/fixtures/generated_contract.json`。summarize可读基础字段做空评分诊断，生成式导出/评分必须走6.15独立重检；保留全部失败/费用与原统计口径。

可用公共验证器显式 generated 检查源场景/计划；unchanged 是合法无修改状态，不代表所有意见解决，也不是情绪评分。失败回退与无视频仍保留，正式纳入规则不随软件兼容修复自动改变。

`src/moodcut/evaluation.py`、`tests/test_evaluation_paired.py`、`tests/test_evaluation.py`、`docs/evaluation.md`；`configs/experiment.json` / `pilot.json` 仅在本任务已确认边界内补充兼容元数据，保留 development/proposal 标记，不擅自启用正式运行。生成账目协议由 P1 发布，媒体由 P4 提供。

依赖 P1 记录契约，可立即用软件合成记录开发；不等待真实模型视频。离线验收：`python -m pytest tests/test_evaluation_paired.py tests/test_evaluation.py -q` 和现有 evaluate dry-run；不下载模型、不跑 VBench/GPU、不生成主观评分。

## 既有模块与验收记录（供复用与回归）

### 当前交付

配对分配、匿名视频导出、空评分模板、人工评分汇总与覆盖/费用已有实现，测试在 test_evaluation_paired.py；原 VBench 工具及 test_evaluation.py 保留。正式样本与评价者分配、真实人工评分尚待确认。

下列勾选项表示工程实现；不表示真实 API、正式实验或人工主观评价已完成。

认领模块：P5 评估，账号以 Issue 为准。依赖：MC-01 PR1 的记录契约；先用合成记录开发。首个 Draft PR：10/15；10/21 前完成协议工具。

### 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

### 交付

能列出三条件的配对任务、输出匿名观看材料、导入人工评分、报告识别结果和失败覆盖；不负责新增Agent，不把评价脚本变成自动付费跑数工具。

### 修改范围

`src/moodcut/evaluation.py`、`configs/experiment.json`、`configs/pilot.json`、`tests/test_evaluation_paired.py`、`tests/test_evaluation.py`、`docs/evaluation.md`。分配、盲评导出和指标汇总先作为 evaluation.py 内的函数实现。后续已确认实验的配置也放 configs；不修改模型/渲染公共配置、初稿、提示词、reviewer 或 renderer。

### PR 1 实验分配与盲评

- [x] 实现build_assignments，按scene×tone×replicate形成block，每block包含baseline/generic_review/moodcut。记录列表顺序稳定、run_id唯一。
- [x] 对同一block三个记录检查initial_plan_sha256一致；发现不一致直接拒绝出比较报告。
- [x] 导出blind_items.csv：item_id、匿名video_file；private_key.csv单独保存condition、target_tone、block_id，不进入观看者页面。随机种子可复现。
- [x] 评分CSV字段：rater_id（匿名）、item_id、perceived_tone、confidence、naturalness、story_clarity、overstatement。tone可选三类或uncertain；自然度/清楚度/过度表达1–5，confidence1–5。uncertain单列并按主识别口径计为未命中。
- [x] 工具已用合成 CSV 单元测试验证流程，不把自己知道答案的调试评分当盲评。真实分配应避免同一观看者连续看到同一故事的多个版本。

### PR 2 指标、覆盖与报告

- [x] 对有评分的可播放clip先计算该clip的tone命中比例，再报告按clip等权平均与混淆计数；显示clip数、rating数、独立scene数。不能让多评分的clip自动获得更大权重。
- [x] 单列计划运行总数、render成功数、review失败/拒绝数、有人工评分clip数、缺失评分数。识别结果只说明被评价子集，不把失败视频算正确。
- [x] 自然度、清楚度和过度表达分别汇总，不合成一个“总分”。Agent的verification不作为人工评分。
- [x] 比较M/G时列出共同可评价block，并报告共同覆盖；若coverage不同，不把共同成功子集结论说成所有运行的无条件提升。
- [x] 零样本/零分母输出null并显示N/A；重复rater-item或缺字段拒绝，不静默去重。写入出错行号。
- [x] 实际calls/token/elapsed与费用按所有尝试汇总；null价格不当0。正式统计与代码mock结果分目录并标source_kind。
- [ ] 正式规模在10/21由组内根据pilot成本和人工能力确认；本Issue只实现可配置工具，正式数据集与运行规模由团队批准后执行。

### 验收

目标命令：`python -m pytest tests/test_evaluation_paired.py tests/test_evaluation.py -q`、`python -m moodcut evaluate --config configs/experiment.json --dry-run`。

测试用合成记录覆盖：一正确、一错误、一失败、一uncertain、一无评分、重复评分、初稿hash不一致、零样本。预期数值人工手算写在测试中。报告能看到失败与分母，不预写“我们方法更好”。

### 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
