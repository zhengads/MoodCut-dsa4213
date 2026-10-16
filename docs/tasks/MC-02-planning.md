# MC-02 MovieAgent 输入素材与规划适配

当前任务：[GitHub Issue #22](https://github.com/zhengads/MoodCut-dsa4213/issues/22)。先做下面未勾选的下一增量；末尾既有交付仅用于复用和回归。

首个增量建议分支：`feat/issue-22-shared-planning`。先检查认领和活动 PR；[分支命名与迁移](../BRANCHES.md)。不在 `archive/` 继续开发。

## 下一增量：一次规划、三组共用的生成式分镜（待实现）

**目标**：把读信示例的手写场景/动作抽成可复用的规划输出；它是各条件共用的生成基础，不是额外消融因素。

### 已核实的缺口

`planning_shot.txt` 仍面向静态图片和 60–90 秒 animatic；`configs/video.json` 的三个动作由读信故事手写。不能为每个条件单独规划动作，再把视频差异归因于台词审查。

### 本次待办与验收

- [ ] 等 P1 的生成式契约合入，沿用 director→scene→shot 输出场景、人物、必需动作、镜头要求、共同短片时长与初始台词；旧 animatic 模式保持兼容。
- [ ] 对同一 scene/tone/replicate 仅规划一次，在拆分三条件前冻结。动作、表情/肢体要求、镜头、时长、素材和基础声音要求均为共同输入；不为 moodcut 单独增强表演。
- [ ] 输入明确决定短片时长，不继承固定 60 秒凑时长。保留所有必需 beats 和来源信息；不可因为模型难生成而静默删情节或改人物。
- [ ] 将共同动作交给 P4 编译器消费，移除生成主路径对读信 shot_id/人物名/动作文本的特判；保留原配置为明确开发示例。
- [ ] FakeClient 覆盖原故事及一个临时的非读信结构夹具，证明不是靠手写故事特判。夹具标为软件测试，不作为新数据集、正式样本或效果证据。
- [ ] 检查 stage 顺序、源输入不变、三组初稿/非台词哈希一致，缺动作/越权引用报错；错误原样留档，不自动重试。

### 写入范围与依赖

`src/moodcut/planner.py`、`importer.py`（仅必要输入适配）、`src/moodcut/prompts/planning_*.txt`、`tests/test_planner.py`、`tests/test_importer.py` 与模块说明。素材清单只在明确输入适配需要时调整。不修改公共 validator、审查模块、生成编译器和公共夹具；所需新字段先交 P1。

依赖 P1 接口小 PR；交付给 P3 同一个初稿，给 P4 共同动作数据。离线验收：规划/导入相关测试，加上述共享/非读信/旧模式回归。命令与输出示例随 PR 给出，全部使用 FakeClient。

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
