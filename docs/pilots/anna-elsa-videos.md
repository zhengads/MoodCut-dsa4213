# Anna/Elsa videos for team review

## Latest v3 attempt: no new video

The separately authorized [actor-v3 real trial](anna-elsa-actor-v3.md) stopped before video preparation on a conflicting/duplicate edit for the same shot. Nine text calls cost $0.00281304, reconciled; video submissions and new clips are zero. [Open the v3 attempt tab](https://zhengads.github.io/MoodCut-dsa4213/#v3) for actual text/status differences. Historical global/v1 tabs below still play the original five files and are not v3 outputs. No paid retry or hand repair occurred. The earlier deployment paragraphs are historical snapshots, not the current PR/branch state.

**[Open the online video comparison page](https://zhengads.github.io/MoodCut-dsa4213/)** to play the original clips directly, switch between the two historical experiments and compare planned line changes across three conditions. Only one clip plays at a time; there is no autoplay. The responsive page also preserves the shared baseline/generic video and the original unresolved opinions. This is a GitHub Pages player page, not a native attachment inside the PR conversation.

The [repository's experimental video Release](https://github.com/zhengads/MoodCut-dsa4213/releases/tag/pilot-anna-elsa-20261024) remains the download archive for five different original MP4 files, covering six condition entries from the two historical PR #48 pilots. All five Release digests/sizes and all five Pages-hosted files match the original local provider files, totaling 5,336,098 video bytes. Videos are copied into a temporary Pages artifact, not Git blobs. The table below retains the original download links; use the Pages link above for in-page playback.

These are **global_v1 and actor_self_review_v1 videos**. The later `actor_self_review_v2` omission-confirmation change has offline software acceptance only; no video was generated for v2 or for this upload. Original pilot records, model outputs, receipts and media are unchanged.

| Historical structure | Condition | Planned Anna / Elsa lines | Original MP4 |
| --- | --- | --- | --- |
| Global critique/revise/verify | baseline | 艾莎，这是你的伞。 / 谢谢你，安娜。 | [Download original](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/global-v1-baseline.mp4) |
| Global critique/revise/verify | generic_review | 艾莎，你的伞。 / 谢啦，安娜。 | [Download original](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/global-v1-generic_review.mp4) |
| Global critique/revise/verify | moodcut | 艾莎，你的伞，还给你。 / 嗯，辛苦你了。 | [Download original](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/global-v1-moodcut.mp4) |
| Two independent actors, unified writer | baseline | 艾莎，这是你的伞。 / 谢谢你，安娜。 | [Download original](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/actor-v1-baseline-and-generic.mp4) |
| Two independent actors, unified writer | generic_review | Same initial lines; both actors returned no issues | [Same baseline file](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/actor-v1-baseline-and-generic.mp4) |
| Two independent actors, unified writer | moodcut | 艾莎，伞还你啦。 / 谢谢你，安娜。 | [Download original](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/actor-v1-moodcut.mp4) |

The table gives planned dialogue for comparison, not a verified transcript of what the provider actually said. Listen for the supplied lines, speakers, pacing, naturalness and warmth, and inspect the generated action/identity. No human scores have been filled. These are development examples, not blinded rating materials or evidence that one method is better; fixed seeds do not remove generated-video randomness.

In the actor-v1 emotional condition, both actors raised an opinion. The writer changed Anna and left Elsa unchanged, giving a reason that misidentifies the speaker and does not establish why a shorter alternative exceeds the duration. That output is preserved in the [actual actor pilot](anna-elsa-actor.md) and [exact JSON](anna-elsa-actor.results.json). The [earlier global pilot](anna-elsa-agent.md) and [its JSON](anna-elsa-agent.results.json) remain separate. Neither set of videos demonstrates the later v2 confirmation gate.

The Release [manifest](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/manifest.json) records each filename, protocol, condition mapping, size and SHA-256. Its [source statement](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/SOURCE.md) preserves attribution: showlab/MovieAgent commit `d84041bed8bc8be460664528d9e9924cdde384ba`, FrozenII Anna/Elsa `best.png`. Underlying character/image rights remain unconfirmed; attribution and provider acceptance are not rights clearance. Original reference images, credentials and private runtime files are excluded. No new paid API or generation was needed to publish these exact historical files.

## Pages deployment and acceptance (2026-10-24)

[Deployment run](https://github.com/zhengads/MoodCut-dsa4213/actions/runs/40085929806) succeeded from `66b29904509b7cd291a99b8f0a3a2703346ae3c3` on the existing PR branch, without merging PR #48. The page source is [web/video-review](../../web/video-review/README.md); the [workflow](../../.github/workflows/video-pages.yml) uses pinned official Pages actions, downloads the fixed Release MP4s, verifies all five hashes/file count and deploys only the static files plus media. Only `feat/issue-8-agent-animation-pilot` and `main` may deploy to the repository's `github-pages` environment.

The public page returned HTTP 200, all five hosted MP4s returned `video/mp4` and matched their original SHA-256/size, and a media byte-range request returned HTTP 206. Browser checks actually played all five different sources at 1344×768 without media errors, checked that starting another clip pauses the previous one, switched experiments and checked keyboard navigation, no autoplay and a 390px single-column mobile layout without horizontal overflow. All six displayed dialogue pairs exactly match the preserved actual result JSON. These engineering checks do not fill human quality ratings.

All 303 protected historical files remained SHA-256 unchanged. No experiment/generation client or paid API was invoked, and no new video was generated. README and PR links make the page discoverable to the team; #8/#9 remain open and PR #48 remains unmerged.
