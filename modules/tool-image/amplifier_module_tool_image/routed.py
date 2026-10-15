"""Provider-neutral routed image effects with durable request identity.

The workspace layer owns files and receipts. Provider methods own native wire
execution; a generic resolver owns candidate order. No vendor SDK is used here.
"""
from __future__ import annotations

import asyncio
import os
from copy import deepcopy

from amplifier_core import ToolResult

from .workspace import (
    MAX_BYTES,
    MAX_SIDE,
    WorkspaceImageTool,
    digest,
    encoded,
    image_info,
)

PROTOCOL = "amplifier.image-operation.v1"
METHODS = ("get_image_generation_capabilities", "prepare_image_generation", "generate_image")


def supported(provider):
    if not all(callable(getattr(provider, name, None)) for name in METHODS):
        return False
    descriptor = provider.get_image_generation_capabilities()
    return isinstance(descriptor, dict) and descriptor.get("protocol") == PROTOCOL and descriptor.get("supported") is True


class RoutedImageTool(WorkspaceImageTool):
    description = (
        "Generate or edit raster images using the session's model routing and permitted provider connections. "
        "Call capabilities first. Edits require inspected workspace inputs and exact SHA-256 hashes; "
        "the first input is the edit target. Saves a new immutable PNG and receipt, never overwrites originals. "
        "Keep one request_id per intended effect. Existing or unknown effects are never replayed; use status. "
        "A receipt is not pixel inspection."
    )

    def capabilities(self):
        providers = self.coordinator.get("providers") or {}
        missing = []
        if not self.root:
            missing.append("session_workspace")
        if self.config.get("allow_paid") is not True:
            missing.append("paid_image_calls_not_enabled")
        if self.config.get("routing_blocked"):
            missing.append("legacy_image_selection_requires_review")
        if self.coordinator.get_capability("model_role_resolver") is None and self.config.get("provider_preferences") is None:
            missing.append("model_role_resolver")
        # Inspect local support only; never resolve a route, list remote models,
        # allocate a plan or consume strategy escalation state in discovery.
        available = []
        for key, provider in providers.items():
            if supported(provider):
                available.append(key)
        if not available:
            missing.append("image_operation_provider")
        return {"backend": "model-routing", "modelRole": self.config.get("model_role", "image-gen"),
                "ready": not missing, "missing": missing, "providerInstances": available,
                "route": "not_selected", "entitlement": "unverified_until_successful_request",
                "limits": {"outputFormat": "png", "imagesPerRequest": 1, "maxInputImages": 4,
                           "maxBytes": MAX_BYTES, "maxSide": MAX_SIDE},
                "outputDirectory": self.config.get("output_directory", "artifacts/images")}

    def _intent(self, input):
        prompt = input.get("prompt")
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 32000:
            raise ValueError("Provide a nonempty prompt up to 32000 characters.")
        options = {key: input.get(key, "auto") for key in ("size", "quality", "background")}
        for key, value in options.items():
            if value not in self.input_schema["properties"][key]["enum"]:
                raise ValueError(f"Unsupported {key}.")
        images = input.get("images", [])
        action = input["action"]
        if not isinstance(images, list) or len(images) > 4 or (action == "edit") != bool(images):
            raise ValueError("Edit needs one to four images; generation takes no input images.")
        lineage = []
        for index, item in enumerate(images):
            if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
                raise ValueError("Each input requires path and sha256.")
            import re
            if not isinstance(item["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
                raise ValueError("Each input needs an exact SHA-256.")
            path = self.path(item["path"])
            lineage.append({"path": str(path.relative_to(self.root)), "sha256": item["sha256"],
                            "role": "target" if index == 0 else "reference"})
        return {"action": action, "prompt": prompt, "options": options, "inputs": lineage}

    async def execute(self, input):
        try:
            if not isinstance(input, dict) or set(input) - set(self.input_schema["properties"]):
                raise ValueError("Unknown image request fields.")
            action = input.get("action")
            if action == "capabilities":
                return ToolResult(success=True, output=self.capabilities())
            folder = self.operation(input.get("request_id"))
            if action == "status":
                return ToolResult(success=True, output=self.status(folder))
            if action not in {"generate", "edit"}:
                raise ValueError("Choose capabilities, generate, edit or status.")
            intent = self._intent(input)
            intent_hash = digest(encoded(intent))
            # Existing identity wins before route/capability/account discovery,
            # and before re-reading inputs which may no longer be available.
            if folder.exists():
                return ToolResult(success=True, output=self.existing(folder, intent_hash))
            caps = self.capabilities()
            if not caps["ready"]:
                return ToolResult(success=False, error={"code": "unavailable", **caps})
            inputs = []
            for item in intent["inputs"]:
                data = self.read(self.path(item["path"]))
                if digest(data) != item["sha256"]:
                    raise ValueError("Edit input changed from its expected SHA-256.")
                info = image_info(data)
                inputs.append({"purpose": item["role"], "mime_type": info["mimeType"],
                               "data": data, "sha256": item["sha256"]})
            base_request = {"protocol": PROTOCOL, "request_id": folder.name,
                            "operation": action, "prompt": intent["prompt"], "inputs": inputs,
                            "output": {"count": 1, "mime_type": "image/png", **intent["options"]}}
            from amplifier_foundation.operation_routing import prepare_operation

            prepared_requests = {}
            async def prepare(provider, preference):
                if not supported(provider):
                    return None
                request = {**base_request, "selection": {"model": preference.model,
                                                         "config": deepcopy(preference.config or {})}}
                outcome = await provider.prepare_image_generation(request)
                if not isinstance(outcome, dict) or outcome.get("protocol") != PROTOCOL or type(outcome.get("supported")) is not bool:
                    raise ValueError("Invalid provider image preparation result.")
                if outcome["supported"] is False:
                    if outcome.get("reason_code") not in {"unsupported_connection", "unsupported_model_or_transport", "unsupported_model",
                        "unsupported_transport", "unsupported_controller", "unsupported_output", "unsupported_controls", "unsupported_sdk", "unsupported_reference_count"}:
                        raise ValueError("Provider image preparation failed; no fallback authorized.")
                    return None
                plan = outcome.get("plan")
                if not isinstance(plan, dict) or len(encoded(plan)) > 65536:
                    raise ValueError("Invalid or oversized provider image plan.")
                prepared_requests[id(provider)] = request
                return plan

            # Validate every possible output before preparation or admission.
            for name in ("request.json", "plan.json", "image.png", "receipt.json", *[f"evidence-{i}.png" for i in range(4)]):
                self.path(folder / name, write=True)
            selected = await prepare_operation(self.coordinator, self.config.get("model_role", "image-gen"),
                {"protocol": PROTOCOL, "operation": action, "output": base_request["output"]}, prepare,
                preferences=self.config.get("provider_preferences"))
            request = prepared_requests[id(selected.provider)]
            parent = self.directory_fd(folder.parent, create=True)
            try:
                try:
                    os.mkdir(folder.name, 0o700, dir_fd=parent)
                    os.fsync(parent)
                except FileExistsError:
                    return ToolResult(success=True, output=self.existing(folder, intent_hash))
            finally:
                os.close(parent)
            directory = self.directory_fd(folder)
            try:
                self.write(directory, "request.json", encoded({**intent, "requestHash": intent_hash, "identityVersion": 2}))
                route = {"providerInstance": selected.provider_id,
                         "preference": selected.preference.to_dict(), "plan": selected.plan}
                self.write(directory, "plan.json", encoded(route))
                try:
                    selected.assert_current(self.coordinator)
                    result = await selected.provider.generate_image(request, plan=selected.plan)
                    receipt = self._receipt(result, intent, selected.provider_id, folder, intent_hash, digest(encoded(route)), directory)
                except BaseException as exc:
                    receipt = {"schema": "amplifier.image.receipt.v1", "status": "unknown",
                        "requestId": folder.name, "requestHash": intent_hash, "errorType": type(exc).__name__,
                        "message": "The image effect did not complete locally. Read status; do not replay."}
                    self.write(directory, "receipt.json", encoded(receipt))
                    if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                        raise
                    return ToolResult(success=False, output=receipt, error={"code": "image_outcome_unknown"})
                self.write(directory, "receipt.json", encoded(receipt))
                return ToolResult(success=receipt["status"] == "completed", output=receipt)
            finally:
                os.close(directory)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            return ToolResult(success=False, error={"code": getattr(exc, "code", "invalid_image_request"), "message": str(exc)})

    def _receipt(self, result, intent, provider_id, folder, intent_hash, route_hash, directory):
        if not isinstance(result, dict) or result.get("protocol") != PROTOCOL or result.get("status") not in {"completed", "blocked", "failed", "unknown"}:
            raise ValueError("Invalid provider image result.")
        outputs = result.get("outputs", [])
        if not isinstance(outputs, list) or len(outputs) > 16:
            raise ValueError("Invalid image output list.")
        images, texts = [], []
        geometry_error = False
        for output in outputs:
            if not isinstance(output, dict):
                raise TypeError("Invalid image output.")
            if output.get("kind") == "text":
                if not isinstance(output.get("text"), str):
                    raise ValueError("Invalid accompanying text.")
                texts.append(output["text"])
            elif output.get("kind") == "image":
                data = output["data"]
                info = image_info(data)
                if output.get("mime_type") != "image/png" or info["mimeType"] != "image/png" or info["mode"] not in {"RGB", "RGBA"}:
                    raise ValueError("An RGB/RGBA PNG is required.")
                if intent["options"]["size"] != "auto" and intent["options"]["size"] != f"{info['width']}x{info['height']}":
                    geometry_error = True
                images.append((data, info))
            else:
                raise ValueError("Unsupported final output kind.")
        text = "\n".join(texts)
        if len(text) > 32000 or len(images) > 4:
            raise ValueError("Provider image output exceeds the evidence limit.")
        completed = result["status"] == "completed" and len(images) == 1 and not geometry_error
        status = "completed" if completed else ("failed" if result["status"] == "completed" else result["status"])
        models = result.get("models", [])
        metadata_error = False
        if not isinstance(models, list) or len(models) > 4:
            models, metadata_error = [], True
        image_models = [row for row in models if isinstance(row, dict) and row.get("purpose") == "image"]
        model = image_models[0].get("resolved") or image_models[0].get("requested") if len(image_models) == 1 else None
        if completed and (not isinstance(model, str) or not 0 < len(model) <= 200):
            model, metadata_error = None, True
        upstream = result.get("upstream")
        usage = result.get("usage")
        if upstream is not None and not isinstance(upstream, dict):
            upstream, metadata_error = None, True
        if usage is not None and not isinstance(usage, dict):
            usage, metadata_error = None, True
        receipt = {"schema": "amplifier.image.receipt.v1", "status": status,
            "requestId": folder.name, "requestHash": intent_hash, "planHash": route_hash,
            "operation": intent["action"], "backend": provider_id, "providerInstance": provider_id,
            "model": model, "models": models, "inputs": intent["inputs"], "options": intent["options"],
            "receiptPath": str((folder / "receipt.json").relative_to(self.root)),
            "providerRequestId": (upstream or {}).get("request_id"),
            "upstream": upstream, "usage": usage, "text": text}
        if geometry_error:
            receipt["reasonCode"] = "output_control_mismatch"
        # Validate serializability/size before saving image bytes. Private native
        # continuation is intentionally not copied into public receipts.
        try:
            if len(encoded(receipt)) > 128000:
                raise ValueError("Image receipt is too large.")
        except (ValueError, TypeError):
            metadata_error = True
            receipt.update(models=[], model=None, upstream=None, usage=None, providerRequestId=None)
        if metadata_error:
            completed = False
            receipt.update(status="failed", reasonCode="invalid_provider_metadata")
        artifacts = []
        for index, (data, info) in enumerate(images):
            name = "image.png" if completed else f"evidence-{index}.png"
            self.write(directory, name, data)
            artifacts.append({"path": str((folder / name).relative_to(self.root)),
                              "sha256": digest(data), "bytes": len(data), **info})
        if completed:
            receipt["artifact"] = artifacts[0]
        elif artifacts:
            receipt["evidenceArtifacts"] = artifacts
        return receipt
