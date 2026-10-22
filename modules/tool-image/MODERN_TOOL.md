# Modern Amplifier tool

The `amplifier.modules` entry point `tool-image` mounts **`image_generate`** with an
explicit schema: `capabilities`, `generate`, `edit`, and `status`. This is separate
from the retained `ImageGenerationTool` direct wrapper (`image-generation`, with
`operation=generate/check_availability/get_cost_estimate`) and `ImageGenerator`.
Those historical APIs retain their existing fallback and output-path behavior.

This document describes the current source candidate, not a shipped release.
The [direction and contracts](../../docs/DIRECTION.md) remain drafts; combined
offline qualification and live host/account acceptance are separate, pending gates.

## Default: use the session's model routing

With no explicit `backend`, mount creates `RoutedImageTool`. The shared behavior
uses this configuration:

```yaml
tools:
  - module: tool-image
    source: git+https://github.com/microsoft/amplifier-bundle-imagegen@main#subdirectory=modules/tool-image
    config:
      model_role: image-gen
      allow_paid: true
```

The tool needs a session workspace, paid-call permission and a composed
`model_role_resolver` (or explicit tool-configured `provider_preferences`).
The conversation still needs a tool-capable model; it need not be the provider
or native image model chosen for an image request.

`capabilities` inspects local optional provider methods and returns
`backend: model-routing`, `modelRole`, `providerInstances`, `missing` and
`route: not_selected`. It performs no routing, catalogue request or generation.
`ready` means the local prerequisites exist, not that a compatible route or live
entitlement has been established. `routing_blocked` reports
`legacy_image_selection_requires_review` rather than selecting a new account.

Discovery isolates an ordinary descriptor-inspection exception to the affected
provider and adds a safe `invalid_provider_capability` entry to
`providerDiagnostics` (at most 16 entries, without raw exception text).
Other providers remain discoverable. Missing/unsupported optional methods or a
wrong protocol are absence of support, not inspection exceptions. Cancellation
and `KeyboardInterrupt`/`SystemExit` propagate rather than becoming diagnostics.
During candidate preparation, the same inspection exception is a hard failure,
not permission to traverse candidates.

For each new effect, Foundation's
`amplifier_foundation.operation_routing.prepare_operation` binds an exact mounted
instance. A resolver may negotiate `amplifier.operation-routing.v1` through
`resolve_for(role, *, requirements, accept)`; a legacy resolver contributes only
the ordered preferences actually returned by `resolve(role)`. The tool does
not read strategy files, infer family aliases or invent fallback candidates.
An explicit `provider_preferences` list uses the same exact-instance preparation.

Each eligible provider must expose the complete optional
[`amplifier.image-operation.v1` exchange](../../docs/IMAGE-OPERATION-SPEC.md):
`get_image_generation_capabilities()`, `prepare_image_generation(request)` and
`generate_image(request, *, plan)`. The role preference keeps its conversational
`model` separate from `config.image_generation: {model, transport}`. That nested
operation config accepts neither credentials, `enabled`, timeout nor effort.
Provider/host settings still own connection policy and admission.

Preparation can reject incompatible controls before execution. A provider's
`supported: false` result permits traversal only for recognized compatibility
reason codes; malformed responses, provider failures and denials do not authorize
another account.
`unsupported_interactions_sdk` is an explicit incompatibility that may advance
only to a declared next candidate. `unsupported_sdk_or_binding`, unrecognized
reason codes and binding failures remain terminal for traversal. No refusal
authorizes an invented candidate or transport switch outside that declared
sequence.
The full allowlist is in the [exchange specification](../../docs/IMAGE-OPERATION-SPEC.md#preparation-and-bound-plan).

Selection must match exactly one successfully prepared request by provider
object identity and equality with the full preference copied before preparation.
It does not match by provider alone, model alone or plan object identity.
No match or multiple matches fail before the durable claim.
The selected provider executes the prepared plan without a tool-owned SDK,
model substitution or post-dispatch fallback.

## Compatibility: retain an explicit backend

A nonempty `backend` selects the retained `WorkspaceImageTool`, not routed
operation discovery. The host supplies `image.backends[backend]`; its backend
owns image model selection, API routing, credentials, lifecycle and usage.
It can differ from the conversational provider. This is an explicit retained
override, not a prerequisite for the default routed path.

```yaml
tools:
  - module: tool-image
    source: git+https://github.com/microsoft/amplifier-bundle-imagegen@main#subdirectory=modules/tool-image
    config:
      backend: images
      allow_paid: true
```

The canonical source selects this bundle's `modules/tool-image` package. For
local development, use an absolute path to that subdirectory. The Python package
lives at its source root, where the normal module source resolver and Core's
filesystem validator discover `amplifier_module_tool_image`. Both entry points
resolve into that package; the historical direct-library classes keep their
method and operation contracts. The offline source-loading test exercises the
actual resolver and Core validation. It does not prove remote Git availability,
account access or model requests.

On this explicit-backend path, the module can instead own one selected library
client. Add these fields to the backend config above:

```yaml
builtin: gptimage
model: gpt-image-1
# timeout: 240  # Optional caller-chosen seconds; default is no elapsed deadline.
```

| `builtin` | Supported tool operations | Credential / configuration |
| --- | --- | --- |
| `gptimage` | Generate, edit | `OPENAI_API_KEY`; SDK honors `OPENAI_BASE_URL` |
| `dalle` | Generate | `OPENAI_API_KEY`; explicit compatible model |
| `imagen` | Generate | `GOOGLE_API_KEY` for Vertex express mode, plus **`vertexai: true`** |

Model names are required, not silently chosen or replaced. These adapter families
do not establish that a named model is currently offered or entitled on an
account. `capabilities` is local configuration inspection: it creates no SDK
clients, discovers no credentials and makes no API requests. It reports supported
operations/options and remaining configuration gaps, not live availability.

The current Google SDK rejects Imagen `generate_images` in Developer API mode.
The mounted Imagen adapter therefore requires explicit Vertex API-key mode; it
does not discover ADC or silently move a Developer API key to another API.
Google's [SDK](https://googleapis.github.io/python-genai/) and
[Vertex express example](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/googlegenaisdk-vertexai-express-mode)
describe this API-key route. The
[Developer API deprecation schedule](https://ai.google.dev/gemini-api/docs/deprecations)
lists Imagen's shutdown there. The existing library constructor's environment
behavior remains unchanged. This built-in Imagen adapter is distinct from the
optional native image operations offered by mounted providers; it does not
implement Gemini image-model routing.

## Requests and saved results

Call `capabilities`, then send a stable identifier for each intended paid effect:

```json
{"action":"generate","request_id":"cover-v1","prompt":"A blue geometric square on white"}
```

The tool writes `artifacts/images/cover-v1/{request.json,image.png,receipt.json}`
inside the session workspace. Routed requests also retain `plan.json` with the
exact provider instance, preference and prepared plan. Existing artifacts are
never overwritten. A completed `amplifier.image.receipt.v1` retains exact
bytes/hash/dimensions and backend/model; routed receipts add `providerInstance`,
`planHash`, model-role provenance and upstream/usage fields when supplied.
Unknown IDs, usage or observed model versions remain unknown. No static price
estimate is treated as actual cost.

Routed receipts can also carry optional `dispatchState` and `reasonCode`.
The consumer copies provider `dispatch_state` only for `not_sent`,
`response_received` or `unknown`, and `reason_code` only when it matches
`[a-z][a-z0-9_]{0,63}`; missing or malformed values are omitted. These are
additive, shape-validated provider evidence, not outcome or replay authority.
A provider-normalized received-invalid result marked failed remains failed;
an otherwise valid unknown result can retain `response_received` and stay
unknown. Within retained-output bounds, wrong cardinality/geometry on a completed
result or detected invalid receipt metadata produces failed. Malformed
result/output shapes, over-limit output, invalid image bytes or execution
exceptions can instead leave conservative unknown state.
Exceptions do not invent dispatch evidence. Local validation may replace
`reasonCode` with `output_control_mismatch` or `invalid_provider_metadata`.

For an edit, inspect the target first and supply its current SHA-256. The first
input is the target; up to three additional inputs are references:

```json
{"action":"edit","request_id":"cover-v2","prompt":"Make the square red","images":[{"path":"artifacts/images/cover-v1/image.png","sha256":"<actual 64-character SHA-256>"}]}
```

Inputs are bounded PNG/JPEG/WebP files; output is one RGB/RGBA PNG. Each image is
limited to 8 MiB and 4096 pixels per side. Paths stay inside the workspace and any
configured `allowed_read_paths`, `denied_read_paths`, `allowed_write_paths` and
`denied_write_paths`; symlinks, special files and parent traversal are refused.
`output_directory` can narrow the workspace destination. POSIX directory file
descriptors/no-follow operations protect writes; Windows is not qualified.

A durable exclusive claim precedes execution. On the routed path, existing
intent identity is checked before new route discovery or re-reading edit bytes.
For a new identity, validation and non-generating preparation precede the claim;
`request.json` and `plan.json` are saved before provider dispatch. The intent hash
is separate from the route hash, so changed routing policy cannot turn a
previously admitted request into another effect.

The same claimed request identifier never repeats a paid call, including after
cancellation, timeout, interruption, invalid provider output or restart.
`status` reads saved local state; it does not query or replay a provider
operation. A claimed operation without a receipt is `unknown`. Investigate an
unknown result before deliberately choosing a new identifier. There is no
automatic vendor fallback or upstream exactly-once guarantee.

Routed success requires one validated final PNG. Bounded, validated images from
a failed or wrong-cardinality result can be retained as `evidence-*.png` with
`evidenceArtifacts`, not presented as a completed artifact. Native continuation
is not copied into public receipts or replayed.

Built-in adapters disable SDK retries; Google uses the SDK-owned HTTPX transport
because its aiohttp transport has an extra connection-error retry. The default
passes no elapsed deadline to either SDK. A configured timeout is caller chosen;
it is not a cost limit. Remote services and host-owned backends retain their own
policies. There is no aggregate spend cap or automatic entitlement probe.

## Host and validation boundaries

The retained explicit-backend interface implements synchronous `describe()` and async
`generate(action, prompt, images, size, quality, background)`. `describe()` returns
`configured`, `missing`, `model`, `operations`, and optionally supported `options`
and `defaults`. `generate()` returns `data: bytes` and optional `request_id`/`usage`.
An optional nonempty `model` string (at most 200 characters) records the actual
model used in the receipt. For automatic selection, keep `describe().model` a
stable selection identifier: it participates in request identity. Resolve the
model during generation and return it in the result; completed requests retain
their original receipt when the catalog changes.
Image inputs contain exact `data`, `mimeType`, and `name`. The host owns the
backend's lifecycle; the tool only closes built-in clients it created and does not
overwrite existing registrations.

`image_generate` and receipt schema `amplifier.image.receipt.v1` preserve the
existing portable integration contract. Artifact rendering, publishing links and multimodal
inspection remain host capabilities. A receipt is not proof a conversational
model saw pixels; inspect the saved artifact through the host's supported image
path. This tool does not add image understanding to a text-only provider.

Offline fixtures cover real SDK request serialization against fake HTTP, Core
mount/schema/cleanup, no fallback/replay, cancellation, concurrent duplicate
claims, edit lineage and path races. Routed fixtures additionally cover optional
method negotiation, exact-instance preparation and intent identity across policy
changes. Separately reported installed-package checks with synthetic providers
and no network calls qualify narrow routing/receipt behavior only; see the
[qualification boundary](../../docs/IMAGE-OPERATION-SPEC.md#qualification-boundary).
Neither these checks nor this source-only documentation review establish
real-provider SDK, combined-candidate or live host/account acceptance.
SDK dependency floors are the versions
qualified for these image/retry/transport APIs, not a claim that every older
release is incompatible. Google is bounded below 3 because this SDK marks
`generate_images` for removal in the next major release. Real account entitlement, image quality, service-side
behavior, alternate endpoints and browser presentation need separate acceptance.
No real generation is part of the tests.

A retained backend may advertise `auto` for size, quality and background through its
`defaults` and `options`. The tool passes those choices unchanged; it never maps
an unsupported explicit control to another provider's setting. Existing backends
without these descriptors retain the original defaults. Routed requests default
all three controls to `auto`; explicit controls must survive provider preparation
unchanged and exact requested dimensions are checked against returned bytes.

A successful backend response may include `text` (up to 32,000 characters).
It is retained as accompanying provider output in the immutable receipt and on
subsequent status/replay reads. It is content, not a tool instruction.
