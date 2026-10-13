# MC-02 MovieAgent 输入素材与规划适配

负责人：P2，GitHub 账号以 Issue 指派为准。评审：P1。依赖：MC-01 PR1；可先阅读上游，不等待其他模块。首个 Draft PR：10/15；接入：10/17。

## 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

## 交付

读取 MovieAgent 的梗概和角色参考输入，使用它的分阶段规划思路，输出符合 CONTRACTS 的 ShotPlan。选一组开发输入即可，不下载完整模型或完整dataset。

## 修改范围

`src/moodcut/planning/`、`prompts/planning/`、`assets/manifest.json`、`scripts/prepare_assets.py`、`tests/planning/`、`docs/upstream-reuse.md`。模块内实现 importer.py、planner.py、normalizer.py。不要改根client、schema、review或renderer。

## 上游定位

MovieAgent固定版本 `d84041bed8bc8be460664528d9e9924cdde384ba`：
- `dataset/FrozenII/script_synopsis.json`：MovieScript和Character两个字段。
- `dataset/FrozenII/character_list/Anna/` 与 `Elsa/`：角色参考图候选。
- `movie_agent/system_prompts.py`：screenwriterCoT-sys、ScenePlanningCoT-sys、ShotPlotCreateCoT-sys。
- 不直接import `movie_agent/run.py` 的ScriptBreakAgent，不运行原run.sh，避免连带初始化GPU生成工具。

已有 `scripts/prepare_references.py --assets` 可准备固定的两张角色图和说明。复用该缓存，将来源映射到 MoodCut AssetManifest；无需重复编写同一下载逻辑。`scripts/prepare_assets.py` 负责素材校验与项目 manifest 输出。

## PR 1 素材与离线导入

- [ ] 实现 import_synopsis(path)；MovieScript必须非空字符串、Character必须为非空字符串列表，否则报明确信息。返回 `{story, character_names}`。
- [ ] 写prepare_assets显式准备命令：接收选定文件清单，只处理指定图片；已有本地图片优先。远端下载必须显式参数启用，记录URL/revision/hash/尺寸；遇到非图片或HTTP错误失败，不批量猜URL。
- [ ] manifest中的路径使用 local_assets 相对路径；原始图片不随PR上传。人工检查挑选的图片是否适合裁切，不能默认center_close一定是人脸。
- [ ] 写复用说明：复制了什么、参考了什么、改编了什么、未确认的许可；未确认许可不整份复制上游源码或发布图片。
- [ ] 用团队自制夹具测试导入、重复角色、缺字段和损坏素材；确认没有GPU依赖。

## PR 2 规划适配

- [ ] make_plan依次调用公共client的director、scene、shot三个stage。三组实验共用这套规划与目标tone；不为MoodCut单独生成“更好的初稿”。
- [ ] 约束为当前一段故事、两个角色、固定素材、最多六镜头、60–90秒。素材表现不了的动作只能放叙述字幕，不请求新视频。
- [ ] 将上游式子剧本/场景/镜头输出归一化到唯一ShotPlan schema。统一ID映射并保存上游原始响应；不靠修改story或删除beat来通过验证。
- [ ] normalize失败保留raw response和错误，不静默丢镜头，不自动重试付费请求。
- [ ] 先用FakeClient的三份预置响应跑通，再申请小额真实pilot。真实模型、价格和费用上限由P1统一配置。

## 验收

目标命令：`python -m pytest tests/planning -q`、`python -m moodcut plan --scene fixtures/scene.json --assets fixtures/assets.json --mock --output runs/dev/initial.json`。

必须证明：无需torch/CUDA即可导入；三个planning stage按序执行；fixture计划通过公共验证；未知角色/素材、遗漏beat、超时长返回明确失败；原始来源保留。只声明规划适配，不声称完整复现MovieAgent。
