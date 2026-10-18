# MC-04 生成视频与分镜渲染

当前任务：[GitHub Issue #24](https://github.com/zhengads/MoodCut-dsa4213/issues/24)。先做下面未勾选的下一增量；末尾既有交付仅用于复用和回归。

首个增量建议分支：`feat/issue-24-video-inspection`。先检查认领和活动 PR；[分支命名与迁移](../BRANCHES.md)。不在 `archive/` 继续开发。

## 当前增量：生成请求编译与本地音视频检查材料已实现

**目标**：复用已有参考图请求、异步任务和真实音视频拼接，让任意符合共同契约的分镜都能准备请求并检查交付。

### 已核实的缺口

`build_generated_video_bundle`已消费1.1共同计划编译三条件请求，实际planner/reviewer/pipeline加FakeClient已接通完整/单镜头离线准备。本地inspect_generated_video已提供来源绑定与观看检查包，复用现有P1回执装配及A/V拼接。旧build_video_bundle保留1.0开发投影，其动作配方不用于新主路径。音轨存在不代表正确说出台词；目前没有成功生成的视频质量验收。

### 本次待办与验收

- [x] 按 P1/P2 契约消费一次规划冻结的场景、动作、镜头和时长；移除主路径对 Anna/Elsa、递信及 s1/s2/s3 的硬依赖，示例配置保留明确来源。
- [x] 为 baseline/generic_review/moodcut 用同一编译模板、参考图、共同方向、声音要求、模型参数及对应镜头 seed 构造请求。条件标签/审查意见不进入模型提示；只有 dialogue 片段随条件变化，生成前核对共享哈希。
- [x] 使用 `input_references` 保持人物参考，不发送卡片首帧；保留原生声音。不得替某一条件另加表情/动作/滤镜、专属音色或时长。
- [x] 复用 `assemble_generated_clips` 与 `video_client.py`，保留真实视频/音频/时长检查、失败/未知费用；缺少音轨或失败镜头不能用静态图顶替成功。不再实现另一个 HTTP client 或 FFmpeg 拼接器。
- [x] 提供可对已有本地片段生成的观看页、接触表、ffprobe 信息及空人工检查表：人物/动作、台词/说话人、声音/口型、连续性。检查结果留给实际观看者填写，不编造通过结论。
- [x] 离线测试覆盖非读信输入、三条件非台词提示一致、篡改共享动作拒绝、完全相同请求在同块复用且费用不重复、缺音轨/时长错误，以及有运动和正弦音的软件媒体夹具。

### 写入范围与依赖

接入协议固定为 CONTRACTS 6.2–6.5/6.12：共同动作只来自 Plan；GenerationSettings 与报价配置分离，调用公共 shared_generation_sha256 重算三条件身份。build_generated_video_bundle已实现，旧 build_video_bundle 保留为开发投影，不默认为正式三条件。Job/请求/费用字段见6.4，公共纯函数由 P1 维护。

先用get_video_template_sha256()取得实际video_generated.txt文本身份，在规划前冻结到P1 block；编译器拒绝旧/虚假模板哈希，不改写历史记录。使用既有run --output-mode generated --source-block入口，无需另建CLI/客户端。完整和单镜头均已用实际P2/P3/P4代码加FakeClient离线联调；非读信软件输入为公交站还伞10秒，不是新数据集或模型效果证据。本地报价与实际消费分开，相同请求沿用P1记录装配做复用和费用去重。

本地检查接口见CONTRACTS 6.13与[rendering说明](../rendering.md#local-video-inspection-and-source-binding-11)：scripts/inspect_generated_video.py读取已有准备/本地证据，复用P1预检和最终重检，给成片绑定source_clips/request/实际字节哈希。输出观看页/实际抽帧接触表/ffprobe/空CSV与JSON人工检查表；条件或片段失败不补静态图，未知费用保持未知。软件媒体明确声明synthetic，判断项全部留空，不进行ASR或情绪评分。

本Issue的工程实现已交付；真实人物/中文对白/口型/情绪质量仍需另行授权的pilot和实际观看者。实际任务接线与#9资格不在本工程任务中自动完成，工具准备就绪不设eligible。

公共 validate_scene/validate_plan 已接受显式 generated，可直接验证1.1软件输入。旧开发对脚本只修复了 unchanged 来源兼容，尚未成为1.1三条件入口；本任务的新编译器与旧投影保持明确区别。

`src/moodcut/video_generation.py`、`prompts/video_generated.txt`（P4公共生成模板）、`renderer.py`（仅复用检查能力所需）、`configs/video.json`、`tests/test_video_generation.py`、必要的 `tests/test_renderer.py`/`test_video.py`、`docs/rendering.md`。新检查命令确需脚本时限 `scripts/inspect_generated_video.py`。`scripts/generate_video.py` 入口和传输/价格逻辑由 P1 维护，接口修改先协调；不改 P2/P3 提示词。

依赖 P1 契约与 P2 数据；检查工具可先用本地软件媒体开发。离线验收：相关测试 + 一份标明 synthetic 的检查材料；所有网络传输用 mock。真实人物、中文对白和情绪质量只能在另行授权的 pilot 后验收。

### 解释限制

固定 seed 不保证改台词后动作、表情或语音完全相同。此流程检验共同设置下的端到端效果，不能单独把增益归因于面部表情。

## 既有模块与验收记录（供复用与回归）

### 当前交付

PNG、字幕、接触表、timeline 与 MP4 已实现并接入主流程。默认自动检测字体，也可显式指定；真实素材的裁切与视觉合适程度仍需人工检查。

生成式增量：`src/moodcut/video_generation.py`、`configs/video.json` 和 `tests/test_video_generation.py` 负责人物参考图请求、台词差异、真实音视频拼接和检查页；生成 CLI `scripts/generate_video.py` 以及异步 HTTP/费用归 MC-01；传输在 `src/moodcut/video_client.py`。见 [生成视频计划](../GENERATIVE_VIDEO_PLAN.md)。已完成离线接入，尚未真实生成验收；不得用原 animatic 替代生成式成片。原渲染器和既有验收保留，用于诊断与回归。

下列勾选项表示工程实现；不表示真实 API、正式实验或人工主观评价已完成。

认领模块：P4 渲染，账号以 Issue 为准。依赖：MC-01 PR1；使用共享夹具，无需等待模型或上游素材。首个 Draft PR：10/15；集成：10/17。

### 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

### 交付

同一套render_plan把baseline和修订plan转成可播放的60–90秒MP4，并输出接触表与时间轴。第一版是静态animatic，不是动作生成视频。

### 修改范围

`src/moodcut/renderer.py`、`tests/test_renderer.py`、`tests/test_video.py`、`docs/rendering.md`。画面、字幕与 FFmpeg 编排先作为 renderer.py 内的函数实现。依赖和共享渲染配置变更与公共基础模块协调后更新，不自行新增平行配置。

### PR 1 画面与字幕

- [x] 固定1280×720、24fps；16:9背景使用统一纯色。单角色居中、双角色左右固定卡片；图片等比contain不拉伸。
- [x] full显示整张图；center_close先取中心60%宽高再等比contain。manifest未允许的crop拒绝。裁切不保证是人脸，真实素材由P2人工确认。
- [x] 使用显式传入的UTF-8可用字体路径；不存在则给出错误，不从网络偷偷下载字体。Pillow绘制字幕，自动换行；溢出画面则报错，不静默裁掉句子。
- [x] dialogue以角色名开头显示；narration单独标“叙述”，保持与实际图片表达的区别。所有方法同版式，不把moodcut加滤镜而baseline不给。
- [x] 输出每镜头PNG和一张contact sheet，保存每镜头开始/结束时间及字幕。

### PR 2 MP4与改动可见性

- [x] 用FFmpeg将每张镜头画面按duration_s拼接，H.264/yuv420p无音轨MP4；通过参数列表调用subprocess，不拼接包含用户文本的shell命令。
- [x] 使用ffprobe核实输出尺寸、帧率、时长，允许帧量化误差不超过1/24秒加容器容差0.1秒；失败保留render_failed。
- [x] 旧out_dir非空时拒绝覆盖，素材文件校验失败不跳过镜头。输出路径只在out_dir内。
- [x] 为同一计划做一项crop/台词修改，比较对应渲染帧确实变化；duration调整后时间轴与总长正确。
- [x] 文档注明依赖FFmpeg与字体，给Windows/Linux使用例；CI的轻量画面测试必须跑，视频集成测试在安装FFmpeg的job跑，不能用skip冒充视频成功。

### 验收

目标命令：`python -m pytest tests/test_renderer.py tests/test_video.py -q`、`python -m moodcut render --plan tests/fixtures/plan.json --assets tests/fixtures/assets.json --font assets/raw/font.ttf --output runs/dev/render`。

交付视频、contact sheet、timeline和ffprobe结果。人工检查中文字幕、角色对应、镜头顺序、裁切和时长。无需调用付费模型。

### 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
