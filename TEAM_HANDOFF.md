# MoodCut 五人实施分工

日期：2026-10-13；全部日期与每日沟通时间采用北京时间。以下时间是组内建议里程碑，正式课程截止时间由组长核实。

## 开发约定

大家从现在开始按下面五个模块开发。我们的第一版目标是：输入同一段故事、角色素材和目标情绪，生成初始分镜，经过情绪审查和局部修改，再用同一渲染器输出修改前后动态分镜。先交一个完整开发样例，再做实验。

每人只认领自己的 Issue 和文件范围。开始当天必须开 Draft PR，不能等整个模块写完才第一次上传。每天 21:00 前在自己的 Issue 更新：今天交付了什么、PR 链接、下一步、阻塞。完成以 PR 合并和验收通过为准，不以“本地能跑”或“已写完”为准。

P1 负责公共接口和集成；P2 负责 MovieAgent 适配与素材；P3 负责情绪审查与修订；P4 负责动态分镜渲染；P5 负责对照实验与评估工具。具体任务卡在 issues/。大家先读 docs/CONTRACTS.md，不自行改字段名；上游资料按 docs/REFERENCES.md 的固定版本和阅读顺序准备。

## 1. 交付目标与第一版边界

研究问题：在相同故事、目标情绪与可用素材下，具体到镜头的情绪反馈和受约束修改，能否比通用审查更准确地传达目标氛围，同时保持剧情和自然度？提升是待检验假设，不预写结论。

第一条开发样例的交付：一个故事输入、一份初始分镜、一份评审、一份修改补丁、一份修订分镜、两段 60–90 秒的 animatic、一次运行的调用与费用记录。开发样例由团队编写或从上游明确改编并标注来源，不能作为独立盲测证据。

第一版支持三种目标 tone：`affectionate`、`suspicious`、`hostile`，分别表示亲切、怀疑、敌意。默认两名角色，最多六个镜头，单段 animatic 时长 60–90 秒。先只验证一段故事的一种 tone；三种 tone 用于后续评估，不在第一个 PR 里扩展。

第一版采用固定角色图片、字幕、叙述字幕、裁切和停留时长；动作可以用明确标注的叙述字幕表达，不能把字幕中写了动作称为画面已经演出了动作。没有新动作生成、口型同步、语音克隆、Unity 环境、视频扩散模型训练或自动下载权重。

第一版以情绪反馈为主线，暂不实现角色私有知识系统、平等投票、复杂多 Agent 辩论和联合加权评分。正式实验规模在开发 pilot 后由团队确认。

## 2. 哪些复用，哪些自己实现

| 项目 | 使用方式 | 责任人 | 验收边界 |
|---|---|---|---|
| MovieAgent `dataset/*/script_synopsis.json` | 复用梗概和角色名单的输入结构；开发样例可选一组，记录原始来源和改编 | P2 | 读出 MovieScript 与 Character，保留来源版本 |
| MovieAgent `character_list/*/best.png` 等 | 作为候选角色参考图；只下载本次选择的小集合，建立素材 manifest | P2 | 路径存在、尺寸可读、角色对应正确；不假装是背景或动态动作库 |
| MovieAgent `system_prompts.py` | 参考 Director/Scene/Shot 规划提示及结构，适配为本项目受限输出 | P2 | 记录复用和修改；未经确认许可不在公开仓库整份复制上游文件 |
| MovieAgent `run.py` 的阶段顺序 | 借用剧本→场景→镜头的规划思路，编写独立文本适配器 | P2 | 不 import 原 ScriptBreakAgent：其初始化会进入生成工具和模型依赖 |
| FilmAgent Critique–Correct–Verify | 参考审查、修改、复查的控制流程，明确引用 | P3 | 最多一轮；保存每步输入输出和未解决意见 |
| OpenRouter 客户端、预算与日志 | 自己写统一适配层，支持 FakeClient 离线模式 | P1 | key 不进代码；计数准确；未知价格不作零成本 |
| 数据契约、运行编排、结构验证 | 自己写 | P1 | 所有模块能用同一夹具接起来 |
| 情绪专项与通用 Reviewer、局部修订器 | 自己写，两者共享预算和执行逻辑 | P3 | 输出到 shot_id，局部修改，失败保留原版本 |
| 图片与字幕渲染器 | 自己写 Pillow/FFmpeg 轻量方案 | P4 | 分镜变化确实影响成片；两种版本同一参数 |
| 对照运行、盲评导出和结果汇总 | 自己写 | P5 | 三条件同初稿；缺失/失败不被静默移除 |

禁止把“参考提示词 + 轻量渲染器”称作完整复现 MovieAgent，也不直接和论文表格中的视频分数比较。对照命名统一为“MovieAgent-inspired planning baseline”，方法章节列出适配与渲染差异。

## 3. 五个人的职责与提交范围

| 角色 | GitHub 负责人 | 主要交付 | 独占修改范围 | 首个 PR | 就绪 PR 的主要评审人 |
|---|---|---|---|---|---|
| P1 | @zhengads | 公共接口、客户端、预算日志、CLI、集成、CI | `src/moodcut/core/`、`cli.py`、包入口、根配置、CI、共享文档与夹具 | 10/14：契约+离线骨架 | P2；执行与费用逻辑请 P3 补审 |
| P2 | 以 Issue 指派为准 | 上游素材 manifest、梗概导入、规划适配 | `src/moodcut/planning/`、`prompts/planning/`、`assets/manifest.json`、`scripts/prepare_assets.py`、`tests/planning/` | 10/15：离线导入与归一化 | P1 |
| P3 | 以 Issue 指派为准 | 通用/情绪评审、修订、一次复查 | `src/moodcut/review/`、`prompts/review/`、`tests/review/` | 10/15：离线评审与补丁验证 | P1；P5 检查对照是否公平 |
| P4 | 以 Issue 指派为准 | FFmpeg 渲染、接触表、时间轴 | `src/moodcut/rendering/`、`tests/rendering/`、`docs/rendering.md` | 10/15：固定夹具转视频 | P2 |
| P5 | 以 Issue 指派为准 | 配对实验索引、盲评 CSV、统计与报告表 | `src/moodcut/evaluation/`、`configs/evaluation/`、`tests/evaluation/`、`docs/evaluation.md` | 10/15：离线对照分配与统计 | P3 |

表中范围是摘要，具体允许路径以五张任务卡为准；P2 的 `docs/upstream-reuse.md`、P3 的 `docs/review.md` 也分别属于对应模块。P1 还维护共享 Skill、AGENTS.md、START_HERE.md、参考来源清单和资料准备工具。

P1 负责整合，各模块按表中安排交叉评审。一个人一个模块不等于一条长期分支：每个可验收增量单独 PR。

## 4. 并行依赖和合并顺序

1. P1 先把 `CONTRACTS.md`、包骨架、FakeClient、共享夹具和第一条离线 CI 合入 main；10/14 当天完成这个最小阻塞项。
2. P2、P3、P4、P5 从这个 main 各自开分支，用夹具开发，不等其他人完成模块。
3. 先合入 P2 的离线导入，再合 P3 的纯补丁应用器和 P4 的离线渲染；这些 PR 不调用任何 API。
4. P1 接起 baseline/moodcut 离线 smoke；P5 接入三条件运行与统计。
5. 仅在组长明确同意规模、模型和费用后，进行一次真实 pilot。付费能力不放进普通 CI。

P1 可以先提供 fixture 驱动的 CLI 路由，未合入模块的命令明确报 module-not-ready，不允许假输出成功。Draft PR 可以不完整；Ready PR 必须能在当前 main 上独立验收。

## 5. 里程碑

| 日期 | 交付 |
|---|---|
| 10/13–10/14 | 确认成员账号；创建五个 Issue；契约、夹具、骨架和 PR 模板合并 |
| 10/15–10/17 | 四个模块首轮离线 PR 合并；一份输入能产生 baseline 与修订版分镜及 animatic |
| 10/18–10/20 | 经费用确认的真实 pilot；检查修改有无视觉效果；修复接口、字幕、断言和记录问题 |
| 10/21 | 根据 pilot 成本和人工标注速度，确认正式样本量、tone、模型、预算、评分规则；冻结配置 |
| 10/22–10/26 | 在已确认范围内运行对照与人工评价；保留失败与全部分母，不临时挑最好案例 |
| 10/27–10/29 | 汇总结果、制作成功与失败案例、报告和演示；检查复现步骤 |
| 10/30 | 发布候选提交/tag 并检查交付；之后仅修阻塞性问题，预留月底缓冲 |

若 10/17 仍无法完成离线链路，组内应先删掉动态效果与额外角色，而不是接更多视频模型。正式实验规模根据 pilot 成本和人工评价能力确定。

## 6. PR 与合并规则

- 任务唯一来源是 GitHub Issue。每项任务一个主负责人；发现相似任务先看 open Issues 和 Draft PR，不重复开发。
- 认领当天开 Draft PR，写出范围与预计就绪时间；24–48 小时内交一个可验收增量。不要按行数凑提交，也不要几天不推送。
- 分支建议 `codex/mc02-import-assets`、`codex/mc03-review-report` 这类任务名；一个 PR 只处理一个任务增量。
- 所有对 main 的改动走 PR。Ready PR 必须有至少一位非作者队友批准、离线 CI 通过、未解决评论为零，才能 squash merge。通过后由作者或组长当日合并，不集中到最后一天。
- 建议开启 main 的 Require pull request、1 approval、Required checks、Resolve conversations、禁止 force push。先让 CI 成功运行一次再指定 required check。仓库目前公开，GitHub Free 支持公开仓库分支保护；管理员应核实实际规则而不是只看 README。
- 评审人在 24 小时内给反馈；急需当天集成的 PR 在 Issue 标明原因，由备选队友评审，不能用“没人看”代替审查。
- 每天北京时间 21:00 前在 Issue 留三行：`已交付/PR`、`下一步`、`阻塞/需要谁`。组长跟进未更新的任务。
- 卡住半天就提交最小复现、报错和已尝试方案。卡住者仍持有 Issue；组长在 Issue 明确转交后，接手者才继续，避免两人同时改。
- 需要动他人目录或公共契约：先开契约/接口 Issue，P1 与受影响模块负责人达成一致，再用单独的小 PR 修改。
- 不把 TASKS.md 当实时锁。P1 维护总览，日常状态用 Issue，避免五个人每天改同一张表。
- 已推送分支同步 main 优先 `git fetch origin` 后 `git merge origin/main`；不强推共享分支。新任务从最新 main 开始。
- 保留现有 `.gitmessage` 的姓名与日期规范。配置 `git config commit.template .gitmessage`。

### 一位队友的标准操作

```bash
git clone https://github.com/zhengads/MoodCut-dsa4213.git
cd MoodCut-dsa4213
git config commit.template .gitmessage
git switch main
git pull --ff-only
git switch -c codex/mc02-import-assets
# 修改自己任务范围内的文件，运行任务卡里的离线验收
git add src/moodcut/planning tests/planning
git commit
git push -u origin codex/mc02-import-assets
```

然后在 GitHub 创建 Draft PR，关联真实 Issue。新增文件时 `git add` 路径按实际文件选择；不要直接 `git add .` 把运行结果或第三方图片全提交。

## 7. 预算与实验原则

默认 mock/offline。任何真实 OpenRouter 请求必须由有授权的人显式使用 paid 开关并给出本次上限；真实费用预估由模型价格和 pilot token 用量计算。15 美元是总额度，不是每人 15 美元。P1 维护同一份费用记录；并行真实跑数前按人划分额度，不能五个人各自认为还有完整余额。

普通 CI 不注入 API key，不运行模型、不下载权重、不下载完整 dataset。日志保存模型版本、prompt 哈希、调用数、实际 token、估计费用和供应方费用（如果可获取）；费用未知必须标 unknown。客户端在最坏 token 费用超过剩余额度时拒绝发起请求；配置不含可信价格时不允许预算模式真实调用。

第一版实验条件：`baseline`（初稿直接渲染）、`generic_review`（通用审查）、`moodcut`（情绪专项反馈与局部修改）。三个条件共享同一 scene/tone/replicate 初稿和素材。后两组使用相同模型、最大轮数、调用槽位、token 上限和可修改字段，只换评审准则。最多一次 critique→revise→verify，不因某组失败而额外补跑。

这能测试情绪专项反馈相对通用审查的价值，不能单独证明“多个 Agent 优于一个 Agent”，也不能证明局部补丁本身优于整篇重写，因为两组共用补丁机制。

人工主要看目标 tone 是否被识别，同时单列自然度、剧情清楚程度和过度表达。评审 Agent 的自评分不充当最终结果。盲评页面隐藏方法名和目标 tone；揭盲映射独立保存。开发样例、代码 mock 数据和正式评价样本必须区分。

## 8. Skill 怎么用

大家共用仓库内 `.agents/skills/moodcut-team/SKILL.md`。入口、配置步骤和可直接复制的指令统一放在 `START_HERE.md`；每个人只替换自己真实的 Issue 编号。Skill 规定开工检查、修改范围、接口、验收、提交与评审流程。

每项任务由一位负责人通过 PR 交付，认领和进度以 GitHub Issue 为准。共享 Skill 的修改统一走 PR，所有成员同步仓库中的最新版本。
