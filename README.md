# Amplifier Imagegen

Composable image generation and editing for Amplifier, with a discoverable
`imagegen` skill and a portable workspace-safe image tool. It preserves the
`tool-image` module ID, `image_generate` tool, Python package
`amplifier_module_tool_image`, and `amplifier.image.receipt.v1` receipts.

## Source-candidate status

[Vision and contracts](docs/DIRECTION.md) describe routed images through optional
provider capabilities, without Core changes. The current source candidate
implements that path alongside retained explicit backends. The contracts remain
drafts, not frozen; this guide is not a release or deployment announcement.
Combined offline qualification of the candidate remains pending. It establishes
no live account entitlement, image quality or host-delivery acceptance.

## Include the capability

Add the capability behavior to an existing session configuration:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-imagegen@main#subdirectory=behaviors/imagegen.yaml
```

The thin repository root also includes `behaviors/imagegen.yaml` and retains
the namespace anchor. The behavior adds the image tool, brief operating context
and on-demand skill without selecting an orchestrator, conversation provider,
account or image model. Its defaults are `model_role: image-gen` and no named
`backend`. The session's model-role resolver owns selection among permitted
mounted providers; the tool does not rank vendors.

Mounting succeeds without image support. `action: capabilities` reports local
prerequisites without selecting a route, listing remote models or generating an
image. `ready: true` is not proof that preparation will find a compatible route
or that an account is entitled to execute it.

The coordinated CLI source candidate composes this external behavior during
fresh resolution, below the selected root. Explicit app-bundle ordering and
tool overrides remain effective; saved mount plans are not retroactively
recomposed. Host composition is not a second copy of this capability.

Choosing the full behavior permits requested paid calls (`allow_paid: true`),
subject to the host's admission policy, but does not generate an image
automatically. To keep discovery and status while disabling paid calls, compose
this override last:

```yaml
tools:
  - module: tool-image
    config:
      allow_paid: false
```

For skill guidance alone, without mounting the image tool:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-imagegen@main#subdirectory=behaviors/skills.yaml
```

The skill behavior adds `@imagegen:skills` to `tool-skills` discovery. It does not
replace existing sources or set visibility/token-budget policy. Compose existing
local and user skill sources first when those overrides should take precedence.
The canonical skill name remains `imagegen`.

## Route and use

The full behavior mounts the module from
`git+https://github.com/microsoft/amplifier-bundle-imagegen@main#subdirectory=modules/tool-image`.
Without an explicit `backend`, the module mounts `RoutedImageTool`. It consumes
Foundation's generic `operation_routing.prepare_operation` helper and negotiates
`amplifier.image-operation.v1` on an exact mounted provider instance. The
resolver's top-level model remains a conversational role choice; native image
selection is carried separately in `config.image_generation: {model, transport}`.
Provider implementations own credentials, native transport and preparation.
Incompatibility may advance only within the resolver's permitted candidates
before dispatch. Failure or uncertainty after dispatch never starts another
paid attempt.

A retained explicit `backend` instead mounts `WorkspaceImageTool` against
`image.backends[backend]`. Existing named backends and explicitly configured
built-in OpenAI GPT Image, DALL-E and Google Imagen adapters retain their
compatibility behavior. The historical direct-library APIs are unchanged.
See [tool configuration and boundaries](modules/tool-image/MODERN_TOOL.md).

Call `image_generate` with `action: capabilities`, then use a stable `request_id`
for each intended `generate` or `edit`. Edits name inspected input paths and their
actual SHA-256 hashes. Original files stay intact. A cancelled, timed-out or
unknown operation is never automatically replayed; `status` reads its receipt.
Saved receipts and hashes do not prove visual inspection. Artifact presentation
and delivery of image pixels remain the host's responsibility.

## Develop and qualify

```sh
uv sync --refresh --upgrade --group dev
uv run --no-sync python -B -m pytest -q -p no:cacheprovider
```

Use an isolated deployment environment and caches; do not point a scratch
`AMPLIFIER_HOME` at an active installation's shared environment. Tests prohibit
network calls, retain the module's offline suite, and exercise real Foundation
composition, skill loading and Core activation through a subdirectory source URI.
Resolved dependency revisions and test results are recorded under `validation/`.
Fresh remote Git installation, real backend/account requests, application UI and
Windows support are separate qualification boundaries. Earlier ported evidence
does not qualify the routed source candidate.

The implementation and tests were ported from the existing tested image module;
the skill was ported from the existing portable skill library. Original sources
and histories remain intact. See [provenance](PROVENANCE.md) and the preserved
[upstream notices](modules/tool-image/UPSTREAM-NOTICES.md).
