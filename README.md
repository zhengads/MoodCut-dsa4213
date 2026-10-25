# MoodCut

**让角色围绕目标情绪审查台词，再由编剧统一修订。**

MoodCut 是 DSA4213 课程研究项目：给定故事、两个角色参考图和目标氛围，共同规划分镜，再比较通用审查与情绪导向审查。研究问题是：情绪专项反馈能否让成片更准确地传达目标氛围，同时保持剧情清楚、表达自然？

[观看视频与台词对比](https://zhengads.github.io/MoodCut-dsa4213/) · [快速开始](#快速开始) · [使用指南](docs/usage.md) · [方法说明](docs/ACTOR_REVIEW_METHOD.md) · [开发协作](#开发协作)

## 方法与三组对照

三组从同一份初稿出发，分别保留自己的审查记录：

| 条件 | 处理方式 |
| --- | --- |
| `baseline` | 保留共同初稿，不审查、不修订 |
| `generic_review` | 两位演员分别做一般性台词自审，由同一编剧统一修订 |
| `moodcut` | 两位演员围绕目标情绪分别自审，由同一编剧统一修订 |

生成模式下，**各组只改台词**；场景、动作、镜头、角色参考、声音及生成设置保持共同输入。固定 seed 不保证不同台词生成的画面完全一致。

当前演员协议为 `actor_self_review_v3`：两个审查条件均最多进行两轮编剧修订与必要的演员确认。最终创作分歧保留在记录中，接口错误、未知费用和预算失败则停止流程。完整规则、历史版本和验收记录见[方法说明](docs/ACTOR_REVIEW_METHOD.md)。

## 当前进展

截至 2026-10-25，S06 v3 开发试跑已生成三段真实视频，总费用 **$0.75421676**。[直接观看](https://zhengads.github.io/MoodCut-dsa4213/#s06-index) · [试跑记录与原始结果](docs/pilots/s06-actor-v3-index.md)

这证明了该样例的技术流程跑通；中文对白、人物一致性、自然度和情绪效果仍待人工检查与独立评价。历史成功和失败均保留在[试跑记录](docs/pilots/)中。

后续候选输入为[六个明显情绪情景 v2](docs/studies/six-story-clear-emotions-20261024/README.md)：affectionate、hostile、tense 各两个故事。它们是待执行的研究输入，范围确认不等于付费运行或正式评价已获批准。

## 快速开始

需要 **Python 3.11+**。以下命令从仓库根目录运行，Windows 使用 PowerShell：

```powershell
git clone https://github.com/zhengads/MoodCut-dsa4213.git
cd MoodCut-dsa4213
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m moodcut smoke --mock --output runs/smoke-01
```

Linux/macOS 将 `.venv/Scripts/python` 换成 `.venv/bin/python`。

`smoke` 检查三条件的 JSON 流程，不联网、不需要 API key，也不渲染视频。输出目录必须是新目录；再次运行时换一个名称。

### 生成离线预览视频

先将 **FFmpeg、ffprobe** 加入 PATH，并安装中文字体（Windows 微软雅黑或 Linux Noto Sans CJK）。随后运行：

```powershell
.venv/Scripts/python -m moodcut run --mock --scene tests/fixtures/scene.json --assets tests/fixtures/assets.json --output runs/demo-01
.venv/Scripts/python scripts/compare_demo.py --run runs/demo-01
Start-Process (Resolve-Path runs/demo-01/comparison.html).Path
```

输出包含共同初稿、三组记录和三段静态 animatic。它使用软件夹具检查流程，不能用于比较方法效果。字体问题可通过 `--font` 或 `MOODCUT_FONT` 指定字体文件。

### 选择正确的入口

| 你要做什么 | 入口与边界 |
| --- | --- |
| 检查文本流程 | `smoke --mock`：离线 JSON，无视频 |
| 查看固定图片和字幕预览 | `run --mock`：默认 animatic |
| 从已有生成式脚本准备视频请求 | `run --output-mode generated --source-block ...`：只编译请求 |
| 执行已准备的视频请求 | `execute-generated`：默认离线；真实调用需明确模型、规模和预算 |
| 检查已有视频、匿名导出、汇总人工评分 | [使用指南](docs/usage.md#检查与评价生成视频) |

**默认 `plan/review/smoke/run` 仍使用原 animatic 流程，不自动启用演员 v3。** v3 需要在生成式脚本编排时显式选择协议；准备脚本、编译请求、生成视频是三个阶段。参数和前置条件见[生成式视频流程](docs/usage.md#生成式视频流程)。

## 文档导航

| 内容 | 文档 |
| --- | --- |
| 命令、输出结构、API 配置、素材准备 | [使用指南](docs/usage.md) |
| 演员自审、编剧修订与版本差异 | [方法说明](docs/ACTOR_REVIEW_METHOD.md) |
| 数据结构、接口、共享身份与账目 | [公共契约](docs/CONTRACTS.md) |
| 静态渲染、请求编译与视频检查 | [渲染说明](docs/rendering.md) |
| 匿名导出、人工评分、覆盖率与费用统计 | [评价说明](docs/evaluation.md) |
| 角色参考图、来源与许可状态 | [动画素材库](assets/library/README.md) |
| 历次试跑的设置、结果与失败 | [试跑记录](docs/pilots/) |
| 模块分工、任务卡与分支规则 | [团队协作](docs/TEAM.md) · [分支规则](docs/BRANCHES.md) |

## 开发协作

先阅读 [AGENTS.md](AGENTS.md) 和[团队工作流](.agents/skills/moodcut-team/SKILL.md)，核对 Issue 与已有 PR，只认领未完成的增量。统一开工指令见[用 AI 开发一个任务](docs/usage.md#用-ai-开发一个任务)。

```powershell
git config commit.template .gitmessage
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/prepare_references.py --check
```

视频测试依赖 FFmpeg/ffprobe 与可用字体，可用 `MOODCUT_TEST_FONT` 指定。参考缓存缺失时按[资料准备说明](docs/REFERENCES.md)处理。普通测试和 CI 不调用付费模型。

```text
src/moodcut/         核心模块；prompts/ 集中存放提示词
configs/            模型、渲染与实验配置
tests/              离线测试与 fixtures/
scripts/            素材准备、视频检查和对比工具
docs/               方法、接口、任务与试跑记录
assets/             素材元数据；原图保存在忽略目录
references/         来源锁定清单、阅读索引与本地缓存
runs/               本地运行输出，不提交
```

## 参考与复用

MoodCut 参考 **MovieAgent** 的分阶段规划与素材组织，以及 **FilmAgent** 的审查—修订—复查方法，采用符合本项目契约的独立适配，不是两篇论文的完整复现。

固定版本、阅读路径与引用见[参考资料](docs/REFERENCES.md)及 [references.bib](references/references.bib)；具体采用范围见[复用说明](docs/upstream-reuse.md)。角色图片的署名与提供商接受均不等于取得使用或再分发许可，原始图片不提交到 Git。
