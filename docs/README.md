# MoodCut documentation

[Project overview](../README.md) · [Watch the twelve stories](https://zhengads.github.io/MoodCut-dsa4213/) · [Script catalog](studies/six-story-clear-emotions-20261024/README.md)

| Task | Guide |
| --- | --- |
| Install, prepare scripts and generate videos | [Usage](usage.md) |
| Understand the three-condition comparison | [Actor review method](ACTOR_REVIEW_METHOD.md) |
| Inspect data structures, identities and accounting | [Contracts](CONTRACTS.md) |
| Validate reports and dialogue patches | [Review implementation](review.md) |
| Compile requests and inspect videos | [Rendering](rendering.md) |
| Export blind comparisons and collect human ratings | [Evaluation](evaluation.md) |
| Run video scoring tools | [VEMOCLAP](vemoclap.md) · [VBench](vbench.md) |
| Find character references and attribution | [Asset library](../assets/library/README.md) |
| Contribute changes | [Team workflow](TEAM.md) · [Branch rules](BRANCHES.md) |
| Read research sources | [References](REFERENCES.md) · [Reuse notes](upstream-reuse.md) |

The current release contains 12 stories numbered 01–12, with 36 condition entries and 28 distinct video files. The [release index](studies/six-story-clear-emotions-20261024/release-index.json) records their filenames and hashes. Final dialogue transcripts and frozen script blocks are not supplied in the ZIP; independent human evaluation remains pending.

Historical inputs, failures and measurements remain in [trial records](pilots/README.md), [evaluation records](studies/emotion-evaluation-20261027/EMOTION_EVALUATION_RECORD.md) and [implementation history](history/README.md). They are not evaluations of the current release. Superseded video releases have been withdrawn.

Current code uses functional protocol names. The historical alias table supports reading saved records without rewriting their identities or prompt hashes.
