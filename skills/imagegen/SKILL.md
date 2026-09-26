---
name: imagegen
description: Generate or edit raster images using a mounted image-generation capability. Use for illustrations, photos, textures, and bitmap assets; use visualize for HTML diagrams.
compatibility: "Requires a mounted image generation or editing adapter. Text generation and filesystem tools alone cannot run this workflow."
user-invocable: true
---

# Image generation

Discover the host's mounted image-generation tools and read their actual schema.
This bundle does not install a provider, supply API credits, or inherit another
application's image-generation service. Keep provider and model selection under
the user's and host's control.

Determine whether the task creates a new image or edits an existing one. Inspect
every edit target and label reference images by role. Specify subject, framing,
style, dimensions/aspect ratio, output format, background/alpha, exact text, and
the properties an edit must preserve. Do not change an established vector asset
system into bitmaps merely because image generation is available.

Call the mounted tool with the requested constraints. Save a workspace copy of
project assets using the returned file operation, without overwriting originals
unless requested. Inspect the result for content, spelling, framing, artifacts,
and actual transparency when needed. Iterate on the failed property while
preserving accepted parts.

When `image_generate` is mounted, call `action: capabilities` first. A ready
configuration is not proof of account entitlement; only a completed provider call
establishes access. The host selects the image backend and model independently of
the conversation model. Do not enable paid calls or change accounts implicitly.
Use a stable `request_id` for one intended effect. For edits, provide each input's
actual path and SHA-256; the first input is the target and the rest are references.
Keep original files and saved output IDs. A timeout, cancellation or `unknown`
receipt does not prove no image was generated or billed: inspect `action: status`
and reconcile it before deliberately starting any new request.

Deliver the exact returned artifact and retain its receipt. If the host advertises
an image receipt attachment action, attach the completed receipt and supply the
saved original's parent ID for edits. Use the host's exact saved-image inspection
path for visual QA. A successful receipt, saved hash, or file preview alone is not
evidence that the model received pixels. Describe missing pixel delivery honestly.

If no tool is mounted, identify that requirement and continue independent work.
An external API fallback requires an available authorized provider and credentials
from host configuration; never expose secrets or silently select a paid service.
Do not describe a prompt, SVG placeholder, or unexecuted request as a generated image.
