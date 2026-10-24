# Actor self-review protocols

## Authorized v2 increment: return omitted feedback to its actor

This implementation increment is offline only. The actual v1 pilot and its original records, receipts and media remain byte-identical. New runs explicitly select `actor_self_review_v2`; v1/global sources retain their original protocol and prompt identities.

The writer's unaddressed opinions must be returned to the corresponding actor with its original report, the original/final dialogue and the exact omission reasons. Each affected actor gets at most one `actor_confirm` request through the DeepSeek review role, grouped over its own omitted issues. It accepts the omission or maintains the objection with a reason, bound to the actor, issue IDs and exact initial/candidate hashes. No writer can supply that response or claim full actor endorsement. Missing, malformed, failed or disputed confirmation blocks request preparation; raw feedback and the candidate remain available for human resolution. There is no automatic rewrite/retry loop. Only omitted opinions are confirmed, not the writer's addressed claims or overall quality.

Responses are saved in ordered `actor_confirmations=[{actor_id,response},...]`. Each response contains exactly `schema_version`, `scene_id`, `mode`, `actor_id`, `initial_plan_sha256`, `candidate_plan_sha256` and `decisions=[{issue_id,decision,reason},...]`; decisions are `accept_omission` or `maintain_objection`. IDs must cover exactly that actor's omitted issues, without extras or duplicates. The payload contains no other actor's reports or confirmations. Both actors are heard once when both have omissions; invalid/failed calls stop immediately without retry.

`actor_confirmation_status` is `not_needed`, `pending`, `accepted`, `disputed` or `failed`. An accepted omission remains unaddressed in the original disposition; it is not relabeled resolved. `actor_endorsement=not_requested` continues to mean no full-script actor sign-off. A valid semantic objection returns `review_failed` with the explicit `disputed` detail, restores the original as the non-final plan and preserves `writer_candidate_plan` plus all original reports/reasons/decisions. It is not recorded as a malformed response or API error. There is no accepted video source until the objection is resolved outside this bounded run. Existing failure accounting and scoring are unchanged.

Both review conditions use this same mechanism and the same review model/settings. At most two additional calls per reviewed condition raise the text-call ceiling from nine to thirteen per block. Existing shared budget/unknown-cost stop rules still apply; no new paid run is authorized here.

Offline replay retained the actual historical Elsa opinion, exact writer response and candidate as development inputs. A developer-authored `maintain_objection` response blocked preparation; a separately labeled software acceptance allowed `prepared_offline`. Each used nine software slots because the historical generic actors had no issues and only Elsa required confirmation. Network audit observed zero HTTP attempts and $0 new spending. Both legacy global/v1 prepared runs passed read-only recompilation; all 303 protected historical files remained unchanged. This is a targeted engineering regression informed by a development failure, not independent evaluation or an autonomous v2 result.

The five original historical videos are now available via the [team video index](pilots/anna-elsa-videos.md) and repository Release; remote digests match the source files. They are not v2 outputs. No videos or original images enter Git.

- [x] Add the bounded actor-confirmation prompt/stage and strict owner/issue/candidate binding, preserving v1 behavior and raw decisions.
- [x] Recheck confirmation at saved-source/request/comparison boundaries; reject absent, forged, disputed or mixed-protocol sources.
- [x] Verify accepted/disputed/malformed/failed/no-omission cases, independent actor payloads, both conditions and budget/role routing with software responses.
- [x] Replay the actual v1 omission and reason as explicitly labeled development input; verify disagreement blocks preparation and an explicit software acceptance can pass, without modifying actual results or making HTTP requests.
- [x] Publish exact historical video bytes as repository release attachments with source/hash/condition mapping and PR links; do not add binaries to Git or represent historical v1 videos as v2 outputs.
- [x] Run relevant regressions, hash/privacy/link checks, update PR #48 and keep it unmerged, with #8/#9 open.

## V2 verification

The broader related regression completed **602 tests and 113 subtests** in 393.98 seconds during implementation. After the final missing-candidate diagnostic guard, a fresh reviewer/patch/client/pipeline/evaluation run passed **278 tests and 47 subtests** in 20.85 seconds. This includes accepted/disputed/malformed/failed/no-omission cases, correct actor/candidate binding, raw-response preservation, extra-stage role routing, unknown-cost stopping, source tampering and comparison summaries. The broader suite was not repeated for documentation-only edits.

A fresh network-denied read-only recheck confirmed the accepted software preparation still compiles, the disputed block cannot prepare requests, both historical global/v1 preparations remain compatible and all 303 protected files are SHA-256 unchanged. New model/video HTTP attempts and spending are zero. The repository Release's five original MP4 digests/sizes match their sources. Its links are downloads; in-PR playback is a separate unresolved delivery task and does not block this code increment.

## Historical v1 real pilot (2026-10-24)

After the offline implementation below, a separately authorized [actual Anna/Elsa actor pilot](pilots/anna-elsa-actor.md) completed eight text calls and two distinct HeyGen videos covering three condition entries. Generic actors had no issues and retained/reused baseline; moodcut changed Anna while retaining one Elsa opinion with a problematic writer explanation. Total $0.50248398 reconciled, reserve untouched. Human acceptance remains pending. Exact outputs are separate from the unchanged historical global-review result. The offline evidence below describes implementation verification, not this later real run.

## Historical v1 implementation and checklist

The approved structure is one planning/screenwriting Agent and two character-specific actor Agents. Baseline keeps the shared initial plan. Both reviewed conditions collect independent feedback from the two actors on the same initial dialogue, then send both reports to one shared screenwriter for a unified dialogue patch. Generic actors use general self-review criteria; moodcut actors use emotion-oriented self-review criteria. The second actor never reads the first actor's feedback, and neither condition starts from the other's revision.

The existing global critique/revise/verify implementation is retained as `global_v1` for historical compatibility. New actor runs explicitly select `review_protocol="actor_self_review_v1"`; this selection and exact prompt identities are stored with the source. The original paid PR #48 run is a `global_v1` technical result and must not be relabeled as actor evidence. Its Markdown/JSON record, receipts, runtime snapshots and delivered videos remain unchanged.

- [x] Implement actor-specific prompts and structural ownership checks in the existing reviewer. Each actor sees the full scene/initial dialogue plus its own character and indexed lines, but issues may reference only that actor's original lines. Both actors report even if the first reports no issues.
- [x] Preserve raw actor reports; namespace their local issue IDs without dropping collisions; combine all feedback by shot before one screenwriter revision. Reuse the original atomic dialogue-only patch validator.
- [x] Route actor feedback to the common DeepSeek review role and unified rewriting to the Gemini planning/screenwriting role. Keep model controls, shared text budget and failure/unknown-cost stop behavior.
- [x] Record writer-declared addressed/unaddressed issue IDs separately from programmatic validation; this protocol has no additional model verification call and makes no claim that a declared addressed issue is objectively solved.
- [x] Bind the protocol, prompt identities, feedback ownership and writer result at saved-source/request/qualification boundaries. Preserve existing legacy sources and all original paid results.
- [x] Verify valid/empty feedback, silent actors, wrong actor/line references, duplicate local IDs, failed second actors, conflicting or illegal patches, complete feedback disposition, independent branch inputs and zero HTTP attempts using explicit software fixtures.
- [x] Run an offline Anna/Elsa replay through the actual pipeline/reviewer/compiler, label all new responses as software evidence, verify historical hashes and update this PR without new paid requests or merging.

## V1 roles, inputs and outputs

1. The planning/screenwriting role creates the common scene/shot plan and original dialogue once. Planning remains director/scene/shot; this change does not add planning stages or edit its outputs.
2. For each reviewed condition, call the same review model once for each character in scene order. Requests contain the same full initial context and only that character's `actor` binding and `own_dialogue` references. Sequential transport does not create a shared conversation or expose another actor's feedback.
3. Each actor returns a standard report with `actor_id` and issues carrying zero-based `line_indices`. Every referenced line must belong to that actor in the original shot. Empty issues are valid, including silent actors. Structural checks do not establish the semantic correctness of free-text opinions.
4. After both reports validate, aggregate all feedback with stable actor-position namespaces. A single planning/screenwriting call receives both reports and all issues grouped by shot. It produces one RevisionPatch plus a complete addressed/unaddressed disposition. No actor directly modifies the plan.
5. Apply the existing patch transaction, generated-plan validator and non-dialogue identity check. No second rewrite or model-judge loop is added. `applied` means a valid changed script; writer-declared issue disposition is not independent verification or a human score. A rejected patch/failed actor stops the workflow.

Both reviewed conditions therefore use at most three requests: two actor reports plus one unified rewrite. If both actors have no issues, retain unchanged and skip rewriting after collecting both reports. Across one planning pass and both conditions, the ceiling remains nine text requests. The model settings and maximum output-token allocation are the same between the two conditions. Actual calls and charges must be reported; the offline implementation itself authorized no paid execution. The later pilot above used its own explicit scope and budget.

## Comparison boundary

The comparison asks whether emotion-oriented actor self-review improves the resulting dialogue relative to general actor self-review under the same planner, actors, rewriting ability and budget. It does not test more Agents, generic-then-emotional serial review, independent actor rewrites, or an extra review round. Story, actions, camera, durations, references, voices and video settings remain common; only dialogue may change. Formal samples, paid execution and subjective evaluation require their own approved scope.

## Historical v1 offline evidence

The actual planner/reviewer/pipeline/compiler passed an offline Anna/Elsa replay using the unchanged historical planning responses and explicitly developer-authored actor/writer responses. The new block is `source_kind=synthetic`, `mock=true`: nine software response slots, three prepared five-second HeyGen 768p requests, local quote $0.750, zero HTTP attempts and $0 new spending. This local quote is not a current provider quotation. A network audit hook rejected connection/request attempts; none occurred. No new video was generated and no subjective judgment was filled.

The generic software branch deliberately retained one actor's opinion with a reason while changing the other actor's referenced line; it remained prepareable with `actor_feedback_status=has_unaddressed`. The moodcut software branch changed both referenced lines and recorded `writer_addressed`. Both retained `actor_endorsement=not_requested`. These examples test bookkeeping and ownership, not whether either method produces better dialogue. They must never replace autonomous model responses in a paid run.

The historical prepared requests also passed a read-only recompile under the updated code. SHA-256 checks found all 124 protected historical records, snapshots, pilot documents and delivered media unchanged. Local replay artifacts remain under the ignored `runs/anna-elsa-actor-offline-20261024/` directory; the portable regression is in `tests/test_reviewer.py`.

## V1 feedback authority and video acceptance

The screenwriter integrates both actors' opinions. Every namespaced issue must be accounted for exactly once. Declared addressed issues require an actual change to a referenced line of the same actor; no unrelated line, speaker, order or line count may change. Missing feedback, illegal patches and failed calls stop the workflow. Raw reports and the exact writer response remain saved, including failed attempts.

Unaddressed feedback requires a specific retained reason. Such a disagreement is visible in the saved review and run summary and does not by itself prevent request preparation or an independently authorized video run. The resulting video is a draft for listening/viewing, not a declaration that both actors approved it. The protocol has no final actor sign-off and no independent model judge. Programmatic traceability cannot prove that a changed line fulfills the actor's semantic intent or that the writer's reason is sound; those limitations remain for human acceptance.

Real video is necessary to evaluate performed dialogue, speakers, timing and emotional expression. The offline implementation verifies the software path only. The historical global-review videos cannot establish the quality of this changed actor method. The subsequent actual actor pilot supplies new videos for human acceptance, which remains pending.

## Selecting a protocol

Use the existing Python entry point with `output_mode="generated"` and explicit `review_protocol="actor_self_review_v2"` for the new confirmation gate. Select `actor_self_review_v1` only to reproduce its historical mechanism; its omitted feedback had no actor-confirmation requirement.

```python
block = run_experiment(scene, manifest, client, out_dir=new_script_directory,
    project_root=project_root, render=False, output_mode="generated",
    generation_settings=settings, template_sha256=get_video_template_sha256(),
    review_protocol="actor_self_review_v2")
```

For offline execution, `client` must be `FakeClient` with labeled software responses. Later request compilation uses the existing `prepare_generated_run`; its default offline execution remains unsubmitted. No new CLI or tool is introduced. Omitting the protocol preserves `global_v1` and its historical critique/revise/verify behavior; it does not silently opt a caller into the actor method. The client/role preset still enforces the shared budget and failure/unknown-charge stop rule when real execution is separately authorized.

## Historical v1 verification

`python -m pytest tests/test_reviewer.py tests/test_patches.py tests/test_client.py tests/test_pipeline.py tests/test_cli.py tests/test_evaluation.py tests/test_evaluation_paired.py tests/test_video_generation.py -q --tb=short --show-capture=no` passed **580 tests and 113 subtests** in 385.98 seconds, with the existing FFmpeg/ffprobe available. Actor regressions cover role routing with mocked HTTP envelopes, independent inputs, both reports in a shared-shot rewrite, empty/silent actors, incorrect ownership and indices, illegal patches, dropped feedback, false addressed claims, retained disagreement, spoofed endorsement and saved-source tampering. No real provider was called.

`python scripts/prepare_references.py --check` verified 33 cached references without downloading or executing upstream code. All 79 local links in the eight changed Markdown documents resolved; public-document privacy and `git diff --check` checks passed. Original paid result documents remain unchanged.
