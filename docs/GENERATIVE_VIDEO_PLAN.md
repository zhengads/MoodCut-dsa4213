# Reference-guided video implementation plan

> Historical offline adapter increment (merged in PR #21). For agentic workers: execute this plan sequentially using the existing executing-plans workflow and repository PR rules. Offline implementation is authorized; paid generation needs a separately accepted model, scale and budget.

**Goal:** Produce short generated scenes with character-reference images and native audio, comparing original dialogue with dialogue-only revisions.

**Architecture:** Keep the existing planning/review records and static renderer as development tools. Compile a separate development video bundle from a shared initial plan, projecting revisions onto dialogue only. Send reference images and explicit scene/action/dialogue instructions to OpenRouter's asynchronous video API, download actual model outputs, then concatenate their video and audio tracks.

**Tech stack:** Python 3.11 standard library, existing MoodCut validators and JSON helpers, FFmpeg/ffprobe, OpenRouter video API.

**Spec:** The requirements and acceptance criteria below are the specification for this increment.

## Requirements and constraints

- Review changes dialogue only; story events, character references, scene directions, durations, seeds and generation settings are shared across the pair.
- Character images are identity references (`input_references`), never a pre-rendered card or an enforced first frame (`frame_images`).
- The development example has three generated six-second clips per condition: 18 seconds per film. Original 60-second plans and formal experiment assignments are preserved. This is a new development presentation, not a retroactive change to prior results.
- Native generated audio is requested and an audio stream is required. Audio presence does not prove correct Chinese speech, speaker assignment, lip synchronization or voice consistency; these require listening and visual inspection.
- Candidate non-dialogue changes are excluded and listed explicitly. The projected script is a derived development input and does not inherit the original verification result.
- No new dataset, automatic subjective scores, formal experiment, GPU work or paid calls in this increment.
- All conditions use the same generation backend/settings. A fixed seed reduces one source of variation but does not guarantee identical visuals across changed prompts.
- Current candidate: `alibaba/wan-2.7`, 720p, 16:9, native audio, $0.10 per output second according to official discovery on 2026-10-15. Six six-second jobs estimate $3.60; this is a quote, not permission or a platform hard cap.
- Before paid submission, refresh the public model catalogue and reject unsupported parameters or a higher advertised rate. Preserve unknown charges and stop later submissions; never retry POST automatically.
- API keys remain in process environment. Receipts omit keys, signed download URLs and raw provider error bodies. Outputs are exclusive new directories under `runs/`.
- Use the existing flat package/tests layout and existing validation/JSON/error utilities. The existing text client remains the shared planning/review client; the video transport handles a distinct asynchronous endpoint.

## Task 1: Compile a dialogue-only, reference-guided pair

Files: create `src/moodcut/video_generation.py`, `configs/video.json`, `tests/test_video_generation.py`.

Interface:

```python
def build_video_bundle(scene: dict, initial: dict, revised: dict,
                       manifest: dict, config: dict, *, project_root: str) -> dict: ...
```

- [x] Add the following contract test and run it before implementation:

```python
def test_requests_use_references_and_dialogue_only(bundle):
    before, after = bundle["conditions"]
    for original, edited in zip(before["jobs"], after["jobs"]):
        assert "frame_images" not in original["request"]
        assert len(original["request"]["input_references"]) == 2
        assert original["request"]["generate_audio"] is True
        assert original["request"]["seed"] == edited["request"]["seed"]
        assert original["direction"] == edited["direction"]
    assert bundle["duration_s_per_condition"] == 18
    assert bundle["estimated_cost_usd"] == "3.60"
```

- [x] Implement source validation using `validate_plan`, exact scene/shot matching, frozen non-dialogue fields, explicit changed/discarded-field records and SHA-256 identities. Build each prompt from shared style, character/reference mapping, direction and that condition's dialogue; exclude narration and review labels. Reject invalid durations, unknown speakers, non-public reference URLs and dialogue too long for the clip (conservative character limit, not a speech-duration guarantee).
- [x] Run `python -m pytest tests/test_video_generation.py -q`; cover reordered/missing shots, unknown IDs, non-dialogue edits, source immutability, reference metadata and failed validation.

## Task 2: Submit, poll, resume and download without duplicate charges

Files: create `src/moodcut/video_client.py`, `tests/test_video_client.py`.

Interfaces:

```python
def fetch_video_models() -> list[dict]: ...
def check_video_model(config: dict, models: list[dict]) -> None: ...

class OpenRouterVideoClient:
    def generate(self, request: dict, *, out_dir: str) -> dict: ...
    def resume(self, out_dir: str) -> dict: ...
```

- [x] Add mocked HTTP tests before implementation: unauthorized submission sends zero requests; a six-second request reserves $0.60; failed/unknown POST is never repeated; unknown usage blocks later generation; terminal failure remains failure; a saved job can be polled/downloaded without POST; credentials cannot follow a cross-origin redirect.
- [x] Persist a submitting receipt before POST and the returned job ID before polling. Poll GET with bounded waits and timeout. A timeout means the remote job may still run and charge; retain job ID for resume. Download through the constructed OpenRouter content endpoint, stripping credentials on external redirects. Reject missing video bytes, malformed job IDs and non-finite/negative charges.
- [x] Run `python -m pytest tests/test_video_client.py -q` with HTTP fixtures only.

## Task 3: Command, media validation and operator documentation

Files: create `scripts/generate_video.py`; update `src/moodcut/video_generation.py`, `tests/test_video_generation.py`, `README.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/TEAM.md`, `docs/tasks/MC-04-rendering.md`, `docs/CONTRACTS.md` and `.agents/skills/moodcut-team/SKILL.md`.

Interfaces:

```python
def assemble_generated_clips(paths: list[str], *, durations: list[int],
                             out_path: str) -> dict: ...
```

- [x] Default command prepares and saves a bundle and exact estimate offline, requiring no key. Paid mode additionally requires `--allow-paid --max-cost-usd`, a live catalogue preflight, key and FFmpeg/ffprobe before submission. Resume operates on one saved job and never submits a replacement.
- [x] Require actual video and audio streams and duration agreement for each downloaded clip. Concatenate generated tracks with FFmpeg; never synthesize a still-frame fallback or silently replace missing audio. Save per-job receipts and pair summary; pending/failed jobs cannot produce a successful condition.
- [x] Add a local FFmpeg test using explicitly synthetic moving test sources and sine audio; verify both tracks, duration and missing-audio rejection. These files are transport fixtures, not a model-generated demonstration.
- [x] Run focused tests, the full suite, offline reference checking and a request preview from the existing real planning/review artifacts. Confirm no POST, no key and no paid usage in all offline checks.
- [x] Inspect the diff, update progress checkboxes and prepare a self-reviewed PR. Do not merge without authorization. Actual output quality and native Chinese dialogue remain unverified until a separately authorized paid pilot.

## Official references

- https://openrouter.ai/docs/guides/overview/multimodal/video-generation
- https://openrouter.ai/docs/cookbook/video-generation/reference-to-video
- https://openrouter.ai/api/v1/videos/models
- https://openrouter.ai/alibaba/wan-2.7

These describe service contracts, not independent evidence of MoodCut's effectiveness.

## Offline execution evidence

2026-10-15: 277 tests and 67 subtests passed using the dsa4213 virtual environment. Thirty focused tests cover request compilation, mocked asynchronous transport, timeout/resume, cost handling, CLI defaults, source hash checks and synthetic moving-video/audio concatenation. The real source-record preview has three clips per version, 18 seconds per version, two dialogue changes and one excluded narration change; five unique request fingerprints among six clip slots. Public catalogue preflight passed for Wan 2.7 at $0.10/second. No video generation POST was sent. Synthetic media are software fixtures; model output and speech quality remain unverified.

## Follow-up integration (not implemented by this plan)

The checked items above describe the offline development-pair adapter, not completion of the generated three-condition system. Follow CONTRACTS section 6 and the next-increment sections of MC-01–MC-05. P1 publishes mode/schema/hash/record contracts; P2 plans one shared action sequence; P3 enforces dialogue-only revision before verification; P4 consumes shared directions and supplies inspection materials; P5 adapts generation records to existing blind export and statistics.

Actions, camera, duration, references, voice requirements, model/settings and seeds are frozen across conditions. Only dialogue changes. Shared planning is infrastructure, not a separately established contribution; fixed seeds cannot hold generated performance identical after dialogue changes. Do not add ablation arms or formal samples without team confirmation.

2026-10-16 status: one Wan six-second submission failed with no video. The provider reported suspected IP infringement; the individual charge is unknown. Seedance has offline compatibility only. No successful native speech/identity/visual-quality acceptance exists. The current scope is offline development and Issue maintenance; no paid calls, retries, VBench/GPU or formal runs are authorized.
