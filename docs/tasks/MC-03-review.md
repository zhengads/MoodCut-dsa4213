# MC-03 通用审查、情绪审查与局部修订

当前任务：[GitHub Issue #23](https://github.com/zhengads/MoodCut-dsa4213/issues/23)。先做下面未勾选的下一增量；末尾既有交付仅用于复用和回归。

首个增量建议分支：`fix/issue-23-dialogue-review`。先检查认领和活动 PR；[分支命名与迁移](../BRANCHES.md)。不在 `archive/` 继续开发。

## 下一增量：在审查源头强制只改台词（待实现）

**目标**：generic_review 和 moodcut 共享同一修改能力，真正复查最终采用的台词脚本。

### 已核实的缺口

- 当前补丁和提示仍允许 dialogue/narration/crop/duration；视频编译器事后丢弃非台词改动，投影后的脚本没有独立复查。
- 已有真实开发输出因同一 shot 多条 edit 被拒绝：`edits[3]: conflicting or duplicate edit`。需要离线复现，不放宽重复/冲突拒绝规则。

### 本次待办与验收

- [ ] 采用 P1 发布的显式生成模式/字段白名单；在 review prompt、revise、补丁验证三处限制 `set` 只能含 dialogue。保留旧 animatic 合法补丁兼容，不能全局悄悄改变旧实验行为。
- [ ] 两类审查接收同一故事/目标 tone/共同初稿，使用相同模型、输出上限、最多一次 critique→revise→verify。仅审查准则不同；允许无意见提前退出并记录实际调用差异。
- [ ] revise 输入按 shot 汇集全部意见，输出一个 shot 最多一条 edit；保留现有有效 issue_id 引用，额外关联信息不能破坏旧 schema。verify 仍逐条覆盖原 report 的所有 issue_id，不通过删掉意见规避重复问题。
- [ ] verify 接收实际会送入生成器的最终 dialogue-only 计划；不先复查多字段候选再把它投影成另一个脚本。旧投影路径保留为开发派生记录，不升级为正式复查通过。
- [ ] 越权修改动作、narration、crop、duration、镜头顺序/数量或新扩展字段时整体拒绝、保留原稿与诊断；输入对象不变。
- [ ] FakeClient 回归：同一镜头多意见汇集、重复 edit 被拒绝、非法非台词字段、无意见 `unchanged`、原子回退、verify 覆盖所有原意见且看到实际最终脚本。只使用脱敏/自制最小软件夹具，不依赖成员本地 runs。

### 写入范围与依赖

接入协议固定为 CONTRACTS 6.1 / 6.2 / 6.5：使用 `allowed_patch_fields(output_mode=...)` 与 `assert_dialogue_only_revision`，review 的 mode 和输出的 output_mode 不混用。Report/Patch 外壳保留1.0，不自行塞入新字段；verify 看到实际最终脚本。旧函数尚未接线，由本任务追加约定参数。

`src/moodcut/reviewer.py`、`patches.py`、`src/moodcut/prompts/review_*.txt`、`tests/test_reviewer.py`、`tests/test_patches.py`、`docs/review.md`。字段白名单/生成模式接口先与 P1 对齐；不修改规划提示词、公共验证器或媒体编译器。可立即补已知失败的离线复现，生成式接入等 P1 接口 PR。

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
