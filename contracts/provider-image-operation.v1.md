# Optional provider image operation — v1 (DRAFT 2026-10-13)

The experimental exchange this capability consumes from a selected provider.

## Who builds against this

Image-operation callers and independent provider implementers exchanging prepared
requests and final outputs. This is a consumer-owned optional convention, not a
required Core interface. [The schema note](../docs/IMAGE-OPERATION-SPEC.md) owns shapes.

## What it is

The provider is the exact mounted connection, not a vendor name or a new SDK client
constructed by the tool. Preparation validates; execution creates the effect.

```text
capabilities() -> recognized protocol and local support
prepare(request) -> supported plan | safe refusal
generate(request, plan) -> final outputs | blocked | failed | unknown
```

## The promises

1. **PI1 — Negotiate optional support.** Recognized protocol version and the
   complete callable surface are required. Unsupported providers remain usable
   for ordinary work. Broken: a vision flag or missing method permits generation.
2. **PI2 — Prepare without generation.** Local descriptors cause no login or
   transmission; preparation may read the selected account's catalogue but never
   generate. Broken: compatibility discovery spends on an image or claims entitlement.
3. **PI3 — Bind before sending.** The prepared plan retains immutable request,
   exact connection, model roles, transport and effective controls. Changes refuse
   dispatch. Broken: a rebound account or model silently receives old intent.
4. **PI4 — Execute only the plan.** The provider uses its own authenticated
   transport without retries, cross-account fallback or automatic continuation.
   Broken: one admitted call produces another transmission after uncertainty.
5. **PI5 — Keep outputs ordered.** Return bounded final image bytes and optional
   text in order; exclude internal thoughts and previews. Disclose unsupported
   controls rather than ignore them. Broken: requested geometry changes silently.
6. **PI6 — Report evidence faithfully.** Requested and observed models, upstream
   IDs, usage, outcome and optional private continuation remain distinct.
   Broken: an alias becomes a claimed observed snapshot or hidden state is displayed.
7. **PI7 — Keep authority outside payloads.** Credentials, endpoints, filesystem
   authority and spending approval come from the bound runtime, never model-filled
   request fields. Broken: request options redirect or authorize a provider call.

## Not in v1

- Required methods or schema additions in amplifier-core; reconsider only after
  multiple implementations and explicit kernel-contract review.
- Generic native-state replay, arbitrary URLs, background jobs and preview streams;
  promote after account binding, retention and lifecycle checks exist.
- Uniform quality/cost across vendors; promote only after comparable evidence,
  never by equating different vendor controls.

## How the kit checks it

These are proposed discriminating checks; no provider is qualified by this file.

| Promise | Good observation | Falsifier |
| --- | --- | --- |
| PI1 | Missing/version-mismatched capability refuses before send | Duck-typed partial interface runs |
| PI2 | Catalogue-only preparation records zero generation calls | Paid probe or hidden sign-in |
| PI3 | Changed request/binding invalidates plan | Another account or model receives it |
| PI4 | Simulated disconnect leaves one attempt and unknown outcome | SDK retry or second transport |
| PI5 | Final ordered image/text validated; unsupported controls rejected | Thought output or ignored control |
| PI6 | Unknown usage stays null; continuation stays private | Invented snapshot, zero-cost claim or SDK object leak |
| PI7 | Malicious payload cannot change credentials or address | Redirected endpoint or escaped file access |

## Open questions

The exact method names and schema are experimental in the companion specification.
Promotion requires both provider implementations, a substitutable fixture provider,
a good/bad kit, a real worked example and an explicit steward decision.
No method import from a peer provider or consuming application is required.

## Changelog

| Date | Change | Evidence |
| --- | --- | --- |
| 2026-10-13 | Initial PI1–PI7 and optional exchange boundary. | Existing named backend lacks request-scoped selection; provider-native APIs differ in model roles and output shape. |
