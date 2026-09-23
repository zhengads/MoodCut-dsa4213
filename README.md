# FilmAgent — DSA 4213 课程项目

> 基于大语言模型的多智能体（LLM-based Multi-Agent）虚拟电影制作框架。
> 本项目为 **DSA 4213** 课程小组作业，选题围绕 FilmAgent 框架的复现、分析与扩展。

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

## 👥 团队成员

> 共 **5 人**。同学加入仓库后请把自己的 GitHub 用户名填进来。

| # | 姓名 | GitHub | 负责模块 |
| --- | --- | --- | --- |
| 1 | 郑明良 | [@zhengads](https://github.com/zhengads) | 待定 |
| 2 | Tang Jiaxin | [@594jx](https://github.com/594jx) | 待定 |
| 3 | <!-- 同学姓名 --> | [@fanx9905-blip](https://github.com/fanx9905-blip) | 待定 |
| 4 | Sona Asatryan | [@ChessLover](https://github.com/ChessLover) | 待定 |
| 5 | <!-- 同学姓名 --> | <!-- @username --> | 待定 |

---

## 🎯 项目目标

> ⚠️ **本小节待小组讨论后确定**，目前是占位内容，讨论后请更新。

- [ ] 明确选题：复现 / 改进 / 应用于新场景（三选一或组合）
- [ ] 确定交付物范围（代码、报告、演示视频等）
- [ ] 确认评分标准与截止时间
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

### 提交与推送

```bash
git add <你改的文件>
git commit -m "feat: 简短说明这次改了什么"
git push -u origin <你的分支>
```

提交信息建议用前缀区分类型：`feat:` 新功能 / `fix:` 修 bug / `docs:` 文档 / `test:` 测试 / `chore:` 杂项。

### 发起 Pull Request

1. 推送后在 GitHub 页面点击 **Compare & pull request**
2. base 选 `main`，compare 选你的分支
3. 填写改了什么、怎么验证的
4. 至少找一名同学 review 后再合并

---

## 📋 任务管理

本项目的任务用 **GitHub Projects 看板** 追踪，列：`Todo` → `In Progress` → `Done`。

- 看板地址：https://github.com/users/zhengads/projects/2
- 详细分工表见 [TASKS.md](TASKS.md)

**使用约定**：
- 开一个任务 → 在 Projects 里建卡片（或建 Issue），指派给负责人
- 开始做 → 卡片拖到 `In Progress`，同时建对应的开发分支
- 做完 → 提 PR，合并后卡片拖到 `Done`
- 卡住了 → 在卡片里留言说明卡在哪，别自己憋着

---

## ⚠️ 注意事项

- **不要提交任何密钥**。API Key、密码、token 一律放 `.env`，已加入 `.gitignore`。
- 大型二进制文件（视频、模型权重）不要直接提交，用网盘或 Git LFS。
- 这个仓库是**私有**的，同学需要先被邀请才能访问。

---

## 📚 参考资料

- 论文：[FilmAgent: A Multi-Agent Framework for End-to-End Film Automation in Virtual 3D Spaces](https://huggingface.co/papers/2501.12909)（arXiv:2501.12909）
- ACM 页面：[SIGGRAPH Asia 2024 Technical Communications](https://dl.acm.org/doi/fullHtml/10.1145/3681758.3698014)
- 项目主页：[filmagent.github.io](https://filmagent.github.io/)
- 官方实现：[github.com/HITsz-TMG/FilmAgent](https://github.com/HITsz-TMG/FilmAgent)
