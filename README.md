# MoodCut

DSA4213 课程项目：面向情绪表达的分镜审查与局部修订。

给定故事、两个角色参考图与目标氛围，系统规划台词并执行审查—修订—复查。成片方向是以参考图保持人物形象，由视频生成模型产生场景、动作和声音。第一阶段 review 只修改台词。

默认 `smoke/run/render` 生成静态 animatic，用于检查文本流程，不代表生成式成片。`run --output-mode generated` 已接通三条件脚本的实际离线请求编译器；旧 `scripts/generate_video.py` 保留开发对的OpenRouter视频适配。接口与拼接已做离线验证，真实视频、中文对白和人物一致性尚待付费pilot验收。

研究问题：情绪专项反馈能否比通用审查更准确地传达目标氛围，同时保持剧情清楚和表达自然？效果需要独立评价，软件流程完成本身不证明提升。

## 安装与离线开工

Python 3.11+。从仓库根目录运行；Windows 示例使用 PowerShell 7：

```powershell
git clone https://github.com/zhengads/MoodCut-dsa4213.git
cd MoodCut-dsa4213
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
git config commit.template .gitmessage
.venv/Scripts/python -m moodcut smoke --mock --output runs/smoke-01
```

Linux/macOS 使用 `.venv/bin/python`。smoke 只跑三条件的 JSON 链路，不联网、不需要 key、不渲染视频。输出目录必须是新目录，已有结果不覆盖。默认开发模式也是 mock，提供 key 不会自动开启付费调用。

需要视频时，先将 FFmpeg 和 ffprobe 加入 PATH；Linux 可安装 `ffmpeg fonts-noto-cjk`。字体按 `--font`、MOODCUT_FONT、configs/render.json、可用系统字体的顺序选择。中文建议 Windows 微软雅黑或 Linux Noto Sans CJK。

```powershell
.venv/Scripts/python -m moodcut run --mock --scene tests/fixtures/scene.json --assets tests/fixtures/assets.json --output runs/demo-01
```

该命令产生一份初稿、三个条件的完整记录与三段 MP4。离线响应为明确标注的软件夹具，两种审查使用同样的测试修改，不能据此比较方法效果。测试故事、图片和模拟结果均不属于正式数据。

### 生成模式：从已有脚本离线准备请求

正式入口已支持读取1.1/generated的脚本block，保留共同初稿与原镜头索引，不重新规划或审查。source-block需来自CONTRACTS 6.7的成功脚本编排，并在规划前冻结实际get_video_template_sha256()身份；不接受旧开发对或animatic记录：

```powershell
.venv/Scripts/python -m moodcut run --output-mode generated --source-block runs/generated-scripts/block.json --shot-id s2 --pricing-config configs/video.json --output runs/generated-s2
```

省略 `--shot-id` 准备全部镜头；各条件选择同一个镜头，seed仍按原完整计划中的索引计算。此入口始终离线、无需key，不支持 `--allow-paid`、规划/响应/渲染覆盖参数，也不查询实时价格；原默认animatic命令不变。

`build_generated_video_bundle`已消费共同scene_direction、逐镜头direction/时长和明确的1.1 GenerationSettings；同一生成模板、人物图、声音和原索引seed跨三条件复用，只有台词部分变化。实际P2/P3/P4代码加FakeClient已通过读信/非读信输入与完整/单镜头离线联调；不等于真实模型或成片验收。模板哈希不匹配、非台词改动或素材验证失败会拒绝，不改写旧block。详见[CONTRACTS 6.12](docs/CONTRACTS.md#612-三条件生成请求编译)和[生成编译说明](docs/rendering.md#generated-request-compilation-11)。

通过身份/请求检查后，输出 `bundle.json`、`preparation.json`、完整 `source_inputs.json` 和原账目 `source_block.json` 快照。preparation只记请求prepared_offline、零新调用/消费，报价另存且不等于支出；不产生视频，也不宣称比较eligible。报价可读取configs/video.json的模型/规格/费率，旧读信配方不用于新编译。来源或编译失败返回非零，已有结果不覆盖。完整接口与验收边界见 [CONTRACTS 6.8](docs/CONTRACTS.md#68-离线生成入口与单镜头选择)。

### 三条件任务执行接线

`execute-generated` 消费上面的请求准备目录，默认离线，只保存三条件未提交记录和空检查材料：

```powershell
.venv/Scripts/python -m moodcut execute-generated --preparation runs/generated-requests --pricing-config configs/video.json --media-origin synthetic --output runs/execution-offline
```

只有另获模型/范围/预算批准后才能启用 `--allow-paid --max-cost-usd`。执行复用现有视频客户端和本地检查包；同块相同请求复用，失败/中断/未知消费停止后续POST。`--resume-execution` 只GET恢复一个已有任务；费用核清后，`--continue-execution` 才能显式继续未提交镜头，跳过已完成任务并扣除历史视频消费。旧回执/记录保留，父快照仅允许一个HTTP后继。准确参数、预算边界和中断处理见[CONTRACTS 6.17](docs/CONTRACTS.md#617-三条件任务执行恢复与继续)。

本增量只通过模拟回执/现有软件视频验收，不调用付费API。真实试跑的输入、模型、规模、费用与人工安排仍待批准，见[试跑协议提议](docs/evaluation.md#三条件试跑协议提议2026-10-23尚未批准运行)。已有[还伞4秒三版本具体试跑单](docs/pilots/umbrella-single-shot.md)，明确固定软件台词的技术预检范围、共同设置、预算、素材/历史费用缺口及验收标准；当前不可启动，不代表真实审查效果。最终只使用execution记录指向的账目，不累加父执行或preflight快照。

### 已有本地视频的观看检查包

```powershell
.venv/Scripts/python scripts/inspect_generated_video.py --preparation runs/generated-requests --evidence runs/local-evidence.json --media-origin provided_local --output runs/video-inspection
```

输入为上述请求准备目录及[本地回执证据](docs/CONTRACTS.md#69-本地生成回执与费用记录装配)，无需key，不提交/恢复任务。软件媒体必须声明`--media-origin synthetic`；provided_local仅说明提供了本地文件，不认证为模型产物。输出观看页、来源/请求/字节哈希绑定、实际抽帧接触表、ffprobe信息和空CSV/JSON人工检查表；复用原拼接器和P1预检/最终记录装配，保留失败与未知费用。详细状态和命令见[CONTRACTS 6.13](docs/CONTRACTS.md#613-本地成片来源绑定与观看检查材料)。

打开输出index.html检查选中范围；页面含条件、目标和预期台词，不用于盲评，也不自动判断说话/口型/情绪是否正确。所有材料就绪只表示ready_requires_manual_inspection；判断项仍留空，comparison仍not_checked/ineligible。只使用records中的最终账目，不把preflight_records的同一历史再累加一次。现有输出不覆盖，失败/不完整返回非零。离线资格见CONTRACTS 6.14；盲评导出/评分接线见CONTRACTS 6.15；真实任务和模型质量仍待完成。

### 生成式匿名导出与评分

```powershell
.venv/Scripts/python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --blind-output runs/generated-blind --seed 17
.venv/Scripts/python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --output runs/generated-coverage.json
.venv/Scripts/python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --ratings runs/completed-ratings.csv --private-key runs/generated-blind/PRIVATE/private_key.csv --output runs/generated-scores.json
```

只传完整最终records，每块一次，保留来源及整个导出目录；不可使用旧资格报告替代当前重检。整块三条件资格通过才导出，失败/未知费用仍在私有诊断及全量分母。公开仅发public，PRIVATE含答案/来源/账目，必须保密；评分表初始为空，不自动填判断。导入评分再次核对来源、映射及全部匿名副本字节，避免源文件没变但观看副本被换。复制中变化会拒绝发布，已有输出不覆盖。

这是离线软件证据接线，formal_inclusion_approved仍false；不批准正式样本/失败纳入规则，不代表语音、画面或方法效果通过。零导出也可生成空诊断包，应检查exported_clips。既有不带价格参数的原始账目查看仍兼容，但不做资格认证。详见[评估说明](docs/evaluation.md#generated-blind-export-and-rating-import-2026-10-23)与[CONTRACTS 6.15](docs/CONTRACTS.md#615-生成式匿名导出和评分接线)。

汇总含generated记录时，总体和各条件新增generation状态细分：未开始、离线未提交、进行中、已装配待人工检查、失败、中断、未知；另报待拼接、混合镜头和保存的远端状态。旧渲染计数及评分/费用分母不变，复用镜头计数不当成新任务，缺失状态不当零调用。字段与计数边界见[CONTRACTS 6.16](docs/CONTRACTS.md#616-生成状态细分汇总)。

## 接入 OpenRouter

`configs/model.json` 已选择第一轮开发 demo 使用的 `openai/gpt-4.1-mini`：输入 $0.40/百万 token、输出 $1.60/百万 token，temperature=0，单次网络超时 120 秒。三个条件共用这份配置，不自动换模型或重试。2026-10-15 核验了 [OpenRouter 模型页](https://openrouter.ai/openai/gpt-4.1-mini) 和 [公开端点参数/价格](https://openrouter.ai/api/v1/models/openai/gpt-4.1-mini/endpoints)：当前 OpenAI 端点支持 max_tokens、temperature、response_format。该选择用于先查看真实输出，不代表已经证明它最适合正式实验。价格变化时同步更新配置；未知价格继续拒绝发送。

key 只从进程环境读取。`.env.example` 是空模板，程序不自动加载 `.env`。不要将 key 写入共享配置、命令文本或 PR：

```powershell
$env:OPENROUTER_API_KEY = Read-Host 'OpenRouter API key' -MaskInput
.venv/Scripts/python -m moodcut check-client --config configs/model.json --max-cost-usd 0.10
```

check-client 只检查本地配置，不联网、不验证远端 key，也不会扣费。确认本次模型、规模和费用上限后，可将离线运行替换为真实调用：

```powershell
# One development story, all three conditions, with pinned Anna/Elsa images.
# Only run after accepting this model and this run's USD 0.10 budget threshold.
.venv/Scripts/python -m moodcut run --allow-paid --model-config configs/model.json --max-cost-usd 0.10 --scene configs/demo_scene.json --assets assets/manifest.json --output runs/live-demo-01
.venv/Scripts/python scripts/compare_demo.py --run runs/live-demo-01
Start-Process (Resolve-Path runs/live-demo-01/comparison.html).Path
```

首次使用这份素材先运行下文的 prepare_references.py --assets 和 prepare_assets.py --check。configs/demo_scene.json 复用已有读信软件故事、改用 Anna/Elsa 名称及中文字幕，asset_ids 指向 MovieAgent 参考图；不是原电影剧情或正式评价数据。demo 可先改为 --mock 查看同一素材的离线流程。

未命中初稿缓存时，一块数据最多 3 次规划请求和每个审查条件 3 次请求，合计 9 次；无意见、无效补丁或失败会提前退出，不自动重试。按当前短输入及上述价格，开发估计约 $0.01–$0.05、1–3 分钟，实际以 usage.cost 和失败记录为准，不承诺精确耗时/价格。真实模型不符合 JSON/公共契约时保存诊断并返回失败，不修饰为成功。

comparison.html 是本地对比页：三段视频、逐镜头字段的修改前/修改后、审查意见、补丁/复查状态，以及规划只计一次的费用和实际调用数。没有改动会明确显示没有变化；失败没有最终分镜时不会说成没有变化。页面不调用模型、不打效果分、不调整提示词。它核对初稿/最终分镜哈希并转义模型文本；请将 HTML 与对应运行目录一起保留。可直接双击 HTML，或在 PowerShell 用 Start-Process 打开。

`max-cost-usd` 是本次客户端的估算阈值，不是账户硬额度。输入使用 UTF-8 字节数加固定余量估算，实际 token 由模型 tokenizer 决定；团队共享 15 美元还需在 OpenRouter 端限制 key/团队总额。费用未知保留 null，并停止该客户端后续请求。不同进程或新建客户端不共享本地余额。

OpenRouterClient 保持 `complete_json(...) -> dict`，可直接传给规划和审查。调用者可查看 client.calls；key 和提示词不进入该费用记录。actual provider_cost_usd 来自 usage.cost，estimated_cost_usd 根据返回 token 与配置单价计算，两者分别保存。

协议依据：[API 与 usage](https://openrouter.ai/docs/api_reference/overview)、[参数与价格上限](https://openrouter.ai/docs/guides/routing/provider-selection)、[平台费用控制](https://openrouter.ai/docs/guides/best-practices/spend-controls)。当前工程验证使用离线响应，不声称真实 OpenRouter 或模型效果已验证。

## 生成真实画面与声音

使用独立的 [生成视频计划与验收边界](docs/GENERATIVE_VIDEO_PLAN.md)。`configs/video.json` 选择 `alibaba/wan-2.7`，720p、16:9、原生声音；2026-10-15 官方 [模型页](https://openrouter.ai/alibaba/wan-2.7) 与公开 `/api/v1/videos/models` 标价 $0.10/秒，支持参考图和 2–10 秒片段。使用 `input_references` 传入人物原图，提示词指定新场景、动作、说话人和台词；不把角色卡片作为首帧。

先对已有且成功的 moodcut 审查准备请求，默认完全离线、不需要 key：

```powershell
.venv/Scripts/python scripts/generate_video.py --run runs/live-demo-01 --output runs/video-preview-01
Start-Process (Resolve-Path runs/video-preview-01/preview.html).Path
```

输入目录需要 scene.json、assets.json、baseline/initial.json、baseline/run.json、moodcut/final.json、moodcut/run.json；工具验证来源哈希，不重新调用规划/审查模型。失败回退不能冒充成功修订。配置的 scene_id、角色和 shot_id 必须与输入匹配；示例只适用已提供的读信开发故事。

开发成片各三个 6 秒镜头，前后各 18 秒；不改写既有 60 秒分镜与实验配置。只采用候选版本的 dialogue 字段，其余改动列在 ignored_non_dialogue_changes；生成的派生输入不继承原复查通过结论。`bundle.json` 保存两版实际请求、台词差异、来源哈希及估算；preview.html 明确标记尚未生成视频。

两版最多六次视频生成，按该价格估算 $3.60，明显超过文本 demo 的 $0.10 预算。完全相同的请求在这一对成片内复用同一视频并记录，减少费用和无关画面差异；不把复用计成新请求。仅在接受本次模型、两版规模与预算后运行：

```powershell
# Example only: requires explicit acceptance of the new video-generation budget.
.venv/Scripts/python scripts/generate_video.py --run runs/live-demo-01 --output runs/generated-pair-01 --allow-paid --max-cost-usd 4.00
Start-Process (Resolve-Path runs/generated-pair-01/comparison.html).Path
```

付费前检查 key、FFmpeg/ffprobe、整对估算和最新公开模型参数/价格。生成可能需要数分钟/镜头，耗时及质量不保证。POST 不重试，轮询或下载中断时保留 job ID，恢复已有任务不会提交替代任务：

```powershell
.venv/Scripts/python scripts/generate_video.py --resume-job runs/generated-pair-01/baseline/shot-01
```

恢复只下载该镜头，不自动继续整对或重新计账；先核对已有 receipt 和平台扣费，再决定后续操作。提交超时且没有 job ID 时需到平台核对，不重新提交来猜测状态。receipt.json 保留状态、已知/未知费用、generation ID 和脱敏后的服务端错误原因，不保存 key 或签名下载 URL。任一费用未知停止后续生成。

成片拼接实际生成的音视频轨，不补静态占位，不把缺少音轨当作成功。输出含每镜头 generated.mp4/receipt.json、每版 film.mp4、generation.json 与 comparison.html。检查音轨存在只证明文件含音频；是否正确说出中文台词、说话人、口型、声音连续和情绪自然度仍需人工听看。固定 seed 不能保证改变台词后画面完全相同，单个样例也不能证明情绪效果提升。当前没有真实视频生成验收证据，不承诺一次调用达到最终质量。

另支持 `bytedance/seedance-2.0-mini` 的参考图＋原生声音配置：保留相同输入，配置中设置该 model，移除 price_per_second_usd，使用 `price_per_million_video_tokens_usd: "3.50"`。当前仅实现 16:9 下 480p（854×480）或 720p（1280×720）、4–15 秒的明确价格契约；不覆盖音视频参考输入。2026-10-16 核对[官方模型页](https://openrouter.ai/bytedance/seedance-2.0-mini)和公开目录：费用按 `宽×高×秒数×24/1024 × $3.50/百万视频 token` 估算，带声音的 720p 六秒约 $0.4536，480p 六秒约 $0.2018。付费入口仍检查实时参数/价格及本次预算，不因切换后端而获得新运行授权。

MovieAgent 官方的 ROICtrl／SVD／HunyuanVideo 自部署链路与这些商用 API 不同；论文展示不能证明服务商一定接受相同输入。更换后端不改变素材身份，不隐瞒输入或关闭审核，也不保证同一素材会被接受。首次 Wan 任务已被服务端以疑似 IP 侵权拒绝；保留失败和未知单笔费用，不能用换模型抹去该记录。Seedance 目前只完成离线适配与公开参数检查，尚未进行付费验收。

## 输入、输出与缓存

输入 SceneInput 和 AssetManifest 的字段见 [公共契约](docs/CONTRACTS.md)。故事、目标氛围 affectionate/suspicious/hostile、角色、剧情 beats、素材和来源由输入明确提供；系统不会从整部电影中静默删角色或擅自改写必需情节。

```text
runs/demo-01/
  scene.json, assets.json
  planning.json              共享规划、原始 JSON、用量与缓存标记
  block.json                 本块总览及三个条件记录
  baseline/                  各条件独立初稿/最终分镜、run.json、渲染结果
  generic_review/            另含 review.json 与诊断日志
  moodcut/
```

三条件 initial_plan_sha256 必须相同，审查输入各自 deepcopy，不共享修订历史。初稿缓存按完整输入、素材清单、模型设置、replicate、schema、规划提示词、输出上限和规划代码哈希区分；变更会生成新身份。损坏缓存或正在使用的缓存锁会报错，保留原文件。输出目录始终新建，缓存复用也不会覆盖旧运行。

费用分两层：planning.json 保存共享规划一次的费用；各 run.json 仅保存自己的审查费用。mock 的逻辑调用次数是模拟次数，real_http_calls 为 0，实际 API 费用为 0，未伪造真实 token 数。run_status 只表示工程流程是否完成，review_status、validation_status、render_status 分别记录，均不等同于情绪识别正确。

## 评估工具

先列任务，不运行模型：

```powershell
.venv/Scripts/python -m moodcut evaluate --config configs/experiment.json --dry-run
```

该配置只有一条已有软件夹具，供开发检查；不自动确定正式样本量。生成视频后可导出匿名材料：

```powershell
.venv/Scripts/python -m moodcut evaluate --records runs/demo-01/block.json --blind-output runs/blind-demo-01
.venv/Scripts/python -m moodcut evaluate --records runs/demo-01/block.json --output runs/demo-01/summary-without-ratings.json
```

只向评价者分发导出的 public/。PRIVATE/private_key.csv 保存条件、目标情绪和视频哈希。ratings.csv 不预填主观答案，需人工填写；填写后用原始记录和私有映射汇总：

```powershell
.venv/Scripts/python -m moodcut evaluate --records runs/demo-01/block.json --ratings runs/blind-demo-01/public/ratings.csv --private-key runs/blind-demo-01/PRIVATE/private_key.csv --output runs/demo-01/human-summary.json
```

填写前的空模板不能用于评分汇总；缺少评价时省略 --ratings，只查看覆盖和费用。`block_ledger_accounting.all_phases` 将共享规划计入一次，只有提供完整 block.json 才给出全流程费用；单独传 run.json 时这项为 null。评价者分配、正式规模与实验冻结由团队确认。

统计按被评分 clip 等权汇总，uncertain 计为情绪未命中；缺失、渲染失败、审查失败及未知费用分别列出。零分母返回 null。M/G 配对比较显示共同可评价 block 与覆盖率，不把共同成功子集说成所有运行的提升。人工自然度、剧情清楚度和过度表达分列，不生成主观评分或合成“总分”。

已有 VBench imaging_quality 工具继续作为单独入口使用，见 [评估说明](docs/evaluation.md)。默认 CLI 不触发 VBench、模型权重下载或 GPU 推理；图像质量分数不能替代情绪评价。

## MovieAgent 素材准备

```powershell
.venv/Scripts/python scripts/prepare_references.py
.venv/Scripts/python scripts/prepare_references.py --assets
.venv/Scripts/python scripts/prepare_assets.py --selection assets/selection.example.json --output assets/manifest.json --check
```

33 份核心参考源码约 178 KB；两张初始图片与说明约 1.2 MB；可选 `--papers` 两篇 PDF 约 57 MB。下载使用固定版本并校验大小/哈希，不运行上游代码。prepare_assets 只处理显式选择的本地图片，不复制、不联网，不推断素材许可或人脸裁切。

已提供两张图的 assets/manifest.json 元数据，--check 核对本地图像与已提交清单，不修改文件。自选素材时修改选择清单，并去掉 --check 输出到新的 manifest 路径；已有文件不覆盖。

selection.example.json 引用 Anna/Elsa，原图保留本地、许可状态明确标为未确认，默认只允许 full 裁切。需要相应 SceneInput 中 character_id 与 asset_ids 的显式映射；不要把两角色素材当作整部 MovieAgent 故事的完整复现。`import-synopsis --help` 可读取上游梗概；超过两个角色的原稿需先明确改编。

## 开发与验证

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/prepare_references.py --check
```

视频测试需要 FFmpeg/ffprobe 和可用字体；可用 MOODCUT_TEST_FONT 指定测试字体。普通 CI 无真实 key，不调用付费 API。测试夹具、mock、开发 pilot 和正式结果要分别标注。

目录保持扁平：`src/moodcut/*.py`、集中 prompts/、根目录 configs/、平铺 tests/ 及共享 tests/fixtures/。资料在 references/，任务与接口在 docs/，素材在 assets/，运行产物在忽略目录 runs/；不提交密钥、上游原始图片、大视频或个人评价身份。

## 离线资格核对

```bash
python -m moodcut qualify-generated-records --records runs/video-inspection/records --pricing-config configs/video.json --output runs/qualification
```

读取最终records及其现有源脚本、请求、回执和媒体，复用P1账目重算与P5检查；报告输出到新目录的qualification.json，全部通过返回0，否则返回1并保留原因。原始记录/账目/人工表不改，未知费用不当零；eligible只表示所选范围的软件证据通过，不能作为正式实验或主观质量证明。现有generated盲评/ratings门禁保留。详见[离线资格契约](docs/CONTRACTS.md#614-离线资格核对报告)。

## 当前任务入口

1.1 公共协议与各模块接入签名见 [CONTRACTS 第6节](docs/CONTRACTS.md#6-下一阶段生成式比较约束待实现)。`moodcut.contracts` 提供白名单、非台词检查和共享身份；公共 `validate_scene/validate_plan` 已支持显式 `output_mode="generated"`。软件示例在 `tests/fixtures/generated_contract.json`，离线检查为 `python -m pytest tests/test_contracts.py tests/test_validation.py -q`。旧 CLI 默认1.0；离线资格报告已实现（CONTRACTS 6.14），盲评导出/评分接线见CONTRACTS 6.15；真实任务尚待完成。

五模块任务索引：基础/契约 [#8](https://github.com/zhengads/MoodCut-dsa4213/issues/8)、共同分镜 [#22（工程已关闭）](https://github.com/zhengads/MoodCut-dsa4213/issues/22)、台词审查 [#23（工程已关闭）](https://github.com/zhengads/MoodCut-dsa4213/issues/23)、生成与检查 [#24](https://github.com/zhengads/MoodCut-dsa4213/issues/24)、评估接入 [#9](https://github.com/zhengads/MoodCut-dsa4213/issues/9)。详见 [交付顺序](docs/TEAM.md)。以Issue实时状态为准；已交付模块直接复用，只认领未完成项，先提交 PR，不自动合并。

生成模式要求共同场景/动作/镜头只规划一次，各条件只改台词；公共边界及规划/审查/请求编译和本地检查材料已支持显式generated，离线资格报告见CONTRACTS 6.14，盲评导出/评分接线已实现（6.15）；任务执行接线见6.17（模拟回执验收）；真实试跑仍待批准和验收。固定 seed 不保证画面相同，规划不是本对照单独检验的变量。当前不调用付费 API，不自行启动实验；接口和验收边界见 [CONTRACTS 第6节](docs/CONTRACTS.md#6-下一阶段生成式比较约束待实现)。

生成式规划调用`make_plan_with_trace(scene, manifest, client, project_root=..., output_mode="generated")`，详见[CONTRACTS 6.10](docs/CONTRACTS.md#610-生成式共同规划适配)。它按显式1.1输入的镜头/总长范围规划，沿用director→scene→shot和共享初稿，不补长为60秒。台词限定审查接口见[CONTRACTS 6.11](docs/CONTRACTS.md#611-台词限定审查与实际最终脚本复查)，汇集同镜头意见、保持单edit并复查实际最终计划。实际P2/P3/P4代码加FakeClient可准备三条件脚本和请求；当前CLI plan/review仍默认animatic，离线媒体检查/资格报告已实现，真实任务与盲评仍待接线，不能视为真实三条件实验已可运行。

本地回执与账目使用`assemble-generated-records --preparation ... --evidence ... --pricing-config ... --output ...`，准确格式见[CONTRACTS 6.9](docs/CONTRACTS.md#69-本地生成回执与费用记录装配)。它只读已有文件，保留失败/未知费用和旧回执计数缺失；报价不当消费，规划及复用只计一次。媒体文件完成后可用qualify-generated-records核对离线资格（6.14），人工听看仍待完成；盲评导出/评分须走6.15重检入口，不以旧导出绕过来源及副本核对。

## 用 AI 开发一个任务

任务分支使用 `<type>/issue-<GitHub编号>-<英文内容>`，例如 `feat/issue-22-shared-planning` 或 `fix/issue-23-dialogue-review`。历史分支已统一放在 `archive/`，不作为新任务起点；本地旧分支同步方法见 [分支规则与迁移表](docs/BRANCHES.md)。

在 GitHub Issue 中认领一个模块，拉取最新 main 后，将以下指令交给编码助手并替换编号：

```text
我负责 GitHub Issue #N，请读取 AGENTS.md、
.agents/skills/moodcut-team/SKILL.md、docs/TEAM.md、docs/CONTRACTS.md、
docs/REFERENCES.md、docs/upstream-reuse.md 和该 Issue 关联的任务卡。
先检查任务认领和已有 PR，避免重复开发。
读取 docs/BRANCHES.md，使用 <type>/issue-<实际GitHub编号>-<英文内容>，
如 feat/issue-22-shared-planning；不使用工具名或成员代号，不在 archive/ 上开发。
执行 python scripts/prepare_references.py --check；若资料缺失，
允许执行 python scripts/prepare_references.py 下载固定公开来源并重新校验。
若哈希不符，保留原文件并报告。按索引阅读本模块所需源码。
先读任务卡顶部下一增量和 CONTRACTS 第6节，再核对既有交付记录；
只完成 Issue 中未勾选的增量，已有功能直接复用。
共同动作/镜头只规划一次，生成模式三条件只改台词；
公共契约/验证器已提供，pipeline脚本编排参数与依赖见CONTRACTS 6.7；
各自接通所属模块，prepared不等于视频完成，不自行增加消融条件或数据集。
只修改任务范围内文件，默认离线，不调用付费 API。
允许提交并推送任务分支、创建或更新 Draft PR、更新该 Issue 的进度。
完成验收后自查当前 diff，在 PR 描述中记录评审结论、测试结果和遗留问题。
这次先提交 PR，不自动合并。
```

无需指定评审人。作者可以自行检查，也可请同伴或 AI 辅助评审；提交者核对结果后负责自己的交付。AI 无法读取 GitHub 时，可粘贴 Issue 全文，并说明远端认领状态尚未核实。

- [模块分工、任务卡与协作流程](docs/TEAM.md)
- [公共接口](docs/CONTRACTS.md)
- [参考资料与源码阅读路径](docs/REFERENCES.md)
- [复用范围](docs/upstream-reuse.md)

## 上游参考

| 项目 | 用于 MoodCut 的内容 | 固定版本 |
|---|---|---|
| [MovieAgent](https://github.com/showlab/MovieAgent) | 剧情与角色输入、分阶段规划、提示词组织 | `d84041bed8bc8be460664528d9e9924cdde384ba` |
| [FilmAgent](https://filmagent.github.io/) | Critique–Correct–Verify 审查流程 | `16c1ce0b553e30eff90ff1274e8a8a63c1d548a3` 的 `FilmAgent/` |

FilmAgent 官方代码链接目前重定向到 `HITsz-TMG/VideoClaw`，本项目读取其 `FilmAgent/` 子目录。固定版本及逐文件哈希见 [sources.lock.json](references/sources.lock.json)。论文说明与源码说明见阅读索引，引用条目见 [references.bib](references/references.bib)。

源码参考缓存位于 `references/upstream/`，不作为运行依赖，也不提交到本仓库。MovieAgent 固定版本未发现项目级许可证；FilmAgent 所在固定版本的仓库根目录提供 MIT LICENSE。实际代码复用需记录范围并保留适用声明，素材使用限制单独核实。

可选资料：

```bash
python scripts/prepare_references.py --papers  # 两篇论文 PDF，约 57 MB
python scripts/prepare_references.py --assets  # Anna/Elsa 两张参考图及说明，约 1.2 MB
```

## 提交与评审

认领具体文件范围，避免重复实现公共 client 或别人的模块。每个可验收增量走 PR；作者可以自行评审，记录当前 diff、实际测试、产物和遗留事项。验收及仓库规则通过后按已有授权合并；无需指定固定同伴评审人。

保留 `.gitmessage` 的姓名与日期格式。项目范围、技术选择和复用依据见 [TEAM.md](docs/TEAM.md)、[实施计划](docs/IMPLEMENTATION_PLAN.md) 和五张任务卡。
