"""Real SDK serialization and modern mount, with no real network or credentials."""

import base64
import hashlib
import io
import json
from importlib.metadata import entry_points
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from openai import AsyncOpenAI, InternalServerError
from PIL import Image

from amplifier_module_tool_image import ImageGenerationTool, backends, mount
from amplifier_module_tool_image.clients import (
    DalleClient,
    GptImageClient,
    ImagenClient,
)
from amplifier_module_tool_image.workspace import WorkspaceImageTool


def png():
    stream = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(stream, format="PNG")
    return stream.getvalue()


def args(**changes):
    return dict(
        prompt="A synthetic square",
        model="explicit-model",
        action="generate",
        images=[],
        size="1024x1024",
        quality="low",
        background="opaque",
        timeout=17,
        **changes,
    )


class Coordinator:
    def __init__(self, root):
        self.capabilities = {"session.working_dir": str(root)}
        self.tool = None

    def get_capability(self, name):
        return self.capabilities.get(name)

    def register_capability(self, name, value):
        self.capabilities[name] = value

    async def mount(self, namespace, tool, name):
        assert namespace == "tools" and name == "image_generate"
        self.tool = tool


async def test_modern_entrypoint_loads_and_mounts_without_changing_legacy_api(tmp_path):
    from amplifier_core import AmplifierSession
    from amplifier_core.loader import ModuleLoader

    (point,) = entry_points(group="amplifier.modules", name="tool-image")
    assert point.load() is mount
    session = AmplifierSession(
        {"session": {"orchestrator": "loop-basic", "context": "context-simple"}}
    )
    session.coordinator.register_capability("session.working_dir", str(tmp_path))
    loader = ModuleLoader()
    mounted = await loader.load("tool-image", {})
    cleanup = await mounted(session.coordinator)
    tool = session.coordinator.get("tools")["image_generate"]
    assert isinstance(tool, WorkspaceImageTool)
    assert tool.input_schema["properties"]["action"]["enum"] == [
        "capabilities",
        "generate",
        "edit",
        "status",
    ]
    assert not (await tool.execute({"action": "capabilities"})).output["ready"]
    legacy = ImageGenerationTool()
    assert legacy.name == "image-generation"
    assert legacy.input_schema["properties"]["operation"]["enum"] == [
        "generate",
        "check_availability",
        "get_cost_estimate",
    ]
    await cleanup()
    await session.cleanup()


async def test_explicit_backend_lazy_client_no_fallback_unknown_and_cleanup(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-never-sent")
    monkeypatch.setenv("GOOGLE_API_KEY", "synthetic-never-sent")
    client = SimpleNamespace(
        client=SimpleNamespace(close=AsyncMock()),
        generate_bytes=AsyncMock(side_effect=TimeoutError("unknown")),
    )
    selected = Mock(return_value=client)
    other = Mock(side_effect=AssertionError("unselected backend constructed"))
    monkeypatch.setattr(backends, "GptImageClient", selected)
    monkeypatch.setattr(backends, "ImagenClient", other)
    monkeypatch.setattr(backends, "DalleClient", other)
    coordinator = Coordinator(tmp_path)
    cleanup = await mount(
        coordinator,
        {
            "builtin": "gptimage",
            "backend": "chosen",
            "model": "chosen-model",
            "allow_paid": True,
        },
    )
    assert (await coordinator.tool.execute({"action": "capabilities"})).output["ready"]
    selected.assert_not_called()
    request = {"action": "generate", "prompt": "A square", "request_id": "one"}
    first = await coordinator.tool.execute(request)
    assert not first.success and first.output["status"] == "unknown"
    second = await coordinator.tool.execute(request)
    assert second.output["status"] == "unknown"
    assert client.generate_bytes.await_count == 1 and selected.call_count == 1
    assert client.generate_bytes.call_args.kwargs["model"] == "chosen-model"
    await cleanup()
    await cleanup()
    client.client.close.assert_awaited_once()
    assert "chosen" not in coordinator.get_capability("image.backends")


async def test_host_registry_collision_replacement_and_no_builtin_ownership(tmp_path):
    coordinator = Coordinator(tmp_path)
    original = object()
    coordinator.register_capability("image.backends", {"host": original})
    with pytest.raises(ValueError, match="already registered"):
        await mount(
            coordinator, {"builtin": "imagen", "backend": "host", "model": "imagen"}
        )
    cleanup = await mount(coordinator, {"backend": "host"})
    await cleanup()
    assert coordinator.get_capability("image.backends")["host"] is original
    cleanup = await mount(
        coordinator, {"builtin": "imagen", "backend": "new", "model": "imagen"}
    )
    selected = coordinator.get_capability("image.backends")["new"]
    coordinator.get_capability("image.backends")["new"] = original
    await cleanup()
    assert (
        selected.closed
        and coordinator.get_capability("image.backends")["new"] is original
    )


async def test_unsupported_google_edit_or_option_denied_before_claim(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("GOOGLE_API_KEY", "synthetic-never-sent")
    constructor = Mock(side_effect=AssertionError("must not create client"))
    monkeypatch.setattr(backends, "ImagenClient", constructor)
    coordinator = Coordinator(tmp_path)
    cleanup = await mount(
        coordinator,
        {
            "builtin": "imagen",
            "backend": "google",
            "model": "imagen",
            "vertexai": True,
            "allow_paid": True,
        },
    )
    image = tmp_path / "input.png"
    image.write_bytes(png())
    edit = await coordinator.tool.execute(
        {
            "action": "edit",
            "prompt": "Blue",
            "request_id": "edit",
            "images": [
                {"path": image.name, "sha256": hashlib.sha256(png()).hexdigest()}
            ],
        }
    )
    assert not edit.success and "does not support" in edit.error["message"]
    option = await coordinator.tool.execute(
        {
            "action": "generate",
            "prompt": "Blue",
            "request_id": "option",
            "quality": "high",
        }
    )
    assert not option.success and not (tmp_path / "artifacts").exists()
    constructor.assert_not_called()
    await cleanup()


@pytest.mark.parametrize("kind", [GptImageClient, DalleClient])
async def test_real_openai_inline_wire_selected_model_zero_sdk_retries(kind):
    requests = []

    async def transport(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(png()).decode()}]},
            headers={"x-request-id": "fixture-1"},
        )

    sdk = AsyncOpenAI(
        api_key="synthetic-never-sent",
        base_url="https://image.invalid/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)),
    )
    client = kind.__new__(kind)
    client.configured, client.client = True, sdk
    options = args()
    if kind is DalleClient:
        options["quality"] = "standard"
    result = await client.generate_bytes(**options)
    assert result["data"] == png() and result["request_id"] == "fixture-1"
    assert len(requests) == 1 and requests[0].url.path == "/v1/images/generations"
    body = json.loads(requests[0].content)
    assert body["model"] == "explicit-model" and body["n"] == 1
    assert requests[0].headers["x-stainless-retry-count"] == "0"
    assert body.get("response_format", body.get("output_format")) in {"b64_json", "png"}
    await sdk.close()

    requests.clear()

    async def failure(request):
        requests.append(request)
        return httpx.Response(500, json={"error": {"message": "synthetic failure"}})

    sdk = AsyncOpenAI(
        api_key="synthetic-never-sent",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(failure)),
    )
    client.client = sdk
    with pytest.raises(InternalServerError):
        await client.generate_bytes(**options)
    assert len(requests) == 1
    await sdk.close()


async def test_real_openai_edit_serializes_exact_input_without_file_writes():
    seen = []

    async def transport(request):
        seen.append(request)
        return httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
        )

    sdk = AsyncOpenAI(
        api_key="synthetic-never-sent",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)),
    )
    client = GptImageClient.__new__(GptImageClient)
    client.configured, client.client = True, sdk
    options = args()
    options.update(
        action="edit",
        images=[{"data": png(), "name": "target.png", "mimeType": "image/png"}],
    )
    result = await client.generate_bytes(**options)
    assert result["data"] == png()
    (request,) = seen
    assert request.url.path == "/v1/images/edits"
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert b'filename="target.png"' in request.content and png() in request.content
    assert b"explicit-model" in request.content and b'name="n"' in request.content
    await sdk.close()


async def test_google_async_configuration_selected_model_retry_zero_no_executor():
    call = AsyncMock(
        return_value=SimpleNamespace(
            generated_images=[SimpleNamespace(image=SimpleNamespace(image_bytes=png()))]
        )
    )
    client = ImagenClient.__new__(ImagenClient)
    client.configured = True
    client.client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_images=call))
    )
    options = args()
    options["quality"] = "standard"
    result = await client.generate_bytes(**options)
    assert result == {"data": png(), "request_id": None, "usage": None}
    sent = call.call_args.kwargs
    assert sent["model"] == "explicit-model"
    config = sent["config"]
    assert config.number_of_images == 1 and config.output_mime_type == "image/png"
    assert (
        config.http_options.timeout == 17000
        and config.http_options.retry_options.attempts == 1
    )
    assert call.await_count == 1


@pytest.mark.parametrize("status", [200, 500])
async def test_real_google_sdk_inline_wire_and_single_attempt(status):
    from google import genai
    from google.genai import errors, types

    seen = []

    async def transport(request):
        seen.append(request)
        if status == 500:
            return httpx.Response(
                500, json={"error": {"message": "Synthetic failure", "code": 500}}
            )
        return httpx.Response(
            200,
            json={
                "predictions": [
                    {
                        "bytesBase64Encoded": base64.b64encode(png()).decode(),
                        "mimeType": "image/png",
                    }
                ]
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    sdk = genai.Client(
        vertexai=True,
        api_key="synthetic-never-sent",
        http_options=types.HttpOptions(httpx_async_client=http),
    )
    client = ImagenClient.__new__(ImagenClient)
    client.configured, client.client = True, sdk
    options = args()
    options["quality"] = "standard"
    try:
        if status == 500:
            with pytest.raises(errors.ServerError):
                await client.generate_bytes(**options)
        else:
            result = await client.generate_bytes(**options)
            assert result["data"] == png()
        (request,) = seen
        assert request.url.path.endswith("/models/explicit-model:predict")
        body = json.loads(request.content)
        assert body["parameters"]["sampleCount"] == 1
        assert body["parameters"]["outputOptions"]["mimeType"] == "image/png"
        assert body["instances"] == [{"prompt": "A synthetic square"}]
    finally:
        await sdk.aio.aclose()
        sdk.close()
        await http.aclose()


async def test_close_failure_still_disables_backend_admission(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-never-sent")
    backend = backends.ClientBackend("gptimage", "model")
    sdk_close = AsyncMock(side_effect=RuntimeError("synthetic close failure"))
    backend.client = SimpleNamespace(
        client=SimpleNamespace(close=sdk_close), generate_bytes=AsyncMock()
    )
    with pytest.raises(RuntimeError, match="close failure"):
        await backend.close()
    assert backend.closed and not backend.describe()["configured"]
    with pytest.raises(ValueError, match="closed"):
        await backend.generate(
            **{
                key: value
                for key, value in args().items()
                if key not in {"model", "timeout"}
            }
        )
    await backend.close()
    sdk_close.assert_awaited_once()
    backend.client.generate_bytes.assert_not_awaited()


async def test_real_core_host_capability_generation_and_cleanup(tmp_path):
    from amplifier_core import AmplifierSession

    session = AmplifierSession(
        {"session": {"orchestrator": "fixture", "context": "fixture"}}
    )
    session.coordinator.register_capability("session.working_dir", str(tmp_path))
    backend = SimpleNamespace(
        describe=lambda: {
            "configured": True,
            "model": "host-model",
            "operations": ["generate"],
        },
        generate=AsyncMock(return_value={"data": png()}),
    )
    session.coordinator.register_capability("image.backends", {"host": backend})
    cleanup = await mount(session.coordinator, {"backend": "host", "allow_paid": True})
    tool = session.coordinator.get("tools")["image_generate"]
    result = await tool.execute(
        {"action": "generate", "request_id": "host", "prompt": "Square"}
    )
    assert result.success and result.output["model"] == "host-model"
    assert (tmp_path / result.output["artifact"]["path"]).read_bytes() == png()
    await cleanup()
    assert session.coordinator.get_capability("image.backends")["host"] is backend
    await session.cleanup()


async def test_imagen_requires_explicit_mode_without_client_or_auth_discovery(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("GOOGLE_API_KEY", "synthetic-never-sent")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    constructor = Mock(
        side_effect=AssertionError("no implicit client or auth discovery")
    )
    monkeypatch.setattr(backends, "ImagenClient", constructor)
    coordinator = Coordinator(tmp_path)
    cleanup = await mount(
        coordinator,
        {
            "builtin": "imagen",
            "backend": "google",
            "model": "model",
            "allow_paid": True,
        },
    )
    result = await coordinator.tool.execute({"action": "capabilities"})
    assert not result.output["ready"]
    assert "explicit_vertexai_api_key_mode_required" in result.output["missing"]
    constructor.assert_not_called()
    await cleanup()
