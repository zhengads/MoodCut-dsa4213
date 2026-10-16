# 分支命名与旧分支迁移

## 新任务命名

统一使用 `<type>/issue-<GitHub编号>-<简短英文内容>`。type 按实际增量选择 `feat`、`fix`、`docs`、`test`、`refactor` 或 `chore`；使用小写英文、数字和连字符。编号是 GitHub Issue 编号，不是 P1–P5 或 MC-01–MC-05。分支名不包含 AI 工具名、成员名，不单独使用成员代号。

没有单独 Issue 的仓库维护可用 `docs/branch-naming` 或 `chore/<内容>`，不编造编号。`main` 仍是默认分支，所有改动走 PR；命名规则不改变 API、实验或合并授权边界。

| 当前任务 | 首个增量建议分支 |
|---|---|
| [#8](https://github.com/zhengads/MoodCut-dsa4213/issues/8) | `feat/issue-8-generated-contracts` |
| [#22](https://github.com/zhengads/MoodCut-dsa4213/issues/22) | `feat/issue-22-shared-planning` |
| [#23](https://github.com/zhengads/MoodCut-dsa4213/issues/23) | `fix/issue-23-dialogue-review` |
| [#24](https://github.com/zhengads/MoodCut-dsa4213/issues/24) | `feat/issue-24-video-inspection` |
| [#9](https://github.com/zhengads/MoodCut-dsa4213/issues/9) | `feat/issue-9-generated-evaluation` |

先检查认领和开放 PR；已有同一增量的活动分支就继续使用，不重复开分支。以上是名称建议，不预先创建空分支。下一个独立增量可换内容后缀，仍关联同一 Issue。

## 历史分支归档

`archive/pr-<已合并PR编号>-<内容>` 只保留历史，不是新任务起点。2026-10-16 使用 GitHub 原生改名接口迁移以下 14 条分支，逐条核对 tip SHA 不变，没有重写提交。迁移前没有开放 PR；历史 PR 和提交中的旧名称属于原始记录，不代表仍在使用。

| 旧名（仅用于迁移查找） | 当前归档名 |
|---|---|
| `P1` | `archive/pr-13-foundation` |
| `codex/issue-8-ci-ffmpeg` | `archive/pr-16-offline-ci` |
| `codex/issue-8-generative-video` | `archive/pr-21-generative-video` |
| `codex/openrouter-client` | `archive/pr-18-openrouter-client` |
| `codex/openrouter-demo-config` | `archive/pr-20-demo-config` |
| `codex/paired-dialogue-task-refresh` | `archive/pr-25-team-tasks` |
| `codex/reference-kit-and-onboarding` | `archive/pr-6-reference-kit` |
| `codex/runnable-pipeline` | `archive/pr-19-pipeline` |
| `codex/simplify-project-layout` | `archive/pr-7-project-layout` |
| `docs/pr-review-requirement` | `archive/pr-4-review-policy` |
| `p3提前测试` | `archive/pr-17-dialogue-review` |
| `p4` | `archive/pr-15-animatic-rendering` |
| `p5` | `archive/pr-14-vbench-evaluation` |
| `zhengads-patch-1` | `archive/pr-5-project-rename` |

## 已有本地克隆如何同步

先用 `git status`、`git branch -vv` 检查本地工作。仅在本地确实存在对应旧分支时，按表改名并设置远端跟踪。例如原审查分支：

```powershell
git branch -m "p3提前测试" archive/pr-17-dialogue-review
git fetch origin --prune
git branch --set-upstream-to=origin/archive/pr-17-dialogue-review archive/pr-17-dialogue-review
```

若新名已存在，先比较两条分支，不强制覆盖。本地有未提交或未推送的工作时先保留并核对；改名保留本地提交，不说明这些工作已经合入 main，也不授权向归档分支继续推送。

新任务从最新 main 建活动分支，例如：

```powershell
git switch main
git pull --ff-only origin main
git switch -c feat/issue-22-shared-planning
```

执行示例前先妥善保存工作区，并确认没有对应活动分支/PR；不是要求所有成员创建同一条示例分支。不要为兼容旧名称重新创建旧远端分支。

若克隆只配置拉取 main，看不到改名后的分支，可显式抓取目标分支后再设置跟踪：

```powershell
git fetch origin refs/heads/archive/pr-17-dialogue-review:refs/remotes/origin/archive/pr-17-dialogue-review
```

旧名称的 git pull 不会自动转向新名称。各成员需同步自己的克隆，参见 [GitHub 分支改名说明](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/renaming-a-branch)。
