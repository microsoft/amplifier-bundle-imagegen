# Image generation and editing

For raster generation or edits, discover and load the `imagegen` skill through
`load_skill`. Inspect `image_generate` capabilities before making a request.
The host explicitly selects the image backend, account and model independently
of the conversational provider; missing configuration does not permit a fallback.

Keep one request ID for each intended effect. Preserve originals and exact input
hashes for edits. Inspect saved status after a timeout, cancellation or unknown
outcome; never replay an uncertain paid effect. Deliver the saved image and its
receipt through the host's artifact and pixel-inspection facilities. A successful
receipt alone does not prove visual inspection.
