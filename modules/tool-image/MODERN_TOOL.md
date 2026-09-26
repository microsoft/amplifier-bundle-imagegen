# Modern Amplifier tool

The `amplifier.modules` entry point `tool-image` mounts **`image_generate`** with an
explicit schema: `capabilities`, `generate`, `edit`, and `status`. This is separate
from the retained `ImageGenerationTool` direct wrapper (`image-generation`, with
`operation=generate/check_availability/get_cost_estimate`) and `ImageGenerator`.
Those historical APIs retain their existing fallback and output-path behavior.

## Select one backend

A host can supply `image.backends[backend]`, including the existing Amplifier
OpenAI provider's optional image capability. The tool does not require that the
conversational provider be OpenAI. It requires a tool-capable conversation model,
a session workspace, explicit image backend selection, and `allow_paid: true`.
The image backend owns its image model, API routing, credentials and usage.

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

Alternatively, this module can own one explicitly selected existing library
client. Add these fields to the config above:

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
behavior remains unchanged. Gemini `generate_content` image models and the
separate Nano Banana proposal are not implemented by this adapter.

## Requests and saved results

Call `capabilities`, then send a stable identifier for each intended paid effect:

```json
{"action":"generate","request_id":"cover-v1","prompt":"A blue geometric square on white"}
```

The tool writes `artifacts/images/cover-v1/{request.json,image.png,receipt.json}`
inside the session workspace. Existing artifacts are never overwritten. A
completed receipt includes exact bytes/hash/dimensions, selected backend/model,
provider request ID and usage when supplied. No static price estimate is treated
as actual cost. Google currently supplies neither request ID nor usage here.

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

A durable exclusive claim precedes the backend call. The same request identifier
never repeats a paid call, including after cancellation, timeout, interruption,
invalid provider output or restart. `status` returns the saved result or `unknown`;
it does not query/replay a provider operation. Investigate an unknown result before
deliberately choosing a new identifier. There is no automatic vendor fallback.

Built-in adapters disable SDK retries; Google uses the SDK-owned HTTPX transport
because its aiohttp transport has an extra connection-error retry. The default
passes no elapsed deadline to either SDK. A configured timeout is caller chosen;
it is not a cost limit. Remote services and host-owned backends retain their own
policies. There is no aggregate spend cap or automatic entitlement probe.

## Host and validation boundaries

Host-supplied backends implement synchronous `describe()` and async
`generate(action, prompt, images, size, quality, background)`. `describe()` returns
`configured`, `missing`, `model`, `operations`, and optionally supported `options`
and `defaults`. `generate()` returns `data: bytes` and optional `request_id`/`usage`.
Image inputs contain exact `data`, `mimeType`, and `name`. The host owns the
backend's lifecycle; the tool only closes built-in clients it created and does not
overwrite existing registrations.

`image_generate` and receipt schema `amplifier.image.receipt.v1` preserve the
existing portable integration contract. Artifact rendering, publishing links and multimodal
inspection remain host capabilities. A receipt is not proof a conversational
model saw pixels; inspect the saved artifact through the host's supported image
path. This tool does not add image understanding to a text-only provider.

Offline tests exercise real SDK request serialization against fake HTTP, Core
mount/schema/cleanup, no fallback/replay, cancellation, concurrent duplicate
claims, edit lineage and path races. SDK dependency floors are the versions
qualified for these image/retry/transport APIs, not a claim that every older
release is incompatible. Google is bounded below 3 because this SDK marks
`generate_images` for removal in the next major release. Real account entitlement, image quality, service-side
behavior, alternate endpoints and browser presentation need separate acceptance.
No real generation is part of the tests.
