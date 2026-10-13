# MoodCut：所有人的 Agent 从这里开始

所有成员使用仓库中的 `moodcut-team` Skill、公共接口和模块任务卡开展开发。开始任务前同步 main，并核对 GitHub Issue 的负责人和当前状态。

## 队友只需要做什么

1. 在自己的电脑打开 MoodCut 仓库，拉取最新 main，并确认 GitHub 登录的是自己的账号。
2. 看组长分配给自己的真实 GitHub Issue 编号。不要把 MC-03 当成 Issue #3。
3. 把下面这段交给自己的编码 Agent，替换 `N`。

```text
请阅读仓库 AGENTS.md 和 .agents/skills/moodcut-team/SKILL.md，
读取 docs/REFERENCES.md、docs/upstream-reuse.md 和 docs/CONTRACTS.md。
执行 python scripts/prepare_references.py --check；如果只是资料缺失，
允许执行 python scripts/prepare_references.py 从清单固定的公开地址下载，
再校验。若哈希不符，保留原文件并报告，不自动覆盖。
按阅读索引查看我负责模块的上游源码，再完成 GitHub Issue #N 的 PR 1
（若 PR 1 已合并，则完成下一个增量）。
先核对本人认领状态、已有 PR、公共契约和允许修改的文件范围。
允许在本任务范围内更新该 Issue 的进度、提交并推送任务分支、
创建或更新关联的 Draft PR，以及请求任务指定的评审人。
默认离线验证，不调用付费 API，不改公共接口，不合并 PR。
不要只输出计划；完成实现、运行验收并给我实际 PR 链接和结果。
```

统一指令通过文件路径加载共同规则，适用于能够读取仓库文件的编码助手。

Agent 应先复述“我负责哪个 Issue、哪些目录、先交哪个增量”，随后实际工作。若发现别人已经认领或已有同一任务的 PR，应指出冲突；不能另开一个重复实现。

## 参考资料准备

核心源码首次下载后可离线阅读。准备工具使用 Python 3.11+ 标准库，不运行上游代码、不安装上游依赖。PDF 论文与参考图分别通过 `--papers`、`--assets` 显式获取；准备后的路径见 [阅读索引](docs/REFERENCES.md)。

若编码助手不能访问 GitHub Issue，将 Issue 完整正文粘贴给它，并提供负责人信息。它应说明无法核实远端认领状态；提交 PR 仍需可用的 GitHub 登录。

## 五个人读取同一套资料

| 共享内容 | 文件 | 谁维护 |
|---|---|---|
| Agent 的实施、提交和评审流程 | `.agents/skills/moodcut-team/SKILL.md` | P1，修改走 PR |
| 仓库入口与底线 | `AGENTS.md` | P1 |
| 研究目标、边界、模块归属、时间表 | `TEAM_HANDOFF.md` | P1，组内确认 |
| 上游来源、固定版本与阅读顺序 | `docs/REFERENCES.md`、`references/sources.lock.json` | P1 协调，P2/P3 核对各自来源 |
| JSON、函数签名、失败处理 | `docs/CONTRACTS.md` | P1，受影响成员一起评审 |
| 各人的具体交付和验收 | `issues/MC-01-...` 至 `MC-05-...` | 派单前由 P1 填负责人；日常状态在 GitHub Issue |
| 所有 PR 的交付证据 | `.github/PULL_REQUEST_TEMPLATE.md` | P1 |

每次开新任务都读取 main 中的当前规范。所有成员使用同一契约，可自行选择编码助手和编辑器。

## 组长派单

1. 用 `issues/` 的五张任务卡完整正文创建模块 Issue，指定唯一负责人、评审人和依赖链接。MC 编号与真实 Issue 编号分别记录。
2. 让成员同步 main，使用上述统一指令；第一轮只完成各自任务卡的 PR 1。
3. P1 优先合入公共夹具和运行骨架。资料准备工具已经可用，规划/审查/渲染/评估接口仍需按模块任务实现。
4. 核实 main 分支保护：PR、非作者批准、required checks、解决评论、禁止强推。先确认检查实际运行成功，再将其设为 required；文档约定不代表保护设置已启用。

## 评审人与组长的提示

评审人可先让 Agent 做本地审阅，然后本人读结论并决定是否批准：

```text
按 .agents/skills/moodcut-team/SKILL.md 的 review 模式检查 PR #N。
核对对应 Issue、公共契约、改动范围和实际测试，列出阻塞问题及证据。
这次只给我本地审阅结果，不提交 GitHub 审批、不合并。
```

已满足评审条件后，组长可以明确授权合并：

```text
请核实 PR #N 当前版本已有非作者批准、验收和所需 CI 通过，
且阻塞评论已解决；全部满足时 squash merge 此 PR。
若不满足，报告具体缺项，不绕过保护。
```

首个工作日交 Draft PR，每天 21:00 前更新 Issue，24–48 小时交一个可验收增量。组长跟进任务阻塞和评审安排。
