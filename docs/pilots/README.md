# Trial and protocol revision records

[Documentation](../README.md) · [Current method](../ACTOR_REVIEW_METHOD.md) · [Public viewing page](https://zhengads.github.io/MoodCut-dsa4213/)

This directory contains dated and versioned development evidence. Statements such as Draft, unmerged or not yet tested describe the state at the time; consult the corresponding PR for merge status. Later successes do not overwrite earlier failures, and a technically completed video does not establish human quality acceptance or independently evaluated effectiveness.

## Actual trials

| Record | Protocol / inputs | Actual outcome |
| --- | --- | --- |
| [Umbrella technical trial and early failures](umbrella-single-shot.md) | Handwritten dialogue for three conditions; cn-02/cn-04 | Three HeyGen videos completed, $0.75; original Wan/Seedance/MIME failures and unknown costs retained |
| [Anna/Elsa global review](anna-elsa-agent.md) | global_review | 9 text calls, 3 videos; $0.75376126, with unresolved model concerns retained |
| [Anna/Elsa dual actors](anna-elsa-actor.md) | actor_self_review | 8 text calls, 2 distinct videos covering three conditions; $0.50248398, generic review reuses baseline, and Elsa's unadopted opinion is retained |
| [Anna/Elsa actor-negotiation first attempt](anna-elsa-actor-negotiation.md) | actor-negotiation / issue_patch | Duplicate edit; no video submitted |
| [Anna/Elsa per-shot interface](anna-elsa-actor-negotiation-shot.md) | actor-negotiation / dialogue_by_shot_object | JSON failure; original text was missing at the time, so the exact subtype is unknown |
| [Anna/Elsa with raw response retention](anna-elsa-actor-negotiation-captured.md) | actor-negotiation / dialogue_by_shot_object | Three videos completed, $0.75277694 |
| [S06 trailing JSON failure](s06-actor-negotiation.md) | actor-negotiation / dialogue_by_shot_object | Original invalid response retained; no video submitted |
| [S06 actor line-reference failure](s06-actor-negotiation-schema.md) | actor-negotiation / dialogue_by_shot_writer_schema | Invalid line reference; no video submitted |
| [S06 with constrained actor references](s06-actor-negotiation-index.md) | actor-negotiation / dialogue_by_shot_owned_schema | Three videos completed, $0.75421676; human inspection pending |

Each Agent trial Markdown file links to its `*.results.json`, executed version and media sources. Do not pool different protocols into one paired sample or count reused videos as new independent generations. Real actor-confirmation integration evidence is in the [P1 historical report](../p1-integration-verification.md).

## Protocol revisions addressing failures

| Note | Boundary addressed |
| --- | --- |
| [Per-shot output contract](anna-elsa-negotiation-shot-contract.md) | One complete dialogue per shot, avoiding duplicate edits for separate opinions |
| [Raw responses and JSON diagnostics](text-response-diagnostics.md) | Private raw-response retention and parsing-failure classification; no repair of model output |
| [S06 writer schema](s06-structured-writer.md) | Structured writer requests and version identity |
| [S06 actor reference constraints](s06-actor-index-constraints.md) | Global line indices constrained to the actor's own dialogue |

Read offline acceptance results in these revision notes separately from subsequent real trials. The [method](../ACTOR_REVIEW_METHOD.md) and [contracts](../CONTRACTS.md) describe the current protocol without duplicating individual test logs.

## Media and provenance

The [original video delivery index](anna-elsa-videos.md) preserves provenance for withdrawn video releases. The public gallery now shows only stories 01–12. [Synthetic character credits](umbrella-sigils-credits.md) preserve the sources and license conditions for cn-02/cn-04. See the [asset library](../../assets/library/README.md) for the rights status of MovieAgent character images.

The public viewing page exposes conditions and story requirements, so it cannot be distributed directly as blind-evaluation material. Preserve historical results, original JSON, failures, costs and image identities.
