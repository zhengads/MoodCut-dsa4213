# MoodCut 实施与验收

目标：将 MovieAgent 风格文本规划、两类有界审查、固定素材 animatic 和配对评估连成可运行流程。Python 3.11、Pillow、FFmpeg/ffprobe；MVP 不依赖 GPU 或上游模型。

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
