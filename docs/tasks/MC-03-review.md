# MC-03 通用审查、情绪审查与局部修订

认领模块：P3 审查修订，账号以 Issue 为准。依赖：MC-01 PR1；使用共享夹具，不必等真实规划。首个 Draft PR：10/15；接入：10/17。

## 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

## 交付

给同一初稿提供两种review模式：generic_review与moodcut。共享执行逻辑和预算，用具体到shot_id的证据与修改建议实现情绪专项反馈。流程参考FilmAgent，最多一次critique→revise→verify。

## 修改范围

`src/moodcut/review/`、`src/moodcut/review/prompts/`、`tests/review/`、`docs/review.md`。模块内实现 service.py、patches.py；提示目录内实现 generic.txt、moodcut.txt、revise.txt、verify.txt。不要改公共client、planner、renderer或共享契约。

## PR 1 报告与纯补丁应用

- [ ] ReviewReport逐条包含shot_id、具体证据、建议、维度和严重程度；缺ID、引用不存在、重复issue_id均拒绝。
- [ ] 实现apply_patch纯函数，deepcopy后修改；只允许契约列出的字段，不删除镜头、不改beat关联、不换角色图片、不改story或tone。
- [ ] 应用后调用公共validate_plan；有任意错误整体回退原plan，status=rejected，保留错误列表。
- [ ] duration的调整必须保持总时长合法；只能使用manifest允许crop；不能用叙述字幕伪装已生成新动作。
- [ ] 测试无意见、单条有效修改、非法字段、未知镜头、多条冲突、输入对象不变、原子回退。

## PR 2 两种提示与有界复查

- [ ] generic提示覆盖剧情、自然度、目标tone和画面可实现性；不能故意不告诉generic目标tone或让其输出格式更弱。
- [ ] moodcut在相同输入上要求定位“目标tone与具体台词/镜头表达之间的偏差”，提出不改剧情事实的局部建议。建议是推断，不写成客观真值。
- [ ] 两模式用同一revise与verify模板、相同模型、max_output_tokens和一次循环。无意见可提前退出；报告实际调用差异。
- [ ] revise产生RevisionPatch，由纯函数应用；verify只复查意见是否解决、有没有新问题，不追加第二轮修订。未解决意见留档。
- [ ] 模型响应错误回退原plan并status=review_failed；不算成功修复。保存report/patch/verification/raw response，便于评审与复现。
- [ ] 用FakeClient队列检查stage顺序与最多3个review请求；不要真实调用API来跑单元测试。

## 验收

目标命令：`python -m pytest tests/review -q`、`python -m moodcut review --scene tests/fixtures/scene.json --plan tests/fixtures/plan.json --assets tests/fixtures/assets.json --mode moodcut --mock --output runs/dev/review.json`。

交付一份可读修改记录：原台词、意见、修改后台词、验证状态。交付需包含可运行实现及验收证据。评审Agent的自评分不能作为最终实验成绩。

## 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
