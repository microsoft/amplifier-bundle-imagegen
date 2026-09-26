# Amplifier Imagegen

Composable image generation and editing for Amplifier, with a discoverable
`imagegen` skill and a portable workspace-safe image tool. It preserves the
`tool-image` module ID, `image_generate` tool, Python package
`amplifier_module_tool_image`, and `amplifier.image.receipt.v1` receipts.

## Include the capability

Add the bundle to an existing session configuration:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-imagegen@main
```

The thin root includes `behaviors/imagegen.yaml`: image tool, brief operating
context, and the on-demand skill. It does not select an orchestrator, conversation
provider, account, or image model. The host supplies the explicitly named
`images` backend. Mounting succeeds without credentials; `action: capabilities`
reports missing configuration without making requests.

Choosing the full behavior permits requested paid calls through that configured
backend (`allow_paid: true`), but does not generate an image automatically. To
keep discovery and status while disabling paid calls, compose this override last:

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

## Configure and use

The full behavior mounts the module from
`git+https://github.com/microsoft/amplifier-bundle-imagegen@main#subdirectory=modules/tool-image`.
A host-owned backend supplies image model selection, credentials and lifecycle;
it can differ from the conversation provider. Explicit built-in OpenAI GPT Image,
DALL-E and Google Imagen adapters are also available, with different operation
support and separate credentials. There is no implicit vendor/model fallback.
See the [module contract](modules/tool-image/MODERN_TOOL.md).

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

Use an isolated environment/cache and a private `AMPLIFIER_HOME`. Tests prohibit
network calls, retain the module's offline suite, and exercise real Foundation
composition, skill loading and Core activation through a subdirectory source URI.
Resolved dependency revisions and test results are recorded under `validation/`.
Fresh remote Git installation, real backend/account requests, application UI and
Windows support are separate qualification boundaries.

The implementation and tests were ported from the existing tested image module;
the skill was ported from the existing portable skill library. Original sources
and histories remain intact. See [provenance](PROVENANCE.md) and the preserved
[upstream notices](modules/tool-image/UPSTREAM-NOTICES.md).
