# MoodCut 实施与验收

目标：将 MovieAgent 风格规划、台词审查修订与人物参考图引导的视频/声音生成连成可验收流程。Python 3.11、Pillow、FFmpeg/ffprobe；通过服务接口生成视频，不要求本地 GPU 或上游模型权重。

既有静态 animatic 是文本流程诊断工具。新增生成式路径与离线验收见 [GENERATIVE_VIDEO_PLAN.md](GENERATIVE_VIDEO_PLAN.md)：脚本、请求准备、异步任务和实际音视频拼接已接入，真实人物一致性、中文对白与画面质量尚未经过付费 pilot 验收。以下既有模块/命令的 60–90 秒约束仍只适用于原 animatic 契约，不作为新成片的时长要求。

## 下一阶段入口

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
