> Historical predecessor record, retained from `amplifier-module-tool-image`
> at `493302e10281e8c4a1e8a8179fe40cfd4ebd1eef`. Statements about its repository
> layout and qualification describe that source; see [bundle provenance](../../PROVENANCE.md)
> for this relocation and its separate validation.

# Image module comparison

Reviewed sources:

- robotdad/amplifier-module-image-generation at
  `79836889ee0787b44206ce6a48492a5aec476282`: the reused client/library baseline.
- kenotron-ms/amplifier-module-tool-nano-banana at
  `4aefe6ab4122d21c8fc2817c32ea32fdf5d82f33`: a reviewed design reference,
  **not copied code**.

Nano Banana uses Google Gemini `generate_content` for image analysis, comparison
and generation. It supports model aliases/per-call selection, reference images
(up to fourteen in its schema), and an expert workflow. Its retry/fallback policy
is separate from this module’s explicit-backend, no-automatic-replay contract.

| Capability | This module and its host integration | Remaining distinction |
| --- | --- | --- |
| Generate a saved image | Mounted generation with host-selected backend and receipt | Model and account support belong to the selected backend |
| Revise a saved image using references | Edit supports a target plus three references, exact input hashes and lineage | Not Nano Banana’s fourteen-reference schema |
| Inspect or compare saved images | Unified’s separate supported image-delivery path can send actual pixels to its conversational provider | This module itself does not implement an analyze/compare model |
| Google generation | Explicit Imagen Vertex API-key adapter, generation only | Gemini reference-based `generate_content` generation remains an optional backend gap |

For revisions where appearance must be retained, pass the actual target image as
the first input and use additional actual images as references; do not replace
visual references with a textual description. State what should change and what
should remain, then inspect the saved result through the host’s pixel path. Exact
input hashes and lineage document the inputs, not a guarantee of model fidelity.

A conversational provider and an image-generation backend need not be the same
vendor. Keeping explicit backend/model selection preserves that separation and
avoids an unknown paid effect being replayed or switched to another model. This
fresh-history release intentionally retains the tested implementation and does
not claim equivalent Google Gemini support or add unqualified retry/fallback
behavior.
