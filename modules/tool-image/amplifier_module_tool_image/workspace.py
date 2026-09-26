"""Image effects with explicit backend selection and durable, non-replayed receipts."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import re
import stat
from pathlib import Path
from typing import ClassVar

from amplifier_core import ToolResult
from PIL import Image

__amplifier_module_type__ = "tool"
MAX_BYTES = 8 * 1024 * 1024
MAX_SIDE = 4096


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def image_info(data):
    if len(data) > MAX_BYTES:
        raise ValueError("Image exceeds the 8 MB limit.")
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("Use a PNG, JPEG or WebP image.")
        if not 0 < image.width <= MAX_SIDE or not 0 < image.height <= MAX_SIDE:
            raise ValueError("Image dimensions exceed 4096 pixels per side.")
        result = {
            "width": image.width,
            "height": image.height,
            "mimeType": Image.MIME[image.format],
            "mode": image.mode,
        }
        image.verify()
        return result


class WorkspaceImageTool:
    name = "image_generate"
    description = (
        "Generate or edit raster images with an explicitly configured image backend. "
        "Call capabilities first. Edits require inspected workspace inputs and exact SHA-256 hashes; "
        "the first input is the edit target. Produces a new immutable PNG and a receipt, never overwrites inputs. "
        "Keep one request_id per intended paid effect. An existing or unknown operation is never replayed; "
        "use status to reconcile it. Tool receipts are not visual inspection."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "action": {"enum": ["capabilities", "generate", "edit", "status"]},
            "request_id": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$",
            },
            "prompt": {"type": "string", "minLength": 1, "maxLength": 32000},
            "size": {
                "enum": [
                    "1024x1024",
                    "1536x1024",
                    "1024x1536",
                    "1792x1024",
                    "1024x1792",
                ]
            },
            "quality": {"enum": ["low", "medium", "high", "standard", "hd"]},
            "background": {"enum": ["opaque", "transparent", "auto"]},
            "images": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "path": {"type": "string"},
                        "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                    },
                    "required": ["path", "sha256"],
                },
            },
        },
        "required": ["action"],
    }

    def __init__(self, coordinator, config):
        self.coordinator, self.config = coordinator, dict(config)
        root = coordinator.get_capability("session.working_dir") or config.get(
            "working_dir"
        )
        self.root = Path(root).expanduser().resolve() if root else None

    def backend(self):
        registry = self.coordinator.get_capability("image.backends") or {}
        return registry.get(self.config.get("backend"))

    def capabilities(self):
        backend = self.backend()
        descriptor = backend.describe() if backend else {}
        missing = []
        if not self.root:
            missing.append("session_workspace")
        if self.config.get("allow_paid") is not True:
            missing.append("paid_image_calls_not_enabled")
        if not backend:
            missing.append("selected_image_backend_not_mounted")
        elif descriptor.get("configured") is not True:
            missing.extend(descriptor.get("missing", ["backend_configuration"]))
        return {
            "backend": self.config.get("backend"),
            "ready": not missing,
            "missing": missing,
            "backendStatus": descriptor,
            "entitlement": "unverified_until_successful_request",
            "limits": {
                "outputFormat": "png",
                "imagesPerRequest": 1,
                "maxInputImages": 4,
                "maxBytes": MAX_BYTES,
                "maxSide": MAX_SIDE,
            },
            "outputDirectory": self.config.get("output_directory", "artifacts/images"),
        }

    def path(self, value, *, write=False):
        if self.root is None:
            raise ValueError("A session workspace is required.")
        path = Path(value).expanduser()
        path = path if path.is_absolute() else self.root / path
        if ".." in path.parts:
            raise ValueError("Parent traversal is not allowed.")
        # All image data remains within the session workspace. A configured
        # file policy can narrow this boundary but cannot expand it.
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            raise ValueError(
                "Access denied: image files must stay in the session workspace."
            ) from None
        resolved = path.resolve()
        if resolved != path or not resolved.is_relative_to(self.root):
            raise ValueError(
                "Access denied: image paths cannot traverse symbolic links."
            )

        def policy_path(value):
            item = Path(value).expanduser()
            return (item if item.is_absolute() else self.root / item).resolve()

        kind = "write" if write else "read"
        denied = [policy_path(p) for p in self.config.get(f"denied_{kind}_paths", [])]
        allowed = [
            policy_path(p)
            for p in self.config.get(f"allowed_{kind}_paths", [str(self.root)])
        ]
        if any(resolved.is_relative_to(p) for p in denied) or not any(
            resolved.is_relative_to(p) for p in allowed
        ):
            raise ValueError("Access denied by the configured image file policy.")
        if not relative.parts:
            raise ValueError("Choose a file or image output directory.")
        return path

    def directory_fd(self, path, *, create=False):
        """Walk with openat/no-follow so symlink swaps cannot redirect writes."""
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in path.relative_to(self.root).parts:
                if create:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=fd)
                        os.fsync(fd)
                    except FileExistsError:
                        pass
                child = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
                )
                os.close(fd)
                fd = child
            return fd
        except BaseException:
            os.close(fd)
            raise

    def read(self, path):
        directory = self.directory_fd(path.parent)
        try:
            fd = os.open(
                path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
            )
            with os.fdopen(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
                    raise ValueError("Choose a regular file no larger than 8 MB.")
                data = stream.read(MAX_BYTES + 1)
                after = os.fstat(stream.fileno())
                if len(data) > MAX_BYTES or (before.st_size, before.st_mtime_ns) != (
                    after.st_size,
                    after.st_mtime_ns,
                ):
                    raise ValueError("Image changed during reading.")
                return data
        finally:
            os.close(directory)

    @staticmethod
    def write(directory, name, data):
        fd = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(directory)

    def operation(self, request_id):
        if not isinstance(request_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", request_id
        ):
            raise ValueError(
                "Provide a stable request_id of 1 to 64 letters, digits, underscores or hyphens."
            )
        return self.path(
            Path(self.config.get("output_directory", "artifacts/images")) / request_id,
            write=True,
        )

    def status(self, folder):
        if not folder.exists():
            return {"status": "not_found", "requestId": folder.name}
        # A claim without a complete result is unknown, including process death.
        result = folder / "receipt.json"
        if not result.exists():
            return {
                "status": "unknown",
                "requestId": folder.name,
                "message": "The operation was claimed. Its outcome is unknown; do not replay it.",
            }
        receipt = json.loads(self.read(result))
        if receipt.get("status") == "completed":
            data = self.read(self.path(receipt["artifact"]["path"]))
            if digest(data) != receipt["artifact"]["sha256"]:
                raise ValueError("Saved image no longer matches its receipt.")
        return receipt

    def existing(self, folder, request_hash):
        try:
            saved = json.loads(self.read(folder / "request.json"))
        except FileNotFoundError:
            return {
                "status": "unknown",
                "requestId": folder.name,
                "message": "The operation was claimed before its request identity was saved. Do not replay it.",
            }
        if saved.get("requestHash") != request_hash:
            raise ValueError("request_id already belongs to a different image request.")
        return self.status(folder)

    async def execute(self, input):
        try:
            if not isinstance(input, dict) or set(input) - set(
                self.input_schema["properties"]
            ):
                raise ValueError("Unknown image request fields.")
            action = input.get("action")
            if action == "capabilities":
                return ToolResult(success=True, output=self.capabilities())
            folder = self.operation(input.get("request_id"))
            if action == "status":
                return ToolResult(success=True, output=self.status(folder))
            if action not in {"generate", "edit"}:
                raise ValueError("Choose capabilities, generate, edit or status.")
            capabilities = self.capabilities()
            if not capabilities["ready"]:
                return ToolResult(
                    success=False, error={"code": "unavailable", **capabilities}
                )
            prompt = input.get("prompt")
            if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 32000:
                raise ValueError("Provide a nonempty prompt up to 32000 characters.")
            descriptor = capabilities["backendStatus"]
            defaults = {"size": "1024x1024", "quality": "low", "background": "opaque"}
            defaults.update(
                {
                    key: value
                    for key, value in descriptor.get("defaults", {}).items()
                    if key in defaults
                }
            )
            options = {key: input.get(key, value) for key, value in defaults.items()}
            limits = descriptor.get(
                "options",
                {
                    "size": ["1024x1024", "1536x1024", "1024x1536"],
                    "quality": ["low", "medium", "high"],
                    "background": ["opaque", "transparent", "auto"],
                },
            )
            for key, value in options.items():
                if value not in self.input_schema["properties"][key][
                    "enum"
                ] or value not in limits.get(key, []):
                    raise ValueError(f"Unsupported {key}.")
            images = input.get("images", [])
            if (
                not isinstance(images, list)
                or len(images) > 4
                or (action == "edit") != bool(images)
            ):
                raise ValueError(
                    "Edit needs one to four images; generation takes no input images."
                )
            inputs, lineage = [], []
            for index, image in enumerate(images):
                if not isinstance(image, dict) or set(image) != {"path", "sha256"}:
                    raise ValueError("Each edit input needs only path and sha256.")
                path = self.path(image["path"])
                data = self.read(path)
                if image["sha256"] != digest(data):
                    raise ValueError("Edit input changed from its expected SHA-256.")
                info = image_info(data)
                inputs.append(
                    {"data": data, "mimeType": info["mimeType"], "name": path.name}
                )
                lineage.append(
                    {
                        "path": str(path.relative_to(self.root)),
                        "sha256": digest(data),
                        "role": "target" if index == 0 else "reference",
                    }
                )
            descriptor = capabilities["backendStatus"]
            if action not in descriptor.get("operations", []):
                raise ValueError(
                    "The selected backend does not support this operation."
                )
            request = {
                "action": action,
                "prompt": prompt,
                "options": options,
                "inputs": lineage,
                "backend": capabilities["backend"],
                "model": descriptor["model"],
            }
            request_hash = digest(encoded(request))
            if folder.exists():
                return ToolResult(
                    success=True, output=self.existing(folder, request_hash)
                )
            # Validate the complete output subtree before claiming or calling.
            for name in ("request.json", "image.png", "receipt.json"):
                self.path(folder / name, write=True)
            parent = self.directory_fd(folder.parent, create=True)
            try:
                try:
                    os.mkdir(folder.name, 0o700, dir_fd=parent)
                    os.fsync(parent)
                except FileExistsError:
                    return ToolResult(
                        success=True, output=self.existing(folder, request_hash)
                    )
            finally:
                os.close(parent)
            directory = self.directory_fd(folder)
            try:
                self.write(
                    directory,
                    "request.json",
                    encoded({**request, "requestHash": request_hash}),
                )
                try:
                    result = await self.backend().generate(
                        action=action, prompt=prompt, images=inputs, **options
                    )
                    data = result["data"]
                    info = image_info(data)
                    if info["mimeType"] != "image/png" or info["mode"] not in {
                        "RGB",
                        "RGBA",
                    }:
                        raise ValueError("Backend must return an RGB/RGBA PNG.")
                    self.write(directory, "image.png", data)
                    receipt = {
                        "schema": "amplifier.image.receipt.v1",
                        "status": "completed",
                        "requestId": folder.name,
                        "requestHash": request_hash,
                        "operation": action,
                        "backend": capabilities["backend"],
                        "model": descriptor["model"],
                        "inputs": lineage,
                        "options": options,
                        "artifact": {
                            "path": str((folder / "image.png").relative_to(self.root)),
                            "sha256": digest(data),
                            "bytes": len(data),
                            **info,
                        },
                        "receiptPath": str(
                            (folder / "receipt.json").relative_to(self.root)
                        ),
                        "providerRequestId": result.get("request_id"),
                        "usage": result.get("usage"),
                    }
                except BaseException as exc:
                    receipt = {
                        "schema": "amplifier.image.receipt.v1",
                        "status": "unknown",
                        "requestId": folder.name,
                        "requestHash": request_hash,
                        "errorType": type(exc).__name__,
                        "message": "The image request did not complete locally. Do not automatically replay it.",
                    }
                    self.write(directory, "receipt.json", encoded(receipt))
                    if isinstance(
                        exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)
                    ):
                        raise
                    return ToolResult(
                        success=False,
                        output=receipt,
                        error={"code": "image_outcome_unknown"},
                    )
                self.write(directory, "receipt.json", encoded(receipt))
                return ToolResult(success=True, output=receipt)
            finally:
                os.close(directory)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            return ToolResult(
                success=False,
                error={"code": "invalid_image_request", "message": str(exc)},
            )
