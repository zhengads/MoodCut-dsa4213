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

Prepared for one authorized execution after offline verification. Actual output, status, charges and media evidence will be recorded here without overwriting any earlier pilot. There have been no paid requests for this run at this preparation stage. Runtime evidence uses the ignored `runs/anna-elsa-agent-20261024/` directory. Issues #8 and #9 remain open; code and results belong to one PR, which must remain unmerged.
