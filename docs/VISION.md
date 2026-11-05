# Imagegen — Vision (DRAFT 2026-10-13)

This is the destination for this capability, written as though already true.
It is not a report of shipped behavior. Changes of direction land here before
implementation; execution evidence belongs in validation records.
The contracts state the observable promises; this page does not duplicate them.
The document set and review boundaries are indexed in [Direction](DIRECTION.md).

## What imagegen is

Imagegen is a portable image-making capability for an agent already at work.
A person describes an image or an edit, and receives a durable artifact whose
origin and outcome remain inspectable. The capability uses the session's model
routing and connected providers rather than requiring a separate image account
picker. The conversational model can differ from the model making the image.
The same behavior composes into a terminal host or a graphical host without
replacing that host's chosen root, instructions, orchestrator or context manager.

## Principles

### 1. Ask for a result, not a backend

The person supplies creative intent and the inputs that matter.
The active routing strategy selects the best compatible route within the
person's permitted connections. A missing route produces an understandable
limitation, not a hidden search for another credential or service.

### 2. The operation is portable

The tool is a thin adapter around reusable image-operation logic.
Providers own their native API and account behavior; hosts own their normal
permissions and presentation. Neither an application menu nor a vendor SDK
becomes part of the portable creative workflow.

### 3. Selection and execution are different

A selected model is not proof that its account can generate an image.
The capability distinguishes a supported interface, a prepared route, a sent
request and a verified artifact. A model catalogue does not grant entitlement,
and a familiar provider name does not identify an exact account.

### 4. One intention has one durable identity

An interrupted operation remains the same operation after a restart.
Its saved outcome is consulted before a new routing decision can be made.
A timeout does not become permission to send another paid request, and a
policy update does not reinterpret an already admitted effect.

### 5. Editing preserves what came before

Every edit begins with inspected inputs and produces a new artifact.
The original remains available, and the relationship between versions is
explicit. Provider-native continuation can improve a workflow without becoming
the only copy of the person's images or silently changing data retention.

### 6. Optional capabilities stay optional

A provider offers image operations through a small versioned convention.
Providers without that convention still serve their ordinary purposes.
This capability evolves without changing the required kernel provider contract
or making one routing implementation a dependency of the image tool.

### 7. Evidence has a precise meaning

A receipt records the effect and the bytes returned; it is not a visual review.
The host can show, inspect and deliver those bytes without making another image.
Unknown usage, entitlement or provider-reported model versions remain unknown.
No observer upgrades a successful local test into a live account claim.

## What this deliberately resists

- A second provider-settings system hidden behind an image-generation menu.
- Hardcoded vendor rankings or automatic paid fallback inside the image tool.
- Replacing the conversation's model with an image-only, non-tool-capable model.
- Peer-provider imports, host-specific code or a mandatory kernel extension.
- Treating image understanding, a preview or a prose answer as a generated image.

## How you can tell it is working

- A person completes 1 generate-and-edit cycle in each of 2 host styles with
  0 image-specific account settings, using already permitted connections.
- An operator changes the routing strategy between 2 new requests and sees
  each receipt name the actual route without changing the conversational model.
- An operator repeats 1 completed or uncertain request after a restart and
  observes 0 additional generation transmissions for that identity.
- A reviewer compares an original and 1 edited version, finds both exact files,
  and can distinguish saved bytes from a separate pixel-inspection record.
- A maintainer substitutes 1 non-matrix resolver and 1 unsupported provider;
  the former can serve the same tool and the latter makes 0 image requests.

## Changelog

| Date | Change | Evidence |
| --- | --- | --- |
| 2026-10-13 | Initial direction for portable routed image operations. | Existing named-backend tool, duplicated host image selection and optional provider compaction precedent; see [source notes](DIRECTION.md#source-observations). |
