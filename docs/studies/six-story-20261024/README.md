# Follow-up small study: six stories with fixed tone assignments, original

This page preserves the original design record. Current study inputs follow the revised [affectionate / hostile / tense revised design](../six-story-clear-emotions-20261024/README.md). All original JSON inputs in this directory remain unchanged; historical suspicious labels are not renamed tense.

Design and input scope confirmed on 2026-10-24. This planned small study uses **6 stories with one fixed tone each: 2 affectionate, 2 suspicious and 2 hostile**. Each story will compare baseline, generic_review and moodcut, without repeats for now, giving 18 condition entries. Stories, characters and tone assignments are fixed by this design; this round does not add stories or cross every story with every tone. This change only supplies inputs, with 0 new model API calls and zero spending.

Here, a “script” means a complete scene task, character roles and fixed events. The planning Agent will generate the two dialogue lines and shared shot plan, so handwritten dialogue is not presented as method output. The six stories were proposed by the assistant and selected by the project user; they are study inputs authored for this project. Character images come from the existing asset library. The plots are not from the original films or an independent external evaluation dataset.

## Assignment table

| ID | Story | Characters | Target tone | Core events |
|---|---|---|---|---|
| S01 | You waited for me | Anna, Kristoff | affectionate | Ask whether the other person has been waiting; explain staying to leave together |
| S02 | Help with wrapping up | Lucy, Gru | affectionate | Offer help with the remaining cleanup; accept the help |
| S03 | The meeting place changed | Elsa, Mattias | suspicious | Ask where the change notification came from; explain it was received but not verified |
| S04 | How did you know I was here? | Nezha, Aobing | suspicious | Ask how the other person knew the location; answer that it was a guess |
| S05 | Who gets the workbench first? | Maxime, Valentina | hostile | Request priority use; refuse to give up the current turn |
| S06 | Who handles cleanup this time? | Lijing, Taiyi | hostile | Propose a task assignment; refuse and request reassignment |

The design uses **12 distinct characters from 3 films**, with each pair drawn from the same film. FrozenII covers affectionate / suspicious, DespicableMe4 covers affectionate / hostile, and NeZha2 covers suspicious / hostile. Each tone spans two films, so no single film supplies all samples for one tone. This does not remove confounding among story, character, film and tone, or allow independent comparisons of which tone is easier or which film performs better.

## Shared input boundaries

- **Duration and actions:** retain the previously costed five-second, single-shot scope. Both characters are already present at the start. No entrance, scene change, prop handoff or complex action is required. This design adds neither duration nor shots.
- **Dialogue task:** one line per character, two lines total, with a suggested combined length of 16–22 Chinese characters. Names may be omitted; delivery should not rely on rushed speech. This is a design suggestion, not a validated speech limit. Both characters need dialogue for both actors to review.
- **Shared plan:** plan each story once. All three conditions share events, shots, actions, duration, character images, voices and video settings; review may change dialogue only. This design does not prescribe camera movement, expressions or actions enhanced for one condition.
- **Character relationships:** use only the traveling-companion, teammate or collaborator relationships specified here. Appearance and clothing come from the reference images; the original films' marriages, official ranks, factions, magical powers and dialogue are not inherited automatically.
- **No direct label leakage:** story prose does not name the emotion or prescribe delivery such as “say gently” or “ask angrily.” The existing `tone` field supplies the target; characters do not speak the label. Viewer materials continue to hide condition and target tone.
- **Scope:** no continuous plot across stories is required. The design does not evaluate complete short-film narratives or continuity across shots.

If two lines cannot be spoken naturally within five seconds, adjust the common duration and budget using an older development story before freezing these six inputs. Do not inspect new-story condition results and then extend only one version, hand-edit its dialogue or replace a story.

## S01: You waited for me — affectionate

**Characters and setting:** Anna is the traveling companion who speaks first; Kristoff is the companion who has been waiting. In daylight, both are already standing side by side near a station waiting area.

**Fixed plot:** Anna checks whether Kristoff has been waiting for her. Kristoff explains that he stayed so they could leave together. Both remain in place at the end; they have not departed.

**Tasks for the two lines:** Anna asks about the wait; Kristoff explains staying to wait and preparing to leave together. The Agent chooses the wording.

**Tone goal:** everyday language should convey being cared for and accompanied, without restricting affection to romance or a declaration of love. Do not add a reason for lateness, an argument, an embrace, a confession or boarding a vehicle.

## S02: Help with wrapping up — affectionate

**Characters and setting:** Lucy and Gru work together as teammates. In daylight, both are already standing beside a table in an ordinary studio.

**Fixed plot:** Lucy offers to help Gru finish tidying up by the table; Gru accepts. Show only the offer and acceptance; the cleanup need not be completed on screen.

**Tasks for the two lines:** Lucy offers specific help; Gru accepts and responds.

**Tone goal:** practical care and acceptance of help should express affection, distinct from the waiting and companionship in S01. Do not add gifts, injuries, dangerous tasks, family background or a romantic relationship. Carrying boxes and exchanging props are not required.

## S03: The meeting place changed — suspicious

**Characters and setting:** Elsa and Mattias are event collaborators, with no assumed superior–subordinate relationship. In daylight, both have stopped in a corridor outside an event hall.

**Fixed plot:** Elsa asks where the information about the changed meeting place came from. Mattias explains that he only received a notification and has not verified it. Its truth remains unknown.

**Tasks for the two lines:** Elsa asks for the information source; Mattias explains that his information is limited and unverified.

**Tone goal:** probe the reliability of information while keeping suspicion distinct from hostility. Do not establish that anyone is lying or add conspiracies or unseen instigators. Do not show a phone, readable notification or letter.

## S04: How did you know I was here? — suspicious

**Characters and setting:** Nezha and Aobing are companions for this activity. In daylight, both are already standing in an ordinary courtyard; Aobing's entrance is not shown.

**Fixed plot:** Nezha asks how Aobing knew he was in the courtyard; Aobing says it was a guess. The story does not confirm whether the explanation is true. Both remain in place.

**Tasks for the two lines:** Nezha asks how the location was known; Aobing offers a guess as the explanation.

**Tone goal:** information asymmetry and the ambiguity of the answer should convey suspicion, distinct from the notification source in S03. Do not add stalking, eavesdropping, betrayal, mind reading, magic or fighting.

## S05: Who gets the workbench first? — hostile

**Characters and setting:** Maxime and Valentina are studio members; their original film villain identities are not part of the premise. In daylight, both are already beside a shared workbench that Valentina currently occupies.

**Fixed plot:** Maxime asks to use the workbench first, now; Valentina refuses to give up her current turn. The arrangement remains unchanged. Neither uses force or leaves.

**Tasks for the two lines:** Maxime requests priority use; Valentina refuses to yield.

**Tone goal:** express opposition through the demand and refusal, without treating volume, profanity or threats as the only means. Do not add table slamming, pushing, grabbing objects, crime or retaliation.

## S06: Who handles cleanup this time? — hostile

**Characters and setting:** Lijing and Taiyi are fellow participants in an activity, with no assumed official rank or master–disciple authority. In daylight, both are already near the door of an ordinary activity room.

**Fixed plot:** Lijing proposes that Taiyi handle this cleanup. Taiyi refuses and asks to redistribute the work. They have not reached agreement or begun tidying up.

**Tasks for the two lines:** Lijing assigns a specific responsibility; Taiyi refuses and requests reassignment.

**Tone goal:** disagreement over responsibilities should convey opposition, distinct from the resource-use order in S05. Do not invent past debts, punishment or harm, or add drinking, magic, carrying objects or fighting.

## Character asset selection and known limitations

See the original [asset library notes](../../../assets/library/README.md), [character selection manifest](../../../assets/library/movieagent-animation.selection.json) and [complete AssetManifest](../../../assets/library/movieagent-animation.manifest.json). During preparation, all 36 candidate images were viewed locally: three for each of 12 characters. The selection consistently uses the indexed `primary_asset_id`, the original `best.png`. This is a rule fixed in advance, not a claim that the images have neutral expressions or passed video-generation acceptance. Input manifests retain original identities, sources, dimensions, SHA-256 hashes, the `full` framing restriction and rights notes. No images are cropped, retouched or added.

| Story | Reference-image considerations |
|---|---|
| S01 | Anna looks slightly worried; Kristoff has an open mouth and a tabletop background |
| S02 | Lucy holds a cup; Gru has glasses on his head; reproducing these prop actions is not required |
| S03 | Elsa is shown in a bright close-up; Mattias has a pronounced frown |
| S04 | Nezha is smiling; Aobing is posed full-body against a gray background, with different character proportions |
| S05 | Maxime is smiling with a clenched fist; Valentina's glasses obscure her eyes and her mouth is open |
| S06 | Lijing is frowning; Taiyi's original image has lower clarity |

These differences are asset priors that must be disclosed; character expressions are not evidence that the dialogue method works. Fixing the same image within each story controls only the within-story method comparison, not character priors across stories. Apart from the older Anna/Elsa task, provider acceptance, identity and speech performance have not been verified for the new pairings in this design.

To limit obvious emotional answer cues, this round excludes the personified emotions from InsideOut2. Minions are also excluded from these tasks using standard Mandarin dialogue. Keep 12 distinct characters, prioritizing each scene's ability to support the same type of natural two-person exchange.

Existing asset rights remain `unconfirmed`. This design preserves the original statements and creates no new image uploads or public redistribution.

## Local inputs and subsequent use

- [design.json](design.json): the six stories, assignments, character roles, prohibited additions and limitations; **not** an execution configuration.
- [inputs/index.json](inputs/index.json): paths and file hashes for six `scene.json` / `assets.json` pairs; indexes local inputs only.
- `inputs/<story-id>/scene.json`: the existing 1.1/generated scene format, with explicit five-second, single-shot boundaries and a project-authored provenance statement.
- `inputs/<story-id>/assets.json`: the two character-image entries copied verbatim from the existing library, with character IDs matching the scene; no rewrite of the full library manifest is needed.

This directory's `.gitattributes` fixes JSON line endings to LF, keeping byte hashes consistent across Windows and Linux checkouts. The index checks actual file bytes without silently normalizing content.

The planning Agent will only need the corresponding `scene.json` and `assets.json`. The `design_question`, asset observations and method-comparison explanations remain in the design document; they are not injected into one review branch. There are no pregenerated dialogue lines, shared plans, actor opinions, video requests or ratings here.

Local checks use the existing `moodcut.validation.validate_scene(..., output_mode="generated")` to validate structure and local images. They also check six unique stories, two per tone, 12 unique characters, input file hashes and the arithmetic of 18 condition entries. These checks do not call the planner, create API clients, compile video requests or access the network. Structural acceptance does not establish plot quality, speech-duration feasibility or video quality.

Before execution, determine the method version, models / duration and budget, viewer assignment, and handling of failed and unchanged samples. Actor revised belongs to the separate [PR #48](https://github.com/zhengads/MoodCut-dsa4213/pull/48). This input change does not depend on that implementation being merged, nor may historical original videos be treated as revised results. The six-story input scope is confirmed with `input_scope_approved=true`; this does not authorize model calls or formally include results that do not yet exist. Accordingly, `execution_enabled`, `paid_run_authorized` and `formal_inclusion_approved` remain `false`.

If input errors or common-duration feasibility require a revision before paid execution, retain the version, reason and original inputs, and recalculate index hashes. After paid execution begins, do not replace stories, characters or tones based on which method wins. Main results should cover every planned entry and report failures, unchanged outputs, reuse and missing ratings separately. The jointly evaluable subset cannot represent all attempts.

## Costs and interpretation

Using the historical bill of $0.25 per five-second video, a scenario with all 18 entries newly generated would cost **$4.50** for video. This excludes text, failures, recovery, price changes and longer durations. Neither a live quote nor an approved batch budget has been set. Identical requests within a block may reuse media under the original rules, but potential savings are not deducted from the budget in advance. New spending for this input change is **$0**.

One tone per story reduces generation volume but supports comparison of the three methods only on these fixed inputs. Six stories are six scene units; 18 entries are not 18 independent stories. Story, character and tone effects cannot be separated. Retain the existing independent human measures of tone recognition, naturalness, story clarity and overstatement. Do not add scoring criteria or replace tasks based on which condition wins.
