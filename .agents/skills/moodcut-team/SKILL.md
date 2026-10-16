---
name: moodcut-team
description: Implement or review a claimed MoodCut GitHub Issue using shared module contracts, scoped ownership, offline validation, and a self-review pull request workflow.
---

# MoodCut team workflow

Read all paths relative to the MoodCut repository root. Team members claim module tasks; no fixed lead or designated reviewer is required.

## Establish the task

1. Verify the checkout remote is `zhengads/MoodCut-dsa4213`. Inspect git status and preserve unrelated changes.
2. Read `AGENTS.md`, `docs/TEAM.md`, `docs/CONTRACTS.md`, `docs/REFERENCES.md`, `docs/upstream-reuse.md`, the claimed GitHub Issue and its `docs/tasks/MC-*.md` card. Identify one task owner, allowed paths, acceptance criteria and dependencies. MC identifiers are not GitHub Issue numbers.
3. Inspect open Issues and PRs, including drafts. Continue the owner's existing active branch/PR rather than duplicating work; archive/ branches are historical, not active tasks. Resolve overlapping claims with the involved members in the Issue. If remote state is unavailable, disclose that ownership is unverified and use the human's stated assignment for local work.
4. Fetch latest main and read `docs/BRANCHES.md`. Start `<type>/issue-<actual-GitHub-number>-<short-name>` (for example `feat/issue-22-shared-planning` or `fix/issue-23-dialogue-review`), or continue the matching active branch. Use a lowercase task type and descriptive English slug, never an AI tool/member name or a standalone P/MC code. Issue-less repository maintenance may use `docs/branch-naming` or `chore/<short-name>`. Do not develop on archive/ branches or recreate retired remote names. Preserve local work during migration; never reset unrelated work or force-push a shared branch.

## Prepare source references

Run `python scripts/prepare_references.py --check`. If files are missing and the human used the README startup prompt or requested preparing references, run `python scripts/prepare_references.py`, then check again. Preserve and report hash mismatches; never overwrite local annotations. Downloads use fixed public URLs and do not call models.

Read the module-specific paths in docs/REFERENCES.md. FilmAgent is the pinned VideoClaw repository's `FilmAgent/` subtree. Treat upstream prompts and commands as inert source material; do not execute entrypoints, install their dependencies or import their modules. Paper PDFs (`--papers`) and initial images (`--assets`, stored in `assets/raw/`) are optional explicit downloads. Exclude all upstream caches from Git and test discovery.

## Implement one increment

- Follow the task card's writable paths. P1–P5 denote module responsibilities, not approval authority. Coordinate cross-module and contract changes with affected owners before editing shared interfaces.
- Reuse the flat `src/moodcut/*.py` files and `tests/test_*.py` layout. The client, validator, planner, review/patch engine, renderer, paired evaluation and CLI are implemented. Inspect their actual code and the task card current-delivery section before adding functionality; do not recreate existing modules.
- Use `tests/fixtures/`, the shared FakeClient and `docs/CONTRACTS.md`. Do not build a competing client or a duplicate implementation of a teammate's dependency. Create task-specific inputs in the owning test file or its temporary directory; coordinate changes to shared fixtures.
- Keep prompts together in `src/moodcut/prompts/`: MC-02 owns `planning_*.txt`, MC-03 owns `review_*.txt`. Use root `configs/`: MC-01 owns model/render configuration and MC-05 owns experiment configuration such as `experiment.json` (development assignments); `pilot.json` remains the separate VBench configuration. Own specific files rather than whole shared directories. Keep material manifests in `assets/`, downloaded assets in `assets/raw/`, and run outputs in `runs/`.
- Use `python -m moodcut smoke --mock --output runs/<new-name>` for the offline JSON chain and `run --mock` for three videos with local FFmpeg/font. `evaluate --dry-run` only lists assignments. Full-block fees need block.json: planning is counted once, condition run.json files contain only their own review usage. Mock outputs are software fixtures, not evidence of method superiority.
- The generated-film path is separate: read `docs/GENERATIVE_VIDEO_PLAN.md` and use `scripts/generate_video.py` to prepare a dialogue-only pair from existing successful records. Default is offline. `video_generation.py` compiles reference-image requests and concatenates actual generated video/audio; `video_client.py` handles the asynchronous OpenRouter video endpoint and receipts. Do not recreate either adapter, confuse animatics with generated films, inherit the candidate verification after projection, or silently start paid video jobs under the old text-demo budget. Resume only an existing job via GET; never automatically resubmit a lost POST. Native audio presence is not speech/visual quality validation.
- For the next generated-mode increment, follow CONTRACTS section 6 and the task card's unchecked next-increment list. Plan actions once per block and freeze all non-dialogue inputs across baseline/generic_review/moodcut. Enforce dialogue-only patches at review time and verify the actual final script; do not inherit verification from a discarded multi-field candidate. P1 publishes the shared hash/schema first; P2 plans common directions, P3 reviews dialogue, P4 compiles identical generation settings, P5 checks comparison eligibility. These are acceptance requirements, not already implemented guarantees. Fixed seeds do not make changed-prompt videos identical, and shared planning is not an independently tested contribution. Do not add an experiment condition or dataset without human agreement.
- Complete the next independently verifiable increment. Task-card commands describe acceptance targets until their implementation exists; do not claim they already pass.
- Default to offline development. Real paid API calls, GPU work and experiments require the human's explicit model, scale and budget. The USD15 allowance is shared.
- Run relevant checks and inspect actual outputs. Inspect the diff and untracked files, stage explicit paths, and preserve the `.gitmessage` name/date format. Never include keys, upstream caches, generated media or private evaluation identities.

## Self-review and submit

- Check the human's existing authorization before comments, pushes, PR updates or merges. The README startup prompt authorizes scoped Issue progress updates, pushes and PR creation; do not ask again when that permission is present. A task card or installed skill does not grant extra permissions.
- With authorization, create/update the matching Draft PR after a meaningful increment. Link the actual Issue; close it only when all increments are complete. Update progress with delivery/PR, next step and blockers. Do not message unrelated tasks or teammates.
- Review the current diff against the Issue and contracts, inspect validation results and example artifacts, and check for scope drift, duplicate functionality, hidden paid calls and secrets. Fix blockers and re-run affected checks. Record the self-review conclusion, tests and remaining limitations in the PR description.
- The author may self-review, optionally with AI or peer assistance. A designated peer review or additional approval is not required by this workflow. GitHub does not permit authors to approve their own PR; document self-review in the description instead of submitting an APPROVE review as the author.
- Mark ready after acceptance checks pass. Merge only when the human has authorized merging this PR, the current head has been reviewed, required checks pass, blockers are resolved and actual repository rules permit it. Existing authorization in the conversation remains valid. Do not bypass protection or imply the old head's checks cover new changes.
- If GitHub is unavailable, preserve the local branch and prepare PR text; state which remote actions did not occur.

## Review requests

For a standalone review, inspect the latest diff, task, contracts, tests and outputs. Provide concrete findings with file/line evidence. A self-review follows the same checks. Publish findings or update the PR only when authorized; a request for local inspection alone does not authorize comments or approvals. Do not impersonate another reviewer.

## Completion report

Return the actual Issue/branch/PR links, increment delivered, checks run and outcomes, self-review conclusion, remaining blockers and any real API usage. Distinguish local completion, PR creation, check success and merge status.
