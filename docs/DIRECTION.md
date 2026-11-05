# Routed image direction: ownership and review

This packet establishes proposed direction, not a release or deployment claim.
The [README](../README.md) and [current tool documentation](../modules/tool-image/MODERN_TOOL.md)
now describe the routed source candidate and its retained explicit-backend path.
The candidate implements optional operation methods without a required Core
interface change. Combined offline qualification remains pending, and source
inspection does not establish live entitlement, image quality or host delivery.
The vision and contracts are still drafts, not ratified or frozen by this update.

## Read in order

1. [Vision](VISION.md): one portable capability, routed through permitted connections.
2. [IC — image lifecycle](../contracts/image-capability.v1.md): effect identity,
   originals, workspace boundaries and verifiable outputs.
3. [PI — provider exchange](../contracts/provider-image-operation.v1.md): optional
   preparation/execution without vendor or host dependencies.
4. [Exchange specification](IMAGE-OPERATION-SPEC.md): current experimental methods
   and data shapes, subordinate to PI rather than a second set of promises.

## One owner per boundary

| Boundary | Canonical owner | This capability's obligation |
| --- | --- | --- |
| Image intention, durable effect and artifact lifecycle | IC in this repo | Enforce and qualify the operation |
| Experimental request/plan/result exchange consumed here | PI and schema note in this repo | Validate plain data, never import provider peers |
| Generic model-role consumption | Foundation convention | Consume optional session capability, not strategy files |
| Candidate rankings and policy compatibility | Active routing implementation | Preserve selected identity, scope and refusals |
| Native wire behavior and account transport | Each provider | Call only its recognized optional surface |
| Composition, admission and presentation | Consuming host | Preserve restrictions; supply honest result evidence |

The [generic consumer draft](https://github.com/microsoft/amplifier-foundation/blob/main/contracts/model-role-consumption.v1.md)
remains a coordinated draft. Its source candidate supplies
`operation_routing.prepare_operation` and negotiates
`amplifier.operation-routing.v1`; this is not a claim of a released resolver extension.
The host/provider responsibilities below are a feature boundary grid, not another
repository's implementation guide. Concrete host and provider contracts live with
their owners; this bundle's runtime does not depend on those repositories.

| Feature | Imagegen | Provider | Routing | Host |
| --- | --- | --- | --- | --- |
| Intent identity, original files, immutable receipt | REQUIRED | EXCLUDED filesystem | EXCLUDED | REQUIRED preserve/display |
| Per-instance wire execution and native output parsing | EXCLUDED SDK policy | REQUIRED | EXCLUDED | EXCLUDED native transport |
| Ordered candidate policy | EXCLUDED | EXCLUDED cross-provider rank | REQUIRED | IDIOM generic controls |
| Effective admission and permission | REQUIRED respect | REQUIRED obey bound plan | REQUIRED preserve scope | REQUIRED enforce applicable guards |
| Pixel inspection and result presentation | REQUIRED distinct evidence | EXCLUDED visual approval | EXCLUDED | IDIOM; no stronger claims |
| Mandatory kernel image extension | EXCLUDED | EXCLUDED | EXCLUDED | EXCLUDED |

REQUIRED describes adoption acceptance, not current conformance. IDIOM allows
presentation differences; EXCLUDED identifies ownership or behavior not granted.

## Source observations

The original direction followed these source observations, not a live inference
trial. They are retained as the historical basis, not descriptions of the updated
candidate:

- `ad077609c84cb2e2b4ce971ddd16c504080ca937`: this bundle mounts `backend: images`;
  `workspace.py` already preserves input hashes and durable non-replayed receipts.
- The coordinator's generic role capability supports strategy-neutral consumers;
  current role consumers differ in fallback behavior, so a required image output
  must not inherit a chat default silently.
- Native providers differ: one can use a mainline model plus a hosted image tool;
  another directly returns native image/text outputs. Image-only models need not
  support function tools. The shared exchange cannot equate these model roles.
- Optional provider-native compaction is a precedent for capability detection
  without making the kernel's required Provider protocol larger.

Vendor/model preference evidence belongs to routing policy and provider-owned
qualification, not to this capability's vision. Product UI image support and API
entitlement are different facts. Only the selected connection can establish the latter.

## Current source candidate

- `behaviors/imagegen.yaml` defaults to `model_role: image-gen` with no named
  backend. Mount chooses `RoutedImageTool` unless an explicit `backend` retains
  `WorkspaceImageTool`. The historical direct-library APIs are unchanged.
- `routed.py` uses Foundation's generic preparation helper, local optional-method
  negotiation and exact mounted instance identity. It stores intent separately
  from route evidence and does not import provider or strategy implementations.
- Coordinated provider candidates implement capabilities, preparation and
  execution. OpenAI defaults to Responses; Gemini defaults to Interactions.
  Compatibility transports require explicit selection. Their owners retain SDK
  qualification and native request policy; no live account claim follows.
- Host candidates compose the external behavior for fresh work. Unified replaces
  image-only selection UI with non-writing legacy-intent translation; the CLI
  composes defaults below the chosen root. Saved plans, retained pins, opt-outs
  and host admission are qualification boundaries, not permission to broaden use.

These are implementation observations, not a change to the accepted direction
or a declaration that every IC/PI promise has passed. The original source notes,
contract changelogs and approval limits remain intact.

## Review and change discipline

New headings are DRAFT. The accepted scope is portable routed images with no Core
changes; exact new words and schema have not been ratified or frozen.
A vision states the destination; contract clauses state observable promises;
this note holds ownership, source facts and remaining review gates.

No implementation ledger, task queue, scheduled check, manager operation or hook
installation is created merely to establish these documents. No claim of full
method adoption is made. Future locking requires a clear specification, a
machine-checkable good/bad pair, a passing real implementation, a worked example
at the user-visible boundary and the steward's decision.

Amend draft text transparently; record accepted direction changes in its changelog.
If a document is later locked, propose exact changes beside it and leave the
locked target unchanged until approved. Do not copy private project records into
these public sources. Cross-repository evidence uses explicit source revisions;
installation manifests continue to follow their owning repository's source policy.
