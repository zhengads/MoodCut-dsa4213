# S02 / S03 evaluation handoff

Related to [Issue #9](https://github.com/zhengads/MoodCut-dsa4213/issues/9).
**Ready for teammate input review and offline preparation; waiting for v4 confirmation.**
No real calls or videos were produced for these two scenes. Publishing this package
does not authorize spending or approve a formal experiment.

## What is ready

| Scene | Tone | Characters | Existing input |
| --- | --- | --- | --- |
| S02: Stay with me | affectionate | Lucy / Gru | [scene](../../studies/six-story-clear-emotions-20261024/inputs/s02_stay_with_me/scene.json), [assets](../../studies/six-story-clear-emotions-20261024/inputs/s02_stay_with_me/assets.json) |
| S03: Footsteps outside | tense | Elsa / Mattias | [scene](../../studies/six-story-clear-emotions-20261024/inputs/s03_footsteps_outside/scene.json), [assets](../../studies/six-story-clear-emotions-20261024/inputs/s03_footsteps_outside/assets.json) |

These are selected existing inputs from the clear-emotions v2 study, not new
stories or the older S06 cleanup-assignment scenario. The scenes/assets are
referenced by exact repository paths and byte hashes in [handoff.json](handoff.json),
not rewritten or supplied with handwritten Agent dialogue.

Included candidate generation settings preserve the S06 preflight's five-second,
single-shot, native Mandarin, HeyGen 768p, 16:9, seed 4213 setup. Character/voice
bindings are adapted to each scene; S03 explicitly retains its shared footsteps
ambience. All settings must be common to the three conditions and confirmed for
the selected v4 runtime. Reference images stay in the ignored local cache, with
original source/rights metadata retained in the existing asset manifests.

## Reproduce the offline preparation

From this branch's repository root, install the normal project dependencies.
If the selected image files are missing, the existing optional reference command
can download and verify the pinned animation library (it also prepares the core
references; no model calls):

```text
python scripts/prepare_references.py --animation-assets
```

Then choose a new output directory:

```text
python docs/evaluation-handoffs/s02-s03-20261025/prepare.py --output runs/s02-s03-handoff-new
```

The helper verifies source hashes, reuses the existing scene/asset validator,
checks actual cached images, and copies scene/assets/settings into two local
folders. It has no client, network call, API key access or paid execution option.
It refuses an existing output folder. It preserves the price snapshot as a
snapshot, without claiming its observed prices are still current.

Optional checks using the existing P1 helper:

```text
python scripts/run_s06_real.py check --input runs/s02-s03-handoff-new/s02_stay_with_me
python scripts/run_s06_real.py check --input runs/s02-s03-handoff-new/s03_footsteps_outside
```

Use the normal PYTHONPATH=src setup for the existing runner. Its filename is
historical; these commands check the supplied scene. **Do not use its `text`
action for v4: the current main implementation selects v3 explicitly.** The old
local v3 paid caller is intentionally not part of this handoff.

## Teammate execution handoff

1. Confirm the exact runtime commit, protocol/writer contract and invocation from
   [v4 PR #66](https://github.com/zhengads/MoodCut-dsa4213/pull/66). At handoff it is
   Draft at `06e771f697a472c37e7edc525b5dbafc4ed8a52a`. The earlier S01 gallery is
   evidence of a separate snapshot, not permission to assume v4 is on main.
2. Confirm the candidate settings and model routing; freeze input, prompt, code
   and settings identities for baseline/generic_review/moodcut. Use the same v4
   protocol for both scenes; do not pool them with historical v3 scores.
3. Refresh endpoint/pricing checks and obtain the applicable model, scale and
   budget approval. The unapproved v3 text proposal was $0.10 per scene / $0.20
   total and is not a v4 budget. No video budget is included. Keep credentials
   local. The original shared $15 allowance is not a current balance or new approval.
4. Use fresh run folders and the team's existing runtime. Preserve failures,
   unmodified/reused outputs and unknown costs. Do not automatically retry or
   repair returned model dialogue. Inspect text results before separately scoped
   video execution. No instructions in this package start a paid job.
5. Return the sanitized complete source package to P5: original scene/assets and
   settings, initial/final plans, prompt/code identities, raw response references,
   all condition records, final ledger, preparation/receipts and media when present.
   Preserve relative paths and hashes, remove credentials, and count each final
   ledger once. Include failures; public summaries alone do not replace source
   records needed for qualification and anonymous export.

## Price snapshot and validation evidence

[text-models-price-snapshot.json](text-models-price-snapshot.json) records the
public catalogue observed on 2026-10-25: Gemini Flash-Lite $0.10/$0.40 and DeepSeek
V3.2 $0.28/$0.42 per million input/output tokens. Main's checked configuration had
DeepSeek $0.26/$0.38. This package does not edit shared config. Recheck prices and
actual selected endpoints before use; local budget gates are not account-wide
provider hard caps.

At main `afdd13b53778fd29b15f4a35d6e0d97784e2546f`, both selected inputs passed the
existing P1 checks; all four PNG references matched hashes/dimensions. Seventeen
existing runner/v3 regression tests passed (including ownership constraints,
source/cost gates and bounded calls). This is v3/offline evidence, not a live
result or v4 acceptance. The selected tests can be rerun with:

```text
python -m pytest tests/test_s06_real_runner.py tests/test_reviewer.py::test_v3_pipeline_routes_nineteen_calls_and_enforces_source_and_cost_gates tests/test_reviewer.py::test_v3_actor_schema_uses_existing_global_ownership_without_repair tests/test_reviewer.py::test_v3_actor_schema_keeps_shot_index_pairs_and_empty_actor tests/test_reviewer.py::test_v3_actor_requests_bind_each_actor_schema_without_added_calls -q
```

No raw machine logs, private paths, keys, reference image bytes, weights or videos
are included. P5 contributed selection/preflight, verified reference identities,
price discrepancy detection and this portable handoff; the existing scenes,
P1 runner and v3/v4 implementation remain team contributions.

## 简短中文总结

S02（亲密）和 S03（紧张）的输入、素材及候选设置已整理，17 项 v3 离线测试通过，尚未付费执行。请队友先确认 PR #66 的 v4 版本、入口和预算，再用新目录运行并保留完整记录交回 P5；此交接不授权付费，也不把 v3 准备结果当成 v4 验收。
