# Twelve clear-emotion scenarios: S01–S12

Revised on 2026-10-24 to meet the updated script requirements. Current inputs use **two stories each for affectionate, hostile and tense**: six stories, 12 distinct characters, one tone per story, three conditions and one replicate, totaling 18 condition entries. The five-second, single-shot scope with one line per character remains unchanged.

S01–S06 retain this v2 design. Added on 2026-10-27, S07–S12 extend the same page with one scenario for each VEMOCLAP basic emotion: anger, disgust, fear, joy, sadness and surprise. The supplementary design, generated-mode JSON inputs, asset manifests, hash-bound index and offline evaluation configuration are included; videos, model outputs and evaluation results are not.

The original [v1 scripts](../six-story-20261024/README.md) and all their JSON inputs are preserved. This is a task revision before execution because the original everyday scenarios did not express the target emotions clearly enough, not a task replacement based on results from these six stories. The original input merge commit is `dff08742caf662cba81f1853cfbfd184d92ee84c`.

## Distinguishing the three tones

| Current tone | Input label | Scenario focus | Distinct from |
|---|---|---|---|
| Affectionate | affectionate | Explicit mutual longing, attachment and companionship; both pairs in this version are adult partners | Routine work assistance or polite greetings |
| Hostile | hostile | Explicitly conflicting positions, accusations, refusal to cooperate or refusal to yield | Shared pressure from external danger |
| Tense | tense | Trusted companions facing unknown danger or an approaching deadline together | Suspicion of the other person's honesty, identity or motives |

`tense` is a new, separate label. The system still accepts legacy `suspicious` to read older stories and ratings; historical suspicion is never renamed tension. This version selects only the three categories above. The current viewer questionnaire should use these three plus “uncertain.” The rating parser retains the older category for compatibility, not to require an additional tone in this round.

## Six plots

| ID | Script | Characters | Tone | Fixed exchange |
|---|---|---|---|---|
| S01 | Reunion after time apart | Anna, Kristoff | affectionate | Anna expresses missing him; Kristoff reciprocates and offers to stay with her |
| S02 | Company when feeling low | Lucy, Gru | affectionate | Lucy asks him to stay; Gru agrees and expresses support |
| S03 | Footsteps outside the door | Elsa, Mattias | tense | Elsa asks for quiet; Mattias replies that the footsteps have not moved away |
| S04 | The exit is about to close | Nezha, Aobing | tense | Nezha warns that little time remains; Aobing urges them to leave immediately |
| S05 | A broken collaboration | Maxime, Valentina | hostile | Maxime accuses her of breaking an agreement; Valentina refuses to apologize and ends the collaboration |
| S06 | Competing for the last place | Lijing, Taiyi | hostile | Lijing demands that Taiyi withdraw; Taiyi explicitly refuses to yield |

### S01: Reunion after time apart — affectionate

**Relationship and starting point:** Anna and Kristoff are adult partners who care about each other and have just reunited after time apart. At the start, they are already facing each other in a quiet entrance hall.

**Fixed plot:** Anna says she missed him during their separation. Kristoff reciprocates and offers to stay with her. The affection must be mutual.

**Dialogue task:** one line expresses longing; the other reciprocates and offers companionship. The planning Agent generates the actual wording; this document supplies no dialogue answers.

**Boundaries:** do not invent reasons for the separation, third parties, disappearances, illness or injury. Do not require kissing, hugging, walking or giving gifts. Make the relationship and exchange clear rather than reducing affection to polite small talk.

### S02: Company when feeling low — affectionate

**Relationship and starting point:** Lucy and Gru are adult partners who trust each other, already seated side by side in a living room. Lucy feels low; the reason is unspecified.

**Fixed plot:** Lucy asks Gru to stay with her. Gru agrees and expresses support. Their relationship allows her to express a need and receive an explicit response.

**Dialogue task:** one line asks for companionship; the other acknowledges the need and offers support.

**Boundaries:** do not add illness, unemployment, loss or betrayal, or make a psychological diagnosis. Do not require crying, physical contact or handing over objects. This differs from the work cleanup help in v1.

### S03: Footsteps outside the door — tense

**Relationship and starting point:** Elsa and Mattias trust each other and are temporarily sheltering from an unidentified danger outside. Both are already inside a closed door; ambient footsteps remain audible outside.

**Fixed plot:** Elsa reminds Mattias to stay quiet. Mattias replies that the footsteps have not moved away and they must wait. Neither the source of the danger nor whether it has passed is revealed.

**Dialogue task:** one line requests quiet under danger; the other indicates they cannot relax yet. Restraint and vigilance are allowed, but the companion must not become a suspect.

**Boundaries:** the door stays closed. No third person appears on screen, and no additional speaker, weapon or attack is added. Footsteps are an explicitly shared environmental sound in this story; do not add scares or sound effects to only one review condition.

### S04: The exit is about to close — tense

**Relationship and starting point:** Nezha and Aobing are trusted companions who need to leave a passage together. They are already standing just inside an exit that is about to close; little time remains.

**Fixed plot:** Nezha warns of the approaching deadline; Aobing urges them both to leave immediately. The shot ends as they prepare to act; whether they escape remains unknown.

**Dialogue task:** one line communicates time pressure; the other urges immediate action, creating urgency.

**Boundaries:** do not blame either person for the delay or add pursuers, villains, announcements, injuries or countdown text. Do not show sprinting, jumping, magic, the door closing or the outcome of the escape.

### S05: A broken collaboration — hostile

**Relationship and starting point:** Maxime and Valentina's collaboration has broken down. Both are already facing each other beside a table in an ordinary meeting room.

**Fixed plot:** Maxime directly accuses Valentina of breaking an agreement. Valentina refuses to apologize and explicitly ends the collaboration. They occupy opposing positions rather than jointly investigating an external problem.

**Dialogue task:** one line makes a direct accusation; the other refuses and cuts off collaboration.

**Boundaries:** an accusation is not an established fact. Do not invent specific breaches, crimes, evidence of betrayal or retaliation. No insults, threats, table slamming, pushing or leaving. Hostility comes from explicit opposition and refusal.

### S06: Competing for the last place — hostile

**Relationship and starting point:** Lijing and Taiyi are competing for the last place in the same activity, with directly conflicting goals. At the start, they are already facing each other outside the registration desk.

**Fixed plot:** Lijing demands that Taiyi withdraw; Taiyi explicitly refuses and says he will not yield. Who gets the place remains unresolved.

**Dialogue task:** one line demands that the competitor give up; the other explicitly refuses to yield.

**Boundaries:** do not introduce official ranks, master–disciple authority, a judge, lists, punishment or deception. Do not show force, magic or the competition outcome. Unlike S04, their goals obstruct each other here; in S04 they face a deadline together.

## S07–S12: VEMOCLAP basic-emotion scenarios


Prepared as a supplementary six-story set using the existing S01–S06 character pairs. The current design uses **one story for each of the six VEMOCLAP basic emotions**: six stories, 12 reused characters, one target emotion per story, three conditions and one planned replicate, totaling 18 condition entries.

The five-second, single-shot scope with one line per character remains unchanged.

S01–S06 remain unchanged. S07–S12 extend the evaluation to the six original VEMOCLAP emotion categories rather than replacing or retrospectively relabelling the original three-tone scenarios.

### Distinguishing the six emotions

| Target emotion | Input label | Scenario focus | Distinct from |
|---|---|---|---|
| Anger | anger | Explicit anger or outrage directed at another person's actions | Hostility based only on conflicting positions |
| Disgust | disgust | Strong revulsion toward an unpleasant substance or smell | Fear of danger or interpersonal anger |
| Fear | fear | Explicit apprehension about a potentially dangerous unknown threat | Vigilance or urgency without expressed fear |
| Joy | joy | Shared happiness following positive news | Romantic affection or unexpected discovery |
| Sadness | sadness | Emotional distress following a meaningful personal loss | A general request for companionship |
| Surprise | surprise | Immediate disbelief at an unexpected result | Happiness, fear or time pressure |

These six labels are distinct from the `affectionate`, `hostile` and `tense` labels used by S01–S06. The two label systems must remain separate in input validation, human questionnaires and result reporting.

### Six plots

| ID | Script | Characters | Emotion | Fixed exchange |
|---|---|---|---|---|
| S07 | Another broken promise | Maxime, Valentina | anger | Maxime angrily confronts Valentina about another broken promise; Valentina defends herself |
| S08 | The foul-smelling medicine | Lijing, Taiyi | disgust | Lijing expresses disgust at Taiyi's foul-smelling medicine; Taiyi acknowledges its unpleasant smell |
| S09 | Something in the forest | Elsa, Mattias | fear | Elsa admits she is frightened by an unknown approaching creature; Mattias shares her fear |
| S10 | The celebration is saved | Anna, Kristoff | joy | Anna announces that their anticipated celebration can proceed; Kristoff shares her happiness |
| S11 | An irreplaceable keepsake | Lucy, Gru | sadness | Lucy expresses sadness over a treasured object that cannot be repaired; Gru comforts her |
| S12 | An unexpectedly finished task | Nezha, Aobing | surprise | Nezha expresses disbelief that Aobing has already completed a difficult task; Aobing confirms it |

#### S07: Another broken promise — anger

**Relationship and starting point:** Maxime and Valentina are former collaborators whose relationship has become strained. Both are already facing each other beside a table in an ordinary meeting room. Maxime has just learned that Valentina has failed to keep another promise.

**Fixed plot:** Maxime angrily confronts Valentina about repeatedly breaking her promises. Valentina responds defensively and does not accept his criticism. Their disagreement remains unresolved.

**Dialogue task:** one line explicitly communicates Maxime's anger over the repeated broken promise; the other defends Valentina's position without resolving the disagreement. The planning Agent generates the actual wording; this document supplies no dialogue answers.

**Boundaries:** do not invent the specific promise, misconduct, crimes, evidence of betrayal or retaliation. Do not introduce additional characters. No insults, threats, shouting requirements, table slamming, pushing or leaving. Unlike S05, the target is an explicit expression of anger rather than the termination of a collaboration.

#### S08: The foul-smelling medicine — disgust

**Relationship and starting point:** Lijing and Taiyi know each other and are already standing beside a table in a quiet room. Taiyi has brought a small bottle of medicinal liquid that smells extremely unpleasant. The bottle is already on the table, and its smell is noticeable.

**Fixed plot:** Lijing reacts with strong disgust to the medicine's smell. Taiyi acknowledges that the smell is unpleasant. Neither character drinks the medicine or removes the bottle.

**Dialogue task:** one line expresses Lijing's revulsion toward the medicine; the other acknowledges the unpleasant smell. The planning Agent generates the actual wording; this document supplies no dialogue answers.

**Boundaries:** do not introduce illness, poisoning, magical accidents, transformations, additional characters or unexpected side effects. No vomiting, exaggerated gagging, spellcasting, throwing objects or leaving. The bottle remains stationary. The emotional focus is disgust rather than fear or hostility.

#### S09: Something in the forest — fear

**Relationship and starting point:** Elsa and Mattias are trusted companions standing together on a quiet forest path. They have noticed signs of an unidentified creature approaching from behind nearby trees. Neither knows whether it is dangerous. Both are already facing the direction of the possible threat.

**Fixed plot:** Elsa admits that she is frightened by the approaching creature. Mattias acknowledges the danger and admits that he is frightened too. The creature remains unseen, and the encounter is unresolved.

**Dialogue task:** one line explicitly expresses Elsa's fear of the unknown creature; the other acknowledges Mattias's own fear and the uncertainty of the situation. The planning Agent generates the actual wording; this document supplies no dialogue answers.

**Boundaries:** do not reveal the creature or introduce additional visible characters, weapons, attacks, injuries or escape outcomes. No screaming, running, exaggerated trembling, magic or jump scares. Do not add frightening sound effects to only one experimental condition. Unlike S03, the target is openly acknowledged fear rather than quiet vigilance.

#### S10: The celebration is saved — joy

**Relationship and starting point:** Anna and Kristoff are adult partners standing together in a quiet entrance hall. They have been looking forward to a celebration, but its arrangements were previously uncertain. Anna has just received confirmation that it can proceed.

**Fixed plot:** Anna happily announces that the celebration will take place after all. Kristoff responds with genuine happiness and shares her excitement. The celebration has not yet begun.

**Dialogue task:** one line expresses Anna's joy and relief about the positive news; the other reciprocates her happiness. The planning Agent generates the actual wording; this document supplies no dialogue answers.

**Boundaries:** do not introduce new characters, gifts, proposals, weddings, surprise guests or additional plot developments. No hugging, kissing, dancing, jumping, singing or celebratory sound effects. Unlike S01, the emotional focus is happiness about a positive outcome rather than romantic longing.

#### S11: An irreplaceable keepsake — sadness

**Relationship and starting point:** Lucy and Gru are adult partners already seated side by side in their living room. Lucy has learned that a treasured keepsake from her past is damaged beyond repair. The object is resting on a nearby table.

**Fixed plot:** Lucy expresses sadness about losing something personally meaningful. Gru acknowledges her disappointment and offers comfort. The object remains damaged, and no solution is found.

**Dialogue task:** one line communicates Lucy's sadness over the irreplaceable keepsake; the other acknowledges her feelings and offers reassurance. The planning Agent generates the actual wording; this document supplies no dialogue answers.

**Boundaries:** do not invent the keepsake's origin, a deceased owner, an accident, betrayal, financial hardship or additional consequences. No crying requirement, physical contact, object repair or leaving. Unlike S02, the emotional focus is sadness about a specific loss rather than requesting companionship.

#### S12: An unexpectedly finished task — surprise

**Relationship and starting point:** Nezha and Aobing are trusted companions already standing together beside a table in a quiet room. Aobing was working on a difficult task that Nezha expected would take much longer to complete. Nezha has just discovered that the task is finished.

**Fixed plot:** Nezha expresses disbelief that Aobing has already completed the task. Aobing confirms that it is finished. Nezha remains surprised by the unexpected result.

**Dialogue task:** one line communicates Nezha's immediate surprise and disbelief at the unusually quick completion; the other confirms the result. The planning Agent generates the actual wording; this document supplies no dialogue answers.

**Boundaries:** do not invent a specific task, magical powers, secret assistance, competitions, rewards or additional characters. No demonstrations, exaggerated physical reactions, jumping or confrontation. The completed result is established before the dialogue begins. Unlike S04, the emotional focus is an unexpected result rather than urgency.


## Inputs and execution scope

- [design.json](design.json): version, definitions of the three tones, six stories, roles and plot boundaries; not an execution configuration.
- [inputs/index.json](inputs/index.json): paths, labels and byte hashes for six scene / asset pairs; `selected_tones` is exactly affectionate, hostile and tense.
- Each story's `scene.json` uses the existing 1.1/generated format. Its `assets.json` still copies the metadata for the corresponding two original character images verbatim from v1. The 12 characters are distinct; no new image selection is made.
- `.gitattributes` fixes JSON line endings to LF so index hashes remain stable across Windows and Linux checkouts.

The three conditions share one initial plan per story, all plot requirements and all non-dialogue requirements. Only dialogue may be revised. Relationships, footsteps, deadlines, actions, expression requirements, shots, durations, reference images and voice settings must not be enhanced separately for one method. Label support extends only structural validation and rating parsing. It does not change planning / actor / writer prompts or supply Agent responses or ratings.

Five seconds for two lines, with a suggested combined length of 16–22 Chinese characters, is an unverified design constraint; natural speech delivery has not passed acceptance.

## Materials and interpretation limits

Character images still come from the [existing asset library](../../../assets/library/README.md), preserving the 12 original v1 images, sources, hashes, framing and `rights_status=unconfirmed`. Existing expression, glasses occlusion, framing and clarity limitations remain. Images are not reselected to match the target emotion more closely, and provider acceptance of the new pairs is not verified here.

This version makes scenario meanings clearer as requested. Relationships and background themselves may reveal the answer, making the target easy for every method and reducing the visible gain from review. Tone recognition for the full video must not be attributed entirely to dialogue revision. Story, character and tone remain confounded across the six stories. Comparisons apply only to methods on these inputs with shared initial plans; character or tone effects cannot be estimated independently. Six stories remain six scene units.

Scoring retains tone recognition, naturalness, story clarity, overstatement, uncertain counted as a miss, equal clip weighting and coverage of all failures. The parser adds tense rows and columns to the confusion matrix without rewriting legacy suspicious labels or scores. Do not replace tasks after seeing which method wins or extend duration for only one method.

## S07–S12 study controls and evaluation

The committed data files are [the S07–S12 design](design-basic-emotions.json),
[its hash-bound input index](inputs/basic-emotions-index.json), and the six
scene/asset pairs listed by that index. The offline assignment configuration is
[configs/basic-emotions-experiment.json](../../../configs/basic-emotions-experiment.json).

### Character-pair and asset reuse

| New scenario | Original scenario | Reused characters |
|---|---|---|
| S07 | S05 | Maxime, Valentina |
| S08 | S06 | Lijing, Taiyi |
| S09 | S03 | Elsa, Mattias |
| S10 | S01 | Anna, Kristoff |
| S11 | S02 | Lucy, Gru |
| S12 | S04 | Nezha, Aobing |

All 12 characters are reused exactly once across S07–S12. No new reference-image selection is intended.

### Experimental controls

The three conditions share one initial plan per story, all fixed plot requirements and all non-dialogue constraints.

Only dialogue may be revised. Character relationships, actions, expression requirements, camera framing, shot count, duration, reference images, voice settings, environmental sounds and generation parameters must not be enhanced separately for one method.

The intended scope remains five seconds, one shot and one spoken line per character. S01–S06 suggested a combined length of 16–22 Chinese characters for five seconds; this remains an unverified feasibility guideline rather than a guarantee of natural delivery.

### Evaluation

For S07–S12, human evaluation should use the six basic-emotion categories plus an explicit `uncertain` option, rather than the three-tone questionnaire from S01–S06.

The evaluation should retain the following principles from S01–S06:

- Target-emotion recognition
- Dialogue naturalness
- Story clarity
- Emotional overstatement
- `uncertain` counted as a recognition miss
- Equal clip weighting
- Explicit accounting for failed generations and missing evaluations

VEMOCLAP should retain its original six-class probabilities and predicted labels without merging categories into affectionate, hostile or tense.

Its predictions are supplementary measures of whole-video emotion recognition, not direct measurements of dialogue quality or emotion intensity.

### Interpretation limits

The new scenarios reuse the original character pairs but change their stories and target emotions. This reduces asset preparation but does not isolate character identity, plot or visual style from emotion.

Each basic emotion appears in only one story. Emotion-specific effects cannot be estimated independently of story and character pair.

The primary comparison is therefore between Baseline, Generic Review and MoodCut within each fixed scenario.

Relationships, settings and props may already provide emotional cues, making some scenarios easier for all methods. Recognition of a target emotion in a generated video cannot be attributed entirely to dialogue revision.

Do not replace scenarios after observing which method performs best, silently exclude failures, or change video duration for only one condition.
