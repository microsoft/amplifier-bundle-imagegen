import asyncio
import hashlib
from copy import deepcopy
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from amplifier_foundation.spawn_utils import ProviderPreference
from amplifier_module_tool_image.routed import PROTOCOL, RoutedImageTool
from PIL import Image


def png():
    output = BytesIO()
    Image.new("RGB", (12, 8), "red").save(output, format="PNG")
    return output.getvalue()


class Provider:
    def __init__(self):
        self.calls = 0
        self.prepares = 0
        self.failure = False
    def get_image_generation_capabilities(self):
        return {"protocol": PROTOCOL, "supported": True}
    async def prepare_image_generation(self, request):
        self.prepares += 1
        return {"protocol": PROTOCOL, "supported": True, "plan": {"operation": request["operation"]}}
    async def generate_image(self, request, *, plan):
        self.calls += 1
        if self.failure:
            raise TimeoutError("possibly sent")
        return {"protocol": PROTOCOL, "status": "completed",
                "outputs": [{"kind": "image", "mime_type": "image/png", "data": png()}],
                "models": [{"purpose": "image", "requested": "image-test", "resolved": None}],
                "upstream": {"request_id": "upstream-test"}, "usage": None}


def fixture(tmp_path, provider=None):
    provider = provider or Provider()
    providers = {"synthetic-blue": provider}
    resolver = SimpleNamespace(resolve=AsyncMock(return_value=[ProviderPreference(provider="synthetic-blue", model="agent-test", config={"image_generation": {"model": "image-test"}})]))
    caps = {"session.working_dir": str(tmp_path), "model_role_resolver": resolver}
    coordinator = SimpleNamespace(get_capability=caps.get, get=lambda name: providers)
    return RoutedImageTool(coordinator, {"allow_paid": True}), provider, resolver, providers, caps


@pytest.mark.asyncio
async def test_same_tool_nonmatrix_resolver_generate_edit_preserves_original(tmp_path):
    tool, provider, resolver, _, _ = fixture(tmp_path)
    assert (await tool.execute({"action": "capabilities"})).output["ready"]
    resolver.resolve.assert_not_called()
    first = await tool.execute({"action": "generate", "request_id": "one", "prompt": "first"})
    assert first.success and first.output["status"] == "completed"
    path = tmp_path / first.output["artifact"]["path"]
    before = path.read_bytes()
    second = await tool.execute({"action": "edit", "request_id": "two", "prompt": "second",
                                "images": [{"path": str(path), "sha256": hashlib.sha256(before).hexdigest()}]})
    assert second.success and path.read_bytes() == before
    assert second.output["inputs"][0]["sha256"] == hashlib.sha256(before).hexdigest()
    assert second.output["providerInstance"] == "synthetic-blue" and provider.calls == 2


@pytest.mark.asyncio
async def test_duplicate_identity_precedes_changed_route_and_missing_provider(tmp_path):
    tool, provider, resolver, providers, caps = fixture(tmp_path)
    request = {"action": "generate", "request_id": "one", "prompt": "first"}
    first = await tool.execute(request)
    providers.clear()
    caps.pop("model_role_resolver")
    repeated = await tool.execute(request)
    assert repeated.success and repeated.output == first.output
    assert provider.calls == 1 and resolver.resolve.await_count == 1
    bad = await tool.execute({**request, "prompt": "different"})
    assert not bad.success and "different" in bad.error["message"]


@pytest.mark.asyncio
async def test_unknown_effect_never_reroutes_or_replays(tmp_path):
    tool, provider, resolver, _, _ = fixture(tmp_path)
    provider.failure = True
    request = {"action": "generate", "request_id": "one", "prompt": "first"}
    first = await tool.execute(request)
    assert not first.success and first.output["status"] == "unknown"
    second = await tool.execute(request)
    assert second.output["status"] == "unknown" and provider.calls == 1
    assert resolver.resolve.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("selected_index", [0, 1])
@pytest.mark.parametrize("same_controller", [False, True])
async def test_negotiated_multiple_models_keep_the_selected_request(tmp_path, selected_index, same_controller):
    class BoundProvider(Provider):
        async def prepare_image_generation(self, request):
            self.prepares += 1
            return {
                "protocol": PROTOCOL,
                "supported": True,
                "plan": {"selection": deepcopy(request["selection"])},
            }

        async def generate_image(self, request, *, plan):
            assert request["selection"] == plan["selection"], "Prepared request changed"
            self.executed_selection = deepcopy(request["selection"])
            return await super().generate_image(request, plan=plan)

    provider = BoundProvider()
    tool, _, _, providers, caps = fixture(tmp_path, provider)
    preferences = [
        ProviderPreference(
            provider="synthetic-blue",
            model="agent-shared" if same_controller else f"agent-{index}",
            config={"image_generation": {"model": f"image-{index}"}},
        )
        for index in range(2)
    ]

    async def resolve_for(role, *, requirements, accept):
        assert role == "image-gen" and requirements["protocol"] == PROTOCOL
        for preference in preferences:
            assert await accept(preference) is True
        return [preferences[selected_index]]

    caps["model_role_resolver"] = SimpleNamespace(
        operation_resolution_protocol="amplifier.operation-routing.v1",
        resolve_for=resolve_for,
    )
    request = {"action": "generate", "request_id": "two-models", "prompt": "first"}
    result = await tool.execute(request)
    assert result.success and result.output["status"] == "completed"
    expected = preferences[selected_index]
    assert provider.executed_selection == {"model": expected.model, "config": expected.config}
    assert provider.prepares == 2 and provider.calls == 1

    saved = {path.name: path.read_bytes() for path in (tmp_path / "artifacts/images/two-models").iterdir()}
    providers.clear()
    caps.pop("model_role_resolver")
    repeated = await RoutedImageTool(tool.coordinator, {"allow_paid": True}).execute(request)
    assert repeated.output == result.output
    assert provider.prepares == 2 and provider.calls == 1
    assert {path.name: path.read_bytes() for path in (tmp_path / "artifacts/images/two-models").iterdir()} == saved


@pytest.mark.asyncio
@pytest.mark.parametrize("include_healthy", [False, True])
async def test_broken_local_descriptor_does_not_hide_other_connections(tmp_path, include_healthy):
    class BrokenDescriptor(Provider):
        def get_image_generation_capabilities(self):
            raise RuntimeError("private-connection-detail-must-not-leak")

    tool, healthy, resolver, providers, _ = fixture(tmp_path)
    broken = BrokenDescriptor()
    providers.clear()
    providers["synthetic-broken"] = broken
    if include_healthy:
        providers["synthetic-blue"] = healthy
    result = await tool.execute({"action": "capabilities"})
    assert result.success
    assert result.output["providerInstances"] == (["synthetic-blue"] if include_healthy else [])
    assert result.output["ready"] is include_healthy
    assert result.output["providerDiagnostics"] == [
        {"providerInstance": "synthetic-broken", "reasonCode": "invalid_provider_capability"}
    ]
    assert "private-connection-detail-must-not-leak" not in repr(result)
    assert broken.calls == broken.prepares == healthy.calls == healthy.prepares == 0
    resolver.resolve.assert_not_called()


@pytest.mark.asyncio
async def test_selected_broken_descriptor_stops_without_fallback_or_secret(tmp_path):
    class BrokenDescriptor(Provider):
        def get_image_generation_capabilities(self):
            raise RuntimeError("private-connection-detail-must-not-leak")

    tool, healthy, resolver, providers, _ = fixture(tmp_path)
    broken = BrokenDescriptor()
    providers["synthetic-broken"] = broken
    resolver.resolve.return_value.insert(
        0, ProviderPreference(provider="synthetic-broken", model="agent-test")
    )
    assert (await tool.execute({"action": "capabilities"})).output["ready"] is True
    resolver.resolve.assert_not_called()
    result = await tool.execute({"action": "generate", "request_id": "broken", "prompt": "first"})
    assert not result.success
    resolver.resolve.assert_awaited_once_with("image-gen")
    assert result.error["code"] == "invalid_provider_capability"
    assert "private-connection-detail-must-not-leak" not in repr(result)
    assert broken.calls == broken.prepares == healthy.calls == healthy.prepares == 0
    assert not (tmp_path / "artifacts/images/broken").exists()


@pytest.mark.asyncio
async def test_cancelled_descriptor_is_not_hidden_as_unsupported(tmp_path):
    class CancelledDescriptor(Provider):
        def get_image_generation_capabilities(self):
            raise asyncio.CancelledError

    tool, provider, _, _, _ = fixture(tmp_path, CancelledDescriptor())
    with pytest.raises(asyncio.CancelledError):
        await tool.execute({"action": "capabilities"})
    assert provider.calls == provider.prepares == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["unsupported_sdk", "unsupported_interactions_sdk"])
async def test_sdk_incompatibility_considers_only_declared_next_candidate(tmp_path, reason):
    class RefusingProvider(Provider):
        async def prepare_image_generation(self, request):
            self.prepares += 1
            return {"protocol": PROTOCOL, "supported": False, "reason_code": reason}

    first = RefusingProvider()
    tool, _, resolver, providers, _ = fixture(tmp_path, first)
    second, undeclared = Provider(), Provider()
    providers.update({"synthetic-green": second, "synthetic-other": undeclared})
    resolver.resolve.return_value.append(ProviderPreference(provider="synthetic-green", model="agent-test"))
    result = await tool.execute({"action": "generate", "request_id": "compatible", "prompt": "first"})
    assert result.success and result.output["providerInstance"] == "synthetic-green"
    assert first.prepares == 1 and first.calls == 0
    assert second.prepares == second.calls == 1
    assert undeclared.prepares == undeclared.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["binding_changed", "unsupported_sdk_or_binding", "unrecognized_refusal"])
async def test_unknown_or_binding_refusals_never_authorize_next_candidate(tmp_path, reason):
    class RefusingProvider(Provider):
        async def prepare_image_generation(self, request):
            self.prepares += 1
            return {"protocol": PROTOCOL, "supported": False, "reason_code": reason}

    first = RefusingProvider()
    tool, _, resolver, providers, _ = fixture(tmp_path, first)
    second = Provider()
    providers["synthetic-green"] = second
    resolver.resolve.return_value.append(ProviderPreference(provider="synthetic-green", model="agent-test"))
    result = await tool.execute({"action": "generate", "request_id": "refused", "prompt": "first"})
    assert not result.success
    assert first.prepares == 1 and first.calls == second.prepares == second.calls == 0
    assert not (tmp_path / "artifacts/images/refused/request.json").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "dispatch", "reason"),
    [
        ("failed", "response_received", "invalid_response"),
        ("unknown", "unknown", "generation_outcome_unknown"),
        ("unknown", "response_received", "incomplete_response"),
    ],
)
async def test_result_dispatch_evidence_survives_direct_retry_and_status(tmp_path, status, dispatch, reason):
    tool, provider, resolver, providers, caps = fixture(tmp_path)
    original = provider.generate_image

    async def unsuccessful(*args, **kwargs):
        result = await original(*args, **kwargs)
        result.update(status=status, dispatch_state=dispatch, reason_code=reason)
        return result

    provider.generate_image = unsuccessful
    request = {"action": "generate", "request_id": "outcome", "prompt": "first"}
    first = await tool.execute(request)
    assert not first.success
    assert first.output["status"] == status
    assert first.output["dispatchState"] == dispatch
    assert first.output["reasonCode"] == reason
    evidence = tmp_path / first.output["evidenceArtifacts"][0]["path"]
    assert evidence.read_bytes() == png()
    saved = {path.name: path.read_bytes() for path in evidence.parent.iterdir()}
    providers.clear()
    caps.pop("model_role_resolver")
    restored = RoutedImageTool(tool.coordinator, {"allow_paid": True})
    assert (await restored.execute(request)).output == first.output
    assert (await restored.execute({"action": "status", "request_id": "outcome"})).output == first.output
    assert {path.name: path.read_bytes() for path in evidence.parent.iterdir()} == saved
    assert provider.prepares == provider.calls == resolver.resolve.await_count == 1


@pytest.mark.asyncio
async def test_denied_file_and_paid_policy_precede_preparation(tmp_path):
    tool, provider, resolver, _, _ = fixture(tmp_path)
    request = {"action": "generate", "request_id": "one", "prompt": "first"}
    tool.config["denied_write_paths"] = [str(tmp_path / "artifacts")]
    assert not (await tool.execute(request)).success
    assert provider.calls == provider.prepares == 0
    resolver.resolve.assert_not_called()
    tool.config.pop("denied_write_paths")
    tool.config["allow_paid"] = False
    assert not (await tool.execute(request)).success and provider.calls == 0


@pytest.mark.asyncio
async def test_concurrent_duplicate_only_dispatches_once(tmp_path):
    tool, provider, _, _, _ = fixture(tmp_path)
    request = {"action": "generate", "request_id": "one", "prompt": "first"}
    results = await asyncio.gather(tool.execute(deepcopy(request)), tool.execute(deepcopy(request)))
    assert all(result.success for result in results) and provider.calls == 1


@pytest.mark.asyncio
async def test_extra_final_images_are_evidence_not_completed_success(tmp_path):
    tool, provider, _, _, _ = fixture(tmp_path)
    original = provider.generate_image
    async def multiple(*args, **kwargs):
        result = await original(*args, **kwargs)
        result["outputs"] *= 2
        return result
    provider.generate_image = multiple
    result = await tool.execute({"action": "generate", "request_id": "one", "prompt": "first"})
    assert not result.success and result.output["status"] == "failed"
    assert len(result.output["evidenceArtifacts"]) == 2 and "artifact" not in result.output
    assert not (tmp_path / "artifacts/images/one/image.png").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["receipt.json", "request.json"])
async def test_saved_metadata_respects_denied_read_paths(tmp_path, name):
    tool, provider, _, _, _ = fixture(tmp_path)
    request = {"action": "generate", "request_id": "one", "prompt": "first"}
    assert (await tool.execute(request)).success
    tool.config["denied_read_paths"] = [f"artifacts/images/one/{name}"]
    query = {"action": "status", "request_id": "one"} if name == "receipt.json" else request
    denied = await tool.execute(query)
    assert not denied.success and "denied" in denied.error["message"].lower()
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_malformed_metadata_keeps_recoverable_bytes_without_success(tmp_path):
    tool, provider, _, _, _ = fixture(tmp_path)
    original = provider.generate_image
    async def malformed(*args, **kwargs):
        result = await original(*args, **kwargs)
        result["upstream"] = ["not a mapping"]
        return result
    provider.generate_image = malformed
    result = await tool.execute({"action": "generate", "request_id": "one", "prompt": "first"})
    assert not result.success and result.output["status"] == "failed"
    path = tmp_path / result.output["evidenceArtifacts"][0]["path"]
    assert path.read_bytes() == png()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_status", ["completed", "unknown"])
async def test_geometry_mismatch_keeps_evidence_through_restart_without_replay(tmp_path, provider_status):
    tool, provider, resolver, providers, caps = fixture(tmp_path)
    original = provider.generate_image

    async def mismatched(*args, **kwargs):
        result = await original(*args, **kwargs)
        result["status"] = provider_status
        return result

    provider.generate_image = mismatched
    request = {"action": "generate", "request_id": "one", "prompt": "first", "size": "1024x1024"}
    first = await tool.execute(request)
    assert not first.success and first.output["status"] != "completed"
    assert "artifact" not in first.output
    path = tmp_path / first.output["evidenceArtifacts"][0]["path"]
    assert path.read_bytes() == png()
    assert not (path.parent / "image.png").exists()
    saved = {p.name: p.read_bytes() for p in path.parent.iterdir()}
    providers.clear()
    caps.pop("model_role_resolver")
    restored = RoutedImageTool(tool.coordinator, {"allow_paid": True})
    repeat = await restored.execute(request)
    assert repeat.output == first.output
    assert (await restored.execute({"action": "status", "request_id": "one"})).output == first.output
    assert {p.name: p.read_bytes() for p in path.parent.iterdir()} == saved
    assert provider.calls == provider.prepares == resolver.resolve.await_count == 1


def test_corrupt_pixel_stream_is_not_a_valid_image():
    import struct
    import zlib

    from amplifier_module_tool_image.workspace import image_info
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    corrupt = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0)) + chunk(b"IDAT", b"invalid zlib") + chunk(b"IEND", b"")
    with pytest.raises(OSError):
        image_info(corrupt)
