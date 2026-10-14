# MoodCut Implementation Plan

> Implement the assigned task according to AGENTS.md, the shared moodcut-team workflow and its module task card. Respect the task's file ownership, acceptance criteria and execution budget.

**Goal:** Build a MovieAgent-inspired text planning pipeline with generic and emotion-specific review, fixed-asset animatic rendering, and auditable paired evaluation.

**Architecture:** P1 owns shared contracts and a single client/pipeline. P2–P5 independently implement planning, review, rendering, and evaluation against shared offline fixtures. The same initial plan, assets, rendering settings, and bounded review opportunities support the three experimental conditions.

**Tech Stack:** Python 3.11, pytest, Pillow, FFmpeg/ffprobe, one explicitly configured OpenRouter model through the common client. No GPU dependency in the MVP.

**Spec:** Repository-root `TEAM_HANDOFF.md` and `docs/CONTRACTS.md`. Follow `.agents/skills/moodcut-team/SKILL.md` for team execution. All implementation paths below are relative to the MoodCut repository root.

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
  cli.py
  core/client.py
  core/validation.py
  core/pipeline.py
  planning/importer.py
  planning/planner.py
  planning/normalizer.py
  review/service.py
  review/patches.py
  rendering/renderer.py
  rendering/frames.py
  rendering/subtitles.py
  evaluation/design.py
  evaluation/blinding.py
  evaluation/metrics.py
prompts/planning/
prompts/review/
assets/manifest.json
fixtures/
scripts/prepare_assets.py
tests/core/
tests/planning/
tests/review/
tests/rendering/
tests/evaluation/
tests/test_smoke.py
```

## Task 1 — Shared contracts and foundation

Owner P1. Full work item: `issues/MC-01-foundation.md`. Files and output interfaces are specified there and in CONTRACTS.md. Produces LLMClient/FakeClient, validate_plan, fixtures, CLI and run_condition. Consumes other modules only in the second PR.

- [ ] Add fixtures exactly matching CONTRACTS and register the Python package.
- [ ] Add the validation regression test below; run it and confirm it fails before implementation.
- [ ] Implement schema/reference checks as enumerated in CONTRACTS; return all detected structural errors as strings.
- [ ] Run `python -m pytest tests/core -q`; confirm the valid fixture passes and the mutant fails.
- [ ] Commit contract, fixtures and core tests; open the first PR for P2 to review before dependent work branches.
- [ ] Implement budgeted client and then integration as the second PR, using the MC-01 acceptance criteria.

```python
# tests/core/test_contract.py
import copy
import json
from pathlib import Path
from moodcut.core.validation import validate_plan

def read_fixture(name):
    return json.loads((Path('fixtures') / name).read_text(encoding='utf-8'))

def test_unknown_character_is_rejected():
    scene, plan, assets = (read_fixture(n) for n in ('scene.json','plan.json','assets.json'))
    assert validate_plan(scene, plan, assets) == []
    bad = copy.deepcopy(plan)
    bad['shots'][0]['dialogue'][0]['character_id'] = 'outsider'
    assert validate_plan(scene, bad, assets)
```

Client implementation must refuse unknown prices in budget-enforced paid mode, charge actual reported tokens where available, and retain unknown supplier cost as null. FakeClient has a finite queue; exhausted fixtures fail rather than falling through to network.

## Task 2 — MovieAgent input and planning adapter

Owner P2. Full work item: `issues/MC-02-planning.md`. Produces import_synopsis and make_plan; consumes scene/manifest and LLMClient. Exact files are listed in task card.

- [ ] Write importer tests using temporary team-authored JSON, not downloading upstream during tests.
- [ ] Run `python -m pytest tests/planning -q`; observe importer missing before implementation.
- [ ] Implement MovieScript/Character type checks and return the normalized dict; implement selected local asset preparation and provenance.
- [ ] Implement director→scene→shot prompts through injected LLMClient, store raw responses, normalize and validate without silently dropping unknown references.
- [ ] Verify stage order using FakeClient and verify the output against public validator.
- [ ] Commit importer/material preparation first; submit planner in a separate PR. Ask P1 for review.

```python
# tests/planning/test_importer.py
import json
import pytest
from moodcut.planning.importer import import_synopsis

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

Owner P3. Full work item: `issues/MC-03-review.md`. Produces apply_patch and review_and_revise, consumes client, validator, immutable scene/plan/manifest.

- [ ] Write the input-preservation and forbidden-change test below; confirm failure before implementing.
- [ ] Implement whitelist patching: validate all IDs and fields; copy original; apply all edits; validate; reject all on any error.
- [ ] Implement two critique prompts and common revise/verify prompts. Generic gets the same target tone and resources.
- [ ] Bound each review stage to one call, record errors, return the original plan on API/parse failure; unresolved verification is logged and never triggers another loop.
- [ ] Run `python -m pytest tests/review -q`; add a fake-client assertion for maximum three review calls and condition context isolation.
- [ ] Commit pure patch engine before LLM service; submit two PRs, request P1 and P5 review.

```python
# tests/review/test_patches.py
import copy
import json
from pathlib import Path
from moodcut.review.patches import apply_patch

def test_cannot_change_beat_ids_and_input_is_immutable():
    def load(name):
        return json.loads((Path('fixtures')/name).read_text(encoding='utf-8'))
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

Owner P4. Full work item: `issues/MC-04-rendering.md`. Produces render_plan, RenderResult, contact sheet and timeline; consumes plan, manifest, project_root, explicit font and output directory.

- [ ] Create frame-level tests using P1's two labeled placeholder images. Verify selected asset IDs determine corresponding visible cards and long captions trigger wrapping/error handling.
- [ ] Implement full versus center60% crop, one/two card layout, dialogue and separately labeled narration; produce per-shot PNG and timeline.
- [ ] Implement FFmpeg subprocess using argv lists, fixed1280×720/24fps/yuv420p, refuse nonempty output directory.
- [ ] Add the integration test below; on an environment with FFmpeg and explicit font run it, inspect contact sheet and video. Font and video test dependencies are declared, not auto-downloaded.
- [ ] Verify one changed crop/dialogue visibly changes its rendered PNG while the same unedited plan renders identically under the same environment.
- [ ] Commit frame rendering then MP4 integration; request P2 review, report actual ffprobe output.

```python
# tests/rendering/test_video.py
import json
import os
from pathlib import Path
from moodcut.rendering.renderer import render_plan

def test_fixture_video_duration(tmp_path):
    root = Path.cwd()
    def load(name):
        return json.loads((root/'fixtures'/name).read_text(encoding='utf-8'))
    result = render_plan(load('plan.json'), load('assets.json'),
        project_root=str(root), out_dir=str(tmp_path/'clip'),
        font_path=os.environ['MOODCUT_TEST_FONT'])
    assert result['status'] == 'rendered'
    assert Path(result['video_path']).is_file()
    assert abs(result['duration_s'] - 60.0) <= (1/24 + 0.1)
```

This integration test requires MOODCUT_TEST_FONT and FFmpeg; put it in the designated render integration job. Unit-only success does not certify MP4 rendering. Renderer should populate duration_s using ffprobe, not simply copying requested duration.

## Task 5 — Paired allocation and independent evaluation

Owner P5. Full work item: `issues/MC-05-evaluation.md`. Produces build_assignments, export_blind_items, summarize; consumes run records and ratings. No direct LLM client calls in evaluation analysis.

- [ ] Write the allocation test below; then implement stable block/run IDs and cartesian allocation.
- [ ] Create synthetic records covering success, failure, missing ratings and mismatched initial hash; keep them clearly separate from real study files.
- [ ] Implement anonymous export and private mapping, seeded ordering, duplicate-rater/item rejection and output field validation.
- [ ] Implement metric calculations exactly as MC-05 specifies, including equal clip weighting, null denominators and all-run coverage/cost tables.
- [ ] Run `python -m pytest tests/evaluation -q`; hand-check expected counts from synthetic records, verify no condition/tone leakage in viewer export.
- [ ] Submit allocation/CSV tooling first, metrics second; P3 reviews fairness and P1 confirms experiment protocol before any formal runs.

```python
# tests/evaluation/test_design.py
from moodcut.evaluation.design import build_assignments

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

Use the five task cards as GitHub Issues, confirm the two unknown accounts, and merge the P1 contract PR before parallel implementations. This handoff assigns human work; no automated implementation, invitations, or remote publication has occurred.
