# MC-04 固定素材动态分镜渲染

## 当前交付

PNG、字幕、接触表、timeline 与 MP4 已实现并接入主流程。默认自动检测字体，也可显式指定；真实素材的裁切与视觉合适程度仍需人工检查。

生成式增量：`src/moodcut/video_generation.py`、`scripts/generate_video.py`、`configs/video.json` 和 `tests/test_video_generation.py` 负责人物参考图请求、台词差异、真实音视频拼接和检查页；异步 HTTP/费用在 MC-01 的 `src/moodcut/video_client.py`。见 [生成视频计划](../GENERATIVE_VIDEO_PLAN.md)。已完成离线接入，尚未真实生成验收；不得用原 animatic 替代生成式成片。原渲染器和既有验收保留，用于诊断与回归。

下列勾选项表示工程实现；不表示真实 API、正式实验或人工主观评价已完成。

认领模块：P4 渲染，账号以 Issue 为准。依赖：MC-01 PR1；使用共享夹具，无需等待模型或上游素材。首个 Draft PR：10/15；集成：10/17。

## 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

## 交付

同一套render_plan把baseline和修订plan转成可播放的60–90秒MP4，并输出接触表与时间轴。第一版是静态animatic，不是动作生成视频。

## 修改范围

`src/moodcut/renderer.py`、`tests/test_renderer.py`、`tests/test_video.py`、`docs/rendering.md`。画面、字幕与 FFmpeg 编排先作为 renderer.py 内的函数实现。依赖和共享渲染配置变更与公共基础模块协调后更新，不自行新增平行配置。

## PR 1 画面与字幕

- [x] 固定1280×720、24fps；16:9背景使用统一纯色。单角色居中、双角色左右固定卡片；图片等比contain不拉伸。
- [x] full显示整张图；center_close先取中心60%宽高再等比contain。manifest未允许的crop拒绝。裁切不保证是人脸，真实素材由P2人工确认。
- [x] 使用显式传入的UTF-8可用字体路径；不存在则给出错误，不从网络偷偷下载字体。Pillow绘制字幕，自动换行；溢出画面则报错，不静默裁掉句子。
- [x] dialogue以角色名开头显示；narration单独标“叙述”，保持与实际图片表达的区别。所有方法同版式，不把moodcut加滤镜而baseline不给。
- [x] 输出每镜头PNG和一张contact sheet，保存每镜头开始/结束时间及字幕。

## PR 2 MP4与改动可见性

- [x] 用FFmpeg将每张镜头画面按duration_s拼接，H.264/yuv420p无音轨MP4；通过参数列表调用subprocess，不拼接包含用户文本的shell命令。
- [x] 使用ffprobe核实输出尺寸、帧率、时长，允许帧量化误差不超过1/24秒加容器容差0.1秒；失败保留render_failed。
- [x] 旧out_dir非空时拒绝覆盖，素材文件校验失败不跳过镜头。输出路径只在out_dir内。
- [x] 为同一计划做一项crop/台词修改，比较对应渲染帧确实变化；duration调整后时间轴与总长正确。
- [x] 文档注明依赖FFmpeg与字体，给Windows/Linux使用例；CI的轻量画面测试必须跑，视频集成测试在安装FFmpeg的job跑，不能用skip冒充视频成功。

## 验收

目标命令：`python -m pytest tests/test_renderer.py tests/test_video.py -q`、`python -m moodcut render --plan tests/fixtures/plan.json --assets tests/fixtures/assets.json --font assets/raw/font.ttf --output runs/dev/render`。

交付视频、contact sheet、timeline和ffprobe结果。人工检查中文字幕、角色对应、镜头顺序、裁切和时长。无需调用付费模型。

## 提交自查

完成本次增量后检查 diff、公共接口和实际验收结果，在 PR 描述中记录自查结论与遗留事项。可自行评审，也可请同伴或 AI 辅助；无需指定评审人。通过所需检查并解决阻塞问题后按仓库规则合并。
