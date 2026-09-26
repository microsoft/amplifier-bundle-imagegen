# Provenance

This bundle relocates the portable image capability into one canonical source.
The module was copied from `bkrabach/amplifier-module-tool-image` at
`493302e10281e8c4a1e8a8179fe40cfd4ebd1eef`, without changing its Python implementation,
module/tool names, direct-library exports, or receipt protocol. Its original
history and consumers remain intact. The packaged module now lives under
`modules/tool-image`; dependency and source references use the canonical bundle.

The `imagegen` skill is copied unchanged from
[`microsoft/amplifier-bundle-work` at `311a56b4620f82fb755260e45b7679cc3dc17629`](https://github.com/microsoft/amplifier-bundle-work/blob/311a56b4620f82fb755260e45b7679cc3dc17629/skills/imagegen/SKILL.md).
This is source attribution, not a runtime dependency on a consuming bundle.
The skill is discovered through this bundle's `@imagegen:skills` namespace.

The module derives from
[robotdad/amplifier-module-image-generation at `79836889ee0787b44206ce6a48492a5aec476282`](https://github.com/robotdad/amplifier-module-image-generation/tree/79836889ee0787b44206ce6a48492a5aec476282).
Its original client/library tests and licensing declaration are preserved; see
[upstream notices](modules/tool-image/UPSTREAM-NOTICES.md) and the
[historical provenance record](modules/tool-image/PROVENANCE.md).
No replacement license grant or attribution is invented.

Historical offline and real OpenAI generate/edit acceptance establish the
ported implementation baseline. They do not establish new remote installation,
account, application presentation, Google live-account, or Windows acceptance
for this bundle. Current local composition and source-loader results are recorded
separately in [validation](validation/README.md).

The predecessor's resolved lockfile is not an active dependency constraint here.
Mutable Git sources remain `@main`; current resolved identities are evidence.
The module's optional Core dependency has no version constraint. Third-party SDK
compatibility ranges are retained unchanged. New bundle tests cover composition,
skill-only discovery, safe missing-backend capability reporting and explicit
paid-call opt-out. The original module suite is retained unchanged.
