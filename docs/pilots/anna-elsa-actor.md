# Anna/Elsa actor self-review: actual development pilot, 2026-10-24

## Scope and execution

The user authorized the new planning Agent plus two independent actor Agents and one unified screenwriter structure, with unchanged models: Gemini 2.5 Flash-Lite for planning/writing, DeepSeek V3.2 for both actors, and HeyGen 768p for three five-second condition entries. Text ceiling $0.10, combined ceiling $1.00, separate $0.10 reserve; stop on failure or unknown cost, no retries or handwritten dialogue fallback. Results stay in PR #48, unmerged. This is one existing umbrella-return development event, not a formal sample expansion.

Execution used code commit `64416d8e8774a17c3ba6cdfebf387614e10db88c` with explicit `actor_self_review_v1`. The original planner/reviewer/pipeline/compiler/video client were used without changing prompts, returned outputs or acceptance checks during the run. There was no FakeClient, replay response, manual line or cached planning substitute. The story supplied the umbrella-return event, target affectionate, characters and five-second bounds; it supplied no dialogue or shot/camera answer. Complete actual outputs, actor reports, writer disposition, call IDs, identities and video properties are in [the result JSON](anna-elsa-actor.results.json).

Read-only preflight verified both original PNG URLs' bytes/MIME, compatible text endpoints within the existing rate caps, HeyGen reference-image SKU and 50% discount, native audio and disabled prompt enhancement. The conservative three-video quote remained $0.75 before identical-request reuse. Text rates remained capped at $0.10/$0.40 per million input/output tokens for Gemini and $0.26/$0.38 for DeepSeek. The shared text budget and provider max-price/no-fallback controls stayed active. Historical key usage was unchanged at $1.76177846 and available balance was $13.23822154 before this run.

## Actual dialogue and feedback flow

| Condition | Anna | Elsa | Actual review path |
| --- | --- | --- | --- |
| baseline | 艾莎，这是你的伞。 | 谢谢你，安娜。 | Shared Gemini initial plan |
| generic_review | 艾莎，这是你的伞。 | 谢谢你，安娜。 | Both actors returned empty reports; no rewrite |
| moodcut | 艾莎，伞还你啦。 | 谢谢你，安娜。 | Both actors raised one opinion; one unified Gemini revision |

Actual text requests: three planning calls, two generic actor calls, two emotional actor calls and one emotional unified rewrite, **eight total**. Both generic actors completed; the first empty report did not suppress the second. The existing no-issues rule skipped the generic writer. Saved request traces confirm all four actor requests received their own character binding and the same original plan, without another actor's feedback. The emotional branch started from the common initial plan rather than the generic branch.

The emotional writer declared Anna's `actor-1:tone_flatness_1` addressed and actually changed her referenced line. It retained Elsa's `actor-2:tone_underwhelming` as unaddressed with its original reason. The result is `applied` with `actor_feedback_status=has_unaddressed`; both branches retain `actor_endorsement=not_requested`, `verification=null` and `verification_kind=programmatic_only`. Valid disagreement was allowed into a pending-acceptance video; no final actor approval or independent score was invented.

The writer's retained explanation has a concrete limitation: it calls Elsa's suggestion “Anna's line” and says the alternatives would extend the dialogue beyond five seconds. One offered alternative, “谢啦，安娜。”, is shorter than the retained “谢谢你，安娜。”, so the explanation is not established by that text. We preserve it as model output, not a verified justification. No developer corrected the explanation, forced Elsa's revision, added another review round or reran a request. This is evidence of an unresolved integration problem, not proof that both actors' intentions were fulfilled.

## Actual videos and charges

All three condition entries completed and were delivered directly for listening/viewing. There are **two distinct actual provider videos**: generic_review has the exact same dialogue/request as baseline and reuses that same-block downloaded video. It adds no new POST or video charge. The moodcut request was generated separately. We did not pay to regenerate an identical generic request or pretend it was a third independent video sample.

Both raw clips are 1344×768 at 24 fps, contain audio and have encoded duration 5.258344 seconds for the requested five seconds. Delivered copies match the raw provider bytes by SHA-256. No retiming, hand edits, replacement media or static placeholders were used. File/audio presence does not establish correct speech, speaker assignment, lip synchronization or emotional expression; user listening/viewing and all formal ratings remain pending.

| Phase | Actual returned charge |
| --- | ---: |
| Shared Gemini planning | $0.00072690 |
| Generic actors, no writer | $0.00062866 |
| Emotional actors plus Gemini writer | $0.00112842 |
| **All text** | **$0.00248398** |
| Baseline video | $0.25000000 |
| Generic same-request reuse | $0.00000000 |
| Emotional video | $0.25000000 |
| **Total** | **$0.50248398** |

The key usage increase reconciled to exactly $0.50248398; remaining balance was $12.73573756. The immediate post-run balance snapshot lagged by one $0.25 video charge; a subsequent read-only balance snapshot matched the complete returned total. Both snapshots remain intact. No extra paid call was made for reconciliation. Text/combined ceilings held and the separate $0.10 reserve was untouched.

Observed paid submission counts are eight text POSTs and two video POSTs, each video submitted exactly once. The original ledger reports 19 video GETs, including polling/download, and 29 text/video HTTP operations; public catalog, image and balance GETs are outside that ledger count. A reused entry's saved receipt counters describe its source task and must not be summed as another submission. Aggregate token/estimated-cost fields retain their original nulls and known subtotals; actual provider spending is known. Planning and reused media are counted once. No failed call, automatic retry, model replacement or handwritten fallback occurred.

## Provenance, preservation and interpretation

References remain the original FrozenII Anna/Elsa `best.png` images from showlab/MovieAgent commit `d84041bed8bc8be460664528d9e9924cdde384ba`, with source attribution and unconfirmed image rights. See [animation library](../../assets/library/README.md). Provider acceptance is not rights clearance. Images, generated videos, credentials, runtime payloads and private paths are not committed.

The original [global-review pilot](anna-elsa-agent.md) and its exact JSON, receipts, snapshots and delivered media remain unchanged: all 124 protected historical files passed SHA-256 preservation checks. This new actor-protocol result has separate records and must not relabel those older outputs. Same input/model and an equal initial dialogue do not mean the new requests were software replays; the new actual call IDs/charges are recorded separately.

This run establishes an actual actor-feedback-to-video technical path, including truthful unchanged behavior, same-request reuse and a visible unaddressed actor opinion. It does not establish emotional improvement, satisfactory actor-consensus behavior, independent blind scores or formal inclusion. Human listening/viewing is the next acceptance step; no new method tuning or paid run is authorized by this record. Issues #8 and #9 remain open; PR #48 remains unmerged.

## Verification

Fresh actor regressions passed 19 tests in 0.65 seconds. The executed implementation head's complete GitHub offline-test and reference-tooling workflows also passed; those checks ran against code commit `64416d8`, before this results-only documentation commit. The actual saved preparation passed a read-only recompile, all four real actor inputs were rechecked for independence, and all delivered media bytes, actual fees/key delta and 124 protected historical hashes were checked. No subjective scores were filled.
