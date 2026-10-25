# Six clear-emotion scenarios: affectionate, hostile and tense (v2)

Revised on 2026-10-24 to meet the updated script requirements. Current inputs use **two stories each for affectionate, hostile and tense**: six stories, 12 distinct characters, one tone per story, three conditions and one replicate, totaling 18 condition entries. The five-second, single-shot scope with one line per character remains unchanged. This change prepares materials and offline tests; it runs no experiment or model API calls.

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

## Inputs and execution scope

- [design.json](design.json): version, definitions of the three tones, six stories, roles and plot boundaries; not an execution configuration.
- [inputs/index.json](inputs/index.json): paths, labels and byte hashes for six scene / asset pairs; `selected_tones` is exactly affectionate, hostile and tense.
- Each story's `scene.json` uses the existing 1.1/generated format. Its `assets.json` still copies the metadata for the corresponding two original character images verbatim from v1. The 12 characters are distinct; no new image selection is made.
- `.gitattributes` fixes JSON line endings to LF so index hashes remain stable across Windows and Linux checkouts.

The three conditions share one initial plan per story, all plot requirements and all non-dialogue requirements. Only dialogue may be revised. Relationships, footsteps, deadlines, actions, expression requirements, shots, durations, reference images and voice settings must not be enhanced separately for one method. Label support extends only structural validation and rating parsing. It does not change planning / actor / writer prompts or supply Agent responses or ratings.

This change prepares inputs and local software checks only. `execution_enabled=false`, `paid_run_authorized=false` and `formal_inclusion_approved=false`. No model calls, video generation or human ratings occurred. Method version, specific models, feasibility of the common duration, live pricing, budget and viewer assignments must still be determined before execution. Five seconds for two lines, with a suggested combined length of 16–22 Chinese characters, is an unverified design constraint; natural speech delivery has not passed acceptance.

## Materials and interpretation limits

Character images still come from the [existing asset library](../../../assets/library/README.md), preserving the 12 original v1 images, sources, hashes, framing and `rights_status=unconfirmed`. Existing expression, glasses occlusion, framing and clarity limitations remain. Images are not reselected to match the target emotion more closely, and provider acceptance of the new pairs is not verified here.

This version makes scenario meanings clearer as requested. Relationships and background themselves may reveal the answer, making the target easy for every method and reducing the visible gain from review. Tone recognition for the full video must not be attributed entirely to dialogue revision. Story, character and tone remain confounded across the six stories. Comparisons apply only to methods on these inputs with shared initial plans; character or tone effects cannot be estimated independently. Six stories remain six scene units.

Scoring retains tone recognition, naturalness, story clarity, overstatement, uncertain counted as a miss, equal clip weighting and coverage of all failures. The parser adds tense rows and columns to the confusion matrix without rewriting legacy suspicious labels or scores. Do not replace tasks after seeing which method wins or extend duration for only one method.

Using the historical rate of $0.25 per five-second video, a scenario with all 18 entries newly generated still estimates **$4.50** for video, with text, failures, price changes and longer durations charged separately. This extrapolates old bills; it is neither a live quote nor approval of this batch budget. New model calls and spending for this change are both **0 / $0**.
