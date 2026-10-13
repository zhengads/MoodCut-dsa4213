# MC-01 公共契约、离线骨架与集成

负责人：P1 / @zhengads。评审：P2；预算和执行逻辑由 P3 补审。依赖：无。首个 Draft PR：10/14；完整离线集成：10/17。此编号不是远端 Issue 号。

## 交付

让四位队友可以用同一份数据独立开发，最后通过一个 CLI 串起来。不要等待自己写完所有基础设施后才把契约交给队友。

## 修改范围

`pyproject.toml`、`.gitignore`、`.env.example`、`.github/workflows/offline.yml`、`.github/PULL_REQUEST_TEMPLATE.md`、`src/moodcut/__init__.py`、`src/moodcut/__main__.py`、`src/moodcut/cli.py`、`src/moodcut/core/`、`fixtures/`、`tests/core/`、`tests/test_smoke.py`、`README.md`、`TASKS.md`、`AGENTS.md`、`START_HERE.md`、`.agents/skills/moodcut-team/`、`issues/`、`docs/CONTRACTS.md`、`docs/REFERENCES.md`、`docs/reading/`、`references/sources.lock.json`、`references/references.bib`、`scripts/prepare_references.py`、`tests/tooling/`、`TEAM_HANDOFF.md`。保留 .gitmessage 约定。任务卡调整需相关负责人确认，不能用修改任务卡绕过现有范围。

## 已有基础

仓库已提供协作规则、参考资料锁定清单和 prepare_references 工具。沿用这些文件，按需修正；本任务仍需实现运行骨架、FakeClient 与公共夹具。现有 `tests/tooling/` 是资料工具测试，继续保留。pytest 收集限定 `tests/`，排除上游参考缓存。

## PR 1 契约与公共夹具

- [ ] 将 CONTRACTS.md、协作规范与 PR 模板纳入仓库；保持 README 的项目说明、链接与配置一致。
- [ ] 建 Python 3.11 的 src-layout 包，测试用 pytest；提供 `python -m moodcut --help`。
- [ ] 编写 `core/client.py` 的 LLMClient/FakeClient，FakeClient 消费预置响应队列并记录 stage、输入和输出上限，不联网。
- [ ] 编写 `core/validation.py`，实现契约第4节的全部结构检查；禁止把结构检查结果叫语义正确。
- [ ] 将契约 SceneInput/ShotPlan 保存为合法 `fixtures/scene.json`、`fixtures/plan.json`，另存 review/patch/verification 响应。生成两张有 A/B 标识的纯色测试图片，保存真实 hash 与尺寸为 `fixtures/assets.json`。素材路径统一在项目根可解析；明确软件夹具非实验数据。
- [ ] 添加忽略项 local_assets/、runs/，测试夹具放 fixtures，避免被现有 data/ 忽略规则吞掉。
- [ ] CI 只装轻量测试依赖并跑离线 core 测试，不注入真实 key，不安装 torch/CUDA。PR 合并后向组员说明契约版本1.0。

验收命令目标：`python -m pytest tests/core -q`；检查非法角色、缺beat、重复shot、超时长和素材越界路径都会失败；fixture通过；FakeClient不访问网络。

## PR 2 客户端、编排与集成

- [ ] 实现环境变量配置的真实 LLMClient；模型ID必须显式配置，key来自环境；输出 JSON 与使用量通过统一接口返回/记录。不把任何人自己的 client 散落到模块里。
- [ ] `--mock` 默认离线；真实调用要求授权、allow-paid、max-cost-usd及价格配置同时存在。用假计费测试余额不足、价格未知、API失败与JSON失败；每个LLM阶段最多一次请求，默认无自动重试。
- [ ] 实现按 scene/tone/replicate/model/prompt/schema/input hash 命名的初稿缓存；同块三个条件复用原稿，deepcopy后分别处理。禁止把M的修订拿给G做初稿。
- [ ] 按 CONTRACTS 接入 plan/review/render/smoke/evaluate 命令；evaluate dry-run只列任务，不发请求。smoke fixture模式跳过实际视频渲染。
- [ ] 写三条件RunRecord；render失败与review失败分开记录；输入输出token和失败请求可获得的费用都计入。未经提供的usage不编造为零。
- [ ] 为根配置与真实API逻辑请求额外评审；付费pilot不属于此Issue的默认授权。

验收命令目标：`python -m pytest tests/core tests/test_smoke.py -q`、`python -m moodcut smoke --mock --output runs/smoke-01`。同块initial hash一致，条件会话隔离，失败记录不丢失，输出路径不覆盖。

## 完成标准

契约和PR1先合入；PR2集成后所有模块离线测试通过；组员不用你的key也能跑mock。没有生成效果提升也可完成工程验收；不得用mock成功当研究成功。
