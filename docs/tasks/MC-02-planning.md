# MC-02 MovieAgent 输入素材与规划适配

任务记录：[GitHub Issue #22](https://github.com/zhengads/MoodCut-dsa4213/issues/22)，工程交付已关闭。复用下列已完成实现，不重新认领同一增量；新需求另记Issue。末尾既有交付用于复用和回归。

首个增量建议分支：`feat/issue-22-shared-planning`。先检查认领和活动 PR；[分支命名与迁移](../BRANCHES.md)。不在 `archive/` 继续开发。

## 生成式共同规划与消费联调（工程交付已合入）

规划适配及P4消费联调已随PR #32/#34合入，Issue #22工程任务已关闭，不在P2中重复实现P4编译器。真实模型质量、实际视频任务和完整比较链路尚未验收。

**目标**：把读信示例的手写场景/动作抽成可复用的规划输出；它是各条件共用的生成基础，不是额外消融因素。

### 已核实的缺口

默认`planning_shot.txt`保留静态animatic；显式generated使用独立planning_generated_*.txt，已按输入范围输出共同scene_direction/逐镜头direction。P4实际编译器已消费这些字段，旧configs/video.json只留作独立读信开发示例/报价快照，不提供新主路径的动作配方。不能为每个条件单独规划动作，再把视频差异归因于台词审查。

### 本次待办与验收

- [x] 沿用 director→scene→shot 接入显式generated和真实公共验证器，输出共同场景/动作/镜头/短片时长与初始台词；animatic默认行为及提示保留。
- [x] 复用pipeline一次规划与条件深拷贝，以真实planner加FakeClient验证三组初稿/非台词哈希及共同Settings一致；不为moodcut单独增强表演。缺P3接口时两个审查条件明确失败，不伪装完整成功。
- [x] 按输入镜头/总长范围排整数时长，不补到60秒；全部beat顺序覆盖、来源provenance和原始响应保留，缺字段/越权引用明确拒绝，不静默修复。
- [x] P4实际build_generated_video_bundle已消费P2通用共同动作字段，主路径不依赖读信名字/镜头/动作配方；真实planner/reviewer/compiler加FakeClient覆盖完整和单镜头请求准备。原配置保留为明确开发示例，不代写P4模块。
- [x] FakeClient覆盖既有读信及临时公交站还伞结构夹具；不同角色/beat/镜头ID与10秒计划均经真实规划代码验证。夹具只作软件测试，不是数据集、正式样本或效果证据。
- [x] stage顺序、源输入不变、共同身份/缓存、缺动作/越权引用及失败原样留档均有离线回归，不自动重试。

### 写入范围与依赖

接入协议固定为 CONTRACTS 6.2 / 6.5：Scene/Plan 1.1 显式 generated，公共动作采用 scene_direction 与 shots[].direction；沿用既有函数并追加 output_mode，不能把未来参数当成当前已有功能。`moodcut.contracts` 由 P1 维护，软件输入示例见 `tests/fixtures/generated_contract.json`。

公共 `validate_scene/validate_plan` 已实现 output_mode="generated"；本模块已传入该参数并使用真实验证器，不另造验证或静默退回1.0。规划适配的阶段/外壳/提示身份准确约定见CONTRACTS 6.10。

`src/moodcut/planner.py`、`importer.py`（仅必要输入适配）、`src/moodcut/prompts/planning_*.txt`、`tests/test_planner.py`、`tests/test_importer.py` 与模块说明。素材清单只在明确输入适配需要时调整。不修改公共 validator、审查模块、生成编译器和公共夹具；所需新字段先交 P1。

P1公共契约/验证/编排已合入。交付给P3同一个初稿，给P4共同动作；基础声音仍来自共同GenerationSettings。pipeline的唯一协同改动为读取规划提示哈希时传mode_options，已在#8记录，以确保generated缓存身份对应真实提示。离线验收为`python -m pytest tests/test_planner.py tests/test_importer.py tests/test_pipeline.py -q`及完整回归，全部使用FakeClient；P2/P3/P4实际代码的脚本/请求接线已交付，真实任务和P5资格仍待后续。

### 实验解释边界

本对照只检验同一规划下，情绪专项台词审查相对通用审查是否有益。不声称证明动作规划有效或“更多 Agent 更好”；单独测试规划贡献需另外确认实验设计。

## 既有模块与验收记录（供复用与回归）

### 当前交付

importer、planner、三份规划提示、prepare_assets 与两张参考图的 manifest 元数据已实现。原图仍在忽略目录；故事改编、具体 beats、目标 tone 和新裁切需人工确认。

下列勾选项表示工程实现；不表示真实 API、正式实验或人工主观评价已完成。

认领模块：P2 规划，账号以 Issue 为准。依赖：MC-01 PR1；可先阅读上游。首个 Draft PR：10/15；接入：10/17。

### 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

### 交付

读取 MovieAgent 的梗概和角色参考输入，使用它的分阶段规划思路，输出符合 CONTRACTS 的 ShotPlan。选一组开发输入即可，不下载完整模型或完整dataset。

### 修改范围

`src/moodcut/importer.py`、`src/moodcut/planner.py`、`src/moodcut/prompts/planning_director.txt`、`src/moodcut/prompts/planning_scene.txt`、`src/moodcut/prompts/planning_shot.txt`、`assets/manifest.json`、`assets/selection.example.json`、`scripts/prepare_assets.py`、`tests/test_importer.py`、`tests/test_planner.py`、`tests/test_prepare_assets.py`、`docs/upstream-reuse.md`。归一化逻辑放在 planner.py；不另建 normalizer 模块。不要修改公共 client、validation、reviewer、renderer 或审查提示词。

### 上游定位

MovieAgent固定版本 `d84041bed8bc8be460664528d9e9924cdde384ba`：
- `dataset/FrozenII/script_synopsis.json`：MovieScript和Character两个字段。
- `dataset/FrozenII/character_list/Anna/` 与 `Elsa/`：角色参考图候选。
- `movie_agent/system_prompts.py`：screenwriterCoT-sys、ScenePlanningCoT-sys、ShotPlotCreateCoT-sys。
- 不直接import `movie_agent/run.py` 的ScriptBreakAgent，不运行原run.sh，避免连带初始化GPU生成工具。

已有 `scripts/prepare_references.py --assets` 可准备固定的两张角色图和说明。复用该缓存，将来源映射到 MoodCut AssetManifest；无需重复编写同一下载逻辑。`scripts/prepare_assets.py` 负责素材校验与项目 manifest 输出。

### PR 1 素材与离线导入

- [x] 实现 import_synopsis(path)；MovieScript必须非空字符串、Character必须为非空字符串列表，否则报明确信息。返回 `{story, character_names}`。
- [x] 写prepare_assets显式准备命令：接收选定文件清单，只处理指定图片；已有本地图片优先。下载统一由 prepare_references.py --assets 显式处理；prepare_assets 只校验本地选择，记录 URL/revision/hash/尺寸，--check 比对已有清单，不覆盖文件。
- [x] manifest 中的路径使用 assets/raw 下相对项目根的路径；原始图片不随PR上传。人工检查挑选的图片是否适合裁切，不能默认center_close一定是人脸。
- [x] 写复用说明：复制了什么、参考了什么、改编了什么、未确认的许可；未确认许可不整份复制上游源码或发布图片。
- [x] 用团队自制夹具测试导入、重复角色、缺字段和损坏素材；确认没有GPU依赖。

### PR 2 规划适配

- [x] make_plan依次调用公共client的director、scene、shot三个stage。三组实验共用这套规划与目标tone；不为MoodCut单独生成“更好的初稿”。
- [x] 约束为当前一段故事、两个角色、固定素材、最多六镜头、60–90秒。素材表现不了的动作只能放叙述字幕，不请求新视频。
- [x] 将上游式子剧本/场景/镜头输出归一化到唯一ShotPlan schema。统一ID映射并保存上游原始响应；不靠修改story或删除beat来通过验证。
- [x] normalize失败保留raw response和错误，不静默丢镜头，不自动重试付费请求。
- [x] 已用 FakeClient 跑通；2026-10-15 真实文本开发样例也已执行，不能视为视频生成或正式实验。后续调用仍须明确模型、价格和本次费用授权。

### 验收

目标命令：`python -m pytest tests/test_importer.py tests/test_planner.py tests/test_prepare_assets.py -q`、`python -m moodcut plan --scene tests/fixtures/scene.json --assets tests/fixtures/assets.json --mock --output runs/dev/initial.json`。

必须证明：无需torch/CUDA即可导入；三个planning stage按序执行；fixture计划通过公共验证；未知角色/素材、遗漏beat、超时长返回明确失败；原始来源保留。只声明规划适配，不声称完整复现MovieAgent。

### 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
