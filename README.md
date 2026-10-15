# MoodCut

DSA4213 课程项目：面向情绪表达的分镜审查与局部修订。

给定故事、两个角色参考图与目标氛围，系统规划台词并执行审查—修订—复查。成片方向是以参考图保持人物形象，由视频生成模型产生场景、动作和声音。第一阶段 review 只修改台词。

已有 `smoke/run/render` 生成静态 animatic，用于检查文本流程，不代表生成式成片。新增 `scripts/generate_video.py` 将已有初稿与台词修订接到 OpenRouter 的参考图视频生成接口；接口与拼接已做离线验证，真实视频、中文对白和人物一致性尚待付费 pilot 验收。

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

恢复只下载该镜头，不自动继续整对或重新计账；先核对已有 receipt 和平台扣费，再决定后续操作。提交超时且没有 job ID 时需到平台核对，不重新提交来猜测状态。receipt.json 保留状态和已知/未知费用，不保存 key 或签名下载 URL。任一费用未知停止后续生成。

成片拼接实际生成的音视频轨，不补静态占位，不把缺少音轨当作成功。输出含每镜头 generated.mp4/receipt.json、每版 film.mp4、generation.json 与 comparison.html。检查音轨存在只证明文件含音频；是否正确说出中文台词、说话人、口型、声音连续和情绪自然度仍需人工听看。固定 seed 不能保证改变台词后画面完全相同，单个样例也不能证明情绪效果提升。当前没有真实视频生成验收证据，不承诺一次调用达到最终质量。

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

## 用 AI 开发一个任务

在 GitHub Issue 中认领一个模块，拉取最新 main 后，将以下指令交给编码助手并替换编号：

```text
我负责 GitHub Issue #N，请读取 AGENTS.md、
.agents/skills/moodcut-team/SKILL.md、docs/TEAM.md、docs/CONTRACTS.md、
docs/REFERENCES.md、docs/upstream-reuse.md 和该 Issue 关联的任务卡。
先检查任务认领和已有 PR，避免重复开发。
执行 python scripts/prepare_references.py --check；若资料缺失，
允许执行 python scripts/prepare_references.py 下载固定公开来源并重新校验。
若哈希不符，保留原文件并报告。按索引阅读本模块所需源码。
先检查任务卡的当前交付状态，只完成 Issue 中尚未实现的增量；已有功能直接复用。
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
