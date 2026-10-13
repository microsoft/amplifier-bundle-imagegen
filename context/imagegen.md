# Image generation and editing

For raster generation or edits, discover and load the `imagegen` skill through
`load_skill`. Inspect `image_generate` capabilities before making a request.
The session's model routing selects a compatible image provider independently
of the conversational model. Explicit legacy backends and paid-call opt-outs
remain effective; missing routing or support never permits an invented fallback.

Keep one request ID for each intended effect. Preserve originals and exact input
hashes for edits. Inspect saved status after a timeout, cancellation or unknown
outcome; never replay an uncertain paid effect. Deliver the saved image and its
receipt through the host's artifact and pixel-inspection facilities. A successful
receipt alone does not prove visual inspection.
