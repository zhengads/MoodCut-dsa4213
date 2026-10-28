# Current scripts: 01–12

The current script catalog follows [Videos S07–S18](https://github.com/zhengads/MoodCut-dsa4213/releases/tag/Videos_S07-S18), published on 2026-10-28: S07–S12 and **S13–S18 V2**. Display numbers now run from **01 to 12** in release order. Original IDs remain in the archive, input files and evaluation records; they are not renamed to S01–S12.

[Download all videos](https://github.com/zhengads/MoodCut-dsa4213/releases/download/Videos_S07-S18/MoodCut_S07-S12_and_S13-S18_V2_All_Videos.zip) · [Numbering and verified file manifest](release-index.json)

The archive contains **12 scenarios, 36 condition MP4 files and 28 distinct video byte hashes**. Each scenario has Baseline, Generic Review and MoodCut entries; some entries reuse identical media. Delivery records report 8.083344 seconds per file (an eight-second generation request).

**Version correction:** the released S13–S18 V2 delivery records identify the shared initial dialogue as `gemini_planning_generated_shared_initial_dialogue`. The old authored two-line drafts are not the baseline for these V2 videos. Likewise, the earlier five-second S07–S12 design is not the duration of this release.

## Script index

| No. | Release ID | Script | Characters | Emotion | Spoken language |
| --- | --- | --- | --- | --- | --- |
| 01 | S07 | [Another broken promise](#script-01) | Maxime / 马克西姆, Valentina / 瓦伦蒂娜 | anger | Mandarin Chinese |
| 02 | S08 | [The foul-smelling medicine](#script-02) | Lijing / 李靖, Taiyi / 太乙 | disgust | Mandarin Chinese |
| 03 | S09 | [Something in the forest](#script-03) | Elsa / 艾莎, Mattias / 马蒂亚斯 | fear | English |
| 04 | S10 | [The celebration is saved](#script-04) | Anna / 安娜, Kristoff / 克里斯托夫 | joy | English |
| 05 | S11 | [An irreplaceable keepsake](#script-05) | Lucy / 露西, Gru / 格鲁 | sadness | English |
| 06 | S12 | [An unexpectedly finished task](#script-06) | Nezha / 哪吒, Aobing / 敖丙 | surprise | Mandarin Chinese |
| 07 | S13 V2 | [A unilateral decision](#script-07) | Lucy / 露西, Gru / 格鲁 | anger | Mandarin Chinese |
| 08 | S14 V2 | [The spoiled drink](#script-08) | Anna / 安娜, Kristoff / 克里斯托夫 | disgust | English |
| 09 | S15 V2 | [A crack beneath the bridge](#script-09) | Nezha / 哪吒, Aobing / 敖丙 | fear | Mandarin Chinese |
| 10 | S16 V2 | [The approval arrives](#script-10) | Lijing / 李靖, Taiyi / 太乙 | joy | Mandarin Chinese |
| 11 | S17 V2 | [The old tree is gone](#script-11) | Elsa / 艾莎, Mattias / 马蒂亚斯 | sadness | English |
| 12 | S18 V2 | [The room is already ready](#script-12) | Maxime / 马克西姆, Valentina / 瓦伦蒂娜 | surprise | English |

## Scenario briefs

The briefs below summarize the committed story requirements. They are not transcripts of the released dialogue. The archive supplies videos and delivery metadata, but no final dialogue transcripts or frozen script blocks.

<a id="script-01"></a>

### 01. Another broken promise — anger

Maxime angrily confronts Valentina about repeatedly breaking her promises. Valentina responds defensively and does not accept his criticism. Their disagreement remains unresolved.

**Boundaries:** do not invent the specific promise, misconduct, crimes, evidence of betrayal or retaliation. Do not introduce additional characters. No insults, threats, shouting requirements, table slamming, pushing or leaving.

**Source brief:** [S07 scene](inputs/s07_broken_promise/scene.json) · **Release folder:** `MoodCut_S07_8s_Chinese_Three_Videos`

<a id="script-02"></a>

### 02. The foul-smelling medicine — disgust

Lijing reacts with strong disgust to the medicine's smell. Taiyi acknowledges that the smell is unpleasant. Neither character drinks the medicine or removes the bottle.

**Boundaries:** do not introduce illness, poisoning, magical accidents, transformations, additional characters or unexpected side effects. No vomiting, exaggerated gagging, spellcasting, throwing objects or leaving. The bottle remains stationary. The emotional focus is disgust rather than fear or hostility.

**Source brief:** [S08 scene](inputs/s08_foul_medicine/scene.json) · **Release folder:** `MoodCut_S08_8s_Chinese_Three_Videos`

<a id="script-03"></a>

### 03. Something in the forest — fear

Elsa admits that she is frightened by the approaching creature. Mattias acknowledges the danger and admits that he is frightened too. The creature remains unseen, and the encounter is unresolved.

**Boundaries:** do not reveal the creature or introduce additional visible characters, weapons, attacks, injuries or escape outcomes. No screaming, running, exaggerated trembling, magic or jump scares. Do not add frightening sound effects to only one experimental condition.

**Source brief:** [S09 scene](inputs/s09_forest_creature/scene.json) · **Release folder:** `MoodCut_S09_8s_English_Three_Videos`

<a id="script-04"></a>

### 04. The celebration is saved — joy

Anna happily announces that the celebration will take place after all. Kristoff responds with genuine happiness and shares her excitement. The celebration has not yet begun.

**Boundaries:** do not introduce new characters, gifts, proposals, weddings, surprise guests or additional plot developments. No hugging, kissing, dancing, jumping, singing or celebratory sound effects.

**Source brief:** [S10 scene](inputs/s10_celebration_saved/scene.json) · **Release folder:** `MoodCut_S10_8s_English_Three_Videos`

<a id="script-05"></a>

### 05. An irreplaceable keepsake — sadness

Lucy expresses sadness about losing something personally meaningful. Gru acknowledges her disappointment and offers comfort. The object remains damaged, and no solution is found.

**Boundaries:** do not invent the keepsake's origin, a deceased owner, an accident, betrayal, financial hardship or additional consequences. No crying requirement, physical contact, object repair or leaving.

**Source brief:** [S11 scene](inputs/s11_irreplaceable_keepsake/scene.json) · **Release folder:** `MoodCut_S11_8s_English_Three_Videos`

<a id="script-06"></a>

### 06. An unexpectedly finished task — surprise

Nezha expresses disbelief that Aobing has already completed the task. Aobing confirms that it is finished. Nezha remains surprised by the unexpected result.

**Boundaries:** do not invent a specific task, magical powers, secret assistance, competitions, rewards or additional characters. No demonstrations, exaggerated physical reactions, jumping or confrontation. The completed result is established before the dialogue begins.

**Source brief:** [S12 scene](inputs/s12_finished_task/scene.json) · **Release folder:** `MoodCut_S12_8s_Chinese_Three_Conditions_Shared_Video`

<a id="script-07"></a>

### 07. A unilateral decision — anger

Lucy objects to Gru breaking their agreement and expresses anger about his unilateral action. Gru defends what he did without denying that he decided alone. The disagreement remains unresolved.

**Boundaries:** do not invent the household arrangement, deception, crime, infidelity, threats, insults, shouting, pushing or departure. Do not directly recite an emotion label. Reference images define identity and clothing only. Do not quote the source film or rely on undeclared film history.

**Source brief:** [S13 scene](inputs/s13_unilateral_decision/scene.json) · **Release folder:** `MoodCut_S13_V2_8s_Chinese_Three_Videos`

<a id="script-08"></a>

### 08. The spoiled drink — disgust

Anna reacts with strong aversion to the smell. Kristoff confirms that the drink has spoiled. Neither person drinks, touches or removes it.

**Boundaries:** do not introduce poisoning, illness, vomiting, exaggerated gagging, magic or another person. Do not directly recite an emotion label. Reference images define identity and clothing only. Do not quote the source film or rely on undeclared film history.

**Source brief:** [S14 scene](inputs/s14_spoiled_drink/scene.json) · **Release folder:** `MoodCut_S14_V2_8s_English_Three_Videos`

<a id="script-09"></a>

### 09. A crack beneath the bridge — fear

Nezha admits concern that the bridge may become unstable. Aobing shares the fear and tells Nezha not to move yet. The cause and outcome remain unknown.

**Boundaries:** do not show collapse, running, jumping, falling, injury, rescue, magic or another person. Do not directly recite an emotion label. Reference images define identity and clothing only. Do not quote the source film or rely on undeclared film history.

**Source brief:** [S15 scene](inputs/s15_cracking_bridge/scene.json) · **Release folder:** `MoodCut_S15_V2_8s_Chinese_Three_Videos`

<a id="script-10"></a>

### 10. The approval arrives — joy

Lijing expresses happiness and relief about the approval. Taiyi reciprocates the joy and anticipation. The event itself has not started.

**Boundaries:** do not add an award, position, money, competition, new person, celebration action, magic or music. Do not directly recite an emotion label. Reference images define identity and clothing only. Do not quote the source film or rely on undeclared film history.

**Source brief:** [S16 scene](inputs/s16_approval_arrives/scene.json) · **Release folder:** `MoodCut_S16_V2_8s_Chinese_Three_Videos`

<a id="script-11"></a>

### 11. The old tree is gone — sadness

Elsa expresses sadness about losing the tree. Mattias understands the loss and offers comfort. The tree is not restored and no solution is found.

**Boundaries:** do not invent the tree's origin, a deceased relative, an accident, a responsible party or a remedy. Do not require crying, embracing or magic. Do not directly recite an emotion label. Reference images define identity and clothing only. Do not quote the source film or rely on undeclared film history.

**Source brief:** [S17 scene](inputs/s17_old_tree_gone/scene.json) · **Release folder:** `MoodCut_S17_V2_8s_English_Three_Videos`

<a id="script-12"></a>

### 12. The room is already ready — surprise

Maxime expresses immediate surprise and disbelief at the early completion. Valentina confirms that the room was ready that morning.

**Boundaries:** do not add secret help, a competition, reward, conflict, magic, exaggerated jumping or another person. Do not directly recite an emotion label. Reference images define identity and clothing only. Do not quote the source film or rely on undeclared film history.

**Source brief:** [S18 scene](inputs/s18_room_ready/scene.json) · **Release folder:** `MoodCut_S18_V2_8s_English_Three_Videos`

## Reading the comparison

Compare the three conditions within the same scenario. The intended control is dialogue-only revision with shared story, cast, actions, framing, reference images and generation settings. Delivery metadata and matching media hashes do not independently verify every control or establish a quality advantage.

Use the six native emotion labels (anger, disgust, fear, joy, sadness, surprise) for this catalog. Human recognition, dialogue naturalness and story clarity remain separate from VEMOCLAP predictions. All release delivery records set `formal_inclusion_approved` to false and require manual speech/quality inspection. Earlier evaluation results are not automatically results for these released V2 files.

## Source files and earlier versions

The old S01–S06 descriptions, three-tone questionnaire, duplicate control sections and authored-draft table have been removed from the current catalog. Original inputs, draft fixtures, hashes, trial failures and evaluation records remain available for reproducibility.

- [Previous complete specification](https://github.com/zhengads/MoodCut-dsa4213/blob/bbb38cb01cca0fe7fff43d3ddd4aa98259a77f1f/docs/studies/six-story-clear-emotions-20261024/README.md) and [original six-story design](../six-story-20261024/README.md).
- [S07–S12 input index](inputs/basic-emotions-index.json) and [assignment configuration](../../../configs/basic-emotions-experiment.json): earlier five-second input specification.
- [S13–S18 authored-challenge input index](inputs/basic-emotion-challenge-index.json) and [assignment configuration](../../../configs/basic-emotions-challenge-experiment.json): earlier authored-draft fixtures, not the released V2 initial dialogue.
- [Historical evaluation record](../emotion-evaluation-20261027/EMOTION_EVALUATION_RECORD.md) and [trial records](../../pilots/README.md): retain original IDs and versions.

The offline assignment configurations list scenarios; they do not reconstruct this release. Reproducing its exact scripts requires the corresponding frozen run blocks, requests and final dialogue, which are not included in the ZIP.
