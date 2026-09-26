"""Exercise Foundation -> Core source activation of the real module subdirectory."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import amplifier_foundation as foundation
from amplifier_core import AmplifierSession
from amplifier_core.loader import ModuleLoader
from amplifier_foundation.bundle import BundleModuleResolver
from amplifier_foundation.modules.activator import ModuleActivator
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("disable_paid", [False, True])
async def test_source_fragment_mount_discovery_and_explicit_paid_opt_out(tmp_path, monkeypatch, disable_paid):
    from amplifier_module_tool_image import backends
    forbidden_client = Mock(side_effect=AssertionError("No image client may be constructed"))
    for name in ("GptImageClient", "DalleClient", "ImagenClient"):
        monkeypatch.setattr(backends, name, forbidden_client)
    # Dependency resolution already happened in the isolated development env.
    # The source resolver, activator and Core loader themselves are real.
    forbidden_install = Mock(side_effect=AssertionError("No dependency install during offline tests"))
    monkeypatch.setattr("subprocess.run", forbidden_install)
    bundle = await foundation.load_bundle(str(ROOT / "bundle.md"), strict=True)
    if disable_paid:
        bundle = bundle.compose(foundation.Bundle(name="host-policy", tools=[
            {"module": "tool-image", "config": {"allow_paid": False}},
        ]))
    row = next(tool for tool in bundle.tools if tool["module"] == "tool-image")
    assert row["config"]["allow_paid"] is (not disable_paid)
    source_uri = ROOT.as_uri() + "#subdirectory=modules/tool-image"
    activator = ModuleActivator(cache_dir=tmp_path / "cache", install_deps=False, strict=True)
    resolver = BundleModuleResolver({}, activator=activator)
    session = AmplifierSession({"session": {"orchestrator": "loop-basic", "context": "context-simple"}})
    coordinator = session.coordinator
    coordinator.register_capability("session.working_dir", str(tmp_path))
    backend = SimpleNamespace(
        describe=lambda: {"configured": True, "model": "synthetic", "operations": ["generate", "edit"]},
        generate=AsyncMock(side_effect=AssertionError("No paid request may be made")),
    )
    if disable_paid:
        coordinator.register_capability("image.backends", {"images": backend})
    await coordinator.mount("module-source-resolver", resolver)
    cleanup = None
    try:
        loader = ModuleLoader(coordinator=coordinator)
        mount = await loader.load("tool-image", row["config"], source_hint=source_uri)
        cleanup = await mount(coordinator)
        tool = coordinator.get("tools")["image_generate"]
        assert tool.input_schema["properties"]["action"]["enum"] == ["capabilities", "generate", "edit", "status"]
        report = await tool.execute({"action": "capabilities"})
        assert report.success and not report.output["ready"]
        missing = "paid_image_calls_not_enabled" if disable_paid else "selected_image_backend_not_mounted"
        assert missing in report.output["missing"]
        assert report.output["entitlement"] == "unverified_until_successful_request"
        result = await tool.execute({"action": "generate", "request_id": "not-authorized", "prompt": "No call."})
        assert not result.success
        assert not (tmp_path / "artifacts").exists()
        resolved = await resolver.async_resolve("tool-image", source_hint=source_uri)
        assert resolved.resolve() == ROOT / "modules/tool-image"
        import amplifier_module_tool_image as package
        assert Path(package.__file__).resolve() == ROOT / "modules/tool-image/amplifier_module_tool_image/__init__.py"
        backend.generate.assert_not_awaited()
        forbidden_client.assert_not_called()
        forbidden_install.assert_not_called()
    finally:
        if cleanup:
            await cleanup()
        await session.cleanup()
