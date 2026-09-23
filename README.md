# FilmAgent — DSA 4213 课程项目

> 本项目为 **DSA 4213** 课程小组作业，参考 **FilmAgent** 与 **VideoClaw** 两套 LLM 多智能体视频生成框架，
> 重点关注其产出视频的**评测方法**（主观感受为主、客观 benchmark 为辅）。

---

## 📖 什么是 FilmAgent

FilmAgent 是一个端到端自动化虚拟电影制作的 LLM 多智能体协作框架，由哈工大（深圳）与清华大学联合提出，
发表于 **SIGGRAPH Asia 2024**（论文：*FilmAgent: Automating Virtual Film Production Through a
Multi-Agent Collaborative Framework*，arXiv:2501.12909）。

它把真实电影剧组的分工映射到智能体上，用四个角色协作完成制作：

| 角色 | 智能体 | 职责 |
| --- | --- | --- |
| 🎬 导演 | Director | 审阅剧情连贯性、动作合理性，最终裁定分镜方案 |
| ✍️ 编剧 | Screenwriter | 把创意发展成故事大纲与分镜脚本 |
| 🎭 演员 | Actor | 提供角色一致性反馈（台词、动作是否符合人设） |
| 📷 摄影师 | Cinematographer | 为每句脚本分配镜头类型与机位 |

### 三个核心阶段

1. **Idea Development（创意开发）** — 把头脑风暴的想法结构化为故事大纲
2. **Scriptwriting（剧本创作）** — 细化每个场景的对白与角色动作
3. **Cinematography（摄影）** — 为每个镜头确定机位方案

### 两种协作机制（本项目的分析重点）

- **Critique-Correct-Verify（批评—修正—验证）**：用于剧本创作。编剧起草 → 导演批评 → 编剧修正 → 导演验证，
  演员在此过程中提供人设一致性反馈，由导演过滤聚合。
- **Debate-Judge（辩论—裁决）**：用于摄影决策。两名摄影师各自独立分配镜头方案，就分歧进行多轮辩论，
  最后由导演综合裁定。

> 论文实验显示：完整的 Group 版本在所有评测维度上均优于单智能体基线（Chain-of-Thought）
> 和更强的单体模型（o1），说明**良好的多智能体协作机制**比单纯堆模型能力更有效。

### 运行环境

框架运行在 **Unity 3D** 虚拟环境中，使用预定义场景（公寓厨房、客厅、会议室等）。
依据"电影语言"定义了 9 种镜头类型（3 种静态：特写/中景/远景；6 种动态：摇摄/变焦/弧拍等），
共 165 个静态镜头与 107 个动态镜头。语音由 ChatTTS 生成，实验使用 GPT-4o。

---

## 📖 什么是 VideoClaw

VideoClaw 是 **FilmAgent 同一个团队（哈工大深圳 TMG + 阿里）的第二代开源框架**，定位是「AI 全自动化视频生成员工」。
相比 FilmAgent 的 Unity 3D 虚拟拍摄，VideoClaw 直接对接**真实的视频生成模型**，产出可交付的成片。

> ⚠️ 注意重名：GitHub 上还有 `T0UGH/videoclaw`（CLI 工具）、Synclip 的 VideoClaw（节点式工作台）等
> 完全无关的项目。我们参考的是 **[HITsz-TMG/VideoClaw](https://github.com/HITsz-TMG/VideoClaw)**。

### 六阶段流水线

**剧本策划 → 角色/场景设计 → 分镜规划 → 参考图生成 → 视频生成 → 后期剪辑**

每个阶段的产出会约束下一阶段，形成逐级收敛的制作流程。

### 多智能体「数字剧组」

| 阶段 | 智能体 |
| --- | --- |
| 剧本 | ScriptWriterAgent |
| 角色设计 | CharacterDesignerAgent |
| 分镜 | StoryboardAgent |
| 参考图 | ReferenceGeneratorAgent |
| 视频生成 | VideoDirectorAgent |
| 剪辑 | VideoEditorAgent |

由 orchestrator 以状态机（pending / running / waiting / completed）统一调度，并持久化会话。

### 值得关注的设计（可能对我们的选题有用）

- **Human-in-the-loop 停靠点**：在关键阶段（约 7~9 个确认点）暂停，让人检查并修改脚本、角色、分镜、参考图和片段 ——
  这正好对应我们想做的**主观评价介入**。
- **场记（script supervisor）状态库**：把人物关系、空间位置、分镜版本作为结构化资产存储，用于保持长视频的一致性。
- **VLM 闭环质检**：用视觉语言模型审查中间图片/帧是否符合脚本。
- **无限续写**：支持短剧的逐集连载。

### 技术栈

视频生成对接 **Wan、Kling** 等主流模型（支持首帧生视频、首尾帧生视频、参考图生视频）；
LLM/VLM 侧支持 DashScope、DeepSeek、GPT、Gemini、Seedream、即梦。
部署为本地 FastAPI（:8000）+ Next.js（:3000），MIT 协议。

---

## 🔗 两个框架的对比

| 维度 | FilmAgent（2024） | VideoClaw（2026） |
| --- | --- | --- |
| 出品方 | 哈工大深圳 + 清华 | 哈工大深圳 TMG + 阿里 |
| 拍摄环境 | Unity 3D 虚拟场景 | 真实视频生成模型 |
| 制作阶段 | 3 阶段（创意/剧本/摄影） | 6 阶段（含角色设计、参考图、剪辑） |
| 智能体 | 4 个角色（导演/编剧/演员/摄影师） | 6 个阶段智能体 + orchestrator |
| 协作机制 | Critique-Correct-Verify、Debate-Judge | 状态机调度 + 人工停靠点 |
| 长视频一致性 | 有限（单场景） | 场记状态库 + VLM 质检 |
| 输出 | 虚拟场景合成视频 | 可交付成片 |

**演进脉络**：FilmAgent 验证了「多智能体协作优于单智能体」，VideoClaw 把这个思路推进到真实生产流程，
并引入了人工介入点。这为我们的选题提供了很好的切入点。

---

## 👥 团队成员

> 共 **5 人**。同学加入仓库后请把自己的 GitHub 用户名填进来。

| # | 姓名 | GitHub | 负责模块 |
| --- | --- | --- | --- |
| 1 | 郑明良 | [@zhengads](https://github.com/zhengads) | 待定 |
| 2 | Tang Jiaxin | [@594jx](https://github.com/594jx) | 待定 |
| 3 | <!-- 同学姓名 --> | [@fanx9905-blip](https://github.com/fanx9905-blip) | 待定 |
| 4 | Sona Asatryan | [@ChessLover](https://github.com/ChessLover) | 待定 |
| 5 | <!-- 同学姓名 --> | <!-- @username --> | 待定 |

> 第 5 位同学的 GitHub 用户名待补充。

---

## 🎯 项目目标

> ⚠️ **选题仍在讨论中，下面是目前的初步方向**（2026-09-23），定稿后请更新。

### 核心思路：借用成熟技术，主打评测方法

我们**不打算从零造一套视频生成系统**，而是复用 FilmAgent / VideoClaw 已验证的多智能体管线，
把研究重心放在**如何评价产出的视频**上。

### 为什么评测是切入点

视频生产类模型的产出质量**高度依赖人的主观感受** —— 一个镜头是否「好看」「连贯」「符合预期」，
很难被单一数值指标完全刻画。而现有的自动评测（FVD、CLIPScore 等）与人的真实观感之间往往存在落差。

因此我们认为：**主观评价应当作为主要依据，客观 benchmark 作为补充佐证。**

### 计划的评测方案（待细化）

| 类型 | 方式 | 说明 |
| --- | --- | --- |
| **主观**（主要） | 人工评分 / 问卷 | 邀请真人观看片段，按维度打分（如动作准确性、剧情连贯性、镜头合理性） |
| **客观**（辅证） | Benchmark 跑分 | 跑现成的自动指标，与主观结果做对比分析 |

> FilmAgent 论文本身就是用 5 分制李克特量表做人工评测的（4 个维度：动作准确性、剧情连贯性、
> 人设贴合度、镜头合理性）。我们可以沿用并调整这套维度。

### 待确定

- [ ] 具体在哪个环节做评测（全流程 / 只评某一阶段）
- [ ] 主观评测的维度设计与样本量
- [ ] 客观 benchmark 选哪些指标
- [ ] 是否需要自己复现一套 baseline 做对比
- [ ] 最终交付物范围（代码 / 实验报告 / 演示视频）
- [ ] 拆解为可分配的任务（见 [TASKS.md](TASKS.md)）

---

## 🗂️ 仓库结构

```
filmagent-dsa4213/
├── README.md          # 项目说明（本文件）
├── TASKS.md           # 任务分工与进度追踪
├── docs/              # 文档：调研笔记、设计稿、会议记录
├── src/               # 源代码
├── tests/             # 测试
└── .gitignore
```

---

## 🚀 快速开始

> ⚠️ 项目尚未初始化代码，以下为占位说明，待技术选型确定后更新。

```bash
# 1. 克隆仓库
git clone https://github.com/zhengads/filmagent-dsa4213.git
cd filmagent-dsa4213

# 2. 配置环境变量（复制模板后填入自己的密钥）
# cp .env.example .env

# 3. 安装依赖（技术栈待定）
# ...
```

### 环境要求

| 项目 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.11+ | 待定，视技术选型 |
| Git | 2.x | 必须 |
| <!-- LLM API Key --> | — | 需要自备，**不要提交到仓库** |

---

## 🤝 协作流程

> 参照团队协作规范，**每次开发前先切到自己的分支**，不要直接在 `main` 上改。

### 开始一个新任务

```bash
git checkout main
git pull
git checkout -b <你的分支名>      # 例如 feat/script-agent
```

### 继续之前的分支

```bash
git checkout main
git pull
git checkout <你的分支>
git rebase main                 # 或者 git merge main（分支落后较多时）
```

### 提交格式（**必填**）

提交信息**必须包含姓名和日期**，这样出了问题能直接找到人。

```
<类型>: <一句话说明改了什么>

姓名: <你的姓名>
日期: <YYYY-MM-DD>
```

**类型**：`feat` 新功能 / `fix` 修 bug / `docs` 文档 / `test` 测试 / `refactor` 重构 / `chore` 杂项

**示例**：

```
feat: 实现编剧智能体的初稿生成

姓名: 郑明良
日期: 2026-09-25
```

推送：

```bash
git add <你改的文件>
git commit            # 会自动弹出模板，按提示填
git push -u origin <你的分支>
```

> **克隆仓库后请先跑一次这条命令**，之后 `git commit` 就会自动弹出格式模板：
>
> ```bash
> git config commit.template .gitmessage
> ```
>
> 用 `git commit -m "..."` 的话就自己按格式写全。

### 发起 Pull Request

> ⚠️ **`main` 分支已开启保护，不能直接推送** —— 所有改动必须走 PR。

1. 推送后在 GitHub 页面点击 **Compare & pull request**
2. base 选 `main`，compare 选你的分支
3. 填写改了什么、怎么验证的
4. **必须有一名同学点 Approve 才能合并** —— 这是分支保护强制的，自己不能合自己的 PR

> 💡 所以分工上建议**互相 review**：你提的 PR 找别人看，别人提的你来看。
> 5 个人轮着来，不会成为瓶颈。

---

## 📋 任务管理

本项目的任务全部用 **GitHub Issues** 追踪，在 [Issues 页面](https://github.com/zhengads/filmagent-dsa4213/issues) 查看。
详细分工表见 [TASKS.md](TASKS.md)。

**标签表示状态**：

| 标签 | 含义 |
| --- | --- |
| `待开始` | 还没人接手 |
| `进行中` | 有人在做 |
| `受阻` | 卡住了，需要协助 |
| `已完成` | 做完了，关掉 Issue |

**使用约定**：

- **认领任务** → 在 Issue 里留言说一声，加上 `进行中` 标签
- **做完** → 关掉 Issue，改成 `已完成` 标签
- **卡住了** → 加上 `受阻` 标签并在 Issue 里说明卡在哪，别自己憋着
- **讨论** → 一律在 Issue 里留言，不要私聊，方便其他人看到上下文

---

## ⚠️ 注意事项

- **不要提交任何密钥**。API Key、密码、token 一律放 `.env`，已加入 `.gitignore`。
- 大型二进制文件（视频、模型权重）不要直接提交，用网盘或 Git LFS。
- 这个仓库是**私有**的，同学需要先被邀请才能访问。

---

## 📚 参考资料

### FilmAgent

- 论文：[FilmAgent: A Multi-Agent Framework for End-to-End Film Automation in Virtual 3D Spaces](https://huggingface.co/papers/2501.12909)（arXiv:2501.12909）
- ACM 页面：[SIGGRAPH Asia 2024 Technical Communications](https://dl.acm.org/doi/fullHtml/10.1145/3681758.3698014)
- 项目主页：[filmagent.github.io](https://filmagent.github.io/)
- 官方实现：[github.com/HITsz-TMG/FilmAgent](https://github.com/HITsz-TMG/FilmAgent)

### VideoClaw

- 官方实现：[github.com/HITsz-TMG/VideoClaw](https://github.com/HITsz-TMG/VideoClaw)
- 英文说明：[README_EN.md](https://github.com/HITsz-TMG/VideoClaw/blob/main/README_EN.md)
- 项目介绍（中文）：[哈工大张民团队联合阿里开源全流程 AI 多智能体导演框架 VideoClaw](https://www.dtinsight.com.cn/nd.jsp?id=4003)

> ⚠️ GitHub 上有多个同名项目（`T0UGH/videoclaw`、Synclip 的 VideoClaw 等），与本文所指**无关**。
> 认准 `HITsz-TMG/VideoClaw`。
