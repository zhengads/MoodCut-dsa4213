# MoodCut 第一版模块契约

本文件定义模块间的公共接口。P1 将契约、夹具与骨架作为第一条 PR 合入仓库，其他模块按此开发。Python 3.11；包路径 `src/moodcut/`；统一使用 JSON 可序列化 dict。

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
def validate_plan(scene: dict, plan: dict, manifest: dict) -> list[str]: ...

# importer.py — P2；只读本地上游文件，无网络
def import_synopsis(path: str) -> dict: ... # {story: str, character_names: list[str]}

# planner.py — P2
def make_plan(scene: dict, manifest: dict, client: LLMClient) -> dict: ...

# reviewer.py — P3，mode 必须显式给出
def review_and_revise(scene: dict, initial_plan: dict, manifest: dict,
                      client: LLMClient, *, mode: str) -> dict: ... # ReviewResult

# patches.py — P3；纯函数，不调用模型、不改输入对象
def apply_patch(scene: dict, plan: dict, manifest: dict,
                report: dict, patch: dict) -> dict: ... # {plan,status,errors}

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
                  project_root: str, font_path: str) -> dict: ... # RunRecord
```

上述 `...` 是 Python 接口声明，不是完成实现。所有函数的具体行为由本文件与任务卡定义。P1 的 FakeClient 使用预置响应队列，record 每次 stage 和上限；队列耗尽、网络企图或非法响应应报错。

make_plan 依次使用 director、scene、shot 三个 planning stage，再转换为 ShotPlan；所有条件共用缓存初稿。不允许 review 模块反过来改变 scene。

review_and_revise 两种 mode 都按 critique → revise → verify 执行，最多各一次。critique 得到 report；revise 得到 patch；apply_patch 结构通过才运行 verify。无意见可不发 revise/verify。模型返回 JSON 不合法或 API 失败不自动重试；保留错误。实际用量与提前退出分别报告，不声称实际费用完全相同。

### OpenRouterClient 与调用账目

`OpenRouterClient(LLMClient)` 已实现；`OpenRouterClient.from_env(config_path, *, allow_paid=False, max_cost_usd=None)` 读取公开模型配置和进程环境中的 OPENROUTER_API_KEY。config_path 默认 configs/model.json；模型 ID 和每百万 token 单价必须显式填写。max_cost_usd 必须为正；只有 allow_paid=True 才能发送请求。构造和 check-client 均不联网，缺省不允许付费。

complete_json 返回原有模型 JSON dict，不包裹 usage，保持 MC-02/MC-03 调用兼容。输出不是对象、JSON 非法/重复键/非有限数、内容被拒绝或截断、接口/超时错误均抛 OpenRouterError；预算不足或既往扣费未知抛 BudgetError。错误不自动重试，不带 key、提示词或原始响应正文。

每次实际 HTTP 尝试在 client.calls 增加独立记录：stage、model_id、response_model、generation_id、max_output_tokens、estimated_input_tokens、reserved_cost_usd、input_tokens、output_tokens、estimated_cost_usd、provider_cost_usd、status、http_status、elapsed_s，以及失败时的 error。status 为 success/invalid_response/request_failed，只表示客户端请求及 JSON 解析，不是最终运行或研究评分。提供商 token/cost 即使模型内容解析失败仍保留；未知字段记 null。零调用的本地拒绝不增加 HTTP 尝试记录。

estimated_cost_usd 基于返回的实际 token 计数和配置单价；provider_cost_usd 使用 usage.cost。两者独立，不能相互冒充。cost 未知则 spent_usd=None，该实例停止继续请求；需从平台核对未知扣费，再规划剩余额度，不直接新建客户端忽略它。spent_usd 已知时对所有尝试的实际 cost 求和，包括失败。调用者负责将记录保存到本次 runs 输出并映射到 RunRecord。

本地预算使用输入 UTF-8 字节数加 64 作为 token 估计，并按 max_output_tokens 预留输出费用。它是单实例估算检查，不是精确 tokenizer 上界、跨进程账本或平台硬额度；不同实例不共享余额。提供商请求限制 token 单价和零按次附加费，仍须使用 OpenRouter 端共享 key/团队额度控制真实总支出。未知价格拒绝发送。

## 3. CLI 目标

以下 plan/review/render/smoke/evaluate 仍是 P1 待集成的命令。帮助、版本及不联网的 `python -m moodcut check-client --config configs/model.json --max-cost-usd 0.05` 已实现；check-client 只做本地配置检查，不验证远端凭据。

```bash
python -m moodcut plan --scene tests/fixtures/scene.json --assets tests/fixtures/assets.json --mock --output runs/dev/initial.json
python -m moodcut review --scene tests/fixtures/scene.json --plan tests/fixtures/plan.json --assets tests/fixtures/assets.json --mode moodcut --mock --output runs/dev/review.json
python -m moodcut render --plan tests/fixtures/plan.json --assets tests/fixtures/assets.json --font assets/raw/font.ttf --output runs/dev/render
python -m moodcut smoke --mock --output runs/dev/smoke
python -m moodcut evaluate --config configs/pilot.json --dry-run
```

smoke mock 模式不联网、不需要 key、不渲染视频，检查 baseline/generic_review/moodcut 三条 JSON 链路与记录；render 独立需要 FFmpeg 和显式字体。真实调用必须同时有授权、`--allow-paid`、`--max-cost-usd`、明确模型及价格配置。paid 不能作为任何命令默认行为。

## 4. 固定存储与结构检查

共享夹具由 P1 写在 `tests/fixtures/`，不用被现有 `.gitignore` 整体忽略的 `data/`。P2 维护 `assets/manifest.json`，原始第三方图片在忽略目录 `assets/raw/`。运行结果在忽略目录 `runs/`。P1 修改 .gitignore；各模块不各自修改根配置。

必检：版本、scene/tone 对齐、唯一 shot_id、有效 beat/character/asset 引用、所有必需 beats 被覆盖、duration>0 且合计60–90、镜头数1–6、visuals每镜头1–2项且crop受允许；dialogue speaker 必须在 scene.characters 中。素材不存在、hash不符、非图片或越界路径均报错。

结构验证不判断角色是否真的完成了叙述事件，也不判断台词是否自然、情绪是否正确。这些通过独立标注检查。
