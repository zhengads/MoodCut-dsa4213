# S06 schema-writer real trial — actor line-ownership failure

**Stopped after eight text calls; zero video submissions.** This separately authorized trial used the corrected actor-negotiation code `c4d61630f41d49a54061ffd1a8c5efb07b8c6b1b` on 2026-10-24. The generic writer's native JSON Schema request succeeded, but emotional Taiyi returned the wrong global dialogue-line index. The existing ownership validator stopped the block before the emotional writer. No retry, model switch, index correction or handwritten fallback occurred.

[Actual status and saved lines](https://zhengads.github.io/MoodCut-dsa4213/#s06-schema), [exact result and actor reply](s06-actor-v3-schema.results.json). There is no new S06 video to watch. The [previous S06 JSON-tail failure](s06-actor-negotiation.md) and historical Anna/Elsa originals remain separate and unchanged.

## Scope and actual sequence

Scene, asset manifest, fixed male voices/indoor ambience, pricing and text-model configurations match the previous S06 attempt exactly. The original cleanup-assignment task, hostile target, two PNG references, five-second single shot, 768p/16:9/seed4213/native Mandarin settings and disabled enhancement are unchanged. Raw PNG bytes/MIME, local hashes, public prices and compatible Gemini structured-output endpoints were checked before submission; the possible three-video quote remained $0.75. Limits were text $0.10, combined $1.00 and an additional untouched $0.10 reserve.

The new writer contract is `dialogue_by_shot_writer_schema`, with unchanged `actor_negotiation` negotiation rules and Gemini 2.5 Flash-Lite / DeepSeek V3.2 roles. Actual order: three shared planning calls, generic actor/actor/writer, emotional actor/actor. **All eight completions were valid JSON** and all raw bodies, model strings and diagnostics were retained and hash-checked. Client JSON success does not mean actor-ownership or overall review success.

| Condition | Saved planned dialogue: Lijing / Taiyi | Actual state |
| --- | --- | --- |
| baseline | 这次收尾你来负责。 / 凭什么？重新分工。 | Common plan saved; video not submitted |
| generic_review | 这次收尾，该你负责了。 / 不行，得重新分工。 | Both actors raised one opinion; schema writer declared both addressed and the revision passed |
| moodcut | Restored initial dialogue for diagnosis | Both actors replied, but Taiyi's ownership reference failed; no emotional writer/candidate/video |

The generic writer used `response_format.type=json_schema`, `strict=true` and the expected first-round schema digest. This is one successful real structured request, not a guarantee of future compliance. No omission required generic actor confirmation. Emotional writer, actor confirmation and second revision were not reached; live negotiation/disagreement behavior was not exercised. Writer-declared addressed status remains distinct from semantic fulfillment or full-script actor endorsement.

## Confirmed new failure

The full shot's original ordered lines are **index 0: Lijing**, **index 1: Taiyi**. The actual actor payload explicitly supplied Taiyi's `own_dialogue` with `line_index=1`. Taiyi's reply quoted its own refusal in its evidence but returned **`line_indices=[0]`**, pointing to Lijing. The saved error is `Actor issue must reference only that actor's original dialogue lines`; replaying the original report through the ownership validator reproduces it.

This is a dialogue-binding error, not a JSON parsing failure or another extra tail. The model's reason for choosing the wrong index is unknown. The original `[0]` remains unchanged: it was not translated from a presumed actor-local index, replaced with `[1]`, or handed to the writer as valid feedback. Moodcut's restored initial plan is diagnostic fallback, not an accepted emotional candidate. The saved-source loader rejects the block; no request-preparation or execution directory exists.

## Accounting and preservation

All eight generation IDs were individually checked through the read-only provider endpoint. Returned costs equal server costs and sum to **$0.00336748**, exactly matching this attempt's account usage increment. Video charges are zero; reserve spent is zero. No paid request was retried or made for publication.

**1038 protected historical files** retained their SHA-256 values, including original S06 failure evidence, prior real media, offline schema replays and frozen inputs. Six older page experiment objects and all eight original hosted MP4 hashes remain unchanged. The page adds a separate seventh tab with correct speakers, hostile target and three explicit no-submission states. No new media Release, image upload or binary video enters Git. Runtime, client, prompt and actor protocol code were not modified during this trial/result increment.

Sources remain showlab/MovieAgent commit `d84041bed8bc8be460664528d9e9924cdde384ba`, NeZha2 Lijing/Taiyi `best.png`; original attribution and unconfirmed image/character-rights declarations are preserved. Human media checks and ratings remain empty, and this failed attempt cannot establish generic superiority or compare video quality.

The executed code head's full CI passed **1039 tests and 191 subtests** (425.68s). Result-head CI/deployment are tracked separately in PR #52. The experiment produced no new video; PR #52 remains Draft/unmerged and #8/#9 open. Another paid attempt is not authorized.
