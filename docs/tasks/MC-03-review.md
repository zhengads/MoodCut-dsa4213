# MC-03 通用审查、情绪审查与局部修订

当前任务：[GitHub Issue #23](https://github.com/zhengads/MoodCut-dsa4213/issues/23)。本次审查实现与离线验收已提供；先核对Issue中的PR合并状态，不重复实现已勾选模块。末尾既有交付用于复用与回归。

首个增量建议分支：`fix/issue-23-dialogue-review`。先检查认领和活动 PR；[分支命名与迁移](../BRANCHES.md)。不在 `archive/` 继续开发。

## 台词限定审查（生成式适配已实现）

**目标**：generic_review 和 moodcut 共享同一修改能力，真正复查最终采用的台词脚本。

### 已核实的缺口

- 默认animatic保留dialogue/narration/crop/duration；显式generated使用独立提示与公共白名单，在补丁源头限制dialogue，并核对实际候选的完整非台词身份后再verify，不使用投影。
- 既有开发错误`edits[3]: conflicting or duplicate edit`已用最小手写软件夹具复现；保持拒绝规则，按镜头汇集全部意见后生成单条edit，verify仍覆盖所有原issue_id。

### 本次待办与验收

- [x] review_and_revise/apply_patch接显式output_mode与公共白名单/完整非台词比较，generated的critique/revise/补丁均限制dialogue，默认animatic允许字段保持兼容。
- [x] 两类审查接收同一故事/tone/初稿，调用者传同一模型配置，各阶段2048输出上限及最多一次critique→revise→verify；无意见1次退出并保留真实调用数。
- [x] issues_by_shot完整汇集原意见，单shot最多一条edit，保留原issue_id引用；不改Report/Patch外壳或删意见，verify覆盖全部原ID。
- [x] verify看到实际补丁应用后的dialogue-only计划，成功返回同一计划，保存review.json/final.json一致性；不投影后继承候选复查结论。
- [x] 越权字段、未知扩展或镜头变化整体拒绝并回退，输入不变；真实字段门禁与候选故障注入分别验收。
- [x] FakeClient覆盖聚合、edits[3]重复拒绝、非法字段、unchanged/空补丁、原子回退、完整复查覆盖和实际P2/P3/P1脚本链；最小夹具手写，不依赖本地历史runs，也不作为模型效果。

### 写入范围与依赖

接入协议固定为CONTRACTS 6.1/6.2/6.5，实际用法与失败语义见6.11。已使用allowed_patch_fields与assert_dialogue_only_revision，mode和output_mode不混用；Report/Patch外壳仍为1.0。公共验证器、实际P2规划及P1编排均已可用。

公共验证器现已接受 output_mode="generated"；本任务把同一输出模式传到验证器。既有视频来源入口已兼容合法 unchanged，仍拒绝 failed/rejected/review_failed；不要为通过来源检查把失败状态改成 unchanged。

`src/moodcut/reviewer.py`、`patches.py`、`src/moodcut/prompts/review_*.txt`、对应测试及docs/review.md；不修改规划提示、公共验证器或媒体编译器。P1协同只为pipeline按模式记录实际审查提示哈希；P2测试协同只把先前“P3缺接口”断言改为真实reviewer加软件无意见响应，不替换业务函数。这些协调记录在#8/#22。

离线验收：`python -m pytest tests/test_patches.py tests/test_reviewer.py -q`，并给出两模式的 FakeClient stage/输入与台词差异记录。Agent verification 不是人工评分，不预写效果结论。

## 既有模块与验收记录（供复用与回归）

### 当前交付

两类审查、原子补丁、一次复查与失败回退已有实现，CLI/pipeline 已接入。后续围绕真实输出诊断，不重写同一套 client/validator。

下列勾选项表示工程实现；不表示真实 API、正式实验或人工主观评价已完成。

认领模块：P3 审查修订，账号以 Issue 为准。依赖：MC-01 PR1；使用共享夹具，不必等真实规划。首个 Draft PR：10/15；接入：10/17。

### 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

### 交付

给同一初稿提供两种review模式：generic_review与moodcut。共享执行逻辑和预算，用具体到shot_id的证据与修改建议实现情绪专项反馈。流程参考FilmAgent，最多一次critique→revise→verify。

### 修改范围

`src/moodcut/reviewer.py`、`src/moodcut/patches.py`、`src/moodcut/prompts/review_generic.txt`、`src/moodcut/prompts/review_moodcut.txt`、`src/moodcut/prompts/review_revise.txt`、`src/moodcut/prompts/review_verify.txt`、`tests/test_reviewer.py`、`tests/test_patches.py`、`docs/review.md`。不要修改公共 client、planner、renderer、共享契约或规划提示词。

### PR 1 报告与纯补丁应用

- [x] ReviewReport逐条包含shot_id、具体证据、建议、维度和严重程度；缺ID、引用不存在、重复issue_id均拒绝。
- [x] 实现apply_patch纯函数，deepcopy后修改；只允许契约列出的字段，不删除镜头、不改beat关联、不换角色图片、不改story或tone。
- [x] 应用后调用公共validate_plan；有任意错误整体回退原plan，status=rejected，保留错误列表。
- [x] duration的调整必须保持总时长合法；只能使用manifest允许crop；不能用叙述字幕伪装已生成新动作。
- [x] 测试无意见、单条有效修改、非法字段、未知镜头、多条冲突、输入对象不变、原子回退。

### PR 2 两种提示与有界复查

- [x] generic提示覆盖剧情、自然度、目标tone和画面可实现性；不能故意不告诉generic目标tone或让其输出格式更弱。
- [x] moodcut在相同输入上要求定位“目标tone与具体台词/镜头表达之间的偏差”，提出不改剧情事实的局部建议。建议是推断，不写成客观真值。
- [x] 两模式用同一revise与verify模板、相同模型、max_output_tokens和一次循环。无意见可提前退出；报告实际调用差异。
- [x] revise产生RevisionPatch，由纯函数应用；verify只复查意见是否解决、有没有新问题，不追加第二轮修订。未解决意见留档。
- [x] 模型响应错误回退原plan并status=review_failed；不算成功修复。保存report/patch/verification/raw response，便于评审与复现。
- [x] 用FakeClient队列检查stage顺序与最多3个review请求；不要真实调用API来跑单元测试。

### 验收

目标命令：`python -m pytest tests/test_patches.py tests/test_reviewer.py -q`、`python -m moodcut review --scene tests/fixtures/scene.json --plan tests/fixtures/plan.json --assets tests/fixtures/assets.json --mode moodcut --mock --output runs/dev/review.json`。

交付一份可读修改记录：原台词、意见、修改后台词、验证状态。交付需包含可运行实现及验收证据。评审Agent的自评分不能作为最终实验成绩。

### 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
