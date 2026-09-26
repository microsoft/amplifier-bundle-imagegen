# amplifier-module-tool-image

A provider-neutral Amplifier tool for generating and editing saved images with
workspace path policies, durable request receipts, and edit lineage.

Built on **[robotdad’s image-generation library](https://github.com/robotdad/amplifier-module-image-generation)**,
with thanks for its OpenAI and Google clients. This module is preserved inside the imagegen capability bundle; [provenance](PROVENANCE.md) records the exact
upstream revision and [notices](UPSTREAM-NOTICES.md) retain its license declaration.

## Mount in Amplifier

```yaml
tools:
  - module: tool-image
    source: git+https://github.com/microsoft/amplifier-bundle-imagegen@main#subdirectory=modules/tool-image
    config:
      backend: images
      allow_paid: true
```

The normal `amplifier.modules` entrypoint mounts **`image_generate`**, with four
operations: `capabilities`, `generate`, `edit`, and `status`. A session workspace
and an explicitly selected image backend are required. `capabilities` performs
local configuration inspection without constructing clients or making API calls.

The recommended host integration supplies `image.backends["images"]`, such as
the Amplifier OpenAI provider’s optional image backend. Its model, endpoint,
credentials and lifecycle are configured by that provider. The conversational
provider can be different: the tool does not require OpenAI for conversation.
Image generation and conversational pixel inspection are separate capabilities.

For hosts without that capability, explicitly configured built-in adapters reuse
the library’s OpenAI GPT Image, DALL-E, and Google Imagen clients. Generate/edit
support varies by backend; no vendor or model is chosen as a paid fallback. See
[MODERN_TOOL.md](MODERN_TOOL.md) for complete configuration and contracts.

## Request and inspect

```json
{"action":"generate","request_id":"image-v1","prompt":"A blue circle on white"}
```

Results are written under `artifacts/images/image-v1/` with a PNG, request claim
and receipt. Completed receipts include hash/dimensions, selected backend/model,
provider request ID and usage when available. Unknown outcomes are retained and
never automatically replayed. `status` reads the saved receipt.

An edit names the saved input and its actual SHA-256:

```json
{"action":"edit","request_id":"image-v2","prompt":"Make the circle red","images":[{"path":"artifacts/images/image-v1/image.png","sha256":"<actual SHA-256>"}]}
```

The original remains intact. Images and paths are validated; outputs are confined
to the session workspace and host path policy. Symlinks, traversal and special
files are refused. Limits are one PNG output, four inputs, 8 MiB per image and
4096 pixels per side. POSIX file-descriptor protections are used; Windows is not
qualified. No implicit healthy-call elapsed deadline is added; callers may
configure one explicitly.

## Direct library API

The preserved `ImageGenerator`, `ImageGenerationTool`, `ImageResult` and
`ImageGenerationError` exports now live in `amplifier_module_tool_image`. The
historical direct wrapper uses `operation=generate/check_availability/get_cost_estimate`
and retains its legacy fallback/output behavior. Use the modern mounted tool for
workspace safety, durable request claims and edits.

## Development and qualification

Install this package and the test dependencies in an isolated Amplifier
development environment, then run `python -m pytest -q`. The source-loading
regression additionally requires Foundation; it must pass rather than be skipped
when qualifying normal bundle URI loading. Tests inject fake transports and
synthetic credentials; they block real network connections.

The implementation baseline has separately passed real OpenAI host-backend
generation/editing. Historical acceptance is attributed in the bundle provenance;
this relocation receives separate offline composition and source-loader checks. It does not claim new live backend, remote-install, Google
account, browser presentation or Windows acceptance. Publication and consuming
profile updates are separate steps.
