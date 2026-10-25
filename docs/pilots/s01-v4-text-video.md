# S01 v4 text and video development case

On 2026-10-25, the separately authorized S01 run completed common planning, generic review, MoodCut revision/revisits, and native-audio video generation. The latest case is [available in the gallery](https://zhengads.github.io/MoodCut-dsa4213/#s01-v4). [Parsed results](s01-v4.results.json) preserve the initial plan, original Actor/writer/revisit responses, settings, executed-source hashes, costs and media identities. This is one development case, not a formal or blind evaluation.

## Observed comparison

| Speaker | Baseline and generic review | MoodCut |
| --- | --- | --- |
| Anna | 我真的好想你啊。 | 我真的好想你啊。 |
| Kristoff | 我也是，我会一直陪着你。 | 我也很想你，现在哪儿也不去了。 |

The one global generic reviewer returned no issues; no writer candidate or revisit was triggered. MoodCut collected two independent Actor reports. Anna reported no issue. Kristoff raised one minor tone concern: “一直” may imply a long-term commitment beyond the present reunion and the brief's no-new-promises boundary. The writer adopted the Actor's proposed example verbatim. Both Actors revisited the actual candidate, including Anna with no original issues. Anna returned no decisions or new issues; Kristoff marked the original issue resolved. No second revision was needed, no final dispute remained, and actor_endorsement stays not_requested.

This illustrates an intent/subtext scope check, not independent proof of better writing. “一直” can also be read as affectionate hyperbole. The case does not test live second-round disagreement, general effectiveness, or whether either rendering speaks every requested word naturally.

## Generation and reuse

All conditions retained the same non-dialogue plan, original Anna/Kristoff references, voice/audio requirements, requested five-second duration, seed 4213 and HeyGen 768p settings. Prompt enhancement was disabled. Only dialogue JSON differed between the two unique video requests. Generic review and baseline requests were identical, so the existing executor reused the exact baseline output: three displayed condition entries, **two independent video generations**, not three replicates.

The unretimed original MP4s are 1344×768, about 5.258344 seconds, with native audio. No audio substitution or manual dialogue repair was performed. Sampled frames show differences in gestures and background details across the two outputs; a fixed seed does not lock those details. Speech and subjective checks remain unscored.

## Verified spending

| Component | Calls | USD |
| --- | ---:| ---:|
| Shared planning, counted once | 3 | 0.00096760 |
| Generic review | 1 | 0.00053126 |
| MoodCut: two reviews, one writer, two revisits | 5 | 0.00285714 |
| Successful text total | 9 | 0.00435600 |
| Two video submissions | 2 | 0.50 |
| Successful text plus video | | **0.50435600** |

Text costs match identified generation metadata; both video receipts record $0.25 and the video interval's account delta is $0.50. The earlier three failed text attempts cost $0.00212910, making all identified S01 attempts $0.50648510. Other account activity is not attributed to these identified calls. Private account snapshots, credentials, raw transport receipts and local paths are not published.

## Failure preservation and request correction

Earlier attempts stopped for two scene segments, an omitted beat, and developer-side shared JSON-Schema references that accidentally constrained free text. All original artifacts remain intact. The successful caller wrapper broke schema-node aliases with a JSON round trip, bound original IDs/order/duration, and guarded free-text fields before submission. It did not patch returned Agent words. Twenty-two offline request checks and 28 focused v4 tests passed before the successful run. The saved source loader, review replay, comparison contract, frozen non-dialogue fields, native A/V and hashes passed rechecks.

V4 was executed from a local development snapshot based on dc8fbaf, with exact runtime and prompt hashes in the result JSON. This gallery change **does not merge that runtime implementation** or retag historical v1/v3 results. It publishes the completed case only.

The gallery now shows completed-video cases; failed/no-video entries are hidden from navigation and playback, while their original data and historical records remain preserved. Raw video hashes remain checked during Pages deployment. Original character reference images are not included in this release. See the [release source statement](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-s01-v4-20261025/SOURCE.md).
