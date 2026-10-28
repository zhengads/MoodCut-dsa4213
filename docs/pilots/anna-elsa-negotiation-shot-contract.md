# Offline correction: one writer output per shot

## Observed failure and scope

The [actual actor-negotiation trial](anna-elsa-actor-negotiation.md), executed with code `c183d3f`, returned two complete dialogue edits for `return-umbrella-shot`. They contain different Elsa lines. The atomic patch validator correctly rejected the transaction; nine real text calls cost $0.00281304 and no video was submitted. The raw [result JSON](anna-elsa-actor-v3.results.json), runtime replies, errors, accounting and original trial Markdown remain unchanged. Their result-only scope describes the first PR #52 submission at `6aa9958`, before this separately authorized offline correction.

The user subsequently authorized fixing the writer interface offline in the same unmerged PR #52. This correction does not repair that paid reply, pick one of its alternatives, generate replacement task dialogue, call a model or authorize another paid attempt. It changes how future actor-negotiation writers must submit their own complete candidate.

## Revised actor-negotiation writer contract

Both generic_review and moodcut, in both writer rounds, now use `writer_output_contract="dialogue_by_shot_object"`. The model returns exactly:

```json
{
  "dialogue_by_shot": {
    "existing-shot-id": [
      {"character_id": "a", "text": "model-selected complete final line"},
      {"character_id": "b", "text": "model-selected complete final line"}
    ]
  },
  "feedback_disposition": {
    "addressed_issue_ids": ["namespaced original opinion IDs"],
    "unaddressed_issue_ids": [],
    "unaddressed_reasons": {}
  }
}
```

The second round additionally requires the existing `objection_responses` object. This example documents a structural schema, not task dialogue or a model result. The prompt supplies one `revision_slots` entry per affected shot, containing its original ordered lines and all associated issue IDs. Multiple actor opinions on that shot share one final dialogue array. Unchanged shots may be omitted; an empty map is valid only when the remaining disposition/revision rules allow no change.

The adapter builds one internal atomic edit per supplied shot in original shot order, copies the model's entire dialogue array without choosing words, and attaches the first original issue ID as a shot association. That association is not an acceptance verdict: complete addressed/unaddressed IDs still decide feedback coverage. Repeated JSON keys fail in the existing strict JSON parser; arrays of alternatives, unknown/feedback-free shots, extra fields or legacy patch envelopes fail rather than falling back to a merge. Existing line ownership/count/order, dialogue-only, candidate/actor confirmation, second-attempt and cost/error gates remain unchanged. Maximum remains nineteen text calls and no third round or paid retry is added.

## Identity, preservation and verification

New reviews, all three run records and the block save the writer-contract identity. New actor-negotiation revision prompts have separate files/hashes; old global/actor-pass/v2 prompts and original actor-negotiation revision prompt files are untouched. Saved actor-negotiation records without the new identity mean the historical `issue_patch` contract and use its exact old prompt hashes for read-only rechecks. New execution always selects the per-shot contract; it cannot auto-fallback to legacy edits. Mixed writer contracts are rejected at source and comparison boundaries.

Saved-source validation independently derives the atomic patch from each raw per-shot writer response before applying existing checks. Changing the saved dialogue map, derived patch, contract label, candidate, actor reply, summary or call order cannot simply inherit earlier validation. Historical failed records stay failed; old successful source packages retain their original identities.

The new two-actor/one-shot regression failed on the old code in both conditions with `Invalid bounded writer response fields`, then passed after the correction. Software tests exercise both rounds, accepted/final-disputed/no-feedback paths, one edit for both actors, malformed/legacy/unknown/alternative outputs, missing speakers, false addressed claims, duplicate JSON keys, raw/derived tampering and existing role/budget stopping. All positive new replies are explicitly developer-authored software fixtures, not autonomous model evidence or paid fallback dialogue.

A denied-network check reproduced the original duplicate-edit rejection unchanged, verified the actual paid trial still cannot prepare requests, and recompiled five preserved global/actor-pass/v2/old-v3 preparation packages read-only. All **570 protected files**, including the complete latest failed trial and its two original public result files, remained SHA-256 unchanged. New HTTP attempts, paid spending and generated videos are zero. Fresh regression counts and current-head CI are recorded in PR #52; offline acceptance does not establish future model compliance, speech quality or method superiority. #8/#9 remain open.

Fresh reviewer/patch/client/pipeline/paired-evaluation regression passed **394 tests and 91 subtests** in 313.76 seconds. A separate denied-network software block used nineteen response slots across both reviewed conditions and both rounds, retained final disputes and prepared all three conditions with one internal edit per changed shot. New-contract comparison passed and mixed writer contracts were rejected. Six changed public documents/85 local Markdown links, 33 cached references, CLI version and diff checks passed. Current-head CI remains separate from this local evidence.
