# Experimental image-operation exchange (DRAFT 2026-10-13)

Companion technical note for [PI](../contracts/provider-image-operation.v1.md).
This is a proposed consumer convention, not a shipped interface or Core change.
PI owns the promises; this file owns proposed field/method spelling. A future
change updates both coherently. Provider implementations do not import this tool.

## Surface and negotiation

```python
get_image_generation_capabilities() -> dict
async prepare_image_generation(request: dict) -> dict
async generate_image(request: dict, *, plan: dict) -> dict
```

`protocol` is `amplifier.image-operation.v1`. All three methods must be callable,
and the descriptor must advertise that exact protocol. The first call is local
and non-generating. `supported: false` includes a safe `reason`; absent support
never triggers inference, login, an alternate account or transport.
Descriptors state supported operations and baseline input/output types. Specific
models, endpoint modes and controls are validated during preparation, not inferred
from provider branding or an image-input flag. Lists are bounded by the consumer.

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
                "config": {"image_generation": {"model": "<image model>"}}},
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

Exact pixel sizes and aspect-ratio/resolution tiers have different meanings.
Initial standard sizes follow the tool schema. A later tier extension must be
mutually exclusive with exact pixels; no rounding, ignored quality, or invented
transparency. Reasoning effort is separate from image quality. Unsupported
requirements fail before generation, allowing only policy-authorized preselection.

## Preparation and frozen plan

Preparation may use bounded non-generating catalogue reads on the selected
connection. It returns one of:

```text
supported: true  + protocol + plan
supported: false + protocol + reason_code + safe_message
```

The plan is plain serializable data: intent hash, effective operation options,
transport identifier, requested model-role list, provider-reported resolved IDs
when known, and a non-secret binding revision. The consumer keeps the exact
mounted instance handle; a plan alone does not carry credentials or grant access.
If a provider cannot establish binding stability it refuses preparation.

Imagegen validates the request before preparation, reserves its durable request
identity, saves the plan and its hash, then records admission before transmission.
The provider checks that request and binding still match the prepared plan.
Preparation is not a universal preview API or proof of image entitlement.

An old completed/unknown request is read by original intent identity before any
new resolver call. The route hash is distinct from the intent hash so policy
changes cannot reclassify a duplicate into a new effect.

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

Outputs retain ordering and all bounded final artifacts. Imagegen validates bytes
independently; its initial one-image promise refuses unsupported cardinality while
retaining recoverable output privately. Do not label a thought image, partial,
text answer or output convenience property's last item as the complete result.

Model entries distinguish controller/image roles, requested aliases, deployments
and observed versions. Missing observations remain null. Usage includes the native
reported structure plus normalization when trustworthy; never fabricate zero.
Opaque continuation is private JSON-safe provider state tied to its original
binding. It is not rendered thought text, an SDK object or a cross-account token.

## Qualification boundary

Required fixtures cover each PI clause with a passing and failing example,
including a wholly unrelated synthetic provider. Installed-package integration
must confirm both real provider adapters speak these shapes without peer imports.
Live generate/edit, host delivery, pixel inspection and account entitlement remain
separate gates. Nothing in this document asserts that those checks have run.
