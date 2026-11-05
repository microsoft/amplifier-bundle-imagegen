# Portable image capability — v1 (DRAFT 2026-10-13)

The lifecycle of one requested image effect, independent of its host or vendor.

## Who builds against this

People generating and editing images, tool callers, and hosts that retain and
present the artifacts. The [vision](../docs/VISION.md) gives the direction;
[provider exchange](provider-image-operation.v1.md) owns the transport boundary.

## What it is

A stable tool request produces a new workspace artifact and an inspectable receipt.
The following is illustrative, not a new executable schema:

```text
generate request-1 -> image-1 + completed receipt
edit request-2 using hash(image-1) -> image-2 + parent lineage
read request-1 after restart -> saved receipt; no new generation
```

## The promises

1. **IC1 — Compose without replacing.** The behavior adds the image tool and its
   guidance without selecting a root, chat provider or orchestration system.
   Broken: adding image support changes the host's chosen conversation setup.
2. **IC2 — Route without guessing.** New effects use the session's generic role
   resolver or an explicit retained override; image-output requirements remain
   mandatory. Broken: a missing route uses an arbitrary account or returns prose.
3. **IC3 — Preserve an effect's identity.** An intent hash covers operation,
   prompt, controls and input hashes; a separate plan records the admitted route.
   Broken: retrying an old identity consults new policy and sends again.
4. **IC4 — Keep uncertainty durable.** Reserve and persist before transmission;
   cancellation, loss or an uncertain result never triggers paid replay or
   fallback. Broken: recovery creates a second effect under the same intention.
5. **IC5 — Respect files and originals.** Inputs are inspected, hash-verified
   workspace files under effective read policy; outputs obey write policy and
   never replace inputs. Broken: a child bypasses a denial or destroys a parent.
6. **IC6 — Verify the promised artifact.** Validate final bytes, type, dimensions
   and supported cardinality before success. Preserve recoverable unexpected
   output as evidence. Broken: text, thought images or partials count as final.
7. **IC7 — Separate result from review.** Receipts retain route, lineage, outcome
   and reported usage without secrets. Delivery and pixel inspection are separate
   observations. Broken: a producer receipt claims visual approval or unknown cost as zero.

## Not in v1

- Video, arbitrary remote downloads and batch effects; promote after a separate
  permission and lifecycle design is accepted.
- Mandatory server-side continuation or storage; promote after retention and
  exact account-bound replay are qualified.
- More than one delivered image per tool request; promote with bounded multi-output
  persistence, receipts and host presentation, not by dropping extra results.

## How the kit checks it

These are required future checks, not executed product acceptance.

| Promise | Good observation | Falsifier |
| --- | --- | --- |
| IC1 | Root and chat configuration unchanged after composition | Replaced instructions or provider |
| IC2 | Non-matrix resolver works; absent route makes zero sends | Hidden provider scan or text success |
| IC3 | Same ID after policy change returns saved outcome | New dispatch or conflicting intent accepted |
| IC4 | Crash at send boundary retains unknown; concurrent duplicate refused | Retry or second-account fallback |
| IC5 | Edit preserves original and child denial blocks write | Traversal, hash mismatch or overwrite accepted |
| IC6 | Decode final output; reject partial-only and wrong count | Success without the promised final artifact |
| IC7 | Receipt, delivery and inspection recorded distinctly | Secret leakage or invented verification |

## Open questions

Which receipt-version extension carries multiple model roles while retaining
existing `amplifier.image.receipt.v1` readers? Resolve with compatibility fixtures.
Locking requires a discriminating good/bad kit, a passing real implementation,
a two-host worked example and the steward's decision; none is implied by this text.

## Changelog

| Date | Change | Evidence |
| --- | --- | --- |
| 2026-10-13 | Initial IC1–IC7. | Current tool's workspace/receipt safeguards and named-backend routing gap; [source notes](../docs/DIRECTION.md#source-observations). |
