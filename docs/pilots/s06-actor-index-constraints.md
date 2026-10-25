# Offline actor-reference constraint correction

This is a developer interface correction in Draft PR #52, not a new model experiment. No paid API, quote/balance check, video generation, retry, replacement dialogue or model-answer repair occurred. Issues #8 and #9 remain open.

## Observed failure and scope

The [original S06 schema trial](s06-actor-v3-schema.md) remains failed. Its [public original response](s06-actor-v3-schema.results.json) records emotional Taiyi citing global `line_indices=[0]` even though `own_dialogue` supplied index `1`; index `0` belongs to Lijing. The existing ownership validator correctly stopped before the emotional writer and all video submission. The reply was valid JSON; this was a reference-binding error, not another JSON-tail error.

Both historical actor prompts contained a literal `[0]` example. This is a possible source of confusion, not a proven cause of the model's choice. New prompts remove that fixed index and explicitly distinguish global positions from positions in the actor's filtered list. Historical prompt files and failed results are unchanged.

## Existing request path, bounded by actual ownership

The existing optional `complete_json(json_schema=...)` now also applies to v3 `actor_critique`. `get_actor_json_schema` derives allowed references from the same `_actor_lines(initial_plan, actor_id)` used to supply `own_dialogue`:

- Each issue chooses one shot-specific schema branch. Its shot ID and integer index enum come only from that actor's actual original lines in that shot. Multi-shot indices cannot be mixed, and multiple owned lines remain available.
- Taiyi in this S06 shot can cite only `[1]`; Lijing can cite only `[0]`. The code does not translate, renumber or replace returned references.
- Actors may return no issues; an actor with no dialogue must return an empty issues array. Identity/schema/mode fields are bound to the supplied request.
- Evidence, suggestions, issue count and issue IDs remain model output. The schema supplies no opinion, acceptance decision or rewritten dialogue. Existing dimension/severity labels retain their existing meaning.
- Generic and emotional groups use the identical schema construction and ownership rules. Their only intentional review difference remains the criteria paragraph. Writer schemas, models, two-round negotiation, final-disagreement handling and hard-error gates are unchanged.

Request schema hashes enter existing call records/traces and source rechecks. To preserve saved identities, new execution uses `writer_output_contract=dialogue_by_shot_json_schema_v2`; the existing field identifies the coordinated v3 prompt/request bundle, not a new negotiation protocol. Old writer-only `dialogue_by_shot_json_schema_v1`, per-shot `dialogue_by_shot_v1`, patch/global/v1/v2 records keep their original prompt hashes and validation paths. Mixed v3 contracts remain ineligible for a single comparison. Schema bytes already count toward existing input-budget reservations.

Unsupported provider schemas, ignored constraints resulting in invalid output, malformed JSON, wrong ownership and unknown costs still stop. No schema downgrade, retry, repair model or correction of the experimental answer is added. Native enforcement of this new actor schema has not been paid-tested.

## Offline acceptance

Task-local software tests cover S06 index ownership, two modes, multiple owned lines, cross-shot pairing, silent actors, unchanged raw replies, unchanged call counts, old prompt identities and tampered actor schema hashes/formats/order. The public original wrong response is a negative regression input, not a new authored answer.

Denied-network replay uses original saved HTTP bytes with the existing real client/parser/reviewer orchestration and a mocked transport. Replay outputs are explicitly synthetic software records; replayed historical costs are not new spending:

- Latest S06: eight original envelopes/content hashes match; all parse as before. The original Taiyi `[0]` remains unchanged and rejected by ownership, with zero emotional writer rounds or video requests. The request now permits only `[1]`. The failed source cannot be compiled.
- Existing successful Anna/Elsa: nine original responses pass unchanged and reproduce the same three final plans; existing request preparation succeeds offline, with no video POST.
- Eight historical request packages remain readable by read-only recompilation, including the previous writer-only schema bundle. Before main synchronization, all 1,115 protected historical files retained their SHA-256 bytes. After synchronization, all trial inputs, responses, result files and media remain unchanged; the sole documentation exception is explained below.

Pre-sync local replay records are under ignored `runs/s06-actor-index-offline-20261024/`: `verify_offline.py`, `acceptance.json`, `preserved-before.json`, synthetic replay outputs and test log. They contain no newly generated model evidence. Public reproduction of the ownership regression is available in `tests/test_reviewer.py`; original private HTTP bytes are intentionally not published.

Validation commands (offline):

```powershell
python -m pytest -q
python scripts/prepare_references.py --check
python runs/s06-actor-index-offline-20261024/verify_offline.py
```

The last command is a one-time local verification using retained private artifacts and exclusive output directories. The pre-main-sync full local regression completed on 2026-10-25: **1,044 tests and 191 subtests passed** in 537.92 seconds. The reference cache check verified 33 files without downloads, and `git diff --check` passed. The live comparison page continues showing the actual failed S06 run; no new result tab or media is fabricated.


## Synchronization with existing main changes

The PR branch had not yet incorporated main's already merged #54 (JSON failure-kind codes), #55 (optional planning schemas) and #56 (new study inputs). Updating the shared client caused one content conflict. Main is merged into this development branch without rewriting history; PR #52 remains unmerged.

Resolution keeps both constructor options (`response_dir` and optional `json_schema_stages`), raw-response diagnostics plus main's stable `failure_kind` codes, and both configured planning and explicit actor/writer schemas. Effective schema selection precedes individual/shared budget reservations; an explicitly supplied schema takes precedence. Optional planning stages remain disabled in the experiment's unchanged configuration. New software checks cover zero-transport budget rejection and explicit-schema/raw-retention coexistence. No new experimental agent answer, setting, story selection or paid run is introduced by synchronization.

Of the original 1,115 protected paths, **1,114 retain their original bytes**. The only exception, `docs/studies/six-story-20261024/README.md`, receives main's existing pointer to its newer study design; it exactly matches main's tracked content. The original README remains in the pre-sync commit/history. All original JSON inputs, trial responses, failures, results and media remain unchanged. The refreshed preservation baseline retains 1,115 paths with this single documented upstream change. Post-sync original-byte replay again rejects the same eight-response S06 failure, reproduces the nine-response Anna/Elsa plans and rechecks eight old packages without network.

Post-sync replay records are separately saved under ignored `runs/s06-actor-index-main-offline-20261025/`; the pre-sync records are retained. Fresh post-sync affected-module verification: **615 tests and 94 subtests passed** in 313.77 seconds across client, reviewer, planner, validation, pipeline and evaluation suites. The pre-sync source also passed its full GitHub CI. The synchronized head requires its own full CI result; earlier checks are not inherited.


## Synchronization with P5 acceptance increment (#57)

The branch now also integrates main `f45590d` (#57). This adds review-status coverage counters and the existing repeatable offline acceptance command, without changing model settings, actor/writer prompts, ownership constraints or generation inputs. The merge had no content conflict. Original trial files and the documented 1,115-path post-sync preservation baseline remain unchanged.

Fresh combined-source checks: **272 tests and 27 subtests passed** for client, reviewer and paired-evaluation unit cases. Existing `scripts/verify_workflow.py` passed all five steps (mock three-condition rendering, anonymous export, no-rating coverage, assignment dry-run and generated software integration). Original-byte negative/positive replay and all eight old request-package recompilations passed again, with no real network/model requests in the replay and no new paid spending. These software videos are not a new real S06 trial.

Evidence is separately retained under ignored `runs/s06-actor-index-p5-offline-20261025/`. The previous head `c7e6bd8` full GitHub CI passed **1067 tests +191 subtests**; the newly synchronized head requires its own CI. PR #52 stays Draft/unmerged and #8/#9 remain open.
