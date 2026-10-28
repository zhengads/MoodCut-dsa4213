# MoodCut documentation

Start with the [project homepage](../README.md) for the research question and quick start. This directory maintains separate guides for current usage, interfaces, team collaboration and historical evidence.

## Current status (2026-10-28)

- Generated script orchestration, three-condition request compilation, task execution, media inspection, qualification rechecks and anonymous export are implemented. The default CLI still produces offline animatics; the actor protocol must be selected explicitly.
- The latest opt-in protocol is `actor_self_review_v4`: generic review uses one global Agent, while MoodCut uses two independent Actors. Both conditions allow at most two revisions and revisit every candidate. New requests use `dialogue_by_shot_json_schema_v2`; older protocols and historical results remain supported.
- S06 v3 completed three real videos at a cost of $0.75421676. The [original trial record](pilots/s06-actor-v3-index.md) preserves the settings, costs and results. Technical success does not establish human quality acceptance or independent evidence of effectiveness.
- The [current script catalog](studies/six-story-clear-emotions-20261024/README.md) now lists only the 12 scenarios in the [2026-10-28 release](https://github.com/zhengads/MoodCut-dsa4213/releases/tag/Videos_S07-S18): display 01–06 correspond to S07–S12, and 07–12 to S13–S18 V2. The ZIP contains 36 condition files, 28 distinct video byte hashes, and delivery durations of 8.083344 seconds.
- S13–S18 V2 delivery records identify Gemini-generated shared initial dialogue. Earlier authored drafts and the five-second S07–S12 inputs remain historical fixtures, not the released scripts. See the [verified file manifest](studies/six-story-clear-emotions-20261024/release-index.json); final dialogue transcripts and frozen run blocks are not included in the release ZIP.
- Issues #8 and #9 were retired as task trackers on 2026-10-28; their closure does not certify the unfinished acceptance work. [PR #58](https://github.com/zhengads/MoodCut-dsa4213/pull/58) is merged and preserves historical Anna/Elsa audit and image-quality evidence. These results must not be relabeled as S06 or current-release results. Independent human ratings and formal inclusion remain outstanding.

## Read by task

| Purpose | Main document |
| --- | --- |
| Installation, commands, API configuration and asset preparation | [Usage guide](usage.md) |
| Three-condition comparison and actor negotiation | [Actor method](ACTOR_REVIEW_METHOD.md) |
| Integration fields, functions, states and accounting | [Shared contracts](CONTRACTS.md) |
| Report validation, atomic patches and legacy global review | [Review implementation](review.md) |
| Generation requests, video inspection and static rendering | [Rendering](rendering.md) |
| Qualification, blind evaluation, human ratings and statistical denominators | [Evaluation](evaluation.md) |
| VBench installation, single-metric execution and resume | [VBench tools](vbench.md) |
| Module responsibilities, file ownership and delivery workflow | [Team collaboration](TEAM.md) · [Branch rules](BRANCHES.md) |
| Upstream reading paths and scope of reuse | [Reference index](REFERENCES.md) · [Reuse notes](upstream-reuse.md) |

## Evidence and history

- [Trial index](pilots/README.md): successes, failures, costs and original JSON, organized by protocol and actual outcome.
- [Historical index](history/README.md): early implementation plans, software acceptance evidence and original document versions.
- [P1 integration report](p1-integration-verification.md): dated integration and real v2 evidence, rather than a current task list.
- [Six-story v1](studies/six-story-20261024/README.md) preserves the original inputs and identities; the revised design uses a separate v2 directory.
- The [previous full specification](https://github.com/zhengads/MoodCut-dsa4213/blob/bbb38cb01cca0fe7fff43d3ddd4aa98259a77f1f/docs/studies/six-story-clear-emotions-20261024/README.md) preserves the removed S01–S06 descriptions and earlier authored-draft challenge design. Original JSON inputs and evaluation identities remain unchanged.
- [Emotion evaluation record (2026-10-25 to 2026-10-27)](studies/emotion-evaluation-20261027/EMOTION_EVALUATION_RECORD.md) documents the VEMOCLAP and VBench development evaluation of S01–S15: how the scoring rules changed, the ablation and control experiments, per-video results and the scripts to reproduce them ([scripts/emotion_eval](../scripts/emotion_eval/README.md)). Exploratory; not a method comparison.

Maintain current status on this page, operational instructions in the usage guide, shared rules in the contracts and experimental results in their dated records. Task cards describe module responsibilities and remaining work without duplicating trial logs. Do not rewrite existing results, failures or raw data to update the narrative.
