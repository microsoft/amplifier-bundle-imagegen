"""Explicit adapters for the existing clients; no fallback or filesystem access.

Hosts can instead register their own image.backends implementation. This optional
adapter uses only the named library client and never creates the other clients.
"""

import math
import os

from .clients import DalleClient, GptImageClient, ImagenClient


class ClientBackend:
    def __init__(self, kind, model, timeout=None, *, vertexai=None):
        if kind not in {"imagen", "dalle", "gptimage"}:
            raise ValueError("builtin must be imagen, dalle or gptimage")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Choose an explicit image model")
        self.kind, self.model = kind, model
        if vertexai is not None and (
            kind != "imagen" or not isinstance(vertexai, bool)
        ):
            raise ValueError("vertexai is a boolean option for the Imagen backend only")
        self.vertexai = vertexai
        self.timeout = float(timeout) if timeout is not None else None
        if self.timeout is not None and (
            isinstance(timeout, bool)
            or self.timeout <= 0
            or not math.isfinite(self.timeout * 1000)
        ):
            raise ValueError(
                "timeout must be positive, finite seconds representable in milliseconds, or null"
            )
        self.client = None
        self.closed = False

    def describe(self):
        key = "GOOGLE_API_KEY" if self.kind == "imagen" else "OPENAI_API_KEY"
        quality = {"imagen": "standard", "dalle": "standard", "gptimage": "low"}[
            self.kind
        ]
        options = {
            "size": ["1024x1024"],
            "quality": [quality],
            "background": ["opaque"],
        }
        if self.kind == "dalle":
            options.update(
                size=["1024x1024", "1792x1024", "1024x1792"], quality=["standard", "hd"]
            )
        elif self.kind == "gptimage":
            options.update(
                size=["1024x1024", "1536x1024", "1024x1536"],
                quality=["low", "medium", "high"],
                background=["opaque", "transparent", "auto"],
            )
        missing = []
        if not os.environ.get(key, "").strip() or self.closed:
            missing.append("selected_backend_configuration")
        if self.kind == "imagen" and self.vertexai is not True:
            missing.append("explicit_vertexai_api_key_mode_required")
        configured = not missing
        return {
            "provider": self.kind,
            "model": self.model,
            "configured": configured,
            "missing": missing,
            "apiMode": "vertex_api_key" if self.kind == "imagen" else "openai_images",
            "operations": ["generate", "edit"]
            if self.kind == "gptimage"
            else ["generate"],
            "outputFormats": ["png"],
            "automaticRetries": False,
            "timeoutSeconds": self.timeout,
            "entitlement": "unverified_until_successful_request",
            "defaults": {
                "size": "1024x1024",
                "quality": quality,
                "background": "opaque",
            },
            "options": options,
        }

    async def generate(self, *, action, prompt, images, size, quality, background):
        descriptor = self.describe()
        if not descriptor["configured"]:
            raise ValueError("The selected backend is not configured or is closed")
        if action not in descriptor["operations"] or (action == "edit") != bool(images):
            raise ValueError("The selected backend does not support this operation")
        for key, value in {
            "size": size,
            "quality": quality,
            "background": background,
        }.items():
            if value not in descriptor["options"][key]:
                raise ValueError(f"Unsupported {key} for selected backend")
        if self.client is None:
            if self.kind == "imagen":
                self.client = ImagenClient(vertexai=True, single_attempt=True)
            else:
                self.client = {"dalle": DalleClient, "gptimage": GptImageClient}[
                    self.kind
                ]()
        return await self.client.generate_bytes(
            prompt=prompt,
            model=self.model,
            action=action,
            images=images,
            size=size,
            quality=quality,
            background=background,
            timeout=self.timeout,
        )

    async def close(self):
        if self.closed:
            return
        self.closed = True
        if self.client is not None and self.client.client is not None:
            if self.kind == "imagen":
                try:
                    await self.client.client.aio.aclose()
                finally:
                    self.client.client.close()
            else:
                await self.client.client.close()


def register_builtin(coordinator, config):
    """Register exactly the requested environment-backed client, if any."""
    backend = None
    identity = config.get("backend")
    if config.get("builtin") is not None:
        if not isinstance(identity, str) or not identity or len(identity) > 100:
            raise ValueError("Choose an explicit backend identifier")
        current = dict(coordinator.get_capability("image.backends") or {})
        if identity in current:
            raise ValueError("An image backend with this id is already registered")
        backend = ClientBackend(
            config["builtin"],
            config.get("model"),
            config.get("timeout"),
            vertexai=config.get("vertexai"),
        )
        current[identity] = backend
        coordinator.register_capability("image.backends", current)

    async def cleanup():
        if backend is None:
            return
        current = dict(coordinator.get_capability("image.backends") or {})
        if current.get(identity) is backend:
            del current[identity]
            coordinator.register_capability("image.backends", current)
        await backend.close()

    return cleanup
