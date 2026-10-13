# MC-04 固定素材动态分镜渲染

负责人：P4，GitHub 账号以 Issue 指派为准。评审：P2。依赖：MC-01 PR1；用自制fixture开发，无需等待LLM或MovieAgent素材。首个 Draft PR：10/15；集成：10/17。

## 开工资料

先按 `docs/REFERENCES.md` 准备核心资料并读取本模块对应文件。复用范围见 `docs/upstream-reuse.md`；函数和数据格式以 `docs/CONTRACTS.md` 为准。

## 交付

同一套render_plan把baseline和修订plan转成可播放的60–90秒MP4，并输出接触表与时间轴。第一版是静态animatic，不是动作生成视频。

## 修改范围

`src/moodcut/rendering/`、`tests/rendering/`、`docs/rendering.md`。模块内实现 renderer.py、frames.py、subtitles.py。依赖变更交给P1合并，不自己改根配置。

## PR 1 画面与字幕

- [ ] 固定1280×720、24fps；16:9背景使用统一纯色。单角色居中、双角色左右固定卡片；图片等比contain不拉伸。
- [ ] full显示整张图；center_close先取中心60%宽高再等比contain。manifest未允许的crop拒绝。裁切不保证是人脸，真实素材由P2人工确认。
- [ ] 使用显式传入的UTF-8可用字体路径；不存在则给出错误，不从网络偷偷下载字体。Pillow绘制字幕，自动换行；溢出画面则报错，不静默裁掉句子。
- [ ] dialogue以角色名开头显示；narration单独标“叙述”，保持与实际图片表达的区别。所有方法同版式，不把moodcut加滤镜而baseline不给。
- [ ] 输出每镜头PNG和一张contact sheet，保存每镜头开始/结束时间及字幕。

## PR 2 MP4与改动可见性

- [ ] 用FFmpeg将每张镜头画面按duration_s拼接，H.264/yuv420p无音轨MP4；通过参数列表调用subprocess，不拼接包含用户文本的shell命令。
- [ ] 使用ffprobe核实输出尺寸、帧率、时长，允许帧量化误差不超过1/24秒加容器容差0.1秒；失败保留render_failed。
- [ ] 旧out_dir非空时拒绝覆盖，素材文件校验失败不跳过镜头。输出路径只在out_dir内。
- [ ] 为同一计划做一项crop/台词修改，比较对应渲染帧确实变化；duration调整后时间轴与总长正确。
- [ ] 文档注明依赖FFmpeg与字体，给Windows/Linux使用例；CI的轻量画面测试必须跑，视频集成测试在安装FFmpeg的job跑，不能用skip冒充视频成功。

## 验收

目标命令：`python -m pytest tests/rendering -q`、`python -m moodcut render --plan fixtures/plan.json --assets fixtures/assets.json --font local_assets/font.ttf --output runs/dev/render`。

交付视频、contact sheet、timeline和ffprobe结果。人工检查中文字幕、角色对应、镜头顺序、裁切和时长。无需调用付费模型。
