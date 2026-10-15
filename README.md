# MoodCut

DSA4213 课程项目：面向情绪表达的分镜审查与局部修订。

给定故事、角色素材和目标氛围，MoodCut 规划初始分镜，定位情绪表达不足的镜头，对台词、叙述、裁切和停留时长进行受约束修改，再输出固定素材动态分镜。研究问题是：情绪专项反馈能否比通用审查更准确地传达目标氛围，同时保持剧情清楚和表达自然？

## 开始协作

```bash
git clone https://github.com/zhengads/MoodCut-dsa4213.git
cd MoodCut-dsa4213
git config commit.template .gitmessage
python scripts/prepare_references.py
```

参考资料准备仅需 Python 3.11+ 和网络，无第三方 Python 依赖，无需 API key。默认下载固定版本的 33 份核心源码、提示词和样例，约 178 KB；再次运行验证缓存，不重复下载。

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
完成任务卡的 PR 1；若已合并，则完成下一个可验收增量。
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

## 目录

```text
src/moodcut/
  __init__.py
  __main__.py       命令行入口
  client.py         公共 LLMClient / FakeClient
  validation.py     结构检查
  pipeline.py       三条件流程编排
  importer.py       上游输入适配
  planner.py        规划与字段归一化
  reviewer.py       通用/情绪审查
  patches.py        受约束修改
  renderer.py       画面、字幕与视频
  evaluation.py     配对、盲评导出与指标
  prompts/          规划和审查提示词
configs/            模型、渲染和实验配置
tests/             测试文件平铺；共享数据在 fixtures/
assets/             素材清单；原始素材在 raw/，不提交
scripts/            资料准备等辅助脚本
references/         上游资料索引、锁定清单和本地缓存
docs/               分工、契约、实施计划和 tasks/ 任务卡
pyproject.toml      Python 包安装与测试配置
.agents/            编码协作 Skill
.github/            PR 模板和 CI
```

上述代码文件和目录已纳入 Git。FakeClient、结构验证、审查修订、固定素材渲染和 VBench 评估工具已有实现；规划与整体编排仍待完成。提示词、配置和共享夹具沿用任务卡指定路径。`assets/raw/` 和 `runs/` 按素材准备或运行需要创建，内容不提交。

按文件范围认领任务；同一目录内的不同文件可由不同成员并行开发。共享模型/渲染配置归 MC-01，`configs/pilot.json` 等实验配置归 MC-05。

## 系统流程

```text
故事 + 目标氛围 + 角色素材
             ↓
       分阶段规划初稿
             ↓
   ┌─────────┼──────────┐
   初稿      通用审查    情绪专项审查
   不修改    局部修订    局部修订
   └─────────┼──────────┘
             ↓
       统一渲染与人工盲评
```

| 条件 | 行为 |
|---|---|
| baseline | 初稿直接渲染 |
| generic_review | 通用质量审查、局部修改、一次复查 |
| moodcut | 情绪专项审查、局部修改、一次复查 |

三条件共享初稿、故事与素材；两个审查条件使用相同模型配置、调用上限和可修改字段。第一版支持 affectionate、suspicious、hostile 三类目标氛围，两个角色、最多六个镜头、60–90 秒。输出为图片、字幕与裁切组成的 animatic。

## 当前开发状态

OpenRouterClient 已接入公共 LLMClient 接口，FakeClient、结构验证、共享夹具、审查修订、渲染和 VBench 工具也已提供。`importer.py`、`planner.py`、`pipeline.py` 仍待实现。项目 CLI 当前支持帮助、版本和不联网的 check-client；plan/review/render/smoke/evaluate 子命令尚待集成。离线测试通过不代表真实情绪效果已验证。

资料工具的离线验收：

```bash
python -m unittest discover -s tests -p "test_prepare_references.py" -v
python scripts/prepare_references.py --check
```

## OpenRouter 接入

安装项目后，编辑 `configs/model.json`：填写已确认的 OpenRouter 模型 ID，以及输入/输出的每百万 token 美元单价。初始值为 null，客户端不会自行选模型或猜价格。保持三条件使用同一份模型配置。`temperature` 默认 0，单次网络超时默认 60 秒。

API key 只从进程环境变量 `OPENROUTER_API_KEY` 读取。`.env.example` 是空模板，程序不会自动加载 `.env`。在 PowerShell 7 中可以这样设置并检查：

```powershell
python -m pip install -e ".[dev]"
$env:OPENROUTER_API_KEY = Read-Host 'OpenRouter API key' -MaskInput
python -m moodcut check-client --config configs/model.json --max-cost-usd 0.05
```

`check-client` 只验证本地配置，不联网、不验证 key 是否有效，也不产生扣费。示例中的 0.05 是本地检查参数，不代表已授权运行。key 不写进共享 JSON、PR 或日志。

经确认模型、规模和本次费用上限后，规划/审查通过同一个客户端调用：

```python
from moodcut.client import OpenRouterClient

# Only run after the model, scale and this budget have been confirmed.
client = OpenRouterClient.from_env(
    "configs/model.json", allow_paid=True, max_cost_usd=0.05,
)
result = client.complete_json(
    stage="connection_check",
    system="Return only a JSON object with a boolean field ok.",
    user='Return {"ok": true}.',
    max_output_tokens=32,
)
print(result)
print(client.calls)  # usage/fees/status; does not contain the API key or prompts
```

真实客户端维持 `complete_json(...) -> dict`，可直接传入 `review_and_revise`，其他模块无需另写 API 客户端。每次调用只发送当前 system/user，不保留聊天历史。一次方法调用至多发出一次 HTTP 请求，不重试、不自动切换模型；不支持 JSON 输出的提供商会被过滤。

费用和 token 逐次保存在 `client.calls`，失败请求也记录。`provider_cost_usd` 来自 OpenRouter 的 usage.cost，`estimated_cost_usd` 根据返回 token 数和配置单价估算，缺失值为 null。`client.spent_usd` 是已知实际费用之和；任一次费用未知时返回 None，并阻止该实例继续发送请求，先核对平台账单。

`max_cost_usd` 是单个客户端实例的本地估算阈值：请求前用输入 UTF-8 字节数加 64 的固定余量估算输入 token，并预留最大输出成本；实际 token 由模型 tokenizer 决定。因此它不是平台硬上限，也不能协调五个人的并发用量。请求同时设置提供商的 token 单价上限和零按次附加费。团队共享 15 美元额度应在 OpenRouter 端设置 key/团队额度并分配本次预算；重新创建客户端不会继承先前实例账目。

本地离线验收：`python -m pytest tests/test_client.py tests/test_patches.py tests/test_reviewer.py -q`。测试拦截 HTTP 并使用自制响应，不需要真实 key，不调用模型。此接入尚未进行真实 API 验证。

协议依据：[Chat Completions 与 usage](https://openrouter.ai/docs/api_reference/overview)、[提供商参数与价格上限](https://openrouter.ai/docs/guides/routing/provider-selection)、[平台费用控制](https://openrouter.ai/docs/guides/best-practices/spend-controls)。

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

一个模块 Issue 由一位负责人认领，按可验收增量提交 PR。分支使用 `codex/issue-编号-内容`，所有改动走 PR。提交前检查当前 diff、接口、测试结果和敏感文件；在 PR 描述记录自查结论。通过验收、所需 CI 和现有仓库规则后，作者可自行合并。无需固定评审人或额外的同伴批准。

自查记录写在 PR 描述中；作者不能给自己的 PR 提交 GitHub 的 Approve 审批。需要 AI 合并时可明确下达：

```text
请自查 PR #N 当前版本的改动和验收证据，将结论更新到 PR 描述。
确认没有阻塞问题、所需检查通过且符合仓库规则后，squash merge 此 PR。
如果有缺项，报告具体问题，不绕过保护。
```

保留 `.gitmessage` 的姓名与日期格式。API key、上游原始素材、模型权重、运行视频及原始个人评分不进入提交。普通开发使用离线夹具；真实模型调用单独确认规模和预算。
