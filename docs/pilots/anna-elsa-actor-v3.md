# Anna/Elsa bounded actor-v3 real trial — stopped before video

Executed on 2026-10-24 with code `c183d3faedf68f11010cfca0486f7cbd9e9ad59f`, after the user's explicit authorization. Exact model outputs, errors, call records, settings and accounting are preserved in [the result JSON](anna-elsa-actor-v3.results.json). This is a development trial, not formal evaluation. **No new video exists.** The [comparison page](https://zhengads.github.io/MoodCut-dsa4213/#v3) records the failed attempt separately from historical global/v1 videos.

## Approved scope and preflight

One existing Anna/Elsa umbrella-return development story, one common Agent-generated plan, three conditions (baseline, generic_review, moodcut), one requested five-second HeyGen clip per condition. Two original MovieAgent PNGs, 768p, 16:9, seed 4213, native Mandarin audio and disabled prompt enhancement were unchanged. Gemini 2.5 Flash-Lite handled planning/unified writing; independent actor reports used the unchanged DeepSeek V3.2 configuration, also configured for confirmations that were never reached. Both branches explicitly selected `actor_self_review_v3` with at most two writer/confirmation rounds and nineteen text calls per block.

Text ceiling $0.10, combined ceiling $1.00, additional untouched reserve $0.10. A valid final creative disagreement could proceed, but hard errors or unknown costs required stopping without retry, model change or handwritten dialogue fallback. This authorization did not approve repairing a returned patch by hand or repeating failed paid requests.

Read-only preflight verified both remote PNG byte hashes and MIME, compatible text endpoints within configured rate ceilings, and the existing HeyGen reference-video SKU/50% discount: $0.25 per five-second clip with two references, $0.75 for three distinct clips. Historical account usage reconciled before submission; starting balance was $12.73573756. No new account or deposit was needed.

## Actual outcome

| Condition | Actual text outcome | Video |
| --- | --- | --- |
| baseline | Common planning completed. Anna: “艾莎，这是你的伞。” Elsa: “谢谢你，安娜。” | Not submitted |
| generic_review | Two actor reports and one unified writer completed. Anna: “艾莎，你的伞还给你。” Elsa unchanged. One writer round, no omissions requiring confirmation. | Not submitted because the block stopped |
| moodcut | Two actor reports and one writer response received. The writer returned two edits for the same shot; the entire patch was rejected. The saved plan restores the original for diagnosis, not an accepted emotional revision. | Not submitted |

The exact error is `actor_revise: ValueError: edits[1]: conflicting or duplicate edit`. Both edits target `return-umbrella-shot` and each replaces its complete dialogue array. The first contains Elsa's original “谢谢你，安娜。” while the second contains “谢啦，安娜。”; these are not disjoint per-actor edits that can safely be concatenated. Both raw edits, original actor reports, dispositions and errors remain in the exact JSON. Nothing was merged, rewritten or retried by the developer.

The block stopped before video preparation/execution. **Nine real text POSTs, zero video POSTs, zero new videos.** No actor-confirmation request or second writer round was reached. This is a response-contract failure in the first emotional rewrite, not an actor maintaining a valid final creative disagreement. It does not establish whether real v3 negotiation would resolve or preserve such a disagreement.

## Costs and preservation

| Item | Actual USD |
| --- | ---: |
| All nine text calls | 0.00281304 |
| Video | 0 |
| Total | **0.00281304** |
| Untouched reserve spent | 0 |
| Reconciled remaining balance | 12.73292452 |

The immediate account snapshot lagged behind returned text charges. A later read-only snapshot matched the complete $0.00281304 usage increment exactly; neither snapshot was overwritten. All returned costs are known. There was no paid retry, model switch, manual dialogue/patch fallback or attempt to generate only the successful conditions after the hard failure.

All **521 protected historical files**, including original paid outputs/media and previous v2/v3 software acceptance artifacts, remained SHA-256 unchanged. Original reference images and private runtime/credential files are excluded from Git; underlying MovieAgent/FrozenII rights remain unconfirmed, and attribution is not a license grant. No new image or video was publicly redistributed by this failed run.

Human media checks and scores remain empty because no new clip exists. The page retains the original five historical MP4s and adds an explicit no-video v3 attempt; no old clip is relabeled as new. #8 and #9 remain open. This PR records the actual outcome and page update; it does not modify prompts/validators or authorize another paid attempt. A future change and rerun must retain this failure and be scoped separately.
