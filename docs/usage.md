# MoodCut 使用指南

[返回项目首页](../README.md)

先完成首页的安装与离线 smoke。下列命令均从仓库根目录执行；Windows 使用 `.venv/Scripts/python`，Linux/macOS 使用 `.venv/bin/python`。示例中的 `runs/...` 输入需要事先准备，所有输出使用新路径，不覆盖历史结果。

## 输入、输出与缓存

输入由故事 `SceneInput` 和素材清单 `AssetManifest` 明确提供，包括目标氛围、角色、剧情 beats、素材与来源。具体字段见[公共契约](CONTRACTS.md)。系统不会自动把多角色原稿改编为两人故事。

默认 animatic 运行的主要输出：

```text
runs/demo-01/
  scene.json, assets.json
  planning.json              共享规划、原始 JSON、用量与缓存标记
  block.json                 本块总览及三个条件记录
  baseline/                  initial/final 分镜、run.json、render/
  generic_review/            另含 review.json 与诊断日志
  moodcut/
```

三条件的 `initial_plan_sha256` 必须一致，审查输入各自复制，不共享修订历史。缓存身份包含输入、素材、模型、replicate、协议与规划实现；改变这些内容会产生新身份，损坏或占用中的缓存会报错并保留原文件。

共享规划费用只计一次，保存在 `planning.json` 和完整 `block.json` 中；各条件的 `run.json` 只记录自己的审查费用。mock 的逻辑调用为模拟次数，真实 HTTP 与 API 支出为零。工程完成状态不代表情绪或画面质量合格。

## OpenRouter 配置

`configs/model.json` 是旧文本 demo 的配置，当前文件选择 `openai/gpt-4.1-mini`；演员试跑的模型分工以对应[试跑记录](pilots/)为准。配置里的单价是本地估算依据，运行前需要核对实际模型参数与价格。

key 只从进程环境读取，程序不自动加载 `.env`；[.env.example](../.env.example) 仅为空模板。PowerShell 7 可安全输入：

```powershell
$env:OPENROUTER_API_KEY = Read-Host 'OpenRouter API key' -MaskInput
.venv/Scripts/python -m moodcut check-client --config configs/model.json --max-cost-usd 0.10
```

`check-client` 只检查本地配置，不联网，也不验证远端 key。提供 key 不会自动开启付费调用。

在明确接受模型、规模与本次预算后，旧文本 demo 可执行以下命令；它产生的是 animatic，不是生成式视频，也不启用演员 v3：

```powershell
# Paid text demo only; first prepare the Anna/Elsa assets below.
.venv/Scripts/python -m moodcut run --allow-paid --model-config configs/model.json --max-cost-usd 0.10 --scene configs/demo_scene.json --assets assets/manifest.json --output runs/live-demo-01
.venv/Scripts/python scripts/compare_demo.py --run runs/live-demo-01
```

该故事是已有读信软件示例的改编，不是原电影剧情或正式评价数据。旧协议未命中规划缓存时最多 9 次文本调用；演员 v3 的整块上限为 19 次，具体模型与设置见[方法说明](ACTOR_REVIEW_METHOD.md)。

`--max-cost-usd` 是客户端估算阈值，不是账户硬额度，也不跨进程共享。真实费用以记录和平台账目为准；未知费用保留为 `null` 并停止后续调用，不自动重试。

## 生成式视频流程

### 1. 准备三条件脚本

需要已有的 1.1/generated 脚本 `block.json`，由 `pipeline.run_experiment(..., output_mode="generated", ...)` 产生。规划前冻结实际视频模板哈希、共同输入和生成设置；演员 v3 还需显式传入 `review_protocol="actor_self_review_v3"`。

这里使用程序接口，普通 CLI `plan/review` 不提供 v3 切换。参数、依赖和产物见[脚本编排契约](CONTRACTS.md#67-已实现的生成脚本编排与共享身份记录)与[演员方法](ACTOR_REVIEW_METHOD.md)。脚本准备不创建视频任务；使用真实文本模型仍需相应预算授权。

### 2. 离线编译请求

```powershell
.venv/Scripts/python -m moodcut run --output-mode generated --source-block runs/generated-scripts/block.json --pricing-config configs/video.json --output runs/generated-requests
```

可添加 `--shot-id s2` 选择一个实际存在的镜头；三组始终选择同一镜头，并保留原完整计划中的索引与 seed。输入不能来自旧 animatic 或旧开发对。

此入口不重新规划或审查，不需要 key，不支持付费调用，也不查询实时价格。编译器检查共同输入、实际模板和台词限定修订，输出：

| 文件 | 用途 |
| --- | --- |
| `bundle.json` | 编译后的视频请求与本地报价 |
| `preparation.json` | `prepared_offline` 状态及本次零调用记录 |
| `source_inputs.json` | 完整来源输入 |
| `source_block.json` | 原脚本与历史账目快照 |

报价不是支出，准备完成不是成片完成。详见[离线入口](CONTRACTS.md#68-离线生成入口与单镜头选择)与[生成编译](rendering.md#generated-request-compilation-11)。

### 3. 执行请求

```powershell
.venv/Scripts/python -m moodcut execute-generated --preparation runs/generated-requests --pricing-config configs/video.json --media-origin synthetic --output runs/execution-offline
```

默认仅保存未提交记录与空检查材料。真实执行需要另行接受模型、范围和预算，并显式使用 `--allow-paid --max-cost-usd`。

相同块内的相同请求可复用；失败、中断或未知费用会停止后续提交。`--resume-execution` 只通过 GET 恢复一个已有任务；费用核清后，`--continue-execution` 才显式提交未尝试的镜头。旧记录保留，最终账目不与父快照重复累加。准确参数与预算边界见[执行、恢复与继续](CONTRACTS.md#617-三条件任务执行恢复与继续)。

## 检查与评价生成视频

### 已有本地视频的检查包

```powershell
.venv/Scripts/python scripts/inspect_generated_video.py --preparation runs/generated-requests --evidence runs/local-evidence.json --media-origin provided_local --output runs/video-inspection
```

`local-evidence.json` 遵循[本地回执格式](CONTRACTS.md#69-本地生成回执与费用记录装配)。软件生成的测试媒体须声明 `synthetic`；`provided_local` 只说明文件来自本地，不认证为模型产物。

输出包括观看页、来源与字节哈希、实际抽帧、ffprobe 信息及空白人工检查表。页面显示条件和预期台词，不用于盲评；音轨存在也不证明中文对白、说话人或情绪正确。使用最终 `records/` 账目，不重复累加 `preflight_records/`。该入口不提交或恢复视频任务。

只需装配账目时使用 `assemble-generated-records`；完整观看材料说明见[本地视频检查](rendering.md#local-video-inspection-and-source-binding-11)。

### 资格核对、匿名导出与评分

```powershell
.venv/Scripts/python -m moodcut qualify-generated-records --records runs/video-inspection/records --pricing-config configs/video.json --output runs/qualification
.venv/Scripts/python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --blind-output runs/generated-blind --seed 17
.venv/Scripts/python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --output runs/generated-coverage.json
```

资格报告只核对所选范围的软件证据，不批准正式纳入或主观质量。导出会独立重检来源和复制后的文件；旧报告不能代替当前检查。整块三条件通过才导出，应检查 `exported_clips`，不能把空诊断包当成功导出。

只向评价者分发 `public/`；`PRIVATE/` 含条件映射和来源账目，必须保密。人工填写评分表后再导入：

```powershell
.venv/Scripts/python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --ratings runs/generated-blind/public/ratings.csv --private-key runs/generated-blind/PRIVATE/private_key.csv --output runs/generated-scores.json
```

空模板不能用于评分。未知费用、失败和缺失不当作零或从分母中静默删除；完整块的共享规划只计一次。统计口径、导出条件和副本完整性要求见[评价说明](evaluation.md)。

## 评价离线 animatic

先查看开发配置的任务列表，不调用模型：

```powershell
.venv/Scripts/python -m moodcut evaluate --config configs/experiment.json --dry-run
```

`configs/experiment.json` 保留原开发夹具，不是六故事研究配置，也不确定正式样本量。首页的 `runs/demo-01` 完成后，可检查匿名导出和账目：

```powershell
.venv/Scripts/python -m moodcut evaluate --records runs/demo-01/block.json --blind-output runs/blind-demo-01
.venv/Scripts/python -m moodcut evaluate --records runs/demo-01/block.json --output runs/demo-01/summary-without-ratings.json
```

只有拿到真实人工评分，才添加 `--ratings` 和对应 `--private-key`。默认 CLI 不运行 VBench 或 GPU 推理，图像质量分数不能替代情绪评价。

## 素材与参考资料

初始 Anna/Elsa 素材：

```powershell
.venv/Scripts/python scripts/prepare_references.py --assets
.venv/Scripts/python scripts/prepare_assets.py --selection assets/selection.example.json --output assets/manifest.json --check
```

参考下载使用锁定版本并校验大小与哈希，不运行上游代码；哈希不符时保留文件并报错。`prepare_assets --check` 只核对本地图像与已有清单。自选素材时修改选择清单，去掉 `--check`，输出到新的 manifest 路径；角色 ID 与素材映射必须显式对应。

| 需要的资料 | 准备命令参数 | 大致范围 |
| --- | --- | --- |
| 核心参考源码 | `prepare_references.py` | 33 份文件，178 KB |
| 初始角色图 | `prepare_references.py --assets` | 两张图与说明，1.2 MB |
| 动画素材库 | `prepare_references.py --animation-assets` | 25 个角色、75 张图与说明，57 MB |
| 两篇论文 | `prepare_references.py --papers` | 57 MB |

加 `--check` 可对所选范围离线复核。素材来源和使用限制见[动画素材库](../assets/library/README.md)、[参考索引](REFERENCES.md)及[复用说明](upstream-reuse.md)。原图与参考缓存不提交 Git。

## 旧开发对入口

`scripts/generate_video.py` 保留了从旧成功审查记录准备 baseline/moodcut 两版视频的适配，不能代替当前三条件入口：

```powershell
.venv/Scripts/python scripts/generate_video.py --run runs/live-demo-01 --output runs/video-preview-01
```

默认只生成离线请求与 `preview.html`。旧配置匹配读信开发故事，不能直接套用任意新场景；历史接口和预算边界见[公共契约第 5 节](CONTRACTS.md#5-生成式开发视频独立于原-animatic)与[原实施计划](GENERATIVE_VIDEO_PLAN.md)。其中的历史模型报价不作为当前报价或运行授权。


## 用 AI 开发一个任务

任务分支使用 `<type>/issue-<GitHub编号>-<英文内容>`，例如 `feat/issue-22-shared-planning` 或 `fix/issue-23-dialogue-review`。历史分支已统一放在 `archive/`，不作为新任务起点；本地旧分支同步方法见 [分支规则与迁移表](BRANCHES.md)。

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

- [模块分工、任务卡与协作流程](TEAM.md)
- [公共接口](CONTRACTS.md)
- [参考资料与源码阅读路径](REFERENCES.md)
- [复用范围](upstream-reuse.md)

## S06 真实端到端开发测试

团队使用 `scripts/run_s06_real.py` 进行真实 S06 开发测试。

### 1. 检查输入

    python scripts/run_s06_real.py check --input runs/NEW-S06-RUN

### 2. 执行真实文本测试

需要提前配置 OpenRouter API Key 并获得付费授权。

    python scripts/run_s06_real.py text --input runs/NEW-S06-RUN --text-budget 0.10 --allow-paid

使用 Gemini、DeepSeek 和 actor_self_review_v3。
输出目录存在时禁止重复提交。

### 3. 编译视频请求

    python -m moodcut run --output-mode generated --source-block runs/NEW-S06-RUN/real-text-01/block.json --pricing-config runs/NEW-S06-RUN/heygen-pricing-live.json --output runs/NEW-S06-RUN/video-requests-live

### 4. 生成真实视频

执行前必须核对当前价格、团队预算和素材使用权限。

    python -m moodcut execute-generated --preparation runs/NEW-S06-RUN/video-requests-live --pricing-config runs/NEW-S06-RUN/heygen-pricing-live.json --media-origin provided_local --output runs/NEW-S06-RUN/video-execution-live --allow-paid --max-cost-usd 0.80

如果执行失败或中断，不要直接重新提交付费请求。

### 5. 检查生成视频

    python scripts/run_s06_real.py inspect --input runs/NEW-S06-RUN

本地预算不等于账户硬限额。
实际费用以提供商账目为准。
生成完成不代表视频质量或正式实验验收通过。
