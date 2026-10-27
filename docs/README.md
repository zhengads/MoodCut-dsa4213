# MoodCut documentation

Start with the [project homepage](../README.md) for the research question and quick start. This directory maintains separate guides for current usage, interfaces, team collaboration and historical evidence.

## Current status (2026-10-27)

- Generated script orchestration, three-condition request compilation, task execution, media inspection, qualification rechecks and anonymous export are implemented. The default CLI still produces offline animatics; the actor protocol must be selected explicitly.
- The latest opt-in protocol is `actor_self_review_v4`: generic review uses one global Agent, while MoodCut uses two independent Actors. Both conditions allow at most two revisions and revisit every candidate. New requests use `dialogue_by_shot_json_schema_v2`; older protocols and historical results remain supported.
- S06 v3 completed three real videos at a cost of $0.75421676. The [original trial record](pilots/s06-actor-v3-index.md) preserves the settings, costs and results. Technical success does not establish human quality acceptance or independent evidence of effectiveness.
- The [six-story v2 design](studies/six-story-clear-emotions-20261024/README.md) supplies candidate inputs for the next round: 18 condition entries, not 18 completed results. `configs/experiment.json` remains a development fixture.
- The same study page now continues with the [S07–S12 basic-emotion design](studies/six-story-clear-emotions-20261024/README.md), adding one scenario for each VEMOCLAP class: anger, disgust, fear, joy, sadness and surprise. Generated-mode JSON inputs, native-label validation and an offline 18-assignment evaluation configuration are included; videos and evaluation results are not.
- #8 and #9 remain open. Additional evaluation results are in the pending [PR #58](https://github.com/zhengads/MoodCut-dsa4213/pull/58); its historical Anna/Elsa results must not be relabeled as S06 or six-story results. Independent human ratings and formal inclusion remain outstanding.

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
- [S01–S12 study design](studies/six-story-clear-emotions-20261024/README.md) contains the original six three-tone scenarios followed by six VEMOCLAP-aligned basic-emotion scenarios.

Maintain current status on this page, operational instructions in the usage guide, shared rules in the contracts and experimental results in their dated records. Task cards describe module responsibilities and remaining work without duplicating trial logs. Do not rewrite existing results, failures or raw data to update the narrative.
