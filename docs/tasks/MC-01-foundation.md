# MC-01 公共契约、离线骨架与集成

## 当前交付

公共客户端、验证器、CLI、缓存与三条件编排已有实现。运行入口见 README；只认领 Issue 中新增缺陷或未验收增量，避免重复搭骨架。真实模型和费用需确认后另行 pilot。

生成式增量：`src/moodcut/video_client.py` 与 `tests/test_video_client.py` 维护 OpenRouter 异步视频任务、预算预留、未知费用和 GET-only 恢复。`scripts/generate_video.py` 在付费前核对最新公开参数和价格；不复用旧文本 demo 的预算授权。请求与媒体边界见 [生成视频计划](../GENERATIVE_VIDEO_PLAN.md)，不另建文本客户端或重复实现公共验证器。

下列勾选项表示工程实现；不表示真实 API、正式实验或人工主观评价已完成。

认领模块：P1 公共基础，账号以 Issue 为准。依赖：无。首个 Draft PR：10/14；完整离线集成：10/17。MC 编号不等于 GitHub Issue 号。

## 交付

让四位队友可以用同一份数据独立开发，最后通过一个 CLI 串起来。不要等待自己写完所有基础设施后才把契约交给队友。

## 修改范围

`pyproject.toml`、`.gitignore`、`.env.example`、`.github/workflows/offline.yml`、`.github/workflows/reference-tooling.yml`、`.github/PULL_REQUEST_TEMPLATE.md`、`src/moodcut/__init__.py`、`src/moodcut/__main__.py`、`src/moodcut/client.py`、`src/moodcut/validation.py`、`src/moodcut/pipeline.py`、`configs/model.json`、`configs/render.json`、`tests/fixtures/`、`tests/test_client.py`、`tests/test_validation.py`、`tests/test_pipeline.py`、`tests/test_cli.py`、`tests/test_smoke.py`、`README.md`、`AGENTS.md`、`.agents/skills/moodcut-team/`、`docs/tasks/`、`docs/CONTRACTS.md`、`docs/REFERENCES.md`、`docs/reading/`、`references/sources.lock.json`、`references/references.bib`、`scripts/prepare_references.py`、`tests/test_prepare_references.py`、`docs/TEAM.md`。保留 .gitmessage 约定。跨模块调整按当前任务授权协调，不能用修改任务卡绕过范围。

## 已有基础

仓库已有完整离线实现、最小包配置与共享夹具；沿用现有模块。tests/test_prepare_references.py 继续保留，pytest 收集限定 tests，排除上游缓存。

## PR 1 契约与公共夹具

- [x] 将 CONTRACTS.md、协作规范与 PR 模板纳入仓库；保持 README 的项目说明、链接与配置一致。
- [x] 沿用现有 pyproject.toml，按实现补齐依赖；测试用 pytest，CLI 在 __main__.py 实现；提供 `python -m moodcut --help`。
- [x] 编写 `client.py` 的 LLMClient/FakeClient，FakeClient 消费预置响应队列并记录 stage、输入和输出上限，不联网。
- [x] 编写 `validation.py`，实现契约第4节的全部结构检查；禁止把结构检查结果叫语义正确。
- [x] 将契约 SceneInput/ShotPlan 保存为合法 `tests/fixtures/scene.json`、`tests/fixtures/plan.json`，另存 review/patch/verification 响应。生成两张有 A/B 标识的纯色测试图片，保存真实 hash 与尺寸为 `tests/fixtures/assets.json`。素材路径统一在项目根可解析；明确软件夹具非实验数据。
- [x] 添加忽略项 assets/raw/、runs/，测试夹具放 tests/fixtures，避免被现有 data/ 忽略规则吞掉。
- [x] CI 只装轻量测试依赖并跑离线 core 测试，不注入真实 key，不安装 torch/CUDA。PR 合并后向组员说明契约版本1.0。

验收命令目标：`python -m pytest tests/test_client.py tests/test_validation.py tests/test_cli.py -q`；检查非法角色、缺beat、重复shot、超时长和素材越界路径都会失败；fixture通过；FakeClient不访问网络。

## PR 2 客户端、编排与集成

OpenRouter 客户端接入已作为独立增量提供。使用方法及单实例估算预算的边界见 README 与 CONTRACTS；CLI、缓存和整体编排已接入，下列项目用于维护验收。

- [x] 实现 OpenRouterClient：模型与价格在 configs/model.json 显式配置，key来自 OPENROUTER_API_KEY；返回模型 JSON，usage/费用独立记录到 client.calls。check-client 只验证本地配置。已做离线传输与真实审查函数的接口测试；真实模型连接尚待确认模型与预算后验证。
- [x] `--mock` 默认离线；真实调用要求授权、allow-paid、max-cost-usd及价格配置同时存在。用假计费测试余额不足、价格未知、API失败与JSON失败；每个LLM阶段最多一次请求，默认无自动重试。
- [x] 实现按 scene/tone/replicate/model/prompt/schema/input hash 命名的初稿缓存；同块三个条件复用原稿，deepcopy后分别处理。禁止把M的修订拿给G做初稿。
- [x] 按 CONTRACTS 接入 plan/review/render/smoke/evaluate 命令；evaluate dry-run只列任务，不发请求。smoke fixture模式跳过实际视频渲染。
- [x] 写三条件RunRecord；render失败与review失败分开记录；输入输出token和失败请求可获得的费用都计入。未经提供的usage不编造为零。
- [x] 自查根配置与真实 API 的执行和费用边界，在 PR 中记录结论；付费 pilot 需单独确认。

验收命令目标：`python -m pytest tests/test_client.py tests/test_validation.py tests/test_pipeline.py tests/test_cli.py tests/test_smoke.py -q`、`python -m moodcut smoke --mock --output runs/smoke-01`。同块initial hash一致，条件会话隔离，失败记录不丢失，输出路径不覆盖。

## 完成标准

契约和PR1先合入；PR2集成后所有模块离线测试通过；组员不用你的key也能跑mock。没有生成效果提升也可完成工程验收；不得用mock成功当研究成功。

## 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
