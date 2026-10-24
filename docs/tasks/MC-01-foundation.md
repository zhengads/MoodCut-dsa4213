# MC-01 公共契约、客户端与集成

Latest authorized v3 trial completed three actual videos with the existing pipeline and automatic private retention for all nine text replies. Cost $0.75277694 reconciled exactly; no retry/manual dialogue. Both first-round writers declared all feedback addressed, with no actor confirmation or second round. [Actual result](../pilots/anna-elsa-actor-v3-captured.md). Earlier failures are unchanged; human listening/viewing remains pending, PR #52 unmerged, #8/#9 open.

PR #52 offline diagnostics: the existing text client retains private HTTP bytes/model strings before parsing, records envelope/content error kinds and safe positions, and preserves known/unknown accounting. Pipeline and CLI capture automatically; direct library callers select a capture root. Original failed trials and missing historical content remain unchanged. [Contract and acceptance](../pilots/text-response-diagnostics.md). No paid calls; PR unmerged, #8/#9 open.

Latest separately authorized per-shot v3 trial (2026-10-24): [actual result](../pilots/anna-elsa-actor-v3-shot.md). Generic returned one valid per-shot dialogue covering three actor opinions; emotional writer content failed strict JSON-object parsing. Nine text requests cost $0.00291790, individually server-verified and matched to this attempt's account delta. No video, confirmation, second round, retry or handwritten fallback. Invalid reply text is not retained/provider-retrievable, so the exact JSON subtype is unknown. Earlier paid and offline records remain intact; PR #52 stays unmerged and #8/#9 open.

Offline correction in the same PR #52: v3 writers now submit one complete dialogue per shot ID, with derived atomic patches and preserved raw replies. Both conditions/rounds share the contract; historical failed results stay unchanged and no paid rerun occurs. [Diagnosis and acceptance](../pilots/anna-elsa-v3-shot-contract.md). #8/#9 remain open.

Latest actual v3 development attempt (2026-10-24): [trial record](../pilots/anna-elsa-actor-v3.md). Nine real text calls, known/reconciled total $0.00281304, stopped on conflicting same-shot writer edits before video preparation. No confirmations/second round, paid retries, new video or human score. This does not test final-disagreement video quality. Existing artifacts remain unchanged; #8/#9 stay open.

## Current bounded negotiation increment (2026-10-24)

PR #48 is merged. Explicit `actor_self_review_v3` supersedes strict v2 for the newly approved bounded workflow: both reviewed conditions get at most two writer/confirmation rounds, with final valid disagreement preserved and allowed to prepare video. Hard errors still block. The source loader rechecks both rounds, exact candidate/owner/issue bindings, summaries and routed call order; P5 accepts consistent v3 summaries while retaining qualification/export rechecks and unchanged scores/denominators. No paid run, new video, human score or formal inclusion is authorized. Historical results and v2 behavior remain intact; #8/#9 remain open. See [current method](../ACTOR_REVIEW_METHOD.md).

Earlier entries below describe their original implementation stage; their draft/unmerged references are historical snapshots.

The offline `actor_self_review_v2` increment in PR #48 routes `actor_confirm` to review, binds owner/issue/candidate decisions at source/request boundaries and refuses incomplete or disputed consent. Both review conditions share the mechanism and budget rules. Historical v1/global results are unchanged; [team video links](../pilots/anna-elsa-videos.md) now point to exact repository release attachments. No new paid run or merge is authorized by this increment.

The subsequent separately authorized [actual actor pilot](../pilots/anna-elsa-actor.md) completed eight text calls and two distinct videos covering three conditions for $0.50248398, with exact key reconciliation. Generic retained/reused baseline; moodcut retained one unaddressed actor opinion with a problematic explanation. Human acceptance is pending, historical results are intact, and PR #48 stays unmerged. The offline implementation record below remains its original scope.

### Actor protocol integration (2026-10-24)

PR #48 now also contains the explicitly authorized [actor self-review increment](../ACTOR_REVIEW_METHOD.md). `actor_critique` routes to the review role, `actor_revise` to the planning/screenwriting role. The existing budget, clients, compiler and source gates are reused. Source loading rechecks actor ownership, full feedback disposition, the actual dialogue patch, protocol/prompt identity and truthful lack of final actor approval. Mixed review protocols are rejected at comparison boundaries. This increment is offline only; original global-review outputs remain unchanged, #8/#9 stay open and the PR remains unmerged.

### Role-routed real-Agent pilot (2026-10-24)

The authorized [Anna/Elsa pilot](../pilots/anna-elsa-agent.md) separates Gemini planning from a common DeepSeek model for both review branches, with one $0.10 text ceiling and a $1.00 combined ceiling. Necessary wiring reuses the original clients/pipeline, adds explicit reasoning control and truthful role-policy/call-model records, and stops subsequent calls on failure/unknown cost. See [contract](../CONTRACTS.md#role-routed-text-pilot-2026-10-24). No prompt or evaluation changes, handwritten dialogue fallback, retries or formal sample expansion are authorized. Actual execution evidence is recorded in the linked pilot; #8/#9 stay open.

### HeyGen pilot adapter and real-video result (2026-10-24)

The existing branch/PR adds HeyGen 768p reference pricing with verified provider discount, fixed native audio without an HTTP audio toggle, disabled prompt enhancement and `<Picture N>` labels. After the first HTTP 400 Content-Type rejection, a separately authorized run with byte-verified inline PNG references completed all three five-second conditions: three POSTs, $0.25 each, $0.75 total, no automatic retry, text-model request or reserve spending. Returned charges match the later read-only key usage delta. All three raw videos have audio and passed local media checks; user listening/viewing acceptance remains pending. The earlier failed request and unknown cost remain preserved. See [pilot record](../pilots/umbrella-single-shot.md) and [adapter contract](../CONTRACTS.md#heygen-pilot-adapter-2026-10-24). Results stay in draft PR #45; Issues #8 and #9 remain open. No new tool or transport is introduced. Older task sections below retain their original scope and dates.

当前任务：[GitHub Issue #8](https://github.com/zhengads/MoodCut-dsa4213/issues/8)。先做下面未勾选的下一增量；末尾既有交付仅用于复用和回归。

### 当前修复：视频失败诊断保存（2026-10-23）

分支`fix/issue-8-video-error-receipts`。PR #44后已授权的真实固定台词试跑仅尝试首个POST，未取得ID/费用，按约停止，无视频；详情及不可追溯的信息见[试跑单的首次提交诊断](../pilots/umbrella-single-shot.md#首次真实提交与本次诊断2026-10-23)。本增量只在原video_client保存脱敏的HTTP状态、服务端原因、失败阶段和受控传输/响应错误，pipeline最终记录透传，原回执/请求/账目不变。离线回归；不重发付费请求、不增加日志框架，#8/#9继续开放。下文素材/接线状态保留为先前交付记录。

本次#8 PNG交付、#9更新试跑单，分支：`feat/issue-8-png-delivery`；离线素材适配已随PR #43合入。三条件任务执行接线已随PR #41合入。先检查认领和活动 PR；[分支命名与迁移](../BRANCHES.md)。不在 `archive/` 继续开发。

### 当前PNG交付与请求重编译（2026-10-23）

分支 `feat/issue-8-png-delivery`。#8已用本项目素材预发布附件交付两张PNG及许可/署名，公开无认证GET远端字节/像素核对通过；原P1/P2/P3/P4在新目录重编译三条件原首镜头，保留软件来源及仅台词差异。#9同步[试跑单v3](../pilots/umbrella-single-shot.md)和[交付清单](../../assets/pilots/umbrella-png-delivery.json)。不新增生产代码/通用工具；账目/余额及运行批准后优先获取真实成片与人工证据。当前无付费API/评分，#8/#9保持开放。下节v2地址缺口为历史记录。

### 当前素材离线适配（2026-10-23）

按明确选择将sigils-people固定版本cn-02/cn-04绑定林/博；原AVIF、完整肖像许可和PNG留在忽略目录。保留来源/署名/XMP，核对原始/转换/解码RGB哈希；新增脚本复用原下载校验、素材构建器与P4编译器，默认本地、--check只读、--fetch仅固定公开来源。三条件共同输入/原首镜头索引及仅台词差异已离线核对，手写来源/mock声明保留。详见[试跑单v2](../pilots/umbrella-single-shot.md)和[credits](../pilots/umbrella-sigils-credits.md)。PNG交付URL仍为占位，历史账目/余额及全部真实运行批准未完成，不调用付费API；#8/#9继续开放。下节v1占位图核对保留为历史交付。

### 当前试跑输入/费用核对（2026-10-23）

复用原编译器、视频成本函数和公开免费目录，核对[还伞单镜头提议](../pilots/umbrella-single-shot.md)：首镜头原索引0、4秒、相同共同设置且三版只改台词。新Seedance设置仅为提议，不改历史Wan记录/哈希或默认config；占位图/URL不能当真实人物输入。三段报价$0.9072，首选额度提议$1.10，历史unknown及当前余额不补零；真实P2/P3文本扩展另批。只做软件验证，不调用付费API，#8/#9保持开放。

### 当前三条件任务执行接线（2026-10-23）

本增量分支 `feat/issue-8-generated-execution`。execute-generated默认离线；显式HTTP执行复用原客户端/P1账目/P4检查包，原始请求三条件顺序执行、合法同请求复用，失败/中断/未知消费停止。GET-only恢复复制旧回执到新目录，费用核清后显式继续仅提交未尝试镜头，累计历史视频费用；父快照仅允许一个HTTP后继。准确接口见CONTRACTS 6.17。只用模拟传输和现有软件视频验收；真实试跑/人工质量与整体任务仍未完成，#8/#9保持开放。

## 生成式三条件入口（离线链路及盲评接线已实现，真实任务待完成）

**目标**：发布供 P2/P3/P4/P5 共用的生成式数据约定，再串通三条件；不重写现有客户端。

### 当前生成状态汇总配合（2026-10-23）

P1现有failed/interrupted/prepared_offline/in_progress等记录及镜头/远端状态已足够；本增量不改状态机、回执映射或账目。#8以实际装配器+现有evaluate的回归确认新generation汇总自动透传，并区分媒体失败、待拼接与提供商completed。完整接口见CONTRACTS 6.16，执行接线见6.17，真实试跑未授权。

### 已有盲评接线（6.15）

P1必要改动为evaluate的`--pricing-config`与生成式独立入口路由；P5实现导出/评分边界重检，复用已有P1账目和P4材料，不新增客户端或账本。仅完整最终block可进入此路径，原始账目查看保持兼容。接口见CONTRACTS 6.15；真实任务及整体待办仍未完成。

P1 `recheck_generated_records` 复用已有装配计算和P4编译器；P5 `qualify_generated_records` 输出独立的逐条件资格报告，CLI为 `qualify-generated-records`。源记录/账目/人工表不改，未知费用和失败全部保留，generated盲评/ratings须走6.15的独立重检入口。验收使用现有软件产物，不调用API；整体待办不因本增量自动完成，#8/#9仍保持开放。详见CONTRACTS 6.14。

### 已核实的缺口

- 已修复 `unchanged` 来源兼容：旧开发对入口接受合法无修改记录，仍拒绝失败回退及“标记无修改但计划改变”的来源。
- 旧scripts/generate_video.py保留开发对；新run --output-mode generated已支持已有三条件脚本的离线入口与单镜头选择。P4正式编译器已在PR #34合入，本地检查材料已在PR #35合入；三条件任务执行接线见6.17，真实试跑仍待批准和验收。
- 公共验证器/pipeline编排及离线CLI边界已支持1.1/generated；P2/P3/P4实际模块的离线联调和P5离线资格报告已实现；盲评导出/评分接线已实现（6.15）；执行接线见6.17，真实试跑未授权。软件测试不当成模型效果验收。

### 整体待办与验收（含真实试跑，当前工程交付见上节）

- [x] 接口小 PR：在 CONTRACTS 第6节发布 1.1 字段、签名、记录/哈希约定；`contracts.py` 提供无 I/O 的白名单、非台词比较和身份纯函数，配有离线协议夹具及回归测试。运行模式与各模块接线仍按下面未勾选项实施。
- [x] 修复 `unchanged` 状态兼容；FakeClient 覆盖无意见、空补丁、有效补丁、rejected、review_failed，失败回退不得冒充有效修订。
- [x] 实现生成模式的可配置镜头/总时长验证，旧 animatic 行为与旧记录兼容；不把短片强行补到 60 秒，也不暗改既有结果。
- [x] pipeline生成模式复用一次规划/缓存、深拷贝三份并冻结初稿；调用公共非台词检查，动作、场景、镜头、时长、素材及未知扩展字段变化即拒绝。依赖真实接线另由P2/P3完成，当前以软件替身验收边界。
- [x] 脚本编排保存 `shared_generation_sha256`、initial/final完整哈希及可重算输入，包括共同计划、参考图内容身份、声音/模型/参数/seed和模板身份；台词与输出位置不进入共享哈希。精确参数和记录见CONTRACTS 6.7。
- [x] P1离线入口与单镜头边界：读取并核对6.7来源，调用6.5编译接口，验证请求/报价并按原索引选择jobs，保存request_sha256和requests/prepared_offline产物。用明确P4软件替身验收，缺真实接口时明确失败；不调用付费API。
- [x] P1本地回执/费用装配边界：assemble-generated-records读取6.8目录与本地脱敏回执/媒体证据，分开准备/进行/失败/中断/文件完成，重新探测A/V与时长；保留未知费用/旧回执计数缺失，规划计一次、合法同请求复用不重复计费。契约/用法见6.9，tests/test_cli.py与test_video_client.py使用明确软件夹具；不代表真实模型或P5资格已验收。
- [ ] 接通真实P2/P3/P4后的baseline/generic_review/moodcut请求准备联调与实际任务记录。实际编译器、离线联调及6.17执行接线已实现，真实试跑未授权；脚本/请求prepared不当成视频完成。付费仍需显式授权/范围/预算，未知费用停止，不自动重试POST。
- [ ] 配对资格与失败状态分开记录：保留失败条件/账目，但不将其作为有效修订对比。P5 导出前再次检查共享输入；规划费用只计一次。

### 写入范围与依赖

公共协议归 P1：`src/moodcut/contracts.py`、`tests/test_contracts.py` 和 `tests/fixtures/generated_contract.json`；其他模块导入它，不复制哈希/白名单实现。具体当前接口与未来接线签名见 CONTRACTS 6.1 / 6.5。

本次已实现边界见CONTRACTS 6.7及tests/test_pipeline.py：一次规划/缓存、条件隔离、非台词越权与身份篡改拒绝、unchanged、失败/未知费用保留。P2/P3依赖替身明确标为软件测试，不补写队友模块，不静默降级旧模式。

离线CLI与单镜头选择见CONTRACTS 6.8、tests/test_cli.py；复用prepare_generated_run。来源/编译失败不写成功产物，所有已有结果保留，P4模块不在本任务代写。

本地记录装配见CONTRACTS 6.9，复用pipeline.assemble_generated_records；只读本地回执、明确复用声明及已有媒体检查，绝不调用generate/resume。新回执记录下载与重定向GET；旧回执不完整计数为null。生成记录的not_checked/ineligible不能当有效比较，CLI生成式盲评/ratings须走6.15的独立重检入口。6.17执行接线已通过模拟验收，真实试跑和人工质量验收仍待批准；不重复写资格/盲评模块。

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
