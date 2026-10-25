# Actor self-review protocols

[Documentation index](README.md) · [Implementation contract](CONTRACTS.md#618-actor-self-review-protocol) · [Pilot records](pilots/README.md)

## Current method

For generated mode, one planner creates a common initial storyboard. Baseline keeps it. In each reviewed condition, two actors independently review their own indexed lines; one writer integrates both reports into a dialogue-only revision. Generic actors consider story, naturalness, tone and timing; moodcut actors prioritize the target emotional expression while preserving story and timing.

Both conditions share model routing, inputs, revision ability and limits. Actors see the full initial context and their own lines, but not each other's reports or confirmations. Scene directions, actions, shots, duration, speaker order, line count, references and generation settings remain frozen.

The current explicit protocol is `actor_self_review_v3`, with coordinated request contract `dialogue_by_shot_json_schema_v2`. Default CLI plan/review/run still uses the compatible global animatic path.

## Bounded negotiation in v3

1. Collect both original actor reports. If neither reports an issue, keep the initial plan and skip the writer and confirmations.
2. Make one unified writer revision. Every original opinion must be declared addressed or unaddressed with a reason. Return omitted issues to their owning actors, bound to the exact original/candidate plans and writer reasons.
3. If an actor maintains an objection, make one final writer revision. It must respond to every maintained issue, actually change a referenced line relative to the first candidate and retain previously addressed feedback. The complete patch still applies to the original plan.
4. Recheck previously disputed issues, including those now declared addressed, and any final omissions with the corresponding actors. A valid final disagreement permits preparation with `negotiation_status=disputed`, exact disputed IDs and raw replies retained. There is no third round.

The maximum is eight calls per reviewed branch, plus three shared planning calls: **19 text calls per block**. Unneeded calls are skipped. Both conditions use the same bounds and shared budget gates.

Invalid/missing responses, wrong ownership/hashes/coverage, illegal patches, a missing required second attempt, API failures, unknown costs or budget failures stop preparation. There is no automatic retry, model switch, JSON repair or handwritten fallback.

## Feedback and result meaning

| Field / outcome | Meaning |
| --- | --- |
| `writer_addressed` / addressed ID | The writer declares an attempt; programmatic checks require an appropriate line change, not semantic success |
| Accepted omission | The owning actor accepts the candidate for the specified omitted issue; the issue stays recorded as unaddressed |
| Final v3 disagreement | A valid second-round draft with preserved disputed IDs, awaiting human inspection |
| `verification_kind=programmatic_only`, `verification=null` | Structural validation, without an independent model or human quality score |
| `actor_endorsement=not_requested` | No whole-script actor sign-off |
| `prepared` / `prepared_offline` | Script/request preparation, not completed media or approved formal inclusion |

`negotiation_rounds` keeps each writer response, disposition, patch, candidate and actor confirmation. Top-level fields mirror the final round. Saved-source, request and qualification checks revalidate raw rounds, stage/model order, prompt identities and summaries; different protocols or writer contracts cannot be pooled as one comparison.

## Request format and compatibility

Writers return one complete ordered dialogue array per affected shot in `dialogue_by_shot`; the reviewer derives at most one atomic edit per shot. The second round additionally returns `objection_responses`. This conversion does not repair conflicting or failed model output.

Current actor schemas derive allowed global line indices from the original plan and actor ownership. An actor with no lines must return no issues. Schemas supply structure and identity constraints, not opinions, replacement dialogue or decisions. Independent validators still reject wrong ownership if a provider ignores the schema.

| Protocol | Omission / disagreement policy | Maximum text calls per block |
| --- | --- | ---: |
| `global_v1` | Global critique → revise → verify; unresolved model opinions remain recorded | 9 |
| `actor_self_review_v1` | Two actor reports and one writer; reasoned omissions may proceed | 9 |
| `actor_self_review_v2` | Owning actor must accept omissions; an objection blocks preparation | 13 |
| `actor_self_review_v3` | At most two writer/confirmation rounds; valid final disagreement may proceed | 19 |

Historical v3 writer contracts `issue_patch_v1`, `dialogue_by_shot_v1` and `dialogue_by_shot_json_schema_v1` keep their original prompts and validation for source compatibility. New execution uses `dialogue_by_shot_json_schema_v2`; saved runs are not retagged. Exact fields are in CONTRACTS 6.18–6.24.

## Selecting a protocol

```python
from moodcut.pipeline import run_experiment
from moodcut.video_generation import get_video_template_sha256

# scene, manifest, client and generation_settings must already be supplied.
template_sha256 = get_video_template_sha256()
block = run_experiment(
    scene, manifest, client,
    out_dir="runs/generated-scripts-new", project_root=".",
    output_mode="generated",
    generation_settings=generation_settings,
    template_sha256=template_sha256,
    review_protocol="actor_self_review_v3",
)
```

This API prepares scripts. It does not compile or execute video requests; follow the [usage guide](usage.md#生成式视频流程). A real client requires the appropriate approved scope and budget. Optional model routing is configured through the existing clients; this example does not select or authorize a provider.

## Evidence and limitations

[S06 v3](pilots/s06-actor-v3-index.md) completed three real videos under the current schema contract. Both writers declared all four opinions addressed in one round, so that pilot did **not** exercise second-round negotiation or prove the quality of actor confirmation.

[Historical pilots](pilots/README.md) retain the earlier wrong-index, invalid-JSON and duplicate-edit failures, the v1 omission case and the successful older contracts. [Offline acceptance history](history/README.md) links the versioned implementation records and test evidence.

Human speech/identity/naturalness checks and independent emotion ratings remain distinct from these technical results. Fixed seeds do not guarantee equal visuals; the comparison tests dialogue-review effects under shared inputs, not an isolated contribution from more agents, actions or facial expressions.
