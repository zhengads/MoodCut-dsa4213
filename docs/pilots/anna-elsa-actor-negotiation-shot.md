# Anna/Elsa actor-negotiation per-shot writer real trial — JSON error before video

The user separately authorized one real trial using the corrected writer contract, unchanged models, HeyGen 768p, three requested five-second conditions, text ceiling $0.10, combined ceiling $1.00 and an additional untouched $0.10 reserve. This trial executed code `cc15e01d873caa8c56c947be018302d959577a4d` on 2026-10-24. See [exact saved results](anna-elsa-actor-v3-shot.results.json) and [the comparison page](https://zhengads.github.io/MoodCut-dsa4213/#v3-shot).

**Outcome: nine text requests, $0.00291790, no video submissions or new clips.** The generic branch successfully used the per-shot contract. The first emotional writer response failed strict JSON-object parsing, so the entire block stopped as required. There was no paid retry, model change, manual repair or handwritten fallback. No actor-confirmation call or second writer round was reached.

## Scope and actual text

Anna/Elsa's existing umbrella-return development story and original two PNGs were reused. Gemini 2.5 Flash-Lite handled common planning/unified writing; independent actor reports used DeepSeek V3.2. Both review conditions used `actor_negotiation` with `writer_output_contract=dialogue_by_shot_object`. Original scene/settings, 16:9, seed 4213, native Mandarin and disabled prompt enhancement were fixed; reference bytes/MIME and current model prices were checked read-only. Text endpoints remained within the configured ceilings and the three-video quote remained $0.75.

| Condition | Saved model-generated dialogue | Actual state |
| --- | --- | --- |
| baseline | Anna: “艾莎，这是你的伞。” Elsa: “谢谢你，安娜。” | Common plan saved; video not submitted |
| generic_review | Anna: “艾莎，伞我用完啦，还你。” Elsa: “谢谢你，安娜。伞还好用吗？” | Three actor opinions, one valid per-shot writer response and one derived atomic edit; no omitted issues requiring confirmation |
| moodcut | Stored initial dialogue only, restored for diagnosis | Emotional writer reply rejected before reviewer received a parsed object; no accepted emotional candidate |

The generic branch demonstrates real compliance with the revised per-shot interface in this one response. It is not evidence that its speech fits five seconds, improves emotion or will consistently pass future runs. The original two-edit failure remains a separate preserved attempt; neither result is relabeled successful video generation.

## Error and retained-evidence limitation

The saved error is `actor_revise: OpenRouterError: Model output must be a finite JSON object without duplicate keys`. The final request returned `finish_reason=stop`, 119 completion tokens and known cost $0.00033870. This generic error covers invalid syntax, duplicate keys, non-finite values or a non-object root. **The retained evidence cannot identify which subtype occurred.** Do not claim it was definitely another duplicated shot key or a token-limit truncation.

The current text client does not retain invalid content before parsing, and reviewer response tracing starts only after a successful parsed return. Consequently the last reply's raw text is unavailable locally. A read-only provider content query returned HTTP 404, `Content not available for this generation`. Every available earlier raw planning/report/writer object, request trace, error, generation ID, token/cost record and account snapshot is retained; the missing reply is explicitly acknowledged rather than reconstructed. This result update does not add a diagnostic tool, change the client or authorize another model request.

## Accounting and history

All nine generation IDs were individually checked through the read-only provider generation endpoint; each server cost equals its saved returned cost. Their exact sum **$0.00291790** equals the account usage increment from the actual starting snapshot to the later observed snapshot. Video cost is zero, no reserve was spent, and final observed balance was **$12.72704618**.

Before this attempt, shared-key usage had increased by **$0.00296044** since the previous trial's reconciled snapshot. The previous trial's nine generation receipts were rechecked unchanged. The additional historical usage has no attributable source in the available ordinary-key/current-day view and is recorded separately, not assigned to this trial. A temporary historical-flatness preflight assertion prevented submission before it was corrected to use this attempt's actual starting snapshot; those local preflight stops made zero model/video POSTs and are not paid retries. Starting balance at the actual submission boundary was $12.72996408. No previous ledger or snapshot was rewritten to make the totals match.

All **606 protected historical files**, including both earlier paid attempts and offline correction artifacts, remained SHA-256 unchanged. Original public result files remain intact. No image/video asset was uploaded for this stopped attempt. Reference-image/character rights remain unconfirmed; attribution is not a license grant.

Human media checks and scores remain empty because no new video exists. The comparison page adds this stopped trial separately and retains the previous failed attempt and five historical playable videos. PR #52 remains the single result/fix PR, Draft and unmerged; #8/#9 remain open. Future diagnosis must account for the missing invalid text, and any further paid trial requires separate authorization.
