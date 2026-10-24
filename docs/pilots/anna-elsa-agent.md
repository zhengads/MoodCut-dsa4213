# Anna/Elsa: actual Agent planning and dialogue-review pilot

## Approved scope (2026-10-24)

The user authorized one development event from the existing umbrella-return story, with Anna returning a borrowed umbrella to Elsa at a rainy bus stop. The supplied input contains the event, characters, target `affectionate` tone and a single five-second shot constraint. It contains no prescribed spoken line, shot direction, camera choice or hand-written planning/review response. Actual scene/shot planning and initial dialogue must come from the planning model; the two review branches independently start from that same initial plan.

| Role / service | Frozen selection |
| --- | --- |
| Shared planning | `google/gemini-2.5-flash-lite`, director/scene/shot, at most three requests |
| Both review conditions | `deepseek/deepseek-v3.2`, critique/revise/verify, at most three requests per condition; unchanged is valid |
| Text controls | temperature 0, timeout 120 seconds, explicit reasoning disabled; [role configuration](../../configs/agent_pilot_models.json) |
| Video | `heygen/heygen-video-1`, 768p, 16:9, requested five seconds per condition, seed 4213, native Mandarin audio, prompt enhancement disabled |
| Scope | baseline + generic_review + moodcut, at most three video submissions; identical requests may reuse an existing clip |
| Budgets | shared text ceiling $0.10, combined text/video ceiling $1.00, separate $0.10 reserve not spendable |
| Stop rule | any failed request, invalid planning/review or unknown charge stops subsequent paid calls; no retry, model switch or handwritten replacement |

Baseline retains the actual Agent initial plan. Generic and emotional review receive independent copies of the same input and use the same review model/settings; only dialogue can change. All actions, framing, durations, references and video settings are common. No ranking or mandatory difference between the three versions is assumed. The native audio/video checks are file checks; correctness, acting and emotion require human viewing/listening. This development probe does not establish method superiority or formal inclusion.

## Inputs and preflight

Use the original MovieAgent Anna/Elsa `best.png` files from fixed revision `d84041bed8bc8be460664528d9e9924cdde384ba`. File sizes, SHA-256 and local/remote bytes are verified against `assets/manifest.json`. For this run, the original pinned `raw.githubusercontent.com` PNG URLs return HTTP 200 and `image/png`; the saved compact manifest keeps those exact URLs throughout planning, review and video compilation. Binary/base64 images are not inserted into text-model prompts. There is no change from a saved text source's URLs to different video inputs after planning.

Source, attribution and unresolved film-image rights remain as described in the [animation library](../../assets/library/README.md). Provider acceptance does not establish permission to redistribute the pictures. Original images, runtime requests/receipts, videos and credentials are excluded from Git.

Read-only endpoint preflight requires support for the existing JSON/temperature/token controls and explicit reasoning control within the configured price ceilings. Text price ceilings per million input/output tokens are $0.10/$0.40 for Gemini and $0.26/$0.38 for DeepSeek. The checked two-image reference-video quote is $0.25 per five-second clip, $0.75 before identical-request reuse. Estimates are not actual spending. Original prompts, source/response records, shared/request identities and phase costs are retained; planning is counted once.

## Execution record

Actual planning/review ran at code commit `832dfac6f0843efba7db89cf6b2e33d73e951dc5`, using the original shipped prompts and validators, without developer edits to any returned plan, report, patch, verification or spoken line. All nine requests succeeded with known charges: Gemini planning $0.00072690; DeepSeek generic review $0.00164658; DeepSeek emotional review $0.00138778; total **$0.00376126**. Both reviews are `applied`. Their verification each retains one unresolved opinion; these are partial review outcomes, not claims that every concern was fixed.

| Condition | Anna | Elsa |
| --- | --- | --- |
| baseline (actual Gemini initial dialogue) | 艾莎，这是你的伞。 | 谢谢你，安娜。 |
| generic_review (actual DeepSeek revision) | 艾莎，你的伞。 | 谢啦，安娜。 |
| moodcut (actual DeepSeek revision) | 艾莎，你的伞，还给你。 | 嗯，辛苦你了。 |

The generic review verification lists `dialogue_too_formal` as resolved and `dialogue_lacks_warmth` as unresolved. The emotional verification lists `tone_1` as resolved and `naturalness_1` as unresolved. These are the model's own judgments, not independent ratings. The common plan, non-dialogue/shared generation identity and both review models/settings are unchanged across the three conditions. See [the exact actual output record](anna-elsa-agent.results.json) for planning responses, reports, patches, verifications, model IDs, generation IDs and returned charges.

An earlier local startup used a string instead of the numeric text budget required by the existing client API. It stopped during configuration construction before any model request; the audit records zero text/video POSTs and its original snapshots remain in `runs/anna-elsa-agent-20261024/`. The corrected startup used numeric 0.10 in a new directory, `runs/anna-elsa-agent-20261024-live/`. No paid request was retried or replayed. Credentials were reused from the existing secure store and never recorded in Git.

All three actual HeyGen tasks completed and were downloaded, one POST per condition at $0.25 each. There were 15 status polls and three content downloads (18 video GETs); including nine text POSTs and three video POSTs, the run made 30 model/video HTTP calls. Text plus video actual cost is **$0.75376126**, below the $1.00 combined ceiling; the separate $0.10 reserve was untouched. A subsequent read-only key snapshot confirms an exactly matching $0.75376126 usage increase. This reconciles this run, not historical unknown charges or an account-wide balance.

| Condition | Actual video task ID | Returned video charge |
| --- | --- | --- |
| baseline | `gen-vid-1792830075-j1h1m0CwzOFFPaUEmDhP` | $0.25 |
| generic_review | `gen-vid-1792830118-NDW0jn457tLiWozSGvTP` | $0.25 |
| moodcut | `gen-vid-1792830160-TD2utUS5h3nsYTcxICWK` | $0.25 |

The original provider clips were delivered directly for listening/viewing. Each is 1344 x 768, 24 fps, with audio and encoded duration 5.258344 seconds for the five-second request. Delivery-copy hashes match the raw clip bytes; exact file and request hashes are in the linked JSON record. No video was substituted, retimed or hand-edited. Final status is `assembled_requires_manual_inspection`; dialogue accuracy, speaker identity, lip sync, action and emotion still require human acceptance. No subjective ratings, automatic emotion scores or formal inclusion approvals were filled.

Verification: the affected client/pipeline suites passed 131 tests; the broader client/pipeline/CLI/evaluation/video-generation suite passed 455 tests and 66 subtests in 417.02s after adding the existing FFmpeg directory to the test process PATH. The first broad attempt had failed because FFmpeg was absent from PATH; it did not call any paid API. After the local startup parameter correction, the client suite including the real preset-construction regression passed 61 tests in 4.05s. No production planner, reviewer prompt, returned response or validation rule was changed in response to this pilot. Issues #8 and #9 remain open; code and results belong to one PR, which must remain unmerged.
