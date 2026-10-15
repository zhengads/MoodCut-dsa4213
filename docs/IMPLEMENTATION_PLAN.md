# MoodCut Implementation Plan

> Implement the assigned task according to AGENTS.md, the shared moodcut-team workflow and its module task card. Respect the task's file ownership, acceptance criteria and execution budget.

**Goal:** Build a MovieAgent-inspired text planning pipeline with generic and emotion-specific review, fixed-asset animatic rendering, and auditable paired evaluation.

**Architecture:** P1 owns shared contracts and a single client/pipeline. P2–P5 independently implement planning, review, rendering, and evaluation against shared offline fixtures. The same initial plan, assets, rendering settings, and bounded review opportunities support the three experimental conditions.

**Tech Stack:** Python 3.11, pytest, Pillow, FFmpeg/ffprobe, one explicitly configured OpenRouter model through the common client. No GPU dependency in the MVP.

**Spec:** `docs/TEAM.md` and `docs/CONTRACTS.md`. Follow `.agents/skills/moodcut-team/SKILL.md` for team execution. All implementation paths below are relative to the MoodCut repository root.

## Global Constraints

- Target repository: https://github.com/zhengads/MoodCut-dsa4213 .
- Upstream reference: showlab/MovieAgent at d84041bed8bc8be460664528d9e9924cdde384ba.
- Tone enum affectionate/suspicious/hostile; two characters; 1–6 shots; total60–90seconds; schema1.0.
- Mock and CI do not access paid APIs. A live pilot needs separate authorization of scale/model/cost.
- Review has at most one critique/revise/verify cycle, and patches obey the whitelist in CONTRACTS.md.
- No video generation, new action synthesis, speech cloning, or original-model training in MVP.
- Shared files are owned by P1; no changes to teammate modules without an agreed interface PR.
- Tests below describe planned verification, not results already obtained.

## File structure

```text
src/moodcut/
  __init__.py
  __main__.py
  client.py
  validation.py
  pipeline.py
  importer.py
  planner.py
  reviewer.py
  patches.py
  renderer.py
  evaluation.py
  prompts/
configs/
tests/
  test_prepare_references.py
  fixtures/
assets/
scripts/prepare_references.py
pyproject.toml
```

All listed paths exist. Business modules currently contain responsibility docstrings; the command entry point exits explicitly as unimplemented. Minimal packaging exists. Prompt/configuration contents, shared fixtures and the acceptance-test files shown below remain task deliverables. Tests are flat files; task cards own specific code, prompt and configuration files. Normalization belongs in planner.py, frame/subtitle helpers in renderer.py, and design/blinding/metrics in evaluation.py.

## Task 1 — Shared contracts and foundation

Owner P1. Full work item: `docs/tasks/MC-01-foundation.md`. Files and output interfaces are specified there and in CONTRACTS.md. Produces LLMClient/FakeClient, validate_plan, fixtures, CLI and run_condition. Consumes other modules only in the second PR.

- [ ] Add fixtures exactly matching CONTRACTS and verify the existing minimal package configuration.
- [ ] Add the validation regression test below; run it and confirm it fails before implementation.
- [ ] Implement schema/reference checks as enumerated in CONTRACTS; return all detected structural errors as strings.
- [ ] Run `python -m pytest tests/test_client.py tests/test_validation.py tests/test_cli.py -q`; confirm the valid fixture passes and the mutant fails.
- [ ] Commit contract, fixtures and core tests; self-review the first PR and record validation before dependent work branches.
- [ ] Implement budgeted client and then integration as the second PR, using the MC-01 acceptance criteria.

```python
# tests/test_validation.py
import copy
import json
from pathlib import Path
from moodcut.validation import validate_plan

def read_fixture(name):
    return json.loads((Path('tests/fixtures') / name).read_text(encoding='utf-8'))

def test_unknown_character_is_rejected():
    scene, plan, assets = (read_fixture(n) for n in ('scene.json','plan.json','assets.json'))
    assert validate_plan(scene, plan, assets) == []
    bad = copy.deepcopy(plan)
    bad['shots'][0]['dialogue'][0]['character_id'] = 'outsider'
    assert validate_plan(scene, bad, assets)
```

Client implementation must refuse unknown prices in budget-enforced paid mode, charge actual reported tokens where available, and retain unknown supplier cost as null. FakeClient has a finite queue; exhausted fixtures fail rather than falling through to network.

## Task 2 — MovieAgent input and planning adapter

Owner P2. Full work item: `docs/tasks/MC-02-planning.md`. Produces import_synopsis and make_plan; consumes scene/manifest and LLMClient. Exact files are listed in task card.

- [ ] Write importer tests using temporary team-authored JSON, not downloading upstream during tests.
- [ ] Run `python -m pytest tests/test_importer.py tests/test_planner.py tests/test_prepare_assets.py -q`; observe importer missing before implementation.
- [ ] Implement MovieScript/Character type checks and return the normalized dict; implement selected local asset preparation and provenance.
- [ ] Implement director→scene→shot prompts through injected LLMClient, store raw responses, normalize and validate without silently dropping unknown references.
- [ ] Verify stage order using FakeClient and verify the output against public validator.
- [ ] Commit importer/material preparation first; submit planner in a separate PR. Record a self-review of the current diff and test results.

```python
# tests/test_importer.py
import json
import pytest
from moodcut.importer import import_synopsis

def test_synopsis_import_and_missing_characters(tmp_path):
    path = tmp_path / 'script.json'
    path.write_text(json.dumps({'MovieScript':'A gives B a letter.','Character':['A','B']}), encoding='utf-8')
    assert import_synopsis(str(path)) == {'story':'A gives B a letter.','character_names':['A','B']}
    path.write_text(json.dumps({'MovieScript':'A gives B a letter.'}), encoding='utf-8')
    with pytest.raises(ValueError):
        import_synopsis(str(path))
```

The real asset import and adaptation may use a chosen small upstream subset. Do not launch run.sh or import ScriptBreakAgent: MovieAgent initializes generation models in that path. Unconfirmed licensing prevents representing copied prompts/media as team-owned public artifacts; provenance is mandatory.

## Task 3 — Emotion feedback and atomic revision

Owner P3. Full work item: `docs/tasks/MC-03-review.md`. Produces apply_patch and review_and_revise, consumes client, validator, immutable scene/plan/manifest.

- [ ] Write the input-preservation and forbidden-change test below; confirm failure before implementing.
- [ ] Implement whitelist patching: validate all IDs and fields; copy original; apply all edits; validate; reject all on any error.
- [ ] Implement two critique prompts and common revise/verify prompts. Generic gets the same target tone and resources.
- [ ] Bound each review stage to one call, record errors, return the original plan on API/parse failure; unresolved verification is logged and never triggers another loop.
- [ ] Run `python -m pytest tests/test_patches.py tests/test_reviewer.py -q`; add a fake-client assertion for maximum three review calls and condition context isolation.
- [ ] Commit pure patch engine before LLM service; submit two PRs, checking contract compliance and comparison fairness in each self-review.

```python
# tests/test_patches.py
import copy
import json
from pathlib import Path
from moodcut.patches import apply_patch

def test_cannot_change_beat_ids_and_input_is_immutable():
    def load(name):
        return json.loads((Path('tests/fixtures')/name).read_text(encoding='utf-8'))
    scene, plan, assets = (load(n) for n in ('scene.json','plan.json','assets.json'))
    original = copy.deepcopy(plan)
    report = {'schema_version':'1.0','scene_id':scene['scene_id'],'mode':'moodcut',
              'issues':[{'issue_id':'r1','shot_id':'s1','dimension':'tone','evidence':'fixture','suggestion':'fixture','severity':'minor'}]}
    patch = {'schema_version':'1.0','scene_id':scene['scene_id'],
             'edits':[{'issue_id':'r1','shot_id':'s1','set':{'beat_ids':[]}}]}
    result = apply_patch(scene, plan, assets, report, patch)
    assert result['status'] == 'rejected'
    assert result['plan'] == original
    assert plan == original
```

## Task 4 — Render realizable animatics

Owner P4. Full work item: `docs/tasks/MC-04-rendering.md`. Produces render_plan, RenderResult, contact sheet and timeline; consumes plan, manifest, project_root, explicit font and output directory.

- [ ] Create frame-level tests using P1's two labeled placeholder images. Verify selected asset IDs determine corresponding visible cards and long captions trigger wrapping/error handling.
- [ ] Implement full versus center60% crop, one/two card layout, dialogue and separately labeled narration; produce per-shot PNG and timeline.
- [ ] Implement FFmpeg subprocess using argv lists, fixed1280×720/24fps/yuv420p, refuse nonempty output directory.
- [ ] Add the integration test below; on an environment with FFmpeg and explicit font run it, inspect contact sheet and video. Font and video test dependencies are declared, not auto-downloaded.
- [ ] Verify one changed crop/dialogue visibly changes its rendered PNG while the same unedited plan renders identically under the same environment.
- [ ] Commit frame rendering then MP4 integration; self-review the asset/rendering contract and report actual ffprobe output.

```python
# tests/test_video.py
import json
import os
from pathlib import Path
from moodcut.renderer import render_plan

def test_fixture_video_duration(tmp_path):
    root = Path.cwd()
    def load(name):
        return json.loads((root/'tests'/'fixtures'/name).read_text(encoding='utf-8'))
    result = render_plan(load('plan.json'), load('assets.json'),
        project_root=str(root), out_dir=str(tmp_path/'clip'),
        font_path=os.environ['MOODCUT_TEST_FONT'])
    assert result['status'] == 'rendered'
    assert Path(result['video_path']).is_file()
    assert abs(result['duration_s'] - 60.0) <= (1/24 + 0.1)
```

This integration test requires MOODCUT_TEST_FONT and FFmpeg; put it in the designated render integration job. Unit-only success does not certify MP4 rendering. Renderer should populate duration_s using ffprobe, not simply copying requested duration.

## Task 5 — Paired allocation and independent evaluation

Owner P5. Full work item: `docs/tasks/MC-05-evaluation.md`. Produces build_assignments, export_blind_items, summarize; consumes run records and ratings. No direct LLM client calls in evaluation analysis.

- [ ] Write the allocation test below; then implement stable block/run IDs and cartesian allocation.
- [ ] Create synthetic records covering success, failure, missing ratings and mismatched initial hash; keep them clearly separate from real study files.
- [ ] Implement anonymous export and private mapping, seeded ordering, duplicate-rater/item rejection and output field validation.
- [ ] Implement metric calculations exactly as MC-05 specifies, including equal clip weighting, null denominators and all-run coverage/cost tables.
- [ ] Run `python -m pytest tests/test_evaluation.py -q`; hand-check expected counts from synthetic records, verify no condition/tone leakage in viewer export.
- [ ] Submit allocation/CSV tooling first, metrics second; self-review comparison fairness and confirm the shared experiment protocol before formal runs.

```python
# tests/test_evaluation.py
from moodcut.evaluation import build_assignments

def test_three_conditions_share_one_block():
    rows = build_assignments([{'scene_id':'dev_a'}], replicates=1,
        tones=['suspicious'], conditions=['baseline','generic_review','moodcut'])
    assert len(rows) == 3
    assert len({r['block_id'] for r in rows}) == 1
    assert len({r['run_id'] for r in rows}) == 3
    assert {r['condition'] for r in rows} == {'baseline','generic_review','moodcut'}
```

## Integration acceptance

- [ ] On a clean checkout, install the agreed package and lightweight dependencies; run offline tests with no API key.
- [ ] `python -m moodcut smoke --mock --output runs/final-smoke` produces three condition records with one initial hash, separate review state, and labeled synthetic provenance.
- [ ] Explicit rendering command with local font yields baseline and moodcut animatics from the same assets; inspect subtitles/crops/timing and save ffprobe evidence.
- [ ] MC-05 exports viewer materials with hidden method/target and preserves failures in coverage records.
- [ ] Verify planned versus actual fees after an authorized pilot; only then determine formal evaluation allocation.
- [ ] Update README with actual verified commands, upstream reuse, known limitations and remaining work; no statement of better emotion performance before independent evidence.

## Execution handoff

Use the five task cards in docs/tasks as module Issues. Claim one task, complete and self-review each increment, and merge the foundational contract implementation before parallel integration.


## OpenRouter client increment (2026-10-15)

**Goal:** Add an OpenRouterClient implementing the existing complete_json interface; keep callers and FakeClient compatible. This increment belongs to MC-01 / Issue #8.

**Architecture:** Standard-library HTTPS POST to the fixed OpenRouter Chat Completions endpoint, with explicit model, JSON-object responses, one request per method call and no automatic retry. Each client stores separate call records and a local estimated-budget ledger; actual provider cost and unknown cost remain distinct.

**Files:** src/moodcut/client.py; tests/test_client.py; .env.example; configs/model.json; README.md; docs/CONTRACTS.md; this plan and docs/tasks/MC-01-foundation.md.

### Request and accounting contract

- Input remains complete_json(stage, system, user, max_output_tokens); output remains the model-produced dict.
- Configure model/pricing/timeout/temperature in configs/model.json and read OPENROUTER_API_KEY only from the process environment. Do not auto-load local secrets or make requests at import/construction.
- Require allow_paid=True and a positive max_cost_usd for a live call. Missing/invalid model, key or token prices fail before HTTP. No default paid model or hardcoded market price.
- Use model, system/user messages, max_tokens, stream=false, response_format=json_object and provider.require_parameters=true. Cap provider prompt/completion prices at configured USD-per-million rates and per-request surcharge at zero; disable provider fallbacks.
- Preflight uses UTF-8 content bytes plus a fixed framing allowance as an input-token estimate and reserves the maximum requested output cost. This is an estimate, not a tokenizer proof or account-wide hard limit. Document OpenRouter key limits for the shared account.
- Parse usage before content validation. Store stage, requested/returned model, generation ID, token counts, estimated cost, provider cost, status and elapsed time for every HTTP attempt, including malformed JSON and failures. Missing values stay null. An uncertain provider charge blocks later calls on the same client pending reconciliation.
- Reject non-object JSON, non-finite values, duplicate JSON keys, truncated/refused/tool-call/error responses and malformed envelopes. Raise a sanitized typed error with no key, prompt or raw response body in messages; retain known usage. Never silently retry a failed stage.

### Task 1: Client and offline transport coverage

- [x] Add tests in tests/test_client.py using mocked urllib transport: matching JSON return, request shape and auth, configured limits, timeout/no retry, HTTP/in-band errors, malformed/truncated JSON, missing cost, usage retention and next-call budget refusal.
- [x] Run the new tests and confirm the missing OpenRouterClient fails collection before implementation.
- [x] Implement OpenRouterClient plus configuration and typed errors in client.py; keep existing FakeClient behavior and signature.
- [x] Test actual reviewer integration with mocked HTTP returning the shared report/patch/verification fixtures; assert critique/revise/verify and independent contexts.
- [x] Run client/review/patch tests, then the local non-render offline suite. The Linux CI runs the full suite with FFmpeg; no API key or model inference in tests.

### Task 2: Configuration and handoff

- [x] Add configs/model.json with null model/prices and .env.example with an empty OPENROUTER_API_KEY. Add a runnable Python usage example and configuration validation instructions to README.
- [x] Document call-record fields, budget limitations and error behavior in CONTRACTS; mark only this client increment in MC-01, leaving pipeline/CLI integration open.
- [x] Verify credential files are ignored, JSON/Python/doc links parse, inspect current diff, and record self-review and exact validation in the PR.
Publication: create a scoped PR related to #8 with the name ZHENG MINGLIANG and date 2026-10-15. PR status and CI evidence are recorded on GitHub. Live calls require the separately confirmed model and run budget.
