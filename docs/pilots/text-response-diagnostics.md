# Offline text-response retention and JSON diagnostics

## Scope and preserved history

PR #52 adds diagnostics to the existing OpenRouter text client, not another execution tool. The increment uses software responses and local artifacts only: no paid API, balance lookup, new video, retry, model switch, JSON repair or handwritten task dialogue. Actor negotiation, prompts, source identities, scores and budgets are unchanged.

Both actual failed trials remain unchanged:

| Actual trial | Observed stopping point | Original text spending | New videos |
| --- | --- | --- | --- |
| [First v3](anna-elsa-actor-v3.md) | Conflicting complete edits for one shot | $0.00281304 | 0 |
| [Per-shot v3](anna-elsa-actor-v3-shot.md) | Emotional writer failed strict JSON-object parsing | $0.00291790 | 0 |

The second trial did not retain invalid model content. It remains missing, with its exact JSON error subtype unknown. New classifications below apply to newly captured responses; they do not reconstruct or reclassify that historical reply. Neither trial is converted into a success.

## Retention boundary

`run_experiment` automatically captures planning under the block output directory and review calls under each condition directory. Both routed role clients use that same execution context. CLI `plan` and `review` capture under their output file's parent. Direct library users outside these entrypoints must pass `OpenRouterClient(response_dir=...)` or use `capture_text_responses(directory)`; an unconfigured standalone client has no implicit output location.

For each received response, the existing client exclusively creates:

```text
PRIVATE/text-responses/<unique-call-id>/
  response.bin
  content.txt
  diagnostic.json
```

`response.bin` is written before envelope parsing. `content.txt` is written after extracting a string completion, before parsing or validating that content, including incomplete/refused completions. It therefore may be absent when the envelope is unreadable or contains no unique string completion. `diagnostic.json` records the call after accounting, including generation ID, HTTP status, available tokens/cost, parse failure and retention metadata. Transport failures without a readable body cannot produce a raw response artifact.

Call records store relative artifact paths, SHA-256 and byte counts, never inline response text. Body/content files retain the received bytes and extracted model string respectively, except that an echoed literal or JSON-escaped current API key is redacted. Metadata flags disclose redaction and hashes describe the retained bytes. Request headers are never saved. These are private development artifacts, not anonymous viewing materials or signed provider evidence. The private directory is Git-ignored even outside `runs/`; the existing blind export continues to copy only its explicitly selected anonymous media and CSVs.

The existing response size limit remains in force. An oversized response saves only the bounded limit-plus-one prefix with `complete=false`, then stops with unknown cost. A body/content/diagnostic write failure is recorded as `retention_error` and cannot release a successful completion; a simultaneous parse/API failure retains its original error. Known provider usage remains known, unknown cost remains null and existing stopping rules apply. No result recovery or automatic retry is added.

## Error fields

`parse_error` is null when no JSON error was identified. Otherwise `layer=envelope|content` distinguishes transport envelope parsing from parsing the model's completion string:

| `kind` | Meaning / additional safe fields |
| --- | --- |
| `syntax_error` | Invalid JSON syntax; `line`, `column`, zero-based `position` |
| `duplicate_key` | Repeated object member at any depth |
| `non_finite` | NaN/Infinity or numeric overflow such as `1e999` |
| `non_object` | A valid JSON value whose root is not an object |
| `invalid_utf8` | Envelope decoding failed; zero-based `byte_offset` |
| `excessive_nesting` | Parser/serializer recursion limit exceeded |
| `parser_error` | Other parser failures; no invented specific diagnosis |

Public error messages carry only layer/kind, not raw snippets or offending key names. Schema/actor/patch violations remain separate hard errors, rather than being mislabeled JSON syntax errors. Valid JSON does not imply a valid plan or actor agreement.

## Offline acceptance

Client tests cover exact retention before parsing, syntax/duplicate/non-finite/non-object/UTF-8/nesting errors, known and unknown costs, HTTP errors, bounded oversized bodies, echoed credential redaction, filesystem failures and unique/restored capture contexts. CLI tests exercise automatic capture on valid planning and invalid planning/review. The existing full v3 integration exercises both routed roles, both conditions and nineteen-call success/disagreement paths; an added invalid-JSON response stops before the next condition with its known charge and raw text preserved. Existing anonymous-export tests require exactly the public CSV/media files.

A separate network-denied replay in `runs/anna-elsa-text-response-offline-20261024` retained five explicitly developer-authored software failures with matching hashes and diagnostic costs, recompiled six historical global/v1/v2/v3 preparation packages read-only, and verified **661 protected files** unchanged before and after. This includes both failed trials, their original public result pairs, prior media and offline evidence. Fixture costs are not spending; actual HTTP calls and new spending are zero. Test counts and current-head CI are recorded in PR #52. Offline checks establish engineering behavior, not future model compliance or video quality. Issues #8/#9 remain open; PR #52 remains unmerged.
