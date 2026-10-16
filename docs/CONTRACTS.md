# MoodCut 模块契约

本文件定义模块间的公共接口。第1–4节为已实现的 1.0 animatic；第5节为既有开发投影；第6节定义1.1生成式数据、公共验证与脚本编排，真实规划/审查、请求编译和CLI接线仍待完成。Python 3.11；包路径 `src/moodcut/`；统一使用 JSON 可序列化 dict。

## 1. 公共数据

`schema_version` 固定 `1.0`。ID 为非空字符串且在所属集合内唯一。所有文本 UTF-8；时间单位秒；绝对素材路径不进共享 JSON。

### SceneInput

```json
{
  "schema_version": "1.0",
  "scene_id": "dev_letter_01",
  "tone": "suspicious",
  "story": "A把信交给B，B看过后收起信，两人离开。",
  "characters": [{"id":"a","name":"A"},{"id":"b","name":"B"}],
  "beats": [
    {"id":"b1","description":"A将信交给B"},
    {"id":"b2","description":"B读信并收起"},
    {"id":"b3","description":"两人离开"}
  ],
  "asset_ids": ["dev_a","dev_b"],
  "min_duration_s": 60,
  "max_duration_s": 90,
  "max_shots": 6,
  "provenance": {"kind":"team_authored_development","source_url":null,"revision":null,"adaptation":"合成接口示例，不是MovieAgent原数据或正式测试集"}
}
```

tone 仅允许 affectionate/suspicious/hostile。两个角色是第一版边界。story、characters、beats、tone、允许素材和时长约束不能由 Reviewer 修改。

### AssetManifest

```json
{
  "schema_version":"1.0",
  "assets":[
    {"asset_id":"dev_a","character_id":"a","path":"tests/fixtures/images/dev_a.png","width":640,"height":640,"sha256":"由准备脚本计算的64位十六进制值","source_url":null,"revision":null,"rights_note":"team-created placeholder","allowed_crops":["full","center_close"]},
    {"asset_id":"dev_b","character_id":"b","path":"tests/fixtures/images/dev_b.png","width":640,"height":640,"sha256":"由准备脚本计算的64位十六进制值","source_url":null,"revision":null,"rights_note":"team-created placeholder","allowed_crops":["full","center_close"]}
  ]
}
```

此处 hash 字段文字是字段说明，正式 fixture 必须由 P1 的确定性占位图生成脚本计算真实 hash；不得当有效 manifest 提交。图片素材相对项目根路径，不允许路径逃逸。真实素材填来源 URL、上游 revision 和授权状态，不能把未知许可标为开放许可。

### ShotPlan

```json
{
  "schema_version":"1.0",
  "scene_id":"dev_letter_01",
  "tone":"suspicious",
  "shots":[
    {"shot_id":"s1","beat_ids":["b1"],"duration_s":20,"visuals":[{"asset_id":"dev_a","crop":"full"},{"asset_id":"dev_b","crop":"full"}],"dialogue":[{"character_id":"a","text":"这封信给你。"}],"narration":"A将信交给B。"},
    {"shot_id":"s2","beat_ids":["b2"],"duration_s":20,"visuals":[{"asset_id":"dev_b","crop":"full"}],"dialogue":[{"character_id":"b","text":"我看过了。"}],"narration":"B读信，随后把信收起来。"},
    {"shot_id":"s3","beat_ids":["b3"],"duration_s":20,"visuals":[{"asset_id":"dev_a","crop":"full"},{"asset_id":"dev_b","crop":"full"}],"dialogue":[],"narration":"两人离开。"}
  ]
}
```

示例是手工编写的离线软件夹具，不能算模型产物或性能证据。renderer 明示为静态 animatic，动作由叙述字幕表达。

### ReviewReport

```json
{
  "schema_version":"1.0",
  "scene_id":"dev_letter_01",
  "mode":"moodcut",
  "issues":[{"issue_id":"r1","shot_id":"s2","dimension":"tone","evidence":"该镜头只有直接确认看过信的台词，缺少表达怀疑的线索。","suggestion":"通过提问与近景表达犹疑，保留读信收信事件。","severity":"minor"}]
}
```

mode 为 generic_review/moodcut。dimension 为 tone/naturalness/story/renderability；severity 为 minor/major。报告是模型意见，不是真值；空 issues 是允许的。

### RevisionPatch

```json
{
  "schema_version":"1.0",
  "scene_id":"dev_letter_01",
  "edits":[{"issue_id":"r1","shot_id":"s2","set":{"dialogue":[{"character_id":"b","text":"这封信，你从哪里拿到的？"}],"visuals":[{"asset_id":"dev_b","crop":"center_close"}]}}]
}
```

每条 edit 用唯一有效 issue_id 与 shot_id 关联。仅可替换该镜头的 dialogue、narration、visuals 的 crop、duration_s；visuals 的 asset_id 列表及顺序保持不变。shot_id、beat_ids、镜头个数和顺序、scene_id、tone 均不许改。一个 shot 最多一条 edit。补丁整体原子应用：任一结构错误则整个补丁拒绝，返回原计划、rejected 状态与错误，不产生半修改结果。

剧情含义保持不能仅靠 beat_ids 判断，人工评价仍需读完整台词。validator 检查引用存在与覆盖，不声称证明语义忠实。

### Verification / ReviewResult / RenderResult

Verification：`{scene_id, resolved_issue_ids:[], unresolved_issue_ids:[], new_concerns:[]}`，两个 ID 列表不重叠且合计覆盖原 report 的全部 issues；new_concerns 为文字数组。它是模型复查意见，不是实验评分。

ReviewResult：`{plan: ShotPlan, report: ReviewReport, patch: RevisionPatch, verification: Verification|null, status: "applied"|"unchanged"|"rejected"|"review_failed", errors:[]}`。验证意见不触发第二轮付费修改；有效补丁应用后，未解决意见如实保留。模型/JSON错误回退原计划并标 review_failed，不能记为成功修复。

RenderResult：`{status:"rendered"|"render_failed", video_path:string|null, contact_sheet_path:string|null, timeline_path:string|null, duration_s:number|null, errors:[]}`。所有产物留在本次 out_dir，已有输出不静默覆盖。

### RunRecord

`{run_id, block_id, scene_id, tone, replicate, condition, initial_plan_sha256, final_plan_sha256, schema_version, model_id, prompt_hashes, review_status, validation_status, render_status, calls, input_tokens, output_tokens, estimated_cost_usd, provider_cost_usd, elapsed_s, errors}`。

condition 为 baseline/generic_review/moodcut。cost 未知为 null，不能置零。运行成功与情绪识别正确分开记录。CLI 返回非零时仍保存失败记录。

## 2. 公共接口与归属

下列文件均位于 `src/moodcut/`，直接按功能平铺。提示词在 `src/moodcut/prompts/`，配置在根目录 `configs/`；具体文件归属见任务卡。

```python
# client.py — P1，所有付费请求只能经过该接口
class LLMClient:
    def complete_json(self, *, stage: str, system: str, user: str,
                      max_output_tokens: int) -> dict: ...

# validation.py — P1；返回错误列表，空列表表示结构通过
def validate_scene(scene: dict, manifest: dict, *, project_root=None, output_mode="animatic") -> list[str]: ...
def validate_plan(scene: dict, plan: dict, manifest: dict, *, project_root=None, output_mode="animatic") -> list[str]: ...

# importer.py — P2；只读本地上游文件，无网络
def import_synopsis(path: str) -> dict: ... # {story: str, character_names: list[str]}

# planner.py — P2
def make_plan(scene: dict, manifest: dict, client: LLMClient, *, project_root=None) -> dict: ...

# reviewer.py — P3，mode 必须显式给出
def review_and_revise(scene: dict, initial_plan: dict, manifest: dict,
                      client: LLMClient, *, mode: str, project_root=None) -> dict: ... # ReviewResult

# patches.py — P3；纯函数，不调用模型、不改输入对象
def apply_patch(scene: dict, plan: dict, manifest: dict,
                report: dict, patch: dict, *, project_root=None) -> dict: ... # {plan,status,errors}

# renderer.py — P4
def render_plan(plan: dict, manifest: dict, *, project_root: str,
                out_dir: str, font_path: str) -> dict: ... # RenderResult

# evaluation.py — P5；纯函数，创建分配记录不发请求
def build_assignments(scenes: list[dict], *, replicates: int,
                      tones: list[str], conditions: list[str]) -> list[dict]: ...

# evaluation.py — P5
def export_blind_items(records: list[dict], *, out_dir: str, seed: int) -> dict: ...
def summarize(records: list[dict], ratings: list[dict]) -> dict: ...

# pipeline.py — P1，initial_plan 由 block cache 取得或只生成一次
def run_condition(scene: dict, initial_plan: dict, manifest: dict,
                  client: LLMClient, *, condition: str, out_dir: str,
                  project_root: str, font_path: str | None, render=True,
                  replicate=1, source_kind="development", output_mode="animatic",
                  generation_settings=None, template_sha256=None,
                  expected_initial_plan_sha256=None,
                  expected_shared_generation_sha256=None) -> dict: ... # RunRecord

def run_experiment(scene: dict, manifest: dict, client=None, *, out_dir: str,
                   project_root=".", font_path=None, render=True, replicate=1,
                   cache_dir=None, source_kind="development", output_mode="animatic",
                   generation_settings=None, template_sha256=None) -> dict: ... # block.json
```

上述 `...` 用于缩写已实现函数的签名。project_root 为 None 时沿用当前目录；CLI/pipeline 显式传项目根目录。FakeClient 使用预置响应队列，record 每次 stage 和上限；队列耗尽、网络企图或非法响应报错。

make_plan 依次使用 director、scene、shot 三个 planning stage，输出上限分别 1024/2048/4096，再转换为 ShotPlan。director 保留输入 beat 顺序；scene 分段完整覆盖原顺序；shot 接受 canonical、shots、plan 或单场景 scenes 封装，不接受多场景静默截断。make_plan_with_trace 同时返回 plan/raw_responses/prompt_hashes；PlanningError 携带失败阶段、错误和已解析原始响应。所有条件共用初稿，不允许 review 模块反过来改变 scene。

run_experiment 只规划一次；可选初稿缓存身份含完整 scene/manifest、模型与温度、replicate、schema、规划提示词哈希、输出上限与 planner 代码哈希。缓存需通过身份、内容哈希和公共验证器；损坏缓存或已有独占锁报错，不覆盖。无自动重试。规划失败仍产出三个失败 RunRecord。run_condition 保存各条件独立副本；review 失败可渲染原稿用于诊断，但 run_status 仍为 failed。

planning.json 记录共享规划费用一次；三个 run.json 不重复分摊规划，包含各自 call_records。block.json 汇集 planning 与 runs。usage 中 calls 是逻辑调用数，real_http_calls 是实际 HTTP 尝试数；FakeClient 后者及实际费用为零，未提供的 token 仍为 null。evaluate 汇总的 overall.usage 只含条件用量，block_ledger_accounting.all_phases 在完整 block.json 可用时包含共享规划一次，缺共享账目返回 null。

review_and_revise 两种 mode 都按 critique → revise → verify 执行，最多各一次。critique 得到 report；revise 得到 patch；apply_patch 结构通过才运行 verify。无意见可不发 revise/verify。模型返回 JSON 不合法或 API 失败不自动重试；保留错误。实际用量与提前退出分别报告，不声称实际费用完全相同。

### OpenRouterClient 与调用账目

`OpenRouterClient(LLMClient)` 已实现；`OpenRouterClient.from_env(config_path, *, allow_paid=False, max_cost_usd=None)` 读取公开模型配置和进程环境中的 OPENROUTER_API_KEY。config_path 默认 configs/model.json；当前开发配置为 openai/gpt-4.1-mini，输入/输出每百万 token 单价为 $0.40/$1.60，2026-10-15 核验；温度 0、超时 120 秒。替换模型时必须显式更新实际价格。max_cost_usd 必须为正；只有 allow_paid=True 才能发送请求。构造和 check-client 均不联网，缺省不允许付费。

complete_json 返回原有模型 JSON dict，不包裹 usage，保持 MC-02/MC-03 调用兼容。输出不是对象、JSON 非法/重复键/非有限数、内容被拒绝或截断、接口/超时错误均抛 OpenRouterError；预算不足或既往扣费未知抛 BudgetError。错误不自动重试，不带 key、提示词或原始响应正文。

每次实际 HTTP 尝试在 client.calls 增加独立记录：stage、model_id、response_model、generation_id、max_output_tokens、estimated_input_tokens、reserved_cost_usd、input_tokens、output_tokens、estimated_cost_usd、provider_cost_usd、status、http_status、elapsed_s，以及失败时的 error。status 为 success/invalid_response/request_failed，只表示客户端请求及 JSON 解析，不是最终运行或研究评分。提供商 token/cost 即使模型内容解析失败仍保留；未知字段记 null。零调用的本地拒绝不增加 HTTP 尝试记录。

estimated_cost_usd 基于返回的实际 token 计数和配置单价；provider_cost_usd 使用 usage.cost。两者独立，不能相互冒充。cost 未知则 spent_usd=None，该实例停止继续请求；需从平台核对未知扣费，再规划剩余额度，不直接新建客户端忽略它。spent_usd 已知时对所有尝试的实际 cost 求和，包括失败。调用者负责将记录保存到本次 runs 输出并映射到 RunRecord。

本地预算使用输入 UTF-8 字节数加 64 作为 token 估计，并按 max_output_tokens 预留输出费用。它是单实例估算检查，不是精确 tokenizer 上界、跨进程账本或平台硬额度；不同实例不共享余额。提供商请求限制 token 单价和零按次附加费，仍须使用 OpenRouter 端共享 key/团队额度控制真实总支出。未知价格拒绝发送。

## 3. CLI

plan/review/render/smoke/run/import-synopsis/evaluate/check-client 已接入。check-client 只做本地配置检查，不验证远端凭据。每个命令接受 --project-root；相对 CLI 输入与输出路径由该根目录解析。

```bash
python -m moodcut plan --scene tests/fixtures/scene.json --assets tests/fixtures/assets.json --mock --output runs/dev/initial.json
python -m moodcut review --scene tests/fixtures/scene.json --plan tests/fixtures/plan.json --assets tests/fixtures/assets.json --mode moodcut --mock --output runs/dev/review.json
python -m moodcut render --plan tests/fixtures/plan.json --assets tests/fixtures/assets.json --output runs/dev/render
python -m moodcut smoke --mock --output runs/dev/smoke
python -m moodcut run --mock --cache-dir runs/plan-cache --output runs/dev/block
python -m moodcut evaluate --config configs/experiment.json --dry-run
python -m moodcut evaluate --records runs/dev/block/block.json --blind-output runs/dev/blind
```

smoke 不联网、不需要 key、不渲染视频，检查三条 JSON 链路；run 默认 mock，--no-render 可跳过视频。render/run 视频先检查 FFmpeg/ffprobe 和可用字体，顺序为 --font、MOODCUT_FONT、configs/render.json、系统候选。显式配置错误不偷偷换字体。真实调用必须同时有授权、--allow-paid、--max-cost-usd、明确模型及价格配置；不自动重试或切换模型。所有输出新建，不覆盖。

evaluate --dry-run 仅列任务；--records 接受 block.json、run.json 或记录列表。--blind-output 复制已有非空 MP4 到匿名 public/videos，public 只有匿名索引和空评分模板；PRIVATE 私有映射含目标 tone、条件、初稿与视频 SHA-256。导出不是播放器验证，发放前需检查视频。--ratings 必须搭配同次导出的 --private-key；旧映射或视频被替换时拒绝。评分字段和统计分母见任务卡 MC-05 与 evaluation.md。

开发检查可另运行 `python scripts/compare_demo.py --run runs/<block>`，在该运行目录生成 comparison.html。该工具只读现有输入/计划/审查/视频和账目，新建 HTML，不改原始文件，不调用 API，不产生评分。字段差异、模型复查和人工评价仍须分开解释；该页面展示条件、目标和审查意见，不作为盲评观看材料发放。

## 4. 固定存储与结构检查

共享夹具由 P1 写在 `tests/fixtures/`，不用被现有 `.gitignore` 整体忽略的 `data/`。P2 维护 `assets/manifest.json`，原始第三方图片在忽略目录 `assets/raw/`。运行结果在忽略目录 `runs/`。P1 修改 .gitignore；各模块不各自修改根配置。

必检：版本、scene/tone 对齐、唯一 shot_id、有效 beat/character/asset 引用、所有必需 beats 被覆盖、duration>0 且合计60–90、镜头数1–6、visuals每镜头1–2项且crop受允许；dialogue speaker 必须在 scene.characters 中。素材不存在、hash不符、非图片或越界路径均报错。

结构验证不判断角色是否真的完成了叙述事件，也不判断台词是否自然、情绪是否正确。这些通过独立标注检查。

## 5. 生成式开发视频（独立于原 animatic）

`scripts/generate_video.py` 读取成功且哈希匹配的既有 baseline/moodcut 记录，默认离线输出 `kind=derived_development_video_pair` 的 bundle 与请求预览。`video_generation.build_video_bundle(scene, initial, revised, manifest, config, *, project_root)` 使用公共 `validate_plan` 核对原记录，明确把 candidate 投影到 dialogue；其他修改列入 ignored_non_dialogue_changes。该派生输入不继承原复查结论，不改变源文件。

`configs/video.json` 显式配置开发场景、人物/参考图、场景动作、声音、镜头时长和生成参数。原计划的 duration_s 仍符合旧契约；新视频时长来自独立配置并另行记录，不能用旧计划时长冒充新视频时长。当前示例前后各 18 秒，仅用于开发，不改正式实验配置。

每个 request 包含 model/prompt/duration/resolution/aspect_ratio/generate_audio/seed/input_references；不包含 frame_images。素材清单的本地图经过公共验证；公开 source_url 作为服务端参考输入，不上传本地文件、不发送卡片版式。前后共用人物、方向、生成设置与 seed，只改变台词。完全相同的请求可复用同一镜头并标记，不能重复记调用和费用。

`video_client.OpenRouterVideoClient` 是独立异步端点的传输适配器，复用公共 BudgetError/OpenRouterError/严格 JSON；不取代原文本 LLMClient。POST 一次，保存 job ID，GET 轮询/下载；resume 只恢复一个已有任务，不能发 POST。每任务 receipt 保留未知扣费和失败；失去提交响应时不自动补交。最新模型目录/价格由付费 CLI 在提交前核对；估算预算不是平台硬上限或共享账户账本。

拼接要求每镜头同时存在实际视频和音频流、时长与请求一致，保留生成音频。generation.json 的 assembled_requires_manual_inspection 只表示文件拼接通过，不能解释为中文台词正确、动作/情绪通过。语音内容、口型、人物一致性、剧情和情绪需独立人工检查；首次真实调用尚未验收。

`video_client.estimate_video_cost(config, request) -> Decimal` 是客户端预算与请求编译共用的报价入口。支持 Wan 2.7 的每秒价格，以及 Seedance 2.0 Mini 的视频 token 价格；不混用计费单位。Seedance 只允许图像参考、原生声音、16:9 的 480p/720p，使用官方 `宽×高×秒数×24/1024` 输出 token 公式；未知 SKU、价格上涨或超出已核对的规格拒绝提交。切换模型保持素材与台词身份，不自动重试被拒绝的输入；新的真实试跑另行确认预算。

## 6. 下一阶段生成式比较约束（待实现）

本节发布生成模式 **1.1** 的公共数据与接入约定。公共纯函数、验证器及pipeline的生成脚本编排/共享哈希记录已实现；编排的准确参数与依赖见6.7。P2/P3真实接口、P4请求编译、P5资格核对及CLI接线仍由各任务完成，不能把脚本记录解释为生成请求或成片。上文1.0 animatic与历史开发投影保留，不重写既有结果。

### 6.1 当前可导入的公共接口

```python
from moodcut.contracts import (
    CONTRACT_VERSION, CONDITIONS, OUTPUT_MODES, GENERATION_SETTING_FIELDS,
    json_hash, allowed_patch_fields, non_dialogue_plan,
    assert_dialogue_only_revision, shared_generation_payload,
    shared_generation_sha256,
)

# CONTRACT_VERSION == "1.1"
# CONDITIONS == ("baseline", "generic_review", "moodcut")
# OUTPUT_MODES == ("animatic", "generated")
def allowed_patch_fields(*, output_mode: str) -> frozenset[str]: ...
def non_dialogue_plan(plan: dict) -> dict: ...
def assert_dialogue_only_revision(initial: dict, revised: dict) -> None: ...
def shared_generation_payload(scene: dict, plan: dict, manifest: dict, settings: dict,
                              *, template_sha256: str) -> dict: ...
def shared_generation_sha256(scene: dict, plan: dict, manifest: dict, settings: dict,
                             *, template_sha256: str) -> str: ...
def json_hash(data) -> str: ...
```

所有函数无文件/网络/模型调用，不修改输入；非法协议身份或越权修改抛 `ValueError`。`pipeline.json_hash` 兼容导出同一个实现，旧序列化字节和缓存身份不变。辅助函数不检查素材文件字节、完整分镜结构、模型能力或剧情语义，调用者仍须完成这些检查。

`allowed_patch_fields` 在 generated 下仅返回 dialogue；animatic 下仍为 dialogue/narration/visuals/duration_s。它是字段策略，不自动应用补丁；旧 crop、角色和原子性限制依然有效。

### 6.2 数据与版本

完整可加载示例：`tests/fixtures/generated_contract.json`。它引用已有 `tests/fixtures/assets.json`，包含 scene、initial_plan、三份 condition_plans、settings、template_sha256、预期 shared_generation_sha256 和三条 run_records。示例来自既有手写软件故事，不是新数据集、模型产物或效果证据；示例 `software-fixture/video-model` 不是真实模型。

| 对象 | 1.1 字段与约束 |
|---|---|
| GeneratedScene | 保留原 SceneInput 字段；schema_version=`1.1`，output_mode=`generated`；新增 min_shot_duration_s/max_shot_duration_s。两角色、原三种 tone、必需 beats/素材引用保持不变。四个时长上下限均为正整数，镜头范围和总长范围各自有序；max_shots 仍为 1–6。 |
| GeneratedPlan | 保留原 ShotPlan 字段；schema_version=`1.1`，output_mode=`generated`；新增非空 scene_direction。每镜头新增非空 direction，duration_s 为正整数，满足 Scene 的镜头范围及总长范围，不再强制 60–90 秒。visuals 保留素材映射，不代表卡片首帧；narration 是共同元数据，不自动变成配音。 |
| AssetManifest | 沿用 schema_version=`1.0` 和现有路径、内容哈希、尺寸、来源及角色约定，不另复制素材。真实提交前仍需验证本地字节与实际参考输入。 |
| GenerationSettings | 精确字段为 schema_version=`1.1`、output_mode=`generated`、model、resolution、aspect_ratio、generate_audio、seed、style、sound、characters；不允许其他键。五个文本字段非空，generate_audio 必须 true，seed 为非负整数。characters 与 Scene 角色同序，每项精确为 id/asset_id/voice，voice 非空，素材必须绑定该角色。 |
| ReviewReport / RevisionPatch / Verification | 沿用第1节的原 JSON 外壳，report/patch 的 schema_version 仍为 `1.0`；执行模式通过 output_mode 参数传递，不把新键塞进旧闭合补丁外壳。generated 模式的每条 set 只含 dialogue；一个 shot 最多一条 edit，引用一个该镜头的有效 issue_id；revise 输入汇集该镜头全部意见，verify 仍覆盖所有原 issue_id。 |

GeneratedScene/Plan/Settings 必须显式声明 1.1/generated，不能把旧 1.0 记录自动改标签升级。公共 validator 已检查1.1场景/计划结构及本地素材；身份辅助函数完整保留未来 scene/plan 扩展字段，不替代完整验证。台词项只允许 character_id/text，不能夹带音色或动作控制。

```python
from moodcut.validation import validate_scene, validate_plan
scene_errors = validate_scene(scene, manifest, project_root=".", output_mode="generated")
plan_errors = validate_plan(scene, plan, manifest, project_root=".", output_mode="generated")
```

两函数返回 list[str]，空列表表示结构通过，不修改输入。默认 animatic 仍使用1.0和60–90秒；显式 generated 要求1.1/generated、整数秒、镜头/总长上下限、scene_direction 和每镜头 direction。未知模式不自动推断或回退。沿用素材路径、文件哈希、尺寸、crop、角色/beat引用、覆盖和镜头数量检查。验证器不检查提供商能力、实际视频表演或台词情绪，也不自动补长片段；模型可用参数仍由提交前预检处理。

GenerationSettings 不放运行路径、价格、计费记录、condition、单独台词或开发对的 shots 配方。动作与时长只从共同 Plan 读取，避免配置和计划各有一份互相冲突的值。原 `configs/video.json` 仍是 1.0 开发对配置；P4 显式适配到新 Settings，报价配置单独传给现有成本函数，不直接把旧配置当作 1.1 Settings。未知模型选项不能静默忽略；新增选项先修改公共契约及身份测试。

### 6.3 两层哈希和比较资格

`json_hash` 使用 `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)` 的 UTF-8 SHA-256，不做 Unicode/数值归一化。字典键序不影响身份；列表顺序保留，1、1.0 和 true 不视为同一输入。1.1 身份输入仅允许 JSON 类型、字符串对象键及有限数值。

`initial_plan_sha256` 是共享初稿的完整哈希，含台词。`final_plan_sha256` 是实际最终脚本完整哈希，含台词。三条件必须共享 initial_plan_sha256，不能把每个条件的 final hash 当作共同初稿身份。

`shared_generation_payload` 精确返回：

```text
{
  contract_version: "1.1",
  scene: 完整 GeneratedScene,
  plan: 完整 GeneratedPlan，仅删掉每镜头顶层 dialogue 键,
  references: 按 scene.asset_ids 顺序选取的
              [{asset_id, character_id, sha256, source_url}],
  settings: 完整 GenerationSettings,
  template_sha256: 编译提示模板的实际 UTF-8 内容哈希
}
```

shared_generation_sha256 是上述载荷的 json_hash。manifest 存储顺序、本地 path、尺寸和许可说明不进入身份；内容哈希与实际 source_url 都进入。未使用的 manifest 条目不进入；scene.asset_ids 中的全部素材均进入。condition、输出位置和计费数据属于外部运行记录，不得放入 Scene/Plan/Settings；未知扩展键不会被辅助函数自动删除。台词仅从 plan.shots[].dialogue 排除，不再删除其他字段或只比较几个已知键。

P3 调用 `assert_dialogue_only_revision`；P4 为每条件重新计算共享身份，只有与初稿相等才编译请求；P5 从保存的输入重新计算，不能仅信任记录里填入的 hash。完整请求另用 json_hash 保存 request_sha256，台词改变应改变请求身份。每镜头 seed 明确为 settings.seed + 镜头从0开始的序号，三条件使用同一序号，不随 condition/重试改变。

固定 seed 不保证改台词后画面/语音完全相同。比较资格只说明输入符合约束，不表示视频可播放或情绪正确；不匹配保留失败及费用记录，但拒绝作为有效比较导出。不能因台词过长就替某条件延长镜头、改动作或自动加一次调用，应保留可实现性错误。

### 6.4 生成记录与账目

GeneratedRunRecord 保留第1节 RunRecord 字段，并使用 schema_version=`1.1`、output_mode=`generated`；三个 condition 名称固定，不接受 dialogue_revision 作为正式三条件别名。新增字段如下：

| 字段 | 类型 / 含义 |
|---|---|
| shared_generation_sha256 | string 或 null；初稿/共享配置未就绪的失败可为 null，比较前必须重算核对 |
| video_model_id | string；model_id 仍指文本审查模型，不混用 |
| generation_status | not_started / prepared_offline / in_progress / assembled_requires_manual_inspection / failed / interrupted |
| comparison_status / comparison_errors | not_checked / eligible / ineligible；原因 string[]。eligible 仅表示共同输入和审查来源满足约束，不是主观质量或正式纳入评分的决定 |
| generation_jobs | 下述镜头记录列表；无请求时为空 |
| review_calls / generation_posts / video_get_calls | 非负整数；分别记录逻辑审查调用、真实生成 POST 尝试和视频 GET 尝试 |

每条 generation_jobs 为 `{shot_id, request_sha256, receipt_path, status, reused_from, generation_posts, estimated_cost_usd, provider_cost_usd}`。status 为 prepared_offline/submitting/in_progress/downloaded/failed/interrupted；未提交时 receipt_path 为 null，真实提交后指向已有脱敏回执，保留远端原状态/错误/job ID。reused_from 为 null 或 `{run_id, shot_id}`，且必须是本 block 内完整请求指纹相同的已下载片段；复用不算新 POST，自己的增量费用为0，来源费用只计一次。

原 calls 保留逻辑调用含义：本条件 review_calls + generation_posts；real_http_calls 记实际 HTTP 尝试，含轮询/下载 GET，和 calls 分开。mock 审查的逻辑次数可以非零，实际 HTTP/费用为0；共享规划及公共预检另存在 block 账目，不重复分摊到三个 run。token 只统计可获得的文本用量，视频没有该字段时保持 null。

RunRecord 的 estimated_cost_usd/provider_cost_usd 是本条件尝试的消费记录，保持 JSON number 或 null，不直接放 Decimal 字符串。请求报价另外保存为 quoted_cost_usd（十进制字符串），不能拿报价当实际支出。只要消费未知，总费用为 null，原回执和已知小计保留；没有请求的0费用必须有零尝试记录支持。

run_status 新增 prepared，表示只完成离线准备；generated 下仅当脚本/审查有效、真实 A/V 拼接通过后才为 completed，否则失败为 failed。render_status 仍沿用 not_started/rendered/render_failed，不把 prepared_offline 映射为 rendered。assembled_requires_manual_inspection 表示文件检查通过，台词/口型/情绪仍未验收。`unchanged` 是合法审查结果；rejected/review_failed 回退不能冒充有效修订。

既有 `scripts/generate_video.py` 开发对入口现已接受 completed 且 review_status 为 applied/unchanged 的来源，并兼容旧 no_changes 只读别名；unchanged/no_changes 的最终完整计划哈希必须等于初稿。仍核对来源哈希，failed/rejected/review_failed 不接受。无意见与空补丁可以合法 unchanged，不表示所有复查意见已经解决。本修复不把该旧入口升级为1.1三条件生成。

Fixture 中的三条记录是零调用、未渲染的 synthetic 软件记录；validation_status/generation_status 为 not_started，comparison_status 为 not_checked，不伪造真实验证或生成。现有 summarize 可读取其基础字段，不表示现有 evaluate 已实现新的共享身份验证。P5 必须先接入新资格核对，再导出生成式比较。

### 6.5 各模块接入签名（验证器已实现，其余仍待接线）

公共 validate_scene/validate_plan 的下列参数已实现；其余函数仍是各模块的后续目标签名，不是已有参数。默认 animatic 兼容旧调用；生成调用必须显式传 output_mode="generated"，与 Scene/Plan 版本一致。不要忽略未知参数或静默退回旧模式。

```python
# P1 validation.py：已实现，返回 list[str]。
def validate_scene(scene, manifest, *, project_root=None, output_mode="animatic") -> list[str]: ...
def validate_plan(scene, plan, manifest, *, project_root=None, output_mode="animatic") -> list[str]: ...
# 以下仍待所属模块实现。P2 planner.py：两个函数均追加此参数。
def make_plan(scene, manifest, client, *, project_root=None, output_mode="animatic") -> dict: ...
def make_plan_with_trace(scene, manifest, client, *, project_root=None, output_mode="animatic") -> dict: ...
# P3 reviewer.py / patches.py：保留 mode 的 generic_review/moodcut 含义。
def review_and_revise(scene, initial_plan, manifest, client, *, mode,
                      project_root=None, output_mode="animatic") -> dict: ...
def apply_patch(scene, plan, manifest, report, patch, *, project_root=None,
                output_mode="animatic") -> dict: ...
# P4 video_generation.py：新入口不冒充旧的开发投影入口。
def build_generated_video_bundle(scene, initial, plans, manifest, settings, *,
                                 project_root, template_sha256, pricing_config) -> dict: ...
# P5 evaluation.py：新增前置资格核对，原统计公式不变。
def validate_generated_comparison(records, *, scene, initial, plans, manifest,
                                  settings, template_sha256) -> list[str]: ...
```

P4 的 plans 必须精确包含 baseline/generic_review/moodcut 三个键；baseline 等于完整 initial，两个 review 最终脚本经 dialogue-only 检查。返回 `{schema_version:"1.1", output_mode:"generated", kind:"generated_three_condition_bundle", initial_plan_sha256, shared_generation_sha256, settings, conditions:[...]}`，conditions 按 CONDITIONS 排列，每项 `{condition, final_plan_sha256, jobs:[...]}`，job 至少含 shot_id/request/request_sha256/quoted_cost_usd。不把 condition 或审查意见注入模型提示；复用现有异步传输、成本函数和 A/V 拼接。

P5 返回所有输入/来源不一致原因，成功为空列表；缺条件、hash 不符、失败回退不可静默通过。它不判断主观分数，也不决定正式失败纳入规则。P1 在后续集成中调用各模块并映射上文记录；CLI 计划追加 `--output-mode {animatic,generated}`，**当前尚未实现**，不得把未来命令当成现有命令验收。

### 6.6 后续接线必须满足的约束

1. **先共同规划，再拆分条件。** 每个 scene/tone/replicate 只产生一次初始台词及共同场景、动作、镜头和时长，冻结后 deepcopy 为 baseline/generic_review/moodcut。P2 的新规划是共享基础，不是本对照的实验变量。
2. **只允许 dialogue 修改。** 生成模式下两类审查使用相同字段白名单；动作、表情/肢体要求、narration、镜头顺序/数量、时长、素材等全部固定。去掉每镜头 dialogue 后的完整计划必须相同，包含未知扩展字段；越权整体拒绝。旧 animatic 多字段能力以显式模式隔离，不改写历史结果。
3. **核对两层身份。** 保留 initial_plan_sha256；新增 shared_generation_sha256，按规范化 JSON 哈希完整的非台词计划、参考图内容身份、共同动作/镜头/声音要求、模型参数/seed、编译模板版本。共享载荷排除实际 dialogue、condition 标签和输出位置；实际请求另存完整指纹。P1 提供唯一规范和公共校验，P4 在请求前、P5 在比较导出前核对。违规保留失败/费用记录，但拒绝作为有效对比。
4. **审查能力公平。** 两类审查共用模型、上限和最多一次 critique→revise→verify，仅准则不同；提前退出按实际记录。每镜头多条意见汇集成一条 edit，verify 覆盖原报告所有意见，并核对实际用于生成的最终脚本。不可继承旧多字段候选在投影前的复查结论。
5. **共同生成条件。** 相同人物参考、动作/镜头、音色/声音要求、模型、分辨率、时长和对应 seed，只替换台词。不得把方法标签/审查意见注入生成提示，也不得针对单组增强动作或表情。相同请求可在同块复用，记录来源及实际调用/费用。
6. **诚实记录未修改和失败。** `unchanged` 是合法审查状态，不等于失败；`rejected/review_failed` 的回退不是有效修订。生成记录须映射三条件及来源，不能把历史 dialogue_revision 开发投影直接重命名为正式实验。失败、超时、无视频和 unknown 费用均保留，正式评分纳入规则需团队确认。
7. **短片模式独立。** 新 generated 模式使用显式的镜头/总时长范围，不强行补到 60 秒。旧 animatic 保留原约束；接口 PR 发布前不要假定 schema_version=1.0 已接受新字段或新时长。

本对照可回答共同规划/生成设置下，情绪专项台词审查相对通用审查的端到端效果。固定 seed 不保证改台词后画面、表情和语音相同，不能单独归因于面部表情、动作规划或 Agent 数量。新增消融条件、数据集、评分口径及正式运行规模须另行确认；本节不授权实验或付费调用。

### 6.7 已实现的生成脚本编排与共享身份记录

`pipeline.run_experiment` 在既有编排上增加keyword-only参数 `output_mode="animatic", generation_settings=None, template_sha256=None`。显式generated要求1.1 Scene/Plan及第6.2节完整Settings；template_sha256由P4按实际编译模板内容计算，P1只检查输入身份，不声明已验证模板实现。默认animatic不变，不允许省略模式而暗传生成设置。

生成模式向P2的 `make_plan_with_trace` 和P3的 `review_and_revise` 显式传递 `output_mode="generated"`。依赖尚未支持时记录失败，不捕获未知参数后改用旧调用。当前离线边界测试使用标注清楚的P2/P3替身及FakeClient，不表示真实模块已经完成联调；client=None不会生成旧animatic假稿来冒充1.1计划。

同一block只有一次规划；缓存有效时不再规划。生成缓存身份另含1.1模式、完整GenerationSettings和模板哈希，并核对保存的计划/共享哈希；损坏缓存保留并失败，不重新调用。编排保存Scene/Manifest/Settings快照，给各条件和审查依赖深拷贝，公共输入不能被审查修改后传染到后续条件。

`run_condition` 同样增加上述三个参数，以及 `expected_initial_plan_sha256`、`expected_shared_generation_sha256`。generated下两个期望值必须与block冻结输入相等，不能省略；standalone调用也必须传。进入审查前重算输入，审查后重新验证本地素材字节和完整计划，调用 `assert_dialogue_only_revision`、重算共享哈希并核对冻结身份。baseline/unchanged另需最终完整哈希等于初稿；审查只接受applied/unchanged，no_changes仅是旧开发对加载别名。非法候选保留审查及最终脚本供审计，run标failed，不作为有效修订。

根输出保存 `scene.json`、`assets.json`、`generation_settings.json`、成功规划后的 `initial.json`、`planning.json`、`block.json`。每条件保存独立输入、generation_settings、initial/final、审查记录（如已执行）及run.json；final_plan_path指向实际保存的候选。block和run记录共享哈希，run.prompt_hashes.video_template保存模板身份，足够从留存输入重算。共享哈希排除台词和输出位置，初稿/最终完整哈希仍包含台词。

此入口只准备脚本，**不编译视频请求、不创建视频任务、不调用animatic renderer**，包括render=True时。通过时block.status和run_status为prepared，generation_status与render_status均为not_started，generation_jobs为空，POST/视频GET为0，video_path为null。失败保留run和账目；共同输入/来源无效时comparison_status为ineligible，通过时仍为not_checked，须等P4/P5后续核对；不宣称eligible或情绪合格。

规划逻辑调用及费用只在planning/block记录；run.review_calls与run.calls只含本条件实际审查调用，generation_posts/video_get_calls为0。沿用客户端账目，已知失败消费保留、未知消费为null，并由原预算门禁阻止后续调用；报价不充作支出。新回归同时覆盖FakeClient及明确标注的HTTP传输替身，所有真实网络连接禁止。完整CLI、三条件请求/单镜头选择、request_sha256和视频/资格装配仍待后续增量。
