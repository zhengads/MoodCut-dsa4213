# 上游复用范围

## 动画参考素材库扩充（2026-10-24）

按明确选用动画素材的要求，从同一MovieAgent固定提交导入FrozenII、DespicableMe4、InsideOut2、NeZha2四部动画共25个角色，每个`best.png`加两张不同Git对象的候选图，合计75张、25份原角色说明。原图只存本地忽略目录；PR提交固定来源/对象/大小/SHA-256清单、角色索引、现有AssetManifest及[使用说明](../assets/library/README.md)，不公开再分发图片。沿用原下载器/素材验证器，仅增加显式下载选项，不运行上游代码或新建素材服务。

没有找到适用于这些电影角色图片的项目级许可或权利人授权；署名与论文引用不能替代许可，不写成“已避免侵权”。许可状态保留unconfirmed，公开再分发和商业使用未获本项目核实。原sigils-people许可不覆盖本库。当前扩充是本地选材索引，不是正式样本选择，原素材/运行身份保持不变；逐图构图、裁切和提供商接受仍需实际选材核对。

另一次明确授权的Anna/Elsa单段素材探测已使用原始两张PNG在HeyGen完成一段768p、5秒请求，费用$0.25、1次POST，无文本调用或重试，实际视频/音轨已交付。该工程结果只证明该任务接受两张输入，不证明版权许可或其它角色可用；不把手写台词当作Agent审查输出。本次导入没有新增付费API、视频生成或评分。以下较早段落保留当时的集成范围与记录。

| 内容 | 处理方式 | 负责模块 |
|---|---|---|
| MovieAgent 剧情 JSON | 导入 MovieScript、Character，记录改编来源 | MC-02 |
| MovieAgent 角色参考图 | 用固定清单下载到本地；映射到 MoodCut 素材 manifest | MC-02 |
| MovieAgent 规划顺序和提示词结构 | 阅读固定版本后编写受限规划适配器 | MC-02 |
| FilmAgent CCV 机制 | 编写一次审查、局部修订、复查的独立实现 | MC-03 |
| 上游客户端、视频生成和 Unity 执行器 | 仅作源码阅读，使用 MoodCut 的 client 与渲染接口 | MC-01、MC-04 |
| 上游示例输出和论文评分 | 调研与开发参考，不作为 MoodCut 独立实验数据或结果 | MC-05 |

## 当前集成边界

共享仓库包含阅读笔记、引用、固定来源清单及资料准备工具。33 份核心参考文件下载到 `references/upstream/`，两篇论文 PDF 可下载到 `references/papers/`；这些文件不进入项目 Python 包、不由测试发现、不作为运行依赖。

初始素材选项提供 Anna/Elsa 两张参考图及说明。清单里的 SHA-256、路径与来源是下载记录；assets/selection.example.json 与 assets/manifest.json 已提供显式映射及尺寸/哈希。下载到本地后用 prepare_assets.py --check 核验；仅开放 full，其他裁切及实际故事角色映射仍需人工确认。

## 来源与许可记录

MovieAgent 固定提交未发现项目级 LICENSE；嵌套后端的许可不作为整个仓库的许可。当前仅保留本地参考副本，公开提交实际采用的代码或素材前核实适用授权。

FilmAgent 当前所在仓库的根 LICENSE 标注 MIT。原始声明随参考文件下载；若复用受该许可覆盖的代码，保留声明并记录来源。图片、视频、角色形象和论文各自的使用限制单独处理。

每次实际采用或改编上游代码时，在对应 PR 补充：源仓库、提交、文件/函数、目标文件、保留的许可声明与修改内容。方法参考也应在报告中引用两篇论文。

## 独立适配实现

importer.py 读取上游 MovieScript/Character 字段；planner.py 和 planning_*.txt 参考分阶段组织方式，独立定义本项目的 director/scene/shot JSON 协议，没有复制上游 Python 执行代码或原提示词全文。reviewer.py 参考 FilmAgent 的 CCV 方法，保留本项目受限补丁；当前演员协商与旧全局审查分别见[方法](ACTOR_REVIEW_METHOD.md)。图像清单仅提交元数据，原始图片仍留在忽略目录。

生成式规划沿用MovieAgent固定版本的ScenePlanning/ShotPlotCreate组织思路，在planner.py及planning_generated_director/scene/shot.txt独立实现MoodCut的1.1共同场景、动作与短片时长协议。未复制上游执行代码或原提示全文，不导入视频/GPU工具；不称为原论文完整复现。测试中的公交站还伞故事由本项目临时手写，仅验软件结构泛用性，不是上游素材、新数据集或模型效果证据。

## 还伞试跑的合成人物参考（2026-10-23）

按明确选择复用sigils-people固定提交cn-02/cn-04两张已有合成人像，仅做离线格式适配；不运行上游ComfyUI/生成脚本或训练模型。图片使用LICENSE-PORTRAITS的CC BY 4.0及其可接受使用条款，不能沿用代码MIT。原AVIF、完整许可与PNG均本地保留，公开仅提交哈希/来源/署名元数据；参见[credits](pilots/umbrella-sigils-credits.md)和[锁定清单](../assets/pilots/umbrella-sigils.lock.json)。PNG保留来源声明，未来材料须附相同公共署名。这段离线适配记录不包含后续托管或运行授权；实际后续交付和试跑见[还伞记录](pilots/umbrella-single-shot.md)，不将不同素材身份混用。
