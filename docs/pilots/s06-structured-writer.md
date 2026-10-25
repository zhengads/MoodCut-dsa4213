# Offline correction: schema-constrained v3 writer requests

## Diagnosis from original evidence

The [actual S06 failure](s06-actor-v3.md) remains stopped, with nine text calls costing $0.00361854 and zero video submissions. Its [original result JSON](s06-actor-v3.results.json), private HTTP bytes, model text, errors and accounting are unchanged. This correction is separately authorized offline; no paid request is repeated.

The saved outer envelope is valid JSON. Its `choices[0].message.content` exactly equals the retained 331-character completion, whose UTF-8 SHA-256 is `8ceeea1b5deed14d2aea21d47f5ad53439a1aeb2d968267af32ed430734a85f2`. Extra braces and a trailing `reasons` fragment follow the first object. Strict parsing reproduces `Extra data` at line 1, column 312, position 311. The reply arrived with `finish_reason=stop`; it was not locally concatenated by the writer adapter or introduced while saving. Both existing writer prompt JSON examples also parse correctly. The evidence localizes the malformed text to the returned completion; it does not explain why the upstream model/provider emitted that suffix.

The confirmed request-side gap is that the client supplied only `response_format={"type":"json_object"}`. The expected writer shape existed in prompt text and local validation, but no explicit JSON Schema was sent to the provider. Adding a schema is preventive transport hardening, not proof that its absence caused this specific generation failure.

## Small scoped change

The existing `complete_json` interface, FakeClient, OpenRouter client and role router accept optional `json_schema=None`. Omission preserves the legacy request format. With a schema, the same request sends `response_format.type=json_schema`, a named schema and `strict=true`; existing `require_parameters=true`, disabled fallbacks, price limits and no-retry behavior remain. Schema bytes enter both per-client/shared budget reservations. The adapter records `response_format_type` and `json_schema_sha256` without changing returned task objects or usage accounting.

Only new v3 `actor_revise` calls request the shape schema, identically for generic/emotional conditions and both rounds. Planning, actor critique, actor confirmation and older protocols retain their existing request formats. The schema describes complete per-shot dialogue arrays, speaker/text fields and feedback disposition; round two additionally requires objection responses. It supplies no dialogue, decision or task solution. Existing ownership, complete-issue coverage, line order/count, actual changes, semantic-boundary and bounded-confirmation validators remain authoritative.

New execution is labeled `writer_output_contract="dialogue_by_shot_json_schema_v1"`, with separate revision/negotiation prompt hashes. Historical `dialogue_by_shot_v1` and `issue_patch_v1` keep their exact original prompt files/hashes and saved-source behavior. Source rechecks bind the new writer call's schema digest/format to its round; comparison rejects mixed writer contracts. This prevents new constrained requests from silently inheriting the identity of old JSON-mode attempts.

Two new prompt versions retain the same writing requirements and explicitly require ending immediately after one object. No parser prefix extraction, brace deletion, text trimming, repair model, response-healing plugin, tool, new client, retry or model switch is introduced. If the provider rejects the schema, ignores it and returns bad JSON, or returns invalid task fields, the existing failure stop still applies. Unknown fees remain unknown and block continuation.

## Provider evidence and limitation

[OpenRouter structured-output documentation](https://openrouter.ai/docs/guides/features/structured-outputs) describes the `json_schema` request, parameter-aware routing and provider-dependent enforcement. [Google's schema documentation](https://ai.google.dev/gemini-api/docs/structured-output#json-schema-support) documents object/array/string/required/additionalProperties support and the need to validate values locally. The small schema uses those shape features; it does not rely on unsupported counting/string constraints.

A public, unauthenticated endpoint-metadata snapshot advertises `structured_outputs` for Gemini 2.5 Flash-Lite's Google endpoints. This is capability evidence, not a successful generation or guarantee of exact enforcement on the live OpenRouter route. No key/balance access or model call was made for this correction. Future live execution still needs a new approved run, normal quote/capability checks and all existing hard-error/cost stops.

## Offline acceptance

Network-denied acceptance in `runs/s06-structured-writer-offline-20261024` uses the **original saved HTTP response bytes**:

- S06: replay all nine original responses through the new routed pipeline. Both writer requests carry the schema; the original bad emotional response still fails at the identical position, with identical retained body/content hashes and known last-call cost. No candidate, request bundle or video is released. Its failed status is not repaired.
- Anna/Elsa: replay all nine previously successful responses unchanged. The new contract prepares all three scripts and compiles video requests offline; every final plan remains identical to its historical source. No generated answer is authored as fallback.
- Recompile seven preserved global/v1/v2/old-v3/per-shot preparation packages read-only. Verify **916 protected files** unchanged before/after, including all actual failures, successful media and frozen story inputs.

The replay summaries explicitly label software transport and historical costs: their logical call counters/returned fees are replayed evidence, **not new HTTP calls or spending**. Actual model calls, new spending and video submissions in this correction are zero. Source/trace files and original raw replies remain private and Git-ignored.

Regression tests cover emitted schema/price/routing controls, schema-size budget reservations, invalid-schema rejection before transport, unsupported-schema stop without downgrade, exact S06 malformed content, both conditions/rounds without extra calls, request-digest tampering, mixed versions and historical prompt identities. The nineteen-slot two-round integration still retains final disagreement and permits only valid request preparation. Fresh suite counts and current-head CI are recorded in PR #52. This is engineering acceptance, not proof of future model compliance, semantic endorsement or video quality. The comparison page's S06 failed state remains accurate and is not redeployed by this correction; PR #52 stays unmerged and #8/#9 open.

Fresh client/reviewer/pipeline/CLI/paired-evaluation regression passed **528 tests and 72 subtests** in 420.48 seconds. The final client/reviewer checks passed **239 tests and 6 subtests** in 12.22 seconds; these counts overlap. The new request-wiring regression first failed on the old client's unsupported schema argument, then passed after implementation. Python syntax, 33 cached references, five public documents/98 local Markdown links and diff checks passed. No paid provider enforcement claim is inferred from these software checks.
