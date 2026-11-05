# Experimental image-operation exchange (DRAFT 2026-10-13)

Companion technical note for [PI](../contracts/provider-image-operation.v1.md).
This describes the experimental exchange in the current source candidate, not a
shipped interface or Core change. PI owns the promises; this file records current
field/method spelling. The contract is not frozen, and combined offline
qualification remains pending. A future change updates both coherently.
Provider implementations do not import this tool.

## Surface and negotiation

```python
get_image_generation_capabilities() -> dict
async prepare_image_generation(request: dict) -> dict
async generate_image(request: dict, *, plan: dict) -> dict
```

`protocol` is `amplifier.image-operation.v1`. All three methods must be callable,
and the descriptor must advertise that exact protocol. The first call is local
and non-generating. Only `supported: true` enables preparation; missing methods,
wrong versions and unsupported descriptors do not authorize execution. Refusal
details, when supplied, use safe reason codes/messages, not raw SDK exceptions.
Absent support never triggers inference, login or an implicit transport switch.
Descriptors report operations, output formats and supported transports; input
formats and refusal details can also be present. Specific models, endpoint modes
and controls are validated during preparation, not inferred from provider
branding or an image-input flag.

The tool's `capabilities` action inspects these local descriptors only. It does
not call the resolver or preparation, and reports `route: not_selected`.
An ordinary descriptor-inspection exception is isolated to that provider during
discovery: `providerDiagnostics` retains up to 16 entries with
`reasonCode: invalid_provider_capability` and the provider instance key (a string
of at most 200 characters, otherwise null), never the raw exception.
Other providers can still report support. Missing methods, wrong protocol or
`supported` other than `true` simply report no support; these are not the same as
an inspection exception. Cancellation, `KeyboardInterrupt` and `SystemExit`
propagate rather than becoming diagnostics.

Preparation uses Foundation's `operation_routing.prepare_operation`; compatible
resolvers advertise `operation_resolution_protocol = "amplifier.operation-routing.v1"`
and implement `resolve_for(role, *, requirements, accept)`. Provider preferences
must identify exact mounted keys. Ordinary `resolve(role)` remains supported,
but only its returned preferences may be considered.
When a candidate is evaluated for preparation, descriptor inspection runs again.
An inspection exception there is a hard `invalid_provider_capability` failure,
not incompatibility or permission to try another candidate. Discovery's diagnostic
handling does not turn a selected candidate's broken descriptor into fallback.

## Request

```python
{
  "protocol": "amplifier.image-operation.v1",
  "request_id": "sample-edit-2",
  "operation": "edit",
  "prompt": "Change the background; preserve the subject.",
  "inputs": [{"purpose": "target", "mime_type": "image/png",
              "data": b"...", "sha256": "<actual SHA-256>"}],
  "selection": {"model": "<role-selected conversational model>",
                "config": {"image_generation": {"model": "<image model>",
                                                 "transport": "<provider transport>"}}},
  "output": {"count": 1, "mime_type": "image/png", "size": "auto",
             "quality": "auto", "background": "auto"}
}
```

Inputs are ordered, permitted, inspected bytes with hashes, not local paths or
remote URLs. For edits the first input is the target; remaining inputs are
references. Generation may gain reference inputs only through a separately
qualified tool-schema change. Existing tool limits remain narrower than some
providers' limits and are never silently raised by discovery.

`selection` contains the resolver's operation-scoped preference. Ordinary agent
routing keeps a tool-capable top-level `model`; the native image model lives in
`config.image_generation.model`. A native-image provider does not call an unused
controller. A hosted image-tool provider validates and executes the model pair.
Credentials, base URLs and permissions are not legal operation config overrides.
The current adapters accept only `model` and `transport` in the nested
`image_generation` mapping: no `enabled`, credentials, timeout or nested effort.
They tolerate top-level `reasoning_effort` and `max_output_tokens` role metadata
without forwarding it as native image controls. Provider settings and host
admission remain separate.

Exact pixel sizes and aspect-ratio/resolution tiers have different meanings.
Initial standard sizes follow the tool schema. A later tier extension must be
mutually exclusive with exact pixels; no rounding, ignored quality, or invented
transparency. Reasoning effort is separate from image quality. Unsupported
requirements fail before generation, allowing only policy-authorized preselection.

## Preparation and bound plan

The convention permits bounded non-generating catalogue reads on the selected
connection. The current OpenAI and Gemini operation adapters instead validate
maintained model/transport support locally; preparation makes no catalogue or
generation request. It may construct the provider's bound SDK client.
It returns one of:

```text
supported: true  + protocol + plan
supported: false + protocol + reason_code + safe_message
```

For a `supported: false` preparation result, only these `reason_code` values
permit traversal, and only to a next candidate already declared by the resolver
or explicit preferences:

```text
unsupported_connection, unsupported_model_or_transport, unsupported_model,
unsupported_transport, unsupported_controller, unsupported_output,
unsupported_controls, unsupported_sdk, unsupported_interactions_sdk,
unsupported_reference_count
```

In particular, `unsupported_interactions_sdk` can allow that declared next
candidate; it cannot invent a replacement or switch transport outside that
declared sequence.
The ambiguous `unsupported_sdk_or_binding`, unrecognized reason codes, malformed
preparation results, provider exceptions and binding failures are terminal for
traversal. They do not authorize another account or transport.

The current adapters' plans contain `protocol`, an opaque `id`, `request_hash`,
`transport`, native image `model`, a `controller` model or null, and `output`
requirements. Gemini also freezes its effective `timeout`. Plans are plain
JSON-serializable data, bounded to 64 KiB by the consumer. These are provider-owned
shapes, not a universal list of required plan keys for other implementations.

For each successful preparation, the consumer retains the provider object, a
deep copy of the full preference taken before preparation, and that prepared
request. It associates the resolver's selection with exactly one such request
using provider object identity and full preference equality. Provider identity
alone, selected model alone and plan object identity are not the match key.
No match or multiple matches fail before the durable request claim; a copied
plan does not change which prepared request is selected.

Providers retain a private copy and connection snapshot behind the opaque plan
ID; credentials and endpoint details are not serialized into it. The consumer
keeps the exact mounted instance handle and checks that it remains current.
The provider validates the request hash, plan and private binding again, then
consumes the plan before its first execution await. A serialized plan alone
neither grants authority nor supports cross-process replay.

Imagegen validates inputs and output paths, prepares a route, then exclusively
claims the request directory. It saves `request.json` and `plan.json` before
invoking generation; the latter contains provider instance, preference and plan.
The receipt includes a separate `planHash`. A concurrent claimant reads existing
state rather than dispatching. Preparation is not a universal preview API,
execution admission or proof of image entitlement.

An old completed/unknown request is read by original intent identity before any
new resolver call. The route hash is distinct from the intent hash so policy
changes cannot reclassify a duplicate into a new effect.

### Current provider transport boundaries

| Provider operation | Default | Explicit compatibility choice |
| --- | --- | --- |
| OpenAI | `responses`: selected controller plus hosted image model, `store: false`, one image-tool call | `images`: native Images API, no controller call |
| Gemini | `interactions`: native image model, `store: false`, non-streaming | `generate_content`: native image model, automatic function calling disabled |

OpenAI executes with SDK `max_retries=0`. Gemini's Interactions retry seam is
qualified against `google-genai` 2.30.1: it needs `HttpRetryOptions(attempts=0)`,
because that builder maps `attempts=1` to two physical sends. Explicit
`generate_content` uses `attempts=1` plus a request-local view forced to borrow
the provider's HTTPX transport, avoiding aiohttp's inner disconnect retry.
Neither view changes the shared chat client's retry policy or owns its cleanup.
These are source/SDK boundaries, not a live service exactly-once guarantee.

Gemini currently requires `auto` size, quality and background; its Flash Lite
image model accepts at most one input. OpenAI validates its supported pixel
sizes, quality and background values before dispatch. A supported model name
or catalogue listing never proves entitlement. There is no automatic switch of
account, model or transport after execution begins.

## Result

```python
{
  "protocol": "amplifier.image-operation.v1",
  "status": "completed",
  "outputs": [{"kind": "image", "mime_type": "image/png", "data": b"..."},
              {"kind": "text", "text": "Optional description"}],
  "models": [{"purpose": "image", "requested": "<alias>", "resolved": None}],
  "upstream": {"request_id": None, "response_id": None, "image_call_id": None},
  "usage": {"normalized": None, "provider": None},
  "effective_options": {}, "warnings": [], "continuation": None
}
```

`status` is completed, blocked, failed or unknown. A recognized terminal refusal
is distinct from an uncertain send; neither permits automatic replay. Safe errors
carry `reason_code` and known dispatch state without raw SDK exception bodies.
Cancellation propagates while the operation owner preserves conservative state.
The runtime guarantees no automatic replay, not exactly-once execution upstream.

For a result that reaches receipt construction, optional `dispatch_state` is
copied to receipt `dispatchState` only when it is `not_sent`,
`response_received` or `unknown`. Optional `reason_code` becomes `reasonCode`
only when it matches `[a-z][a-z0-9_]{0,63}`. Missing or malformed optional values
are omitted, not echoed, inferred or themselves treated as a failed result.
These are validated additive fields on `amplifier.image.receipt.v1`, not a
required receipt-version change or independently verified transport observations.
Local checks can replace `reasonCode` with `output_control_mismatch` or
`invalid_provider_metadata`.

Dispatch evidence and outcome are separate. A provider-normalized invalid
response returned as `status: failed` with `dispatch_state: response_received`
remains failed. An otherwise valid `status: unknown` result can retain
`response_received` and remain unknown. Within the retained-output bounds, a
returned `completed` result with wrong image cardinality or requested geometry
becomes failed; detected invalid receipt metadata also produces failed. This is
not a promise that every invalid response becomes failed: malformed result/output
shapes, over-limit output or invalid image bytes can raise during validation and
enter the conservative unknown exception path.
An execution exception, including uncertain transport, leaves an unknown receipt
without inventing dispatch evidence. Neither `not_sent` nor any other evidence
permits replay of the claimed identity or a fallback attempt.

Outputs retain ordering and all bounded final artifacts. Imagegen validates bytes
independently; its one-image promise refuses unsupported cardinality. It can
retain up to four validated images as `evidenceArtifacts` for a failed result,
not as completed output. Malformed or over-limit output is not guaranteed to be
recoverable. Do not label a thought image, partial,
text answer or output convenience property's last item as the complete result.

Model entries distinguish controller/image roles, requested aliases, deployments
and observed versions. Missing observations remain null. Usage includes the native
reported structure plus normalization when trustworthy; never fabricate zero.
Opaque continuation is private JSON-safe provider state tied to its original
binding. It is not rendered thought text, an SDK object or a cross-account token.
Both current adapters return `continuation: None`; Imagegen neither copies that
field into public receipts nor replays native continuation. The tool retains
`amplifier.image.receipt.v1` with additive route/model/upstream evidence rather
than claiming a new frozen receipt contract.

## Qualification boundary

Required fixtures cover each PI clause with a passing and failing example,
including a wholly unrelated synthetic provider. Installed-package integration
must confirm both real provider adapters speak these shapes without peer imports.
Separately reported installed-package evidence covers 28 existing cases with
synthetic providers and no network calls. That is narrow routing/receipt
qualification, not qualification of real-provider SDK transports or the combined
candidate. This documentation alignment is a source review, not a new test run.
Live generate/edit, host delivery, pixel inspection and account entitlement remain
separate gates. Combined candidate qualification is pending; this document
establishes no live calls or deployment acceptance. Earlier named-backend evidence
does not qualify the routed path.
