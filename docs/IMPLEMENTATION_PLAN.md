# MoodCut 实施与验收

目标：将 MovieAgent 风格规划、台词审查修订与人物参考图引导的视频/声音生成连成可验收流程。Python 3.11、Pillow、FFmpeg/ffprobe；通过服务接口生成视频，不要求本地 GPU 或上游模型权重。

既有静态 animatic 是文本流程诊断工具。新增生成式路径与离线验收见 [GENERATIVE_VIDEO_PLAN.md](GENERATIVE_VIDEO_PLAN.md)：脚本、请求准备、异步任务和实际音视频拼接已接入，真实人物一致性、中文对白与画面质量尚未经过付费 pilot 验收。以下既有模块/命令的 60–90 秒约束仍只适用于原 animatic 契约，不作为新成片的时长要求。

## 下一阶段入口

### 2026-10-23：#8 PNG交付与请求重编译，#9试跑单v3

分支 `feat/issue-8-png-delivery`。复用现有GitHub素材预发布附件，交付cn-02/cn-04 PNG及同等公开的署名/完整许可，无认证GET核对远端字节、尺寸和像素。使用现有P1/P2/P3软件回放及P4在新目录重编译三条件原首镜头请求，保留旧身份和全部失败/费用边界；记录见[试跑单v3](pilots/umbrella-single-shot.md)和[交付清单](../assets/pilots/umbrella-png-delivery.json)。不新增生产代码、托管服务、执行框架或测试框架，不调用付费API。PNG地址缺口已解除；剩余主要是账目/余额、运行价格/预算与负责人确认后的真实试跑。

**工程投入判断与下一步：已出现离线工程多、真实反馈少的失衡。** #37–#43连续七个增量主要完善资格、评分接线、状态、执行和输入准备，已有872项测试及116个子测试，但仍无成功验收的人物生成成片。必要的身份、费用和失败保留有价值；这些测试不能回答中文台词、口型、递伞动作或情绪审查是否有效。完成本次交付后冻结通用工具范围，仅针对真实运行暴露的具体阻塞做最小修复。

建议后续按既有待批准协议取得证据：先在费用/范围获准后做已定义的单镜头三版本技术试跑并实际听看；技术可用后，再另批真实P2/P3规划与审查，用实际模型输出重新冻结三条件，保留全部失败、未修改和消费；最后按团队确认的故事/重复数/观看者安排做独立盲评，同时报告效果、覆盖与成本。三句手写台词或一组4秒视频只能作为开发技术证据，不支撑方法优越性或跨镜头连续性主张。当前不新建正式数据集、不改变评分口径、不运行上述实验。

### 2026-10-23：#8 合成人物离线适配，#9 试跑单v2

分支 `feat/issue-8-sigils-offline-assets`。按已选cn-02/cn-04下载固定公开来源并另存PNG；保留完整许可、署名/XMP与转换前后/解码RGB哈希。新增本地适配/只读核对脚本，复用原素材校验和编译器；完整软件回放与单镜头请求证明共同输入一致、仅台词不同，旧源/旧导出文件不变。来源、署名、命令和交付URL缺口写入[试跑单v2](pilots/umbrella-single-shot.md)。不上传图片、不改默认模型/提示词/生产执行代码、不调用付费API；真实运行批准字段保持false/null，#8/#9继续开放。下节为已合入PR #42的v1历史交付。

### 2026-10-23：#9 具体试跑单，#8 输入/费用核对

分支 `docs/issue-9-concrete-pilot`。交付[还伞单镜头试跑单](pilots/umbrella-single-shot.md)、非执行配置的候选JSON及公开价格快照；不改默认模型/实验配置、提示词或生产代码，不运行付费API或生成素材。

- [x] 核对已有还伞完整计划、首镜头原索引/4秒、三版逐字台词、手写软件来源和人物占位图；不把新模型设置重贴到旧block，不隐藏example.invalid、历史拒绝及unknown费用。
- [x] 选定Seedance 2.0 Mini/720p提议，按原成本函数核算三段报价$0.9072；首选固定软件输入技术预检额度$1.10（新文本0），真实P2/P3另批扩展总额提议$1.20。定义人工/文件/账目门禁、失败停止与单镜头未覆盖项，批准字段保持false/null。
- [x] 通过原P1/P2/P3软件回放/P4编译与定向成本回归核对候选、设置/仅台词差异、预算和来源不变；检查公开内容、链接及清单不可启动状态，完成PR材料准备，提交后不合并。#8/#9保持开放。

验收：实际P1/P2/P3+FakeClient九槽位软件回放、P4完整编译后原首镜头选择、三个不同请求及仅dialogue差异均核对；报价$0.9072，文本扩展输入字节代理＋最大输出预留$0.0471356，不当真实消费/未来保证。默认execute-generated输出未提交/空人工表，禁止构造真实客户端/目录查询，文档清单作为preparation被拒绝。8份原快照身份一致，114个源/旧导出文件未变，验证阶段网络尝试0；公开免费目录价格核对在离线验证前完成，未查询密钥/余额。已有定向成本/编译回归9项通过（3.46s）；首轮因命令未带已有FFmpeg路径出现1项setup错误，修正环境后全部通过，未改代码。8份文档/JSON、49个本地Markdown链接、JSON/预算一致性、公开隐私及diff检查通过；不重复运行与本次文档增量无关的本地完整视频回归，最终head CI在PR跟踪。

### 2026-10-23：#8 三条件任务执行接线，#9 试跑协议（离线验收完成）

分支 `feat/issue-8-generated-execution`。复用1.1请求准备、原视频客户端、P1账目及P4检查包，不改规划/审查/编译提示、评分或正式纳入规则。

- [x] `execute-generated` 默认离线收集；显式视频HTTP门禁、完整所选范围报价、实际镜头时长/实时目录预检和P4重编译身份核对。三条件顺序执行、同块同镜头同请求复用、先留证后POST，异常/未知消费停止，未执行镜头仍留在全量记录。
- [x] 选定单任务GET-only恢复到新回执副本；独立显式继续仅提交未尝试镜头，扣除链路已知视频消费、复用已完成来源，不补交丢失POST。每个父快照仅允许一个HTTP后继，已有记录/回执不覆盖。
- [x] 模拟传输/回执及现有软件视频验收：完整/单镜头、失败/中断/恢复/继续、未知费用、预算/身份/目录门禁，到检查、资格及盲评导出；检查源文件不变和零真实网络。
- [x] 在现有 `docs/evaluation.md` 协议表整理最小试跑提议和待批准项；同步契约、CLI和过时入口描述。完成离线回归、自查和PR材料准备，提交后先不合并，#8/#9保持开放。

验收：本地完整859项及116子测试通过（700.38s）；最后父回执预检/复制副本加固后的29项执行回归通过（103.19s），两项保护在内存停用时均失败，恢复后通过。较早客户端/CLI组合182项通过。最终实现复用已有保存的软件视频，通过检查→资格→3个匿名视频导出/空评分导入；4次模拟POST、2个合法复用条目；GET恢复新增POST为0，显式继续新增3次而累计账目仍为4次。失败/未知费用及全量记录保留；114个源/旧导出文件哈希未变，审计钩子下真实网络尝试0，人工表仍空。原回执/状态/媒体/复用/账目主体AST不变，33份缓存参考、47个本地文档链接、语法/隐私/diff检查通过。最终head的全量CI在PR中跟踪，不把加固前的完整回归当成最终head全部测试。

本增量不调用付费API、真实视频提交/恢复/下载或GPU，不改变正式故事/样本/评分口径。软件传输的金额和媒体不充作真实账单或模型质量；真实试跑仍需模型、范围和预算的独立批准。

### 2026-10-23：#9 生成状态细分汇总（Refs #8，离线验收完成）

复用P1现有状态与最终账目，不改回执映射、评分公式、资格/正式纳入规则或费用。当前生成失败/中断/未提交容易只落在旧render_pending_or_skipped_runs，本增量在总体和各条件单列生成状态、镜头状态与保存的远端状态；旧渲染指标保留。

- [x] P5：新增独立generation汇总，明确生成记录分母，区分未开始、离线未提交、进行中、文件已装配待人工检查、失败、中断和未知；补充待拼接、部分未提交及失败原因，记录镜头级混合状态/声明复用，未知不推成零调用。
- [x] #8必要接线：核对原CLI和generated导出/评分路径均复用汇总；若无接口缺口不改pipeline或另建状态机。软件回归覆盖真实装配器的失败/中断/未提交、媒体失败、混合镜头、旧记录/未知、空分母及全量账目不变。
- [x] 现有保存软件产物CLI验收、针对性及完整离线回归、来源不变/文档/隐私检查和PR材料准备；提交后#8/#9保持开放，不合并。

验收：完整离线832项测试及116个子测试通过（735.78s），针对性23项通过；新增12项纯汇总回归，另扩展已有P1/CLI和导出/评分回归。已有保存synthetic产物正常三条件均计入待人工检查；临时副本明确标注为软件状态投影，失败/中断/未提交经原装配器及CLI核对，原账目和未知费用保持，账目重检通过。106个源文件哈希未变；旧匿名导出映射可读且8个导出文件未变；网络审计钩子下零连接尝试，无真实人工评分。旧评分/覆盖/用量主体AST在排除新增generation字段后完全一致，33份缓存参考、44个本地文档链接、语法、隐私和diff检查通过。

只使用现有软件夹具及产物，不调用付费API，不提交/恢复/下载视频，不开展GPU或正式实验，不填写真实人工评分。

### 2026-10-23：#9 生成式盲评导出和评分接线（Refs #8，离线验收完成）

复用 6.14 资格核对、现有匿名复制器及评分公式。只接完整最终 block；显式本地价格配置，每次导出/评分重新核对来源。仅完整三条件软件资格通过的块进入匿名材料，其余全部原记录仍进入覆盖、费用和逐条件诊断；这是软件完整性门禁，不替团队批准正式纳入规则。

- [x] P5：在复制前后核对来源/目标字节；公开目录仅匿名视频、索引和空表，私有清单绑定最终 block、镜头范围、映射和实际导出文件。失败复制不发布半成品。
- [x] P5/P1：evaluate 显式价格参数及生成式导出/评分入口；评分必须持匹配私有映射并重检导出副本。旧 animatic 兼容，不允许低层公开函数绕过生成资格；复用原评分与全量分母，原 block 账目逐块只列一次。
- [x] 测试：正常导出/软件评分算术、来源及副本/映射篡改、失败/未知费用/无评分/零导出、单镜头、多块与重复输入；保存产物离线验收和源文件不变检查。
- [x] 文档：契约、任务卡、README及协作门禁更新到新入口；完成离线回归、自查及 PR 材料准备，提交后不合并，#8/#9 保持开放。

验证：本地完整回归815项及116个子测试通过（578.18s）。后续边界加固的最终19项接线回归通过（331.72s），单镜头导出/导入及原账目目录兼容用例分别再次通过；PR的CI另完整重验最终版本。评分主体AST与旧实现一致。现有保存软件产物导出3个匿名视频、以空评分完成导入核对，106个源文件和原账目不变；审计钩子下网络尝试0，未产生真实人工评分。33份缓存参考、43个本地文档链接、语法、隐私及diff检查通过。

不新增数据集、实验条件或评分口径，不填真实人工判断，不调用 API/GPU。旧资格报告自身仍不授权导出，formal_inclusion_approved=false。

### 2026-10-23：#9 离线资格核对闭环（离线验收完成，Refs #8）

范围：复用 #37 的 P5 检查和 P1 本地记录装配，读取现有最终 records，重新核对源脚本、实际 P4 请求、回执/复用与账目、音视频字节，输出独立的逐条件资格报告。原始记录、费用、人工检查表不改；generated 盲评/ratings 门禁保留，不提交/恢复视频或调用付费 API。

- [x] P1：将现有本地装配的计算与文件写出分离，提供无写入的重检入口；复用同一编译器和选镜头逻辑验证保存请求，比较最终记录、快照与重新计算的账目，不另建账本。
- [x] P5：串联输入和媒体检查，输出每条件 eligible/ineligible 与原因、原始完整记录和未知费用；文件/资格/主观质量及正式纳入保持分离。
- [x] CLI：新增只读输入的 qualify-generated-records，报告写入新目录；不覆盖，失败返回非零并保留诊断，旧盲评/ratings 门禁不变。
- [x] 验收：正常三条件、篡改来源/请求/回执、非法复用、账目变更、单镜头、失败和未知费用；使用已有 P1–P4 软件夹具及现有保存产物，无网络/模型调用。
- [x] 修正当前任务卡、契约及协作入口中过时描述；完成自查、回归及 PR 说明准备，后续提交 PR，不合并，#8/#9 保持开放。

验收：完整离线回归801项测试及116个子测试通过（408.97s）；新增14项资格测试通过，最终快照绑定调整后的CLI/原文件保留用例再次通过。已有保存软件产物经新CLI核对为三条件eligible，98个源文件内容哈希不变，网络连接被审计钩子禁止；只保存新报告。33份缓存参考校验、41个本地文档链接及diff检查通过。报告不代表模型质量、真实账单或正式实验结果。

按 [TEAM](TEAM.md) 的五张当前 Issue 和 [CONTRACTS 第6节](CONTRACTS.md#6-下一阶段生成式比较约束待实现) 交付待实现增量。下方为既有 animatic 工程验收，不是生成式研究已经完成。新动作规划只做一次供三组共用；生成模式只改台词，不能把动作差异混入审查对照。默认离线，正式实验与付费运行另行确认。

### MC-01 公共契约发布清单

Goal：先发布生成式 1.1 字段、公共纯函数及软件夹具，其他模块按同一接口接入。
Architecture：`src/moodcut/contracts.py` 只维护协议常量、字段白名单、JSON 身份与非台词比较，不执行规划/审查/生成。`pipeline.json_hash` 保留兼容导出，复用唯一哈希实现。旧 1.0 validator/CLI 不在本增量升级。
Tech Stack：Python 3.11 标准库、现有 pytest，不增加依赖。
Spec：Issue #8 首个接口待办、CONTRACTS 第6节；不改实验设计，不调用 API/GPU。

- [x] 写 `tests/test_contracts.py`：旧哈希兼容、台词变化不影响共享身份，动作/声音/参考图/模板/未知字段变化会影响身份，非法值拒绝、输入不变、软件记录可读。缺接口时先确认 ModuleNotFoundError，完成后31项通过。
- [x] 实现 `contracts.py` 公共常量、白名单、非台词比较和共享身份纯函数；在 `pipeline.py` 兼容导出原 json_hash。新增 `tests/fixtures/generated_contract.json` 协议软件示例，实际内容哈希可重新计算。
- [x] 用 CONTRACTS 取代模糊的未来约束，明确字段、状态、签名、模块接入步骤及已实现/后续实现边界；同步五张任务卡与统一入口，不勾选后续集成任务。
- [x] 完整离线回归312 passed / 67 subtests；固定33份资料校验通过、零下载。媒体回归已在配置 FFmpeg 的离线环境完成。不关闭 Issue、不自动合并，保留原负责信息。

## 当前工程交付

| 模块 | 实现 | 验证入口 |
|---|---|---|
| MC-01 | 共用客户端、预算检查、结构验证、CLI、共享初稿缓存、分条件记录 | test_client / test_validation / test_cli / test_pipeline / test_smoke |
| MC-02 | 本地梗概导入、显式角色映射、素材校验、director→scene→shot 规划 | test_importer / test_prepare_assets / test_planner |
| MC-03 | 通用/情绪审查、原子补丁、一次复查与失败回退 | test_patches / test_reviewer |
| MC-04 | 镜头 PNG、字幕、接触表、时间轴、固定规格 MP4 | test_renderer / test_video |
| MC-05 | 稳定配对分配、匿名导出、人工评分汇总、覆盖与费用 | test_evaluation_paired；原 VBench 工具使用 test_evaluation |

代码在 src/moodcut 平铺；提示词在 src/moodcut/prompts；模型、渲染和开发分配配置在 configs。继续复用现有实现，任务卡定义模块维护范围，不代表需要重新开发。

## 端到端验收

从仓库根目录安装 `python -m pip install -e ".[dev]"`。运行以下命令；输出目录使用尚不存在的新名字：

```bash
python -m pytest -q
python -m moodcut smoke --mock --output runs/accept-smoke
python -m moodcut run --mock --output runs/accept-video
python -m moodcut evaluate --config configs/experiment.json --dry-run
python -m moodcut evaluate --records runs/accept-video/block.json --blind-output runs/accept-blind
python -m moodcut evaluate --records runs/accept-video/block.json --output runs/accept-summary.json
python scripts/prepare_references.py --check
```

视频命令需 PATH 中有 FFmpeg/ffprobe，并提供或自动找到可用字体。检查三个 MP4 可播放、1280×720/24fps/60–90 秒、字幕无溢出；修改台词或裁切后对应 PNG 应变化。两种 mock 审查使用相同测试修改，不能据此比较方法。

同一 scene/tone/replicate 的三个条件必须使用同一 initial_plan_sha256，审查数据独立。未缓存时最多规划 3 次、baseline 0 次审查、两类 review 各 3 次；无意见和失败可提前结束。缓存按输入、manifest、模型设置、replicate、schema、规划提示、上限与代码版本区分。缓存损坏或已有锁报错并保留文件。

planning.json 只记录共享规划，各 run.json 只记录本条件；block.json 保留两层账目。汇总传完整 block.json 时，全流程费用计共享规划一次。所有失败和未知费用保留，不把 unknown 当零；mock 的真实 HTTP 和费用为零。普通 CI 不联网调用模型或下载权重。

## 接入真实模型

README 提供环境变量、configs/model.json 和 `check-client` 的命令。模型 ID、价格和本次预算须明确；实际调用要求 --allow-paid 与 --max-cost-usd。依赖检查在请求前完成。单实例本地预算不是跨进程或账户硬额度，团队 15 美元仍需平台控制。

开发 demo 已配置 openai/gpt-4.1-mini（当前输入/输出 $0.40/$1.60 每百万 token），configs/demo_scene.json 指向已有 MovieAgent 图像清单。scripts/compare_demo.py 可对现有 block 生成逐镜头改动与视频对比页。示例运行预算为 $0.10，未因写入配置而调用模型；它不是正式实验的模型或样本冻结决定。

真实模型可能返回不合契约的输出；保存原始解析响应、错误、用量，返回非零，不自动补跑或用 mock 顶替。工程离线验收不等于真实 OpenRouter 凭据、模型输出质量或研究效果验证。

## 尚需团队判断

- 选定并确认开发故事、目标 tone、必需 beats、两角色改编和素材裁切；软件不擅自从整部电影删角色。
- 确认实际模型、当前价格及小规模 pilot 预算后运行真实模型。
- 根据 pilot 确认正式样本、评价者分配、评分解释与冻结配置，再开展人工评价。
- 阅读真实片段，判断自然度、剧情保留和情绪表达；不能用结构通过或 Agent verification 替代。

configs/experiment.json 是现有软件夹具的开发分配示例，configs/pilot.json 保留原 VBench 配置。两者用途不同，均不自动授权正式实验。

模块边界与后续分工见 TEAM.md 和 docs/tasks；公共接口见 CONTRACTS.md；上游来源与复用范围见 REFERENCES.md、upstream-reuse.md。所有增量走 PR，自查当前 diff、相关测试与产物，不自动合并。


## Scoped v4 review update (2026-10-25)

Reuse the existing bounded reviewer, shot writer, patch checks and saved-result validation. Add an explicitly selected `actor_self_review_v4`: one global reviewer for generic review, two independent character Actors for MoodCut, with intent/subtext/emotional-gap instructions. Keep every historical protocol, prompt and result unchanged. Both branches permit at most two writer candidates; every candidate is revisited by all reviewers, including writer-addressed feedback and Actors without initial issues. A maintained objection triggers round two; reasoned unresolved feedback is allowed. Final disagreement stays visible and is not endorsement.

Validation: synthetic FakeClient regressions for reviewer counts, unconditional revisits, bounded rounds, ownership, frozen fields, failures and saved-result replay; run the existing offline suite. No paid API, video generation or formal experiment is authorized.
