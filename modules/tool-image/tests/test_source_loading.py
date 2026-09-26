"""Offline normal source-resolver qualification (requires Foundation installed)."""

from pathlib import Path
from unittest.mock import Mock

import pytest


async def test_local_source_uri_uses_foundation_and_core_validation(
    monkeypatch, tmp_path
):
    # Foundation is optional for standalone library users. Qualify this test in
    # an Amplifier development environment, not only an entrypoint-only runtime.
    bundle = pytest.importorskip("amplifier_foundation.bundle")
    from amplifier_core import AmplifierSession
    from amplifier_core.loader import ModuleLoader
    from amplifier_foundation.modules.activator import ModuleActivator

    import amplifier_module_tool_image as package
    from amplifier_module_tool_image import backends

    monkeypatch.setenv("AMPLIFIER_HOME", str(tmp_path / "amplifier"))
    forbidden = Mock(side_effect=AssertionError("No client or install is needed"))
    for name in ("GptImageClient", "DalleClient", "ImagenClient"):
        monkeypatch.setattr(backends, name, forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    repository = Path(__file__).resolve().parents[1]
    activator = ModuleActivator(cache_dir=tmp_path / "cache", install_deps=False)
    source_uri = repository.as_uri()
    resolver = bundle.BundleModuleResolver({}, activator=activator)
    session = AmplifierSession(
        {"session": {"orchestrator": "loop-basic", "context": "context-simple"}}
    )
    session.coordinator.register_capability("session.working_dir", str(tmp_path))
    await session.coordinator.mount("module-source-resolver", resolver)
    # This is intentionally a fresh loader with the actual Foundation resolver.
    # An installed entrypoint must not hide invalid source package layout.
    loader = ModuleLoader(coordinator=session.coordinator)
    cleanup = None
    try:
        mounted = await loader.load("tool-image", {}, source_hint=source_uri)
        cleanup = await mounted(session.coordinator)
        tool = session.coordinator.get("tools")["image_generate"]
        assert tool.input_schema["properties"]["action"]["enum"] == [
            "capabilities",
            "generate",
            "edit",
            "status",
        ]
        assert not (await tool.execute({"action": "capabilities"})).output["ready"]
        resolved = await resolver.async_resolve("tool-image", source_hint=source_uri)
        assert resolved.resolve() == repository
        assert Path(package.__file__).resolve() == repository / (
            "amplifier_module_tool_image/__init__.py"
        )
        forbidden.assert_not_called()
    finally:
        if cleanup is not None:
            await cleanup()
        await session.cleanup()
