# MoodCut 模块契约

本文件定义模块间的公共接口。第1–4节为已实现的1.0 animatic；第5节为既有开发投影；第6节定义已实现的1.1生成式数据、验证/脚本编排、规划/审查、请求编译、本地记录装配及媒体检查材料。离线资格报告已实现（6.14）；盲评导出/评分接线已实现（6.15）；任务执行接线见6.17（模拟回执验收）；真实试跑仍待批准和验收。Python 3.11；包路径 `src/moodcut/`；统一使用JSON可序列化dict。

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

### HeyGen pilot adapter (2026-10-24)

`heygen/heygen-video-1` is restricted here to 768p, 16:9, 5–15 integer seconds and 1–9 image references. `video_request_controls` fixes `provider.options.heygen.parameters.prompt_enhancement="disabled"`. HeyGen always generates scene audio and does not expose the `generate_audio` toggle, so its HTTP request omits that field while GenerationSettings still requires native audio. The compiler adds `<Picture N>` reference labels. All other models retain their original request shape; the shared settings schema is unchanged.

Pricing uses the reference-to-video SKU, never its cheaper text-only SKU: `(duration * reference_price_per_second_usd + max(0, image_count - 2) * reference_image_price_usd) * (1 - provider_discount)`. Public GET discovery separately verifies the sole HeyGen endpoint's discount. Missing/changed discounts, new pricing SKUs, increased rates or unavailable enhancement controls stop before POST. Frozen pilot rates are $0.10/second and $0.04/additional image before the verified 50% discount, yielding $0.25 for five seconds and two images. Only returned usage reconciles actual charges.

The compiler also accepts explicit `data:image/png;base64,...` references for this model, checking strict base64, PNG signature and exact SHA-256 equality with the locally verified asset. The inline URL participates in the shared identity and request hash. Ordinary HTTPS preparations remain byte-compatible. The first HeyGen attempt was rejected because the GitHub attachment returned `application/octet-stream`; a valid PNG hash alone did not establish the provider's Content-Type requirement. The correction was first verified offline; that preparation did not authorize retrying the failed task. A subsequent, separately authorized inline-PNG pilot completed three actual clips at $0.25 each ($0.75 total), with audio/media checks passed and manual acceptance pending; see [pilot record](pilots/umbrella-single-shot.md). This result grants no automatic retry or further paid execution. The original transport, ledger, inspection and scoring implementations remain in use.

### Role-routed text pilot (2026-10-24)

`RoleRoutedClient.from_env(config_path, allow_paid=..., max_cost_usd=...)` accepts exactly two public configuration objects, `planning` and `review`, and reuses two fresh `OpenRouterClient` instances. The existing director/scene/shot stages use the planning model; critique/revise/verify in both review conditions use the same review model and controls. No prompts, responses, patches or validation rules are changed. `reasoning_enabled` is an optional boolean; omitted preserves the old HTTP shape, while explicit false sends `reasoning.enabled=false`.

The router applies one shared text reservation/actual-cost ceiling across both roles, preserves ordered call records with their actual requested/returned model IDs, and stops on any request failure, unknown charge or budget breach. In `run_experiment`, a routed condition failure also stops later conditions before another model call; their records retain the original inputs, `review_status=not_started`, zero calls and an explicit prior-failure diagnostic. Legacy single-client behavior is unchanged.

For routed blocks, `model_id` is a `role-policy/<sha256>` identifier, not a provider model. `text_model_settings` on the block, planning record and condition records binds both actual role model IDs, temperatures and reasoning controls. It participates in the original planning cache identity. Saved-source rechecks require the same policy and verify each phase's requested call model against its assigned role; a policy ID without its metadata is rejected. Existing records without a role policy remain compatible. Paid text and video limits remain separate client controls; a run must subtract known text spending from its approved combined ceiling before video execution.

The approved Anna/Elsa development pilot and actual results are recorded in [the pilot sheet](pilots/anna-elsa-agent.md). Its budget does not authorize retries, replacement models, handwritten dialogue fallback or formal sample expansion. Those results use the original global-review protocol. The subsequent offline actor protocol in 6.18 routes `actor_critique` to review and `actor_revise` to planning/screenwriting; it does not change or relabel the historical run.

## 6. 下一阶段生成式比较约束（待实现）

本节发布生成模式 **1.1** 的公共数据与接入约定。公共纯函数、验证器、pipeline脚本编排、离线CLI/记录装配及P2/P3/P4规划审查编译/本地检查材料已实现，详见6.7–6.13。P5资格/导出见6.14/6.15，任务执行接线见6.17，真实试跑仍待批准和验收，不能把prepared脚本或请求解释为真实成片，也不能把本地软件媒体检查当成模型质量验收。上文1.0 animatic与历史开发投影保留，不重写既有结果。

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
| review_calls / generation_posts / video_get_calls | review_calls 为非负整数；POST/GET 为非负整数或 null（旧回执缺计数）。null 不当成0，缺失原因及已知小计另存 |

每条 generation_jobs 为 `{shot_id, request_sha256, receipt_path, status, reused_from, generation_posts, estimated_cost_usd, provider_cost_usd}`。status 为 prepared_offline/submitting/in_progress/downloaded/failed/interrupted；未提交时 receipt_path 为 null，真实提交后指向已有脱敏回执，保留远端原状态/错误/job ID。reused_from 为 null 或 `{run_id, shot_id}`，且必须是本 block 内完整请求指纹相同的已下载片段；复用不算新 POST，自己的增量费用为0，来源费用只计一次。

原 calls 保留逻辑调用含义：本条件 review_calls + generation_posts；real_http_calls 记实际 HTTP 尝试，含轮询/下载 GET，和 calls 分开。mock 审查的逻辑次数可以非零，实际 HTTP/费用为0；共享规划及公共预检另存在 block 账目，不重复分摊到三个 run。token 只统计可获得的文本用量，视频没有该字段时保持 null。

缺历史尝试计数时 calls/real_http_calls 也可以为 null；只对已知成分求小计，见6.9。HTTP尝试指客户端发起的请求（包括被跟随的内容重定向），不表示服务端已处理或计费；网络栈内部重传不另计。prepared_offline 的0必须来自明确未提交，而不是从终态倒推。

RunRecord 的 estimated_cost_usd/provider_cost_usd 是本条件尝试的消费记录，保持 JSON number 或 null，不直接放 Decimal 字符串。请求报价另外保存为 quoted_cost_usd（十进制字符串），不能拿报价当实际支出。只要消费未知，总费用为 null，原回执和已知小计保留；没有请求的0费用必须有零尝试记录支持。

run_status 新增 prepared，表示只完成离线准备；generated 下仅当脚本/审查有效、真实 A/V 拼接通过后才为 completed，否则失败为 failed。render_status 仍沿用 not_started/rendered/render_failed，不把 prepared_offline 映射为 rendered。assembled_requires_manual_inspection 表示文件检查通过，台词/口型/情绪仍未验收。`unchanged` 是合法审查结果；rejected/review_failed 回退不能冒充有效修订。

既有 `scripts/generate_video.py` 开发对入口现已接受 completed 且 review_status 为 applied/unchanged 的来源，并兼容旧 no_changes 只读别名；unchanged/no_changes 的最终完整计划哈希必须等于初稿。仍核对来源哈希，failed/rejected/review_failed 不接受。无意见与空补丁可以合法 unchanged，不表示所有复查意见已经解决。本修复不把该旧入口升级为1.1三条件生成。

Fixture 中的三条记录是零调用、未渲染的 synthetic 软件记录；validation_status/generation_status 为 not_started，comparison_status 为 not_checked，不伪造真实验证或生成。现有 summarize 可读取其基础字段做空评分诊断；生成式导出和评分必须使用6.15的完整最终block及独立重检入口。

### 6.5 各模块接入签名（含已实现的输入检查，离线资格见6.14）

公共validate_scene/validate_plan、P2 make_plan/make_plan_with_trace、P3 review_and_revise/apply_patch及P4 build_generated_video_bundle的下列参数已实现；P5输入前置检查与离线资格报告（6.14）及盲评导出/评分接线（6.15）已实现。默认animatic兼容旧调用；生成调用必须显式传output_mode="generated"，与Scene/Plan版本一致。P4独立函数只接1.1/generated，不接受旧开发对。不要忽略未知参数或静默退回旧模式。

```python
# P1 validation.py：已实现，返回 list[str]。
def validate_scene(scene, manifest, *, project_root=None, output_mode="animatic") -> list[str]: ...
def validate_plan(scene, plan, manifest, *, project_root=None, output_mode="animatic") -> list[str]: ...
# P2 planner.py：已实现，具体阶段约束与提示身份见6.10。
def make_plan(scene, manifest, client, *, project_root=None, output_mode="animatic") -> dict: ...
def make_plan_with_trace(scene, manifest, client, *, project_root=None, output_mode="animatic") -> dict: ...
# P3 reviewer.py / patches.py：已实现，mode仍指generic_review/moodcut；详见6.11。
def review_and_revise(scene, initial_plan, manifest, client, *, mode,
                      project_root=None, output_mode="animatic") -> dict: ...
def apply_patch(scene, plan, manifest, report, patch, *, project_root=None,
                output_mode="animatic") -> dict: ...
# P4 video_generation.py：已实现，实际模板哈希入口与编译规则见6.12。
def get_video_template_sha256() -> str: ...

def build_generated_video_bundle(scene, initial, plans, manifest, settings, *,
                                 project_root, template_sha256, pricing_config) -> dict: ...
# P5 evaluation.py：已实现输入前置检查，原统计公式不变。
def validate_generated_comparison(records, *, scene, initial, plans, manifest,
                                  settings, template_sha256, project_root=None) -> list[str]: ...
```

P4 的 plans 必须精确包含 baseline/generic_review/moodcut 三个键；baseline 等于完整 initial，两个 review 最终脚本经 dialogue-only 检查。返回 `{schema_version:"1.1", output_mode:"generated", kind:"generated_three_condition_bundle", initial_plan_sha256, shared_generation_sha256, settings, conditions:[...]}`，conditions 按 CONDITIONS 排列，每项 `{condition, final_plan_sha256, jobs:[...]}`，job 至少含 shot_id/request/request_sha256/quoted_cost_usd。不把 condition 或审查意见注入模型提示；复用现有异步传输、成本函数和 A/V 拼接。

P5输入检查返回输入/来源不一致原因，成功为空列表；缺条件、hash不符、失败回退不可静默通过。它不判断主观分数，也不决定正式失败纳入规则。P1/P5离线资格报告见6.14，盲评导出/评分接线见6.15，后续仍需真实任务；`run --output-mode {animatic,generated}`的离线请求入口已实现，准确用法见6.8，不代表付费执行或盲评接线已完成。

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

规划逻辑调用及费用只在planning/block记录；run.review_calls与run.calls只含本条件实际审查调用，generation_posts/video_get_calls为0。沿用客户端账目，已知失败消费保留、未知消费为null，并由原预算门禁阻止后续调用；报价不充作支出。新回归同时覆盖FakeClient及明确标注的HTTP传输替身，所有真实网络连接禁止。本节只完成脚本；离线CLI/请求选择边界见6.8，实际P4编译及本地媒体检查见6.12/6.13，离线资格见6.14；盲评导出/评分接线见6.15；真实任务仍待后续增量。

### 6.8 离线生成入口与单镜头选择

已实现P1入口与P4实际编译器（6.12）；6.7的脚本编排、此处的请求准备及后续视频生成是三个不同阶段。

```text
python -m moodcut run --output-mode generated --source-block runs/generated-scripts/block.json --shot-id s2 --pricing-config configs/video.json --output runs/generated-s2
```

source-block接受已有block.json或其目录，必须为6.7产生的prepared、1.1/generated三条件脚本。shot-id省略时选全部；不重新规划/审查，不接受旧dialogue_revision/animatic、失败回退或已提交的视频运行。默认run仍为animatic；generated入口始终无需key、零HTTP，无付费执行路径。它拒绝allow-paid、预算、responses、cache、scene/assets、model-config、font、no-render、replicate/source-kind等非默认覆盖；mock只表示显式选择离线，不改写来源mock/provenance。CLI输入/输出相对project-root解析，已有输出不覆盖。

程序接口在 `pipeline.py`（路径与既有pipeline调用一样，由调用者相对当前目录解析；CLI负责project-root解析）：

```python
def prepare_generated_run(source_block, *, out_dir, project_root=".", shot_id=None, pricing_config) -> dict: ...
```

它重读block及planning/run/review磁盘记录，核对根与各条件的Scene/Manifest/Settings/初稿、版本、状态、角色素材字节、完整/共享哈希和模板身份。baseline/unchanged必须完整等于初稿，两类审查只准applied/unchanged；最终脚本只改台词，且与留存review.json的状态/候选计划一致。忽略不可信的final_plan_path指针，读取对应条件目录的final.json。source中的逻辑调用/历史账目保留，不充当本次调用。生成中或已提交的来源不能用作此脚本准备入口。

随后调用P4的 `build_generated_video_bundle`（6.5原签名），传完整三组计划、共同设置/模板、独立本地报价配置。函数不存在则报Missing generated request compiler (#24)，不导入旧build_video_bundle替代；不得加生产用fake编译器。P1核对编译输入未被修改，返回bundle的版本/kind、初稿/最终/共享身份、完整镜头顺序、设置、每请求哈希、声音/参考输入、时长、原索引seed及本地报价，之后再次核对来源未被同时编辑。P4仍负责提示模板内容、人物参考映射、语义控制及模型参数实现，不把P1边界检查当成其验收。

编译完整计划后才按shot-id筛选jobs；不截断Plan、不重排镜头或重新编号seed。各条件同一个选择，job另存shot_index，request.seed仍为settings.seed+原完整计划索引。bundle保留完整初稿/共享身份及full_plan_shot_ids、selected_shot_ids，每条实际请求使用公共json_hash记录request_sha256。所有完整请求先通过边界验证，即使仅选择一个镜头。

成功输出四份JSON：bundle.json为筛选后的编译结果；source_inputs.json为完整源Scene/Manifest/initial/plans/settings/template；source_block.json保留原block与历史费用；preparation.json为独立的generated_request_preparation对象，preparation_stage=requests、status=prepared_offline、comparison_status=not_checked、video_path=null，新calls/HTTP/视频POST/GET及消费均为0。它不是完整GeneratedRunRecord，也不当作视频completed或比较eligible；后续#8/#9仍需装配实际任务和资格记录。

preparation中的quoted_cost_usd是选中jobs的本地报价之和（尚未考虑未来同请求复用），不是支出、实时价格或调用授权；本次零消费不覆盖source_block中已知/未知历史消费。pricing_config_sha256记录报价配置身份。入口不做模型目录查询、调用、下载或渲染；首次真实运行仍需单独授权及实时参数/费用预检。输入/编译失败不创建成功准备产物，返回非零，现有结果保留。

原协议边界回归保留明确的P2/P3/P4替身及缺失依赖故障注入。6.12新增实际planner/reviewer/compiler/pipeline加FakeClient的完整和单镜头请求准备测试；所有真实网络连接禁止。旧animatic回归保留。本地媒体检查材料见6.13；离线资格见6.14；盲评导出/评分接线见6.15；真实任务尚未完成，不把离线准备写成成片端到端可运行。

### 6.9 本地生成回执与费用记录装配

P1提供以下离线接口，不创建文本/视频客户端，不调用generate/resume、目录查询、网络或模型，也不拼接/替换视频：

```python
def assemble_generated_records(preparation, *, evidence, out_dir, pricing_config, project_root=".") -> dict: ...
```

```bash
python -m moodcut assemble-generated-records --preparation runs/generated-s2 --evidence runs/local-evidence.json --pricing-config configs/video.json --output runs/generated-records-s2
```

CLI路径相对project-root；程序接口路径相对当前目录。输入为6.8准备目录、同一份本地报价配置、下列本地证据JSON。仍需保留原脚本目录及参考素材，入口重读并核对源block/脚本/审查/素材、保存快照、初稿/完整/共享身份、原shot_index/seed、请求指纹和报价配置身份。源或准备身份错误在写输出前拒绝；不重新调用P4编译器。原协议替身测试保留，6.12新增实际编译请求与软件媒体/回执的复用费用联调，不将此入口当成真实生成链路已就绪。

```json
{
  "schema_version": "1.1",
  "block_id": "从source_block.json复制原block_id",
  "provenance": "说明证据来源；软件夹具须明确标注",
  "conditions": [
    {"condition": "baseline", "jobs": [{"shot_id": "s2", "receipt_path": "baseline/s2/receipt.json"}]},
    {"condition": "generic_review", "jobs": []},
    {"condition": "moodcut", "jobs": []}
  ]
}
```

三条件按固定顺序出现。jobs可以为空或只提供部分选中镜头，省略镜头表示明确未提交；已经尝试过的镜头必须提供回执（包括失败回执），不能通过省略来声明免费。每条job仅允许shot_id、receipt_path或reused_from；后两项不能并用。未知/重复镜头和未知字段拒绝。receipt_path及media_check_path相对证据JSON目录，回执video_path相对回执目录；只接受本地文件路径。由调用者提供已脱敏回执，禁止将key或签名URL写入证据。保留原回执JSON快照、来源路径和json_hash，不覆写输入。

新video_client回执schema_version为1.1，仍保留旧字段，增加download_attempts（内容端点GET）、download_redirect_attempts（实际跟随的内容重定向GET）、video_get_calls及real_http_calls、http_counts_complete。每次尝试前保存计数，包括失败尝试；POST不自动重试。GET=轮询+下载端点+内容重定向，HTTP=POST+GET。只有新回执完整计数才给完整总数。1.0回执仍可读；缺失历史计数保留null，记录missing_counters，不能从downloaded推测1次下载或从failed推测0次。旧回执恢复时仅追加observed_*下界，缺历史部分始终未知，不会通过一次恢复变成完整。这里的HTTP次数不是平台计费次数。

逐镜头保留远端原状态、job_id/provider_error及回执身份。未提供回执为prepared_offline；submitted/pending/in_progress及提供商completed但尚未下载为in_progress；超时、轮询/下载中断为interrupted；远端失败、无可用job ID、身份不匹配、无文件/缺音轨/时长错误为failed，保留已知消费和失败原因，不补图、不自动重试。run保持prepared，出错为failed；原准备对象不能直接改名为成片。

下载片段通过已有video_generation._probe重新检查本地文件的真实视频/音轨及请求时长（容差0.5秒），保存实际文件SHA-256。单镜头直接使用该片段作为完整所选范围的成片。多镜头在未提供拼接检查时保持in_progress；提供condition.media_check_path后，读取P4已有assemble_generated_clips结果并要求补齐如下绑定字段（不修改P4编译器/拼接器）：

```text
{
  video_path: 本地拼接视频路径，相对检查JSON目录,
  sha256: 拼接文件实际字节SHA-256,
  source_clips: 按选中镜头顺序排列的
    [{shot_id, request_sha256, sha256: 对应源片段实际字节SHA-256}],
  ...原有媒体检查信息
}
```

装配器核对绑定并重新探测成片音视频和所选镜头总时长，不仅信任JSON中has_audio/duration_s。文件检查通过且源脚本有效才为run_status=completed、render_status=rendered、generation_status=assembled_requires_manual_inspection。多镜头来源绑定是本地检查材料的声明与哈希核对，不证明拼接内容的语义正确。是否说对台词、说话人、口型、动作及情绪仍需人工听看；软件测试用动态图案与正弦音，不能证明模型表现。单镜头结果保留完整计划身份及selected_shot_ids，不能当完整多镜头片。

复用形式为`{"shot_id":"s2","reused_from":{"run_id":"本block源run_id","shot_id":"s2"}}`。来源必须是同block内非复用、完整请求指纹一致且文件检查通过的已下载片段。拒绝跨block、不同请求/镜头、未下载、循环或链式复用；显式复用新增POST/GET和消费均0，原来源未知扣费仍保留未知。重复提交同一job_id回执不作为新任务消费；重复条目标失败，费用只在原条目计一次，冲突快照的总量置未知。

block.accounting含规划一次加各run的审查/视频增量；run.call_records和review_calls保留原审查来源，calls=review_calls+generation_posts，real_http_calls另外累计视频HTTP。报价仅在job.quoted_cost_usd及原回执，video_client的旧estimated_cost_usd本质也是报价，不能当消费。本传输回执只有provider_cost_usd可作为已记录视频消费，视频estimated_cost_usd和不可获得的token保持null；无尝试或合法复用才记明确0。任何未知消费/计数使对应总数为null；accounting.known_subtotals/incomplete_fields、video_accounting、missing_counters保留已知部分及缺失原因。准备阶段的零新增消费不能清空原规划/审查账目。

输出新目录包含block.json、各condition/run.json，以及源block/完整输入/bundle/preparation/evidence/receipts快照。assembly_activity始终为本次装配零请求，与历史回执累计次数分开。已有输出即拒绝，不覆盖；部分失败仍写完整条件记录及账目，CLI返回1。结构/来源预检错误不写成功输出。没有失败但尚未完成可返回0，必须查看status，不能把命令成功等同视频完成。

comparison_status通过本地边界时仍为not_checked，有失败则ineligible；本接口永不设置eligible。P5须按6.3从实际输入做资格复核。CLI evaluate的生成式盲评导出/ratings必须通过6.15的重新核对；普通离线账目查看仍可用。旧evaluation低层导出/评分入口拒绝生成式比较，不能绕过独立重检。本增量不改评分口径、数据集、实验条件或真实运行授权。

### 6.10 生成式共同规划适配

`planner.make_plan`及`make_plan_with_trace`已支持6.5签名的显式`output_mode="generated"`。默认animatic沿用原三份planning_*.txt、1.0归一化和60–90秒约束；generated使用独立planning_generated_director/scene/shot.txt和真实公共1.1验证器。不自动升级Scene/Plan，不从60秒默认值推导短片时长，也不选择故事、素材、模型或新实验条件。

三个stage仍为director→scene→shot，每阶段最多一次complete_json调用，无自动重试。返回结构仍为`{plan, raw_responses, prompt_hashes}`，make_plan只取plan。客户端由调用者传入；离线使用FakeClient，规划器不自行创建客户端或生成媒体。现有CLI plan仍是默认animatic；生成式规划从程序接口/pipeline调用，6.8的CLI只消费已有脚本block。

```python
from moodcut.planner import make_plan_with_trace, get_planning_prompt_hashes
# scene必须由显式输入提供1.1/generated、镜头及总长范围；manifest仍为1.0。
result = make_plan_with_trace(scene, manifest, client, project_root=project_root,
                              output_mode="generated")
hashes = get_planning_prompt_hashes(output_mode="generated")
```

director返回原有scene_id/tone/beat_order/approach，所有beat必须恰好按输入顺序出现。generated的scene阶段返回`{scene_id, scene_direction, segments:[{beat_ids, description, direction, duration_s}]}`：scene_direction为共同地理/场景要求，每段为一个未来镜头；direction含必需动作、镜头及表演要求，duration_s为满足Scene镜头范围的整数，合计满足总长范围。segments覆盖全部beat且顺序不变，不包含空段，数量不超过max_shots。

shot阶段返回1.1/generated计划，为每段补镜头ID、合法素材引用和初始台词。其scene_direction必须与scene阶段相同，镜头数量及逐镜头beat_ids/direction/duration_s必须原样保留；不得暗改动作、重排、拆删段或补长。最后交公共validate_plan检查完整结构、角色/beat/素材引用、crop、动作与时长。台词只允许character_id/text；narration仍是共同元数据，不自动转为语音。共同声音/模型参数来自独立GenerationSettings，不为某条件单独规划。

normalize_plan也接受显式output_mode。generated可解包完整plan或单scene外壳，保留JSON扩展字段并拒绝冲突元数据/多scene，不静默删字段；不为缺失的schema_version/output_mode/scene_id/tone补头。规划入口随后验证，因此旧1.0或不完整响应明确失败。默认animatic的既有部分外壳补头保持兼容。

scene、manifest、来源provenance和原始响应均深拷贝；完整源Scene保留在payload及pipeline保存的scene.json中，不以改写故事或删除beat来修复模型输出。PlanningError保留失败stage、错误及已取得的原始响应，pipeline写入planning.json，失败不会重新规划。结构检查与提示词约束不证明模型保留了全部剧情语义，也不证明实际表演效果。

规划提示哈希按模式读取。pipeline的缓存身份与planning.prompt_hashes使用同一模式的实际提示，原有planner代码哈希继续参与缓存身份；不能把animatic提示身份记在generated规划上。复用现有一次规划/条件深拷贝，不增加第二套编排。tests/test_planner.py以实际planner和pipeline加FakeClient覆盖既有读信与临时非读信软件输入、短片时长、阶段失败留档、三条件初稿/共享哈希及缓存；临时夹具不是新数据集或模型效果证据。

P2/P3/P4实际代码现已接入pipeline，以FakeClient可保存三条件prepared脚本并离线编译请求（见6.11/6.12），不能解释为成片或eligible比较；本地媒体材料见6.13，离线资格见6.14，真实任务和盲评接线仍待所属任务完成。对照仍只检验同一规划下台词审查的端到端价值，不独立证明规划贡献或更多Agent更优。

### 6.11 台词限定审查与实际最终脚本复查

review_and_revise/apply_patch已支持6.5的显式output_mode参数；mode仍只指generic_review/moodcut，两者不能混用。默认animatic保留dialogue/narration/visuals crop/duration_s能力；generated只允许set包含dialogue，复用allowed_patch_fields和assert_dialogue_only_revision，并传显式模式给实际公共验证器。Report/Patch外壳仍为1.0，不添加关联字段或自动升级旧计划。

```python
from moodcut.reviewer import review_and_revise, get_review_prompt_hashes
result = review_and_revise(scene, initial, manifest, client, mode="moodcut",
                           project_root=project_root, output_mode="generated")
hashes = get_review_prompt_hashes(output_mode="generated")
```

两类审查接收相同故事、目标tone、共同初稿和manifest，调用者传入同一模型配置；模块不创建/切换客户端。所有阶段统一MAX_OUTPUT_TOKENS=2048，每阶段最多一次critique→revise→verify，不自动重试。generated使用review_generated_generic/moodcut/revise/verify.txt；只有critique准则不同，修订/复查模板与字段能力相同。声音、动作、表情/镜头/时长/素材及未知扩展字段均固定；某意见无法只靠台词安全解决时可保留未解决，不强行改剧情或扩能力。

revise的新增输入字段issues_by_shot为按原计划镜头顺序的`[{shot_id, issues:[完整原意见...]}]`，同镜头意见按报告顺序保留；完整原report仍单独传入。每镜头至多一条edit，issue_id选择该镜头的一条有效原意见；其余ID不从report删除，也不塞进闭合Patch外壳。animatic共用这一聚合输入/修订提示改进，原允许字段与重复/冲突拒绝规则不放宽。

补丁原子应用后，reviewer再次核对实际候选的完整非台词内容，再把该候选作为revised_plan传verify。verify仍覆盖原report全部issue_id，包括未被edit直接引用的同镜头意见；覆盖缺失、重复或冲突为review_failed并回退初稿。不存在“先复查多字段候选、再投影成另一计划”的路径；成功返回的plan就是该次verify看到的计划。request/response、错误和实际次数写入既有review.trace；pipeline将review.json/final.json一起保存并核对来源。

无意见可在critique后返回unchanged（1次）；有意见但空补丁/同值补丁仍verify全部原意见（最多3次），合法时unchanged。越权补丁为rejected，任何模型/响应/复查失败为review_failed，保留初稿、原report/patch/verification及诊断；失败不能改标签冒充unchanged。未解决意见或new_concerns不触发第二轮，applied/unchanged都不是人工效果评分。CLI review仍为默认animatic，generated可从程序接口/既有pipeline调用。

get_review_prompt_hashes返回按模式选取的实际system文本UTF-8 SHA-256，pipeline的prompt_hashes使用同一入口；原历史记录不重写。与P1的协同只限提示身份接线，不另建编排。tests/test_reviewer.py/test_patches.py使用手写最小软件夹具重建edits[3]重复shot错误：仍拒绝重复edit，同时验证多意见汇集、单edit合法修订及逐ID完整复查。恶意候选故障注入验证完整非台词检查，不能当真实模块联调。

实际P2/P3/P1链路测试只用FakeClient返回软件JSON，不替换planner/reviewer/validator；可得到baseline/generic_review/moodcut的prepared脚本及applied/unchanged、独立调用账目和共同身份，且通过真实P1源block加载检查。P4请求编译进度见6.12；真实视频、#9比较资格和人工效果尚未完成，脚本prepared/Agent意见不当成成片、有效比较或情绪改善证据。数据集、条件和评分口径不变。

### 6.12 三条件生成请求编译

video_generation.build_generated_video_bundle已按6.5原签名实现，无新增CLI或编排器。输入为显式1.1/generated Scene/initial、精确三键plans、1.0 Manifest、完整GenerationSettings及独立本地pricing_config；不接受开发对或自动升级。复用公共_json_copy、validate_plan、assert_dialogue_only_revision和shared_generation_sha256，验证本地素材字节及四份计划、baseline完整初稿身份、各条件完整非台词一致和共享身份。越权/无效候选直接拒绝，不投影、不修复。

get_video_template_sha256()返回prompts/video_generated.txt实际有效UTF-8文本哈希；以read_text的通用换行规则读取，同一文本同时用于哈希与渲染。规划前用该入口取得模板身份，传给run_experiment并冻结到原block；编译器必须与保存的template_sha256匹配。旧软件夹具的任意模板声明不是生产模板，不改写已保存的哈希或历史脚本来通过检查；模板变更需准备新来源。公共共享哈希规范不变。

模板以SHARED_REQUIREMENTS_JSON保存共同style/sound/tone/scene_direction、角色/声音/参考序号，以及当前镜头direction/duration_s/visuals；末尾DIALOGUE_JSON只填该最终脚本的有序台词。模板不接收condition、审查意见、最终哈希或单组表演增强。动作/镜头/时长只来自共同Plan，narration仍保留在身份中但不转为配音，未知扩展不被当成额外模型控制。相同dialogue与共同输入产生字节一致的完整request，变动台词时仅该JSON片段变化。

scene.asset_ids全部图像按原顺序成为input_references，公共URL检查复用既有_public_reference；模板明确每个reference_index的asset/character/name以及settings指定的primary_identity，声音来自共同characters绑定。只准备公开HTTPS图像参考，不发卡片首帧、不下载/上传素材。验证本地字节不证明远端URL内容一致或提供商接受，原素材拒绝记录仍有效。

每请求精确包含model/prompt/duration/resolution/aspect_ratio/generate_audio/seed/input_references；原索引seed为settings.seed+index。job含shot_id/request/request_sha256/quoted_cost_usd；conditions固定公共顺序，每项保存实际final_plan_sha256，bundle保留完整initial/shared/settings身份及actual template/reference记录。本地quote只调用既有estimate_video_cost，不构造客户端或查询价格。旧configs/video.json可作为价格快照，其shots/style/sound/character配方不参与新编译；模型默认与价格未改。台词长度沿用每秒最多8字符的保守工程检查，不是语速或效果真值，失败不补时长/额外调用。

P1既有prepare_generated_run重读/核对来源后调用真实编译器，完整编译后再选镜头，保留完整计划和原索引seed。实际planner/reviewer/validator/compiler/pipeline加FakeClient已覆盖读信与公交站还伞10秒软件输入、全镜头/单镜头CLI、源文件不变、哈希/模板/设置/引用篡改拒绝。协议替身测试仍明确标注；新联调不替换业务函数。完全相同请求交给现有assemble_generated_records，以动态图案/正弦音和手写回执验证同块复用及费用一次记账，软件账目不是实际扣费。

编译增量只交付离线请求。现有HTTP/费用传输及assemble_generated_clips保持复用，不新写客户端或拼接器；本地成片来源绑定与观看材料见6.13。离线资格见6.14；盲评导出/评分接线见6.15；三条件真实任务及真实台词/口型/情绪验收仍待完成。prepared_offline仍为零新调用/消费、无视频且comparison=not_checked；固定seed不保证改变台词后生成表现相同。不改实验条件、数据集或评分口径，不授权付费调用。

### 6.13 本地成片来源绑定与观看检查材料

P4在video_generation.py提供inspect_generated_video，复用6.9的P1记录装配和既有assemble_generated_clips，不更改其签名、传输、报价或账目。原_probe默认结果不变；include_raw=True可附本次ffprobe实际streams/format供侧车材料保存。

```python
def inspect_generated_video(preparation, *, evidence, out_dir, pricing_config,
                            media_origin, project_root=".") -> dict: ...
```

```bash
python scripts/inspect_generated_video.py --preparation runs/generated-requests --evidence runs/local-evidence.json --media-origin provided_local --output runs/video-inspection
```

preparation及evidence完全沿用6.8/6.9。media_origin必须声明synthetic或provided_local；前者为软件媒体，后者仅指提供的本地文件，不认证为模型产物。CLI路径相对project-root，程序接口沿用调用者路径语义；pricing默认configs/video.json且须匹配已准备的价格身份。无key/allow-paid/提交/恢复路径，不构造客户端、查询目录或联网。输出已存在即拒绝。

先调用assemble_generated_records写preflight_records，复用它对原脚本、资产、请求、回执、复用、文件A/V/时长及账目的核对；源结构预检失败不创建成功检查包。failed条件保留错误，不修复失败回执；未下载/未提交不产出成片。对可检查条件复制实际片段到固定数字文件名（不用shot_id拼路径），重新核对原件/副本字节。已有合法绑定成片直接复制，否则调用原A/V拼接器；不生成静态替代，不另写HTTP/拼接实现。

每条件media_check.json兼容6.9，至少保留有序source_clips（精确shot_id/request_sha256/源片段字节sha256）、成片sha256、相对video_path；另保存block/initial/shared/selected身份、实际源文件及采样绑定。ffprobe.json含实际片段和成片的探测摘要及原streams/format。处理后再次检查字节，派生evidence仅调整本地路径和media_check_path，原输入/回执/账目不改；原证据快照保留。

再调用同一个assemble_generated_records写records，重新核对原回执/片段及成片来源绑定和A/V/时长。最终记录失败或不再completed时不广告为可检查成片；处理中失败可保留诊断文件，状态不冒充完成。records/block.json为最终本地账目，preflight_records只是同一历史的较早快照，二者费用不能累加。报价不当消费、planning一次、同请求复用增量0、失败/未知费用/null历史GET仍由原P1实现保留。本次inspection_activity的0仅表示新请求/消费为0，不清空历史未知消费。

检查包输出index.html、inspection.json、派生evidence及两次记录快照；就绪条件另有film.mp4、clips、frames、contact_sheet.png、media_check.json和ffprobe.json。接触表复用renderer已有布局，每镜头10%/50%/90%取实际帧，保存样本时间/哈希，ASCII序号对应页面原镜头名。相对页面媒体链接无需服务器；记录再次核验仍依赖原始来源/回执。

manual_checks.json/CSV按条件/镜头保存请求/片段/成片身份，以及character_action、dialogue_speaker、audio_lipsync、continuity、notes。判断为null/空白，状态not_reviewed；CSV防公式前缀转义不改JSON原ID。页面展示条件、目标、共同方向及“预期台词”，不是ASR或盲评，不含自动质量分数。由实际观看者另存填写，不因A/V存在或抽帧成功填通过。

顶层status为ready_requires_manual_inspection/incomplete/failed；仅全部所选条件材料就绪时CLI返回0，其余返回1。单镜头保留完整计划身份和selected范围，不冒充全片。所有comparison_status仍not_checked或ineligible，永不设eligible；#9资格/正式评分口径不变。以实际P1/P2/P3/P4+FakeClient、动态图案/正弦音及手写回执覆盖绑定、费用去重/未知、缺音轨/时长、字节变化、单镜头/原成片、失败/未提交和安全路径/页面。软件媒体并非模型或效果证据；真实人物、中文台词、口型、连续性、情绪及实际任务仍需另行授权/验收。


### 6.14 离线资格核对报告

```python
# P1：只读输入，复用原装配计算及实际P4编译器；不写中间记录。
def recheck_generated_records(records, *, pricing_config, project_root=".") -> dict: ...
# P5：组合P1重检、输入/媒体检查，保留完整原始block并输出逐条件结果。
def qualify_generated_records(records, *, pricing_config, project_root=".") -> dict: ...
```

```bash
python -m moodcut qualify-generated-records --records runs/video-inspection/records --pricing-config configs/video.json --output runs/qualification
```

records为最终P1记录目录或block.json；pricing与原preparation一致，源脚本/请求/回执/媒体需仍在记录位置。CLI的相对路径由project-root解析，程序接口输入路径沿用调用者路径语义；素材验证使用显式project_root，不修改进程cwd。旧validate_generated_comparison新增可选project_root=None，省略时保持原当前目录语义。

P1将既有assemble_generated_records计算与写出分离，二者使用同一账目、复用归属、回执及A/V核验实现。重检重新读取源脚本/快照，用实际P4编译器与模板重算完整请求并按原索引选镜头，核对已保存bundle；逐项比较最终block、磁盘run文件、来源/准备/回执快照和重算结果。不会创建客户端、POST/GET、恢复/下载或拼接视频，也不写新的账本；ffprobe只读现有本地文件。

P5复用#37的输入与媒体检查。qualification.json包含kind=generated_qualification_report、schema_version=1.1、output_mode=generated、原始record_block及其canonical records_sha256、三条件comparison_status/errors、块级comparison_status/errors及accounting_verified。结构/来源无法读取时保留可读的原block并给出诊断；条件失败保留全部三条记录及费用，不过滤失败。全部条件通过才为eligible；unknown费用或旧GET缺失保持null和已知小计，核对一致时不单独否决资格。accounting_verified只表示本地保存账目与P1重算一致，不认证提供商账单。

报告不修改原始comparison_status、source_kind、费用或人工检查表。正式纳入formal_inclusion_approved=false、export_enabled=false、speech_and_visual_quality=not_reviewed；eligible仅指当前所选镜头的软件证据，不说明真实人物/台词/情绪、提供商真实性或正式实验通过。activity的0只指本次新HTTP/POST/GET/消费，不抹去历史未知费用。只使用最终records账目，不把preflight_records的同一历史累计第二次。

输出目录必须新建；eligible时CLI返回0，其他情况返回1并写诊断。资格报告自身不授权导出；当前evaluate的独立重检入口见6.15。生成状态汇总见6.16；真实任务执行、正式协议和人工评价仍待完成。本增量只用现有软件夹具/产物验证，不授权付费API、实验规模或新评分口径。

### 6.15 生成式匿名导出和评分接线

```python
export_generated_blind_items(record_paths, *, out_dir, seed, pricing_config, project_root=".") -> dict
summarize_generated_records(record_paths, ratings, *, private_key=None, pricing_config, project_root=".") -> dict
```

仅接受完整最终1.1/generated_record_block文件或其目录，不接受单条件run、任意行列表、旧开发对或资格报告。每个最终block只传一次；重复路径/块/条件和混合source_kind拒绝。价格配置必须显式给出并与保存准备一致，路径相对project_root解析。每次重新调用6.14，不信任旧报告或记录的声明资格，不改变原comparison_status。

CLI复用evaluate，生成式路径必须给出`--pricing-config`。`--blind-output`与`--ratings`分开使用；评分必须搭配同次导出的`--private-key PRIVATE/private_key.csv`。无评分可只传records和价格配置查看完整诊断。旧animatic入口兼容；公开低层export_blind_items拒绝生成记录，summarize拒绝直接输入生成式评分（空评分的原始记录诊断仍兼容）。

只复制整块三条件均eligible的记录；单条件失败时该块不作为可比较材料导出，其他块可独立导出。此为软件证据完整性门禁，不批准正式失败/unchanged纳入规则。所有输入行、逐条件原因和原始费用留在PRIVATE/summary.json及评分汇总，未导出行仍在覆盖、缺失评分和费用分母。零可导出时仍生成空索引/表和完整私有诊断，命令成功表示诊断包写出，不表示有可分发视频。

复用原匿名复制器及随机种子，复制前/后源文件和目标字节必须等于已核对media_check.sha256；复制后再核对完整来源/回执/账目并检查副本。先在临时目录完成，失败不发布目标目录，不覆盖已有输出。公开目录仅有匿名MP4、blind_items.csv(item_id/video_file)及空ratings.csv。电影内容/声音仍需协调人检查是否泄露条件，软件不会自动判断语义匿名性。

PRIVATE/generated_export.json绑定每个完整block的canonical哈希、原本地路径、镜头范围（由完整block哈希覆盖）、匿名item/run映射、实际导出视频字节、私有key及公开索引哈希。私有文件不能发给观看者；哈希用于本地一致性检查，不是签名或提供商真实性认证。评分必须保留整套导出目录；来源也必须仍在保存位置。逐项校验全部映射和副本（包括未评分项），只接受实际导出的匿名item_id，不允许run_id回退。更换源/片段/回执、删减映射或替换副本后拒绝旧评分接线。

评分仍复用原summarize算术：clip等权、uncertain记未命中、M/G仅共同已评分块做差并另报覆盖，空分母为null。condition usage仍不含共同规划；block_ledger_accounting.blocks逐块保留完整原始accounting（含unknown/known_subtotals/incomplete_fields），每块一次，绝不累加preflight。accounting_verified/complete如实标明当前重检状态；不把不一致账目当已核实支出。未生成的新任务和原始空人工表不改。

导出/评分始终formal_inclusion_approved=false、speech_and_visual_quality=not_reviewed。6.14报告export_enabled仍false，须走本节独立重检入口；软件产物和合成CSV算术不是模型或独立人工效果证据。生成状态细分类汇总见6.16；真实任务、正式协议与真实观看者验收仍待后续；本接口不创建client，不调用API/GPU或自动评分。

### 6.16 生成状态细分汇总

`summarize`及现有evaluate、generated匿名导出私有summary、评分结果复用同一汇总器。含generated记录时，overall和每个by_condition都新增generation对象；纯旧animatic/空输入保持原结构，不臆测生成状态。没有新CLI参数，不重建P1状态机或账目，不修改评分/资格/正式纳入规则。

generation.generated_runs为当前汇总范围内output_mode=generated的记录数，not_applicable_runs为其他记录数；二者相加等于原coverage.planned_runs。by_status七类互斥计数之和等于generated_runs，各条件使用自己的分母：

| by_status键 | 保存记录的含义，不推断真实提供商活动 |
|---|---|
| not_started | 生成阶段尚未开始；规划/审查/验证失败也可能停在此处 |
| prepared_offline | 请求离线准备、未提交；不从零调用/空回执倒推此状态 |
| in_progress | 尚未完成本地成片；提供商completed、部分下载或待拼接均可能在此类 |
| assembled_requires_manual_inspection | 文件已装配检查，仍待人工质量判断 |
| failed | P1保存的失败，包括请求/回执/本地媒体错误，不能全称为提供商失败 |
| interrupted | P1保存的中断，例如轮询超时/中断或下载中断；不当成零费用 |
| unknown | 缺失、null、未知或非法状态，保留在总分母，不猜成未开始/未提交 |

其他generation字段是独立诊断轴，不能相加当成额外运行数：pre_generation_failed_runs为run_status=failed且generation_status=not_started；failed_run_causes按所有run_status=failed的原failure_kind计数（缺失为unspecified），可包含generation/media/review等，与状态轴重叠。awaiting_assembly_runs仅指in_progress、尚未rendered且非空镜头记录全部downloaded；远端completed不等于已下载或拼接。runs_with_unsubmitted_jobs数有prepared_offline镜头的运行，可揭示混合运行里的未提交部分。

generation.jobs.recorded_jobs和by_status统计保存的镜头记录条目，状态为prepared_offline/submitting/in_progress/downloaded/failed/interrupted/unknown，七类合计等于recorded_jobs。完整运行即使因一个failed镜头覆盖了其interrupted状态，镜头轴仍保留两者。declared_reused_jobs统计声明了reused_from的条目，不认证复用合法性，不计为新POST/独立提供商任务；费用继续由原P1账目负责。remote_status_counts只按已保存的非空远端字符串计数，保留polling_timeout/download_interrupted/expired等原值，不另行映射；jobs_without_remote_status不等于未提交（复用也可能无该字段）。

runs_with_empty_job_records只数显式空列表；runs_with_invalid_job_records数缺失/非列表或含非对象条目的运行。非对象条目计入镜头unknown；整个镜头字段不可读时不捏造镜头条目或尝试数。这些是记录诊断，不替代6.14/6.15的来源/资格重检。

旧render_failed_runs/render_pending_or_skipped_runs等保留原口径，与生成状态并列查看，不相加。旧timeout_runs仍只按failure_kind=timeout计数，不自动包括failure_kind=generation的轮询超时；后者见interrupted及remote_status_counts.polling_timeout。全部原始失败/未知费用/缺失评分及M/G配对分母、clip等权和uncertain口径不变。输出只增加诊断，不修补原记录、回执、人工表或原block账目。

### 6.17 三条件任务执行、恢复与继续

P1新增以下接线，复用原OpenRouterVideoClient、6.9记录计算及6.13检查包；不另建传输、编译器、状态机、账本或评分器。旧run/generated入口仍只准备请求；旧scripts/generate_video.py仍只处理历史开发对。真实试跑尚未授权，协议提议见 [evaluation.md](evaluation.md#三条件试跑协议提议2026-10-23尚未批准运行)。

```python
def execute_generated_run(preparation, *, out_dir, pricing_config, project_root=".",
                          allow_paid=False, max_cost_usd=None, media_origin="provided_local",
                          resume_execution=None, resume_condition=None, resume_shot_id=None,
                          continue_execution=None) -> dict: ...
```

```bash
# 默认离线，不构造客户端/查询目录/提交/恢复/下载；输出未提交诊断和空人工表。
python -m moodcut execute-generated --preparation runs/generated-requests --pricing-config configs/video.json --media-origin synthetic --output runs/execution-offline
```

CLI路径相对project-root，程序接口路径相对当前目录。media-origin为显式synthetic或provided_local，与6.13同义；不改源source_kind/mock，不把软件视频当模型产物。默认allow_paid=False，预算单独出现即拒绝；未提供HTTP授权时此入口不会模拟生成视频，验收传输替身仅存在于测试/忽略的本地验收脚本。

获得独立模型/范围/费用批准后，方可在相同命令添加`--allow-paid --max-cost-usd <已批准USD阈值>`启用视频HTTP；GET恢复也要求此门禁，不能因为是GET便默认允许。新提交前：重读实际脚本/参考图与保存的四份准备文件，复用P1身份检查，实际调用P4完整编译再按原索引选择，比对完整bundle；不接受篡改后自算哈希的提示。检查本地FFmpeg/ffprobe、凭据存在、全部选中镜头报价和最新模型目录，按实际请求时长核查参数/价格，不沿用旧三镜头配方的duration。目录预检后再次核对源输入及父执行/回执/账目未变；无效预检不创建执行目录，不发视频POST/GET。历史规划/审查消费未知时停止新提交。

三条件按CONDITIONS、镜头按保存顺序执行。只把原request交给现有客户端，不注入方法标签，不改seed或非台词参数。路径使用固定条件和数字索引，不用shot_id作目录名。先保存evidence中的本地回执目标和execution检查点，再调用generate；回执由原客户端在POST前写入，执行器不伪造/补齐回执。若硬中断发生在预留路径与真实POST之间，缺回执仍按未知处理，不能自动重交。

每个已下载片段在下一POST/复用前通过原P1回执、实际音视频/时长/账目检查。仅同block、同shot_id、完整request_sha256相同且拥有非复用下载来源时复用，记录reused_from；不复用失败/未下载来源，不形成链式复用。费用未知、任务/媒体失败、异常及人工键盘中断立即停止后续POST，所有三条件和未执行镜头继续留在evidence及最终记录。异常记录只留类型与通用诊断，提供商详情沿用脱敏回执，不保存任意依赖异常文本。

视频客户端在原receipt.json追加可选`last_error`，记录`phase=submit/poll/download`、`kind=http/transport/invalid_response`及已知HTTP状态码、异常类型或受控原因；HTTP响应有x-request-id时保存脱敏后的请求标识。HTTP错误正文最多读取8193字节，仅对不超过8192字节的JSON提取白名单错误字段写入原`provider_error`；HTML、损坏或超长正文不落盘，仍保留状态码。字符串限长、嵌套限深，移除key、Bearer、URL及data URI；不保存请求头、完整响应或请求副本。最终generation_jobs同时保留last_error/provider_error，原始回执快照继续保存。诊断不改变任务状态、ID、费用与计数，缺ID/未知费用仍阻止后续POST，不增加重试或恢复权限；旧回执缺这些字段仍按原规则读取，不能补造历史错误。

恢复与继续是两个互斥、显式动作：

- `--resume-execution runs/earlier --resume-condition baseline --resume-shot-id <原ID>`：只恢复一个已有、非复用、可绑定job ID的任务；限submitted/pending/in_progress/completed/轮询超时或中断/下载中断。不恢复未提交、无ID提交未知、终态失败或已下载任务，不自动继续剩余镜头。先复制该回执到新输出的resumed-job，核对副本哈希后才调用原client.resume，只有GET；旧回执/媒体/记录不变。新回执的POST和GET是同一任务的累计历史，不是新提交。
- `--continue-execution runs/recovered`：只在全部既有尝试均已下载、费用明确且无失败后，才允许提交其余明确未提交镜头。重用原拥有者缓存，跳过已完成任务；USD阈值覆盖此执行链已知视频消费加全部剩余请求报价（复用前），客户端只得到扣除历史视频消费后的余额。未知消费/进行中/中断/失败不能通过新客户端绕过。没有剩余任务时仅允许离线收集。

上述两种动作默认仍离线；启用HTTP仍须独立授权及allow-paid/正预算。每个父执行目录用独占创建的http_successor.json预留唯一HTTP后继，避免同一快照并发恢复/继续。保留此占用，即使后继中断也不自动删除/解锁；先定位对应后继并离线核查。此门禁不提供跨准备目录/独立新执行的全局去重，也不是平台幂等或共享账户硬预算；独立新执行代表另一次显式运行，不能当恢复旧任务使用。

输出：evidence.json、execution.json以及原P4的inspection目录；HTTP任务回执/视频在该执行自己的目录，恢复时只复制目标回执。检查点用本目录临时文件原子替换，源准备/脚本/旧回执不改。父evidence/preparation身份必须匹配，哈希为本地一致性检查，不认证提供商。execution保存mode、源身份、media_origin、HTTP是否启用、本次POST尝试数、错误、检查状态和records_path；stopped/incomplete返回非零，默认prepared_offline与材料齐备assembled_requires_manual_inspection返回0。键盘中断尽力留证并做本地检查，强制杀进程不保证有最终记录；已有evidence可用6.13离线收集，不能重启POST循环。

执行结束或可捕获异常后调用原inspect_generated_video，不在执行器内重写拼接/费用。最终账目只取execution.records_path（正常为inspection/records/block.json）；inspection/preflight_records、父/子执行都是同一历史的快照，不能累计。资格/匿名导出/评分仍分别走6.14/6.15独立重检，人工检查保持空，comparison仍not_checked/ineligible，不批准正式纳入。GET恢复仅补收已有任务，费用可能未知且不受本地新提交额度硬限制；真实声音/台词/人物/质量必须另行人工验收。

### 6.18 Actor self-review protocol

`review_and_revise`, `get_review_prompt_hashes`, `pipeline.run_condition` and `pipeline.run_experiment` accept optional `review_protocol="global_v1"`. The explicit `"actor_self_review_v1"` value requires generated mode and uses the existing planner, patch validator, compiler and budgeted clients. Historical records without this field retain global critique/revise/verify semantics; the original paid PR #48 results are not retagged. See [method and offline evidence](ACTOR_REVIEW_METHOD.md).

Baseline keeps the common initial plan. Both reviewed conditions independently call `actor_critique` once per scene character with full initial context, its character binding and `own_dialogue` (shot ID, zero-based line index, text). Generic and emotion-oriented actors differ only in criteria. Reports add `actor_id`; each standard issue adds nonempty, distinct `line_indices`, restricted to that actor's original lines. The second actor sees no earlier report. Empty first/silent actor feedback does not skip the second actor. Both empty skip rewriting.

Save raw responses as ordered `actor_reports=[{actor_id,response},...]`; combined IDs are `actor-<position>:<local_id>`, with `actor_id`, `source_issue_id` and `line_indices` retained. One `actor_revise` receives both reports plus all combined issues grouped by shot. It returns exactly `{patch,feedback_disposition}`. The disposition contains disjoint, complete `addressed_issue_ids`, `unaddressed_issue_ids` and `unaddressed_reasons` keyed exactly by unaddressed ID. The existing one-edit-per-shot atomic dialogue-only patch applies. Preserve line count, speaker order/assignment; only addressed issues' referenced lines may change, and every addressed issue must actually change its actor's referenced line. No silent dropping of opinions or fabricated actor approval is allowed.

With `configs/agent_pilot_models.json`, `RoleRoutedClient` routes actor feedback to DeepSeek review and unified writing to Gemini planning, with the same controls/shared budget and no retries. At most two actor calls plus one writer per reviewed condition: three planning plus six review-branch requests in a full block. No new model verification call is added. Result fields include exact `writer_response`, `feedback_disposition`, `verification=null`, `verification_kind="programmatic_only"`, `actor_endorsement="not_requested"` and `actor_feedback_status=no_issues|writer_addressed|has_unaddressed` for valid results. Failed/incomplete responses remain preserved and rejected for preparation.

Unaddressed opinions with reasons do not alone block request preparation or separately authorized video execution. They remain visible in saved reviews/run summaries; the video is pending listening/viewing acceptance. Addressed is a writer declaration, not objective semantic fulfillment. Structural checks cannot prove that a changed line respects the actor's intent or that an unaddressed reason is sound. No scores or final actor sign-off are generated.

Protocol and exact actor prompt hashes enter cache/source identity. Source loading revalidates reports, ownership, disposition, patch/final-plan consistency and run summary; request compilation and qualification reuse this loader. Comparison records must use one consistent protocol. New software replay remains synthetic/mock; no paid API or new video generation occurred in the offline implementation increment. A subsequent separately authorized [actual actor pilot](pilots/anna-elsa-actor.md) records real outputs, unchanged/reuse behavior and a retained actor disagreement; human quality acceptance remains pending. Original global-review paid records and media remain byte-identical.

### 6.19 Actor confirmation of omitted feedback

Explicit `review_protocol="actor_self_review_v2"` adds one bounded `actor_confirm` request per actor whose original issues remain unaddressed by the writer. Both conditions use the same confirmation prompt, review role, 2048 output-token limit and existing shared budget. No omitted issues means no confirmation call; both original actor reports are still collected. With the two-character contract, each reviewed condition uses at most five calls and the block at most thirteen. There is no extra writer loop, retry, model switch or new paid authorization.

Each request carries the full original and candidate plans, its bound actor, that actor's original raw report, its omitted issues and exact writer reasons, own original/revised indexed lines and both plan hashes. It contains no other actor's report or confirmation. The response is exactly `{schema_version,scene_id,mode,actor_id,initial_plan_sha256,candidate_plan_sha256,decisions}`; each decision is `{issue_id,decision,reason}`, with `decision=accept_omission|maintain_objection` and a nonempty explanation. IDs must cover exactly that actor's omitted opinions once. Wrong owner, scene, mode, hashes, duplicates, extra fields or missing decisions fail closed. Responses are preserved as `actor_confirmations=[{actor_id,response},...]`.

An omission is released only after explicit consent from its corresponding actor. Accepted omissions remain unaddressed in `feedback_disposition`; acceptance is not a claim that the issue was fixed. `actor_confirmation_status=not_needed|pending|accepted|disputed|failed` records the separate gate. `actor_endorsement=not_requested` and `verification_kind=programmatic_only` still mean no full-script actor sign-off or independent semantic verification. The targeted actor confirmation is separately recorded, not substituted into the old `verification` field.

A valid objection produces `review_failed` with `actor_confirmation_status=disputed`, retains `writer_candidate_plan` and every report/reason/response, and restores the original as the non-final `plan`. It does not become an API/format error. Both affected actors are heard once when their responses are valid; invalid/failed calls stop immediately. No disputed/missing/invalid/failed confirmation may prepare video requests. Human resolution or a later independently authorized run is outside this bounded increment.

The existing cache/source identity includes v2 and all four actor prompt hashes; v1 retains its original three exact prompt identities and behavior. Source loading rechecks raw decisions, actor ownership, issue coverage, actual candidate/patch consistency, summary status, stage sequence and routed models. Request preparation and qualification reuse that loader. The comparison checker also requires one consistent protocol and valid v2 confirmation summaries for omissions. Scoring and denominators are unchanged. Structural checks cannot guarantee sound model reasoning, and writer-declared addressed issues are not separately actor-verified by this feature.

Offline acceptance replays the historical Elsa opinion/writer reason as development inputs with explicit software decisions. Objection blocks preparation; software consent permits only `prepared_offline`. No paid API or new video was called. Historical results remain unchanged, and [team viewing links](pilots/anna-elsa-videos.md) identify the uploaded original global/v1 media rather than v2 results.

### 6.20 Bounded actor negotiation

Explicit `review_protocol="actor_self_review_v3"` adds the same bounded second revision to both reviewed conditions; global/v1 and strict v2 retain their identities and behavior. See [method, plan and evidence](ACTOR_REVIEW_METHOD.md). No CLI, client, execution framework, score or default protocol changes. Use the existing `run_experiment(..., output_mode="generated", review_protocol="actor_self_review_v3")` API and source preparation/execution interfaces.

Two original actor reports precede the first `actor_revise`. Its `{patch,feedback_disposition}` shape and dialogue-only/ownership constraints are unchanged. Confirm each affected actor's omitted issues once using `actor_confirm`; v3 decisions are `accept_candidate|maintain_objection`. A maintained objection requires exactly one further `actor_revise`, using `review_actor_negotiate.txt` and the full `previous_round` plus `required_objection_ids`. The second writer response additionally contains `objection_responses`, keyed exactly by those IDs with nonempty responses. It must attempt/address every prior objection, actually modify a referenced own-actor line relative to the previous candidate and retain all earlier addressed IDs. Its patch applies to the original plan and all initial feedback remains covered. These are structural attempt checks, not semantic verification.

The second `actor_confirm` targets the union of previously disputed IDs and final omitted IDs, grouped by actor. Previously disputed issues are confirmed even if the writer now declares them addressed. Payloads preserve own original report, previous own decisions, full original/candidate plans and hashes, current writer omission reasons or objection responses, and indexed own dialogue; they exclude other actors' reports/replies. Exact response ownership/hash/coverage rules from 6.19 still apply, using the v3 acceptance literal. Accepted omission stays unaddressed; final maintained objection stays disputed even when writer-declared addressed.

`negotiation_rounds` is an ordered array of at most two objects, each containing exactly `writer_response,patch,feedback_disposition,writer_candidate_plan,plan,status,actor_feedback_status,actor_confirmations,actor_confirmation_status,confirmation_issue_ids,disputed_issue_ids`. Top-level fields mirror the final round. Zero issues implies zero rounds and no invented candidate or confirmations. `negotiation_round_count` is 0–2; `negotiation_status` is `no_issues|complete|disputed|failed`. One-round disputes cannot prepare. After the second valid round, remaining objections yield an applied/unchanged draft with `actor_confirmation_status=disputed`, `negotiation_status=disputed` and exact disputed IDs; preparation is allowed pending human inspection. Full-script actor endorsement and independent verification remain absent.

The source loader validates every round against the original reports/plan, required second-round changes, exact actor decisions, top-level/run summaries, prompt identities, stage order and routed models. Calls are two `actor_critique`, followed by one or two groups of `actor_revise` and zero to two `actor_confirm`. Per-branch maximum is eight, full-block maximum nineteen including three shared planning calls. Both conditions share all controls and existing budget reservations; no paid authorization is implied.

Hard errors still stop: missing/invalid response, illegal patch, wrong actor/hash/issue coverage, missing second attempt, API failure, unknown cost or budget failure. No retry/third round/manual fallback occurs. Raw attempted rounds/candidates remain available, while the root plan restores the original and status becomes `review_failed`. Existing accounting keeps all failures and unknown costs. Comparison checks accept a consistent v3 protocol and valid completed/disputed summaries; actual qualification/export still recheck full saved sources and media through 6.14/6.15. Disagreement is not silently excluded or scored as failure/success; formal inclusion remains separately unapproved.

### 6.21 V3 writer output keyed by shot

New v3 execution uses `writer_output_contract="dialogue_by_shot_v1"` in reviews, all condition rows and block metadata. Both writer rounds return `{dialogue_by_shot,feedback_disposition}`; the second also returns `objection_responses`. `dialogue_by_shot` maps each affected existing shot ID to exactly one complete final ordered dialogue array. Prompt `revision_slots` groups all original issue IDs and original lines once per affected shot. No model-supplied `patch`, `edits`, issue-level alternative arrays or extra fields are accepted. Empty maps/omitted unchanged shots remain subject to all disposition and second-attempt requirements.

The existing reviewer derives a standard patch in original shot order: at most one edit per map key, first original issue ID for that shot as association, model-selected full dialogue copied verbatim. This does not merge conflicting edits, select actor wording, imply the association issue is addressed, or repair an earlier failed model output. Existing atomic patch/actor ownership/dialogue-only and complete feedback checks remain authoritative. The strict JSON client rejects repeated keys before conversion; unknown or feedback-free shot IDs, malformed arrays/speakers/counts, false addressed claims and illegal fields stop without retry.

`writer_response` remains the exact raw per-shot envelope; `patch` is the separately derived internal object. Saved-review validation recomputes it on every round and checks actual candidate/final identity. Block/rows/reviews must agree on the writer contract; pure comparison rejects mixed contracts even when every record says actor-v3. New revision prompt files/hashes distinguish the new interface and enter existing cache/source identity. No client, score, trial condition, actor confirmation policy, nineteen-call limit or cost authorization changes.

Absent writer-contract metadata in historical v3 means `issue_patch_v1`; its original revision prompt files/hashes and strict patch validation remain available for read-only source compatibility. New execution always selects `dialogue_by_shot_v1`, with no automatic legacy-output fallback. The original failed v3 paid response, its rejection and all original result bytes remain unchanged; it is not converted into a successful run. See [the separate offline correction record](pilots/anna-elsa-v3-shot-contract.md).
