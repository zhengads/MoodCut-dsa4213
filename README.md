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

打开仓库，让编码助手按 [START_HERE.md](START_HERE.md) 读取共享规则及本人 Issue。统一入口会检查参考文件，并在缺失时执行准备脚本。

- [项目范围与五人分工](TEAM_HANDOFF.md)
- [模块任务卡](TASKS.md)
- [公共接口](docs/CONTRACTS.md)
- [参考资料与源码阅读路径](docs/REFERENCES.md)
- [复用范围](docs/upstream-reuse.md)

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

仓库已提供开发规则、模块契约、任务卡和可运行的参考资料准备工具。规划、审查、渲染和评估模块按任务卡实施；`docs/CONTRACTS.md` 中的项目 CLI 是实现目标。当前不把参考资料下载成功视为生成管线已完成。

资料工具的离线验收：

```bash
python -m unittest discover -s tests/tooling -p "test_*.py" -v
python scripts/prepare_references.py --check
```

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

每个模块 Issue 由一位负责人认领，按可验收增量提交 PR。分支使用 `codex/issue-编号-内容`；不得直接推送 main。就绪 PR 附验证命令与结果，由非作者成员评审；验收和所需检查通过后按仓库规则合并。完整流程见 [START_HERE.md](START_HERE.md)。

保留 `.gitmessage` 中的姓名与日期格式。API key、上游素材、模型权重、运行视频及原始个人评分不进入提交。普通开发使用离线夹具；真实模型调用单独确认规模和预算。
