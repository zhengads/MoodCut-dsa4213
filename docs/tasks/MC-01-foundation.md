# MC-01 公共契约、客户端与集成

当前任务：[GitHub Issue #8](https://github.com/zhengads/MoodCut-dsa4213/issues/8)。先做下面未勾选的下一增量；末尾既有交付仅用于复用和回归。

首个增量建议分支：`feat/issue-8-generated-contracts`。先检查认领和活动 PR；[分支命名与迁移](../BRANCHES.md)。不在 `archive/` 继续开发。

## 下一增量：生成式公共契约与三条件入口（待实现）

**目标**：发布供 P2/P3/P4/P5 共用的生成式数据约定，再串通三条件；不重写现有客户端。

### 已核实的缺口

- `reviewer.py` 返回 `unchanged`，但 `scripts/generate_video.py:load_source` 仅接受 `applied/no_changes`，合法无修改记录会被误拒绝。
- 生成脚本目前只支持 baseline / dialogue_revision 开发对，不是完整三条件入口；没有仓库内可复用的单镜头选择入口。
- 旧结构验证固定 60–90 秒；生成记录尚未与三条件 RunRecord/评估入口接通。非台词输入相等尚未在全链路强制核对。

### 本次待办与验收

- [x] 接口小 PR：在 CONTRACTS 第6节发布 1.1 字段、签名、记录/哈希约定；`contracts.py` 提供无 I/O 的白名单、非台词比较和身份纯函数，配有离线协议夹具及回归测试。运行模式与各模块接线仍按下面未勾选项实施。
- [ ] 修复 `unchanged` 状态兼容；FakeClient 覆盖无意见、空补丁、有效补丁、rejected、review_failed，失败回退不得冒充有效修订。
- [ ] 实现生成模式的可配置镜头/总时长验证，旧 animatic 行为与旧记录兼容；不把短片强行补到 60 秒，也不暗改既有结果。
- [ ] 每个 scene/tone/replicate 只规划一次并深拷贝三份；审查前后比较去掉每镜头 dialogue 后的完整计划。动作、场景、镜头、时长、素材及未知扩展字段有变即拒绝。
- [ ] 记录共享非台词输入哈希 `shared_generation_sha256`：包括共同计划、参考图内容身份、动作/镜头/声音要求、生成模型/参数/seed 和提示模板版本。哈希规范与实现同步；condition 标签、实际台词及输出路径不进入共享哈希。实际请求另存完整哈希。
- [ ] 接通 baseline/generic_review/moodcut 的离线请求准备与记录；提供正式的单镜头选择参数。默认零网络、无需 key，显式付费标志/范围/预算仍为必要条件；未知费用停止，不自动重试 POST。
- [ ] 配对资格与失败状态分开记录：保留失败条件/账目，但不将其作为有效修订对比。P5 导出前再次检查共享输入；规划费用只计一次。

### 写入范围与依赖

公共协议归 P1：`src/moodcut/contracts.py`、`tests/test_contracts.py` 和 `tests/fixtures/generated_contract.json`；其他模块导入它，不复制哈希/白名单实现。具体当前接口与未来接线签名见 CONTRACTS 6.1 / 6.5。

主改 `src/moodcut/__main__.py`、`pipeline.py`、`validation.py`、`video_client.py`、`scripts/generate_video.py` 及对应现有测试、`docs/CONTRACTS.md`。P1 维护共享夹具；不要改 P2/P3 提示词或 P4 编译器。`configs/video.json` 由 P4 维护，传输/价格字段变更先协调。入口选项及新字段在接口 PR 中给出准确用法后，队友再接入。

第一步无依赖；接口 PR 后可与其他模块并行，最终集成依赖 P2/P3/P4/P5。离线验证：相关现有测试，以及新加的 shared hash 篡改拒绝、三条件初稿一致、单镜头零 HTTP、失败记录与预算测试。测试使用临时软件夹具，不运行实验。

### 本增量不包含

跨进程硬预算系统、正式数据集、付费生成、模型训练与主观评分。现有本地阈值不是平台硬额度，明确保留该限制。

## 既有模块与验收记录（供复用与回归）

### 当前交付

公共客户端、验证器、CLI、缓存与三条件编排已有实现。运行入口见 README；只认领 Issue 中新增缺陷或未验收增量，避免重复搭骨架。真实模型和费用需确认后另行 pilot。

生成式增量：`src/moodcut/video_client.py` 与 `tests/test_video_client.py` 维护 OpenRouter 异步视频任务、预算预留、未知费用和 GET-only 恢复。`scripts/generate_video.py` 在付费前核对最新公开参数和价格；不复用旧文本 demo 的预算授权。请求与媒体边界见 [生成视频计划](../GENERATIVE_VIDEO_PLAN.md)，不另建文本客户端或重复实现公共验证器。

下列勾选项表示工程实现；不表示真实 API、正式实验或人工主观评价已完成。

认领模块：P1 公共基础，账号以 Issue 为准。依赖：无。首个 Draft PR：10/14；完整离线集成：10/17。MC 编号不等于 GitHub Issue 号。

### 交付

让四位队友可以用同一份数据独立开发，最后通过一个 CLI 串起来。不要等待自己写完所有基础设施后才把契约交给队友。

### 修改范围

`pyproject.toml`、`.gitignore`、`.env.example`、`.github/workflows/offline.yml`、`.github/workflows/reference-tooling.yml`、`.github/PULL_REQUEST_TEMPLATE.md`、`src/moodcut/__init__.py`、`src/moodcut/__main__.py`、`src/moodcut/client.py`、`src/moodcut/validation.py`、`src/moodcut/pipeline.py`、`configs/model.json`、`configs/render.json`、`tests/fixtures/`、`tests/test_client.py`、`tests/test_validation.py`、`tests/test_pipeline.py`、`tests/test_cli.py`、`tests/test_smoke.py`、`README.md`、`AGENTS.md`、`.agents/skills/moodcut-team/`、`docs/tasks/`、`docs/CONTRACTS.md`、`docs/REFERENCES.md`、`docs/reading/`、`references/sources.lock.json`、`references/references.bib`、`scripts/prepare_references.py`、`tests/test_prepare_references.py`、`docs/TEAM.md`。保留 .gitmessage 约定。跨模块调整按当前任务授权协调，不能用修改任务卡绕过范围。

### 已有基础

仓库已有完整离线实现、最小包配置与共享夹具；沿用现有模块。tests/test_prepare_references.py 继续保留，pytest 收集限定 tests，排除上游缓存。

### PR 1 契约与公共夹具

- [x] 将 CONTRACTS.md、协作规范与 PR 模板纳入仓库；保持 README 的项目说明、链接与配置一致。
- [x] 沿用现有 pyproject.toml，按实现补齐依赖；测试用 pytest，CLI 在 __main__.py 实现；提供 `python -m moodcut --help`。
- [x] 编写 `client.py` 的 LLMClient/FakeClient，FakeClient 消费预置响应队列并记录 stage、输入和输出上限，不联网。
- [x] 编写 `validation.py`，实现契约第4节的全部结构检查；禁止把结构检查结果叫语义正确。
- [x] 将契约 SceneInput/ShotPlan 保存为合法 `tests/fixtures/scene.json`、`tests/fixtures/plan.json`，另存 review/patch/verification 响应。生成两张有 A/B 标识的纯色测试图片，保存真实 hash 与尺寸为 `tests/fixtures/assets.json`。素材路径统一在项目根可解析；明确软件夹具非实验数据。
- [x] 添加忽略项 assets/raw/、runs/，测试夹具放 tests/fixtures，避免被现有 data/ 忽略规则吞掉。
- [x] CI 只装轻量测试依赖并跑离线 core 测试，不注入真实 key，不安装 torch/CUDA。PR 合并后向组员说明契约版本1.0。

验收命令目标：`python -m pytest tests/test_client.py tests/test_validation.py tests/test_cli.py -q`；检查非法角色、缺beat、重复shot、超时长和素材越界路径都会失败；fixture通过；FakeClient不访问网络。

### PR 2 客户端、编排与集成

OpenRouter 客户端接入已作为独立增量提供。使用方法及单实例估算预算的边界见 README 与 CONTRACTS；CLI、缓存和整体编排已接入，下列项目用于维护验收。

- [x] 实现 OpenRouterClient：模型与价格在 configs/model.json 显式配置，key来自 OPENROUTER_API_KEY；返回模型 JSON，usage/费用独立记录到 client.calls。check-client 只验证本地配置。已做离线传输与真实审查函数的接口测试；真实文本开发样例已执行，生成视频质量尚未验收。
- [x] `--mock` 默认离线；真实调用要求授权、allow-paid、max-cost-usd及价格配置同时存在。用假计费测试余额不足、价格未知、API失败与JSON失败；每个LLM阶段最多一次请求，默认无自动重试。
- [x] 实现按 scene/tone/replicate/model/prompt/schema/input hash 命名的初稿缓存；同块三个条件复用原稿，deepcopy后分别处理。禁止把M的修订拿给G做初稿。
- [x] 按 CONTRACTS 接入 plan/review/render/smoke/evaluate 命令；evaluate dry-run只列任务，不发请求。smoke fixture模式跳过实际视频渲染。
- [x] 写三条件RunRecord；render失败与review失败分开记录；输入输出token和失败请求可获得的费用都计入。未经提供的usage不编造为零。
- [x] 自查根配置与真实 API 的执行和费用边界，在 PR 中记录结论；付费 pilot 需单独确认。

验收命令目标：`python -m pytest tests/test_client.py tests/test_validation.py tests/test_pipeline.py tests/test_cli.py tests/test_smoke.py -q`、`python -m moodcut smoke --mock --output runs/smoke-01`。同块initial hash一致，条件会话隔离，失败记录不丢失，输出路径不覆盖。

### 完成标准

契约和PR1先合入；PR2集成后所有模块离线测试通过；组员不用你的key也能跑mock。没有生成效果提升也可完成工程验收；不得用mock成功当研究成功。

### 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
