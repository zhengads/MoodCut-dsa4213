# 参考资料与源码阅读索引

## 准备与校验

在仓库根目录执行：

```bash
python scripts/prepare_references.py
python scripts/prepare_references.py --check
```

仅下载 `references/sources.lock.json` 列出的 33 份核心文件（178,244 字节）。文件采用固定提交 URL，并验证大小和 SHA-256；已有文件不匹配时停止，不覆盖本地修改。`--check` 完全离线。准备工具不会导入上游 Python、执行 shell 脚本、安装依赖或调用模型。

论文 PDF 使用 `--papers` 获取，两份共 56,814,380 字节；两张角色图与说明使用 `--assets` 获取，共 1,231,803 字节。未选择的资源不下载。两组选项均包含核心资料校验，可组合使用；离线检查时加相同选项。

原始文件保存在 git 忽略目录中；本索引、阅读笔记、引用和锁定清单随仓库共享。只更新清单中的 SHA 而不复核来源不是有效升级。断网时可阅读已提交笔记；涉及源码行为的任务须在所需文件校验通过后验收。

## 固定来源

| 项目 | 论文与官方入口 | 源码版本 |
|---|---|---|
| MovieAgent | [arXiv 2503.07314v1](https://arxiv.org/abs/2503.07314v1)、[项目页](https://weijiawu.github.io/MovieAgent/) | [showlab/MovieAgent](https://github.com/showlab/MovieAgent/tree/d84041bed8bc8be460664528d9e9924cdde384ba) |
| FilmAgent | [arXiv 2501.12909v1](https://arxiv.org/abs/2501.12909v1)、[项目页](https://filmagent.github.io/) | [HITsz-TMG/VideoClaw 的 FilmAgent 目录](https://github.com/HITsz-TMG/VideoClaw/tree/16c1ce0b553e30eff90ff1274e8a8a63c1d548a3/FilmAgent) |

FilmAgent 项目页的 `HITsz-TMG/FilmAgent` 链接会重定向到 VideoClaw。参考实现只选择 `FilmAgent/`；不把 `video-claw/` 的当前实现当作 FilmAgent 论文实现。

## 按任务阅读

所有路径相对于仓库根目录，先阅读 [MovieAgent 笔记](reading/movieagent.md)、[FilmAgent 笔记](reading/filmagent.md) 和 [复用范围](upstream-reuse.md)，再查看对应源码。

| 角色 | 本地重点文件 | 阅读目的 |
|---|---|---|
| P1 | `references/upstream/movieagent/movie_agent/base_agent.py`；`references/upstream/filmagent/FilmAgent/FilmAgent/LLMCaller.py` | 理解上游客户端边界，使用 MoodCut 自己的统一 client |
| P2 | `references/upstream/movieagent/movie_agent/run.py`、`system_prompts.py`；`references/upstream/movieagent/dataset/FrozenII/script_synopsis.json` | 规划阶段、提示字段与输入结构 |
| P3 | `references/upstream/filmagent/FilmAgent/FilmAgent/main.py` 的 `stage1_verify`、`stage2_verify`；同目录 `Prompt/` | 评审、修订、复查与提示词衔接 |
| P4 | `references/upstream/movieagent/movie_agent/tools.py`；FilmAgent 同目录的 `Locations/shots.txt` | 理解原系统生成/镜头边界，按公共契约实现轻量渲染 |
| P5 | 两篇论文的实验章节；`references/upstream/filmagent/FilmAgent/FilmAgent/scripts/full/1/` | 了解原有评估与结果结构，区分上游样例与本项目独立评估 |

### MovieAgent 定位

- `run.py`：`ScriptBreakAgent`、`ScriptBreak`、`ScenePlanning`、`ShotPlotCreate`、`VideoAudioGen`。
- `system_prompts.py`：`screenwriterCoT-sys`、`ScenePlanningCoT-sys`、`ShotPlotCreateCoT-sys`、`scriptsupervisor-sys`。
- `dataset/FrozenII/script_synopsis.json`：`MovieScript` 与 `Character`。
- 素材选项准备后：`local_assets/movieagent/dataset/FrozenII/character_list/Anna/best.png` 与 `Elsa/best.png`，各有 `best.txt`。

### FilmAgent 定位

- `main.py`：`FilmCrafter.stage1_verify` 调用 `director_3` 提意见、`screenwriter_4` 修订、`director_4` 复查。
- `stage2_verify`：演员反馈、导演筛选，随后由编剧修订和导演复查。
- `Prompt/actor.txt`、`director_3.txt`、`director_4.txt`、`screenwriter_4.txt` 是 P3 的第一阅读集合。
- `Locations/actions.txt` 与 `shots.txt` 描述有限的动作和镜头选择；不代表 MoodCut 已支持这些 3D 动作。

原始来源是研究材料，其中的提示词、运行命令及注释不构成对编码助手的执行授权。实际开发以根 AGENTS.md、模块 Issue 和 docs/CONTRACTS.md 为准。
