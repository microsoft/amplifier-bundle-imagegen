"""Real bundle composition and skill discovery from an unrelated workspace."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import amplifier_foundation as foundation
from amplifier_core import AmplifierSession
from amplifier_foundation.mentions import BaseMentionResolver
from amplifier_module_tool_skills import mount as mount_skills
import pytest

ROOT = Path(__file__).resolve().parents[1]
IMAGE_SOURCE = "git+https://github.com/microsoft/amplifier-bundle-imagegen@main#subdirectory=modules/tool-image"
SKILLS_SOURCE = "git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=modules/tool-skills"


def tool(bundle, name):
    return next(row for row in bundle.tools if row["module"] == name)


@pytest.mark.parametrize("manifest", ["bundle.md", "behaviors/imagegen.yaml", "behaviors/skills.yaml"])
async def test_portable_entry_points_resolve_their_own_namespace(manifest, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bundle = await foundation.load_bundle(str(ROOT / manifest), strict=True)
    bundle.resolve_pending_context()
    assert bundle.source_base_paths["imagegen"] == ROOT
    assert not bundle.providers and not bundle.session and not bundle.agents
    assert tool(bundle, "tool-skills") == {
        "module": "tool-skills", "source": SKILLS_SOURCE,
        "config": {"skills": ["@imagegen:skills"]},
    }
    if manifest == "behaviors/skills.yaml":
        assert [row["module"] for row in bundle.tools] == ["tool-skills"]
        assert not bundle.context
    else:
        assert tool(bundle, "tool-image") == {
            "module": "tool-image", "source": IMAGE_SOURCE,
            "config": {"backend": "images", "allow_paid": True},
        }
        assert ROOT / "context/imagegen.md" in bundle.context.values()


@pytest.mark.parametrize("manifest", ["behaviors/imagegen.yaml", "behaviors/skills.yaml"])
async def test_composition_preserves_host_policy_and_adds_skills(manifest):
    config = {
        "skills": [".amplifier/skills", "~/.amplifier/skills", "@existing:skills"],
        "visibility": {"enabled": False, "visibility_token_budget": 137, "priority": 7},
    }
    base = foundation.Bundle(
        name="host", providers=[{"module": "provider-existing", "config": {"default_model": "chosen"}}],
        session={"orchestrator": {"module": "host-loop"}, "context": {"module": "host-context"}},
        tools=[{"module": "tool-extra"}, {"module": "tool-skills", "config": deepcopy(config)}],
        agents={"existing": {"description": "Host-owned specialist"}}, instruction="Host-owned policy.",
    )
    behavior = await foundation.load_bundle(str(ROOT / manifest), strict=True)
    combined = base.compose(behavior)
    assert combined.providers == base.providers
    assert combined.session == base.session
    assert combined.agents == base.agents
    assert combined.instruction == base.instruction
    assert tool(combined, "tool-skills")["config"] == {
        **config, "skills": [*config["skills"], "@imagegen:skills"],
    }
    assert "tool-extra" in {row["module"] for row in combined.tools}


async def test_canonical_skill_discovery_and_loading_without_image_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bundle = await foundation.load_bundle(str(ROOT / "behaviors/skills.yaml"), strict=True)
    resolver = BaseMentionResolver(
        bundles={name: replace(bundle, base_path=path) for name, path in bundle.source_base_paths.items()},
        base_path=tmp_path,
    )
    assert resolver.resolve("@imagegen:skills") == ROOT / "skills"
    session = AmplifierSession({"session": {"orchestrator": "loop-basic", "context": "context-simple"}})
    coordinator = session.coordinator
    coordinator.register_capability("mention_resolver", resolver)
    cleanup = await mount_skills(coordinator, tool(bundle, "tool-skills")["config"])
    try:
        assert "image_generate" not in coordinator.get("tools")
        skill_tool = coordinator.get("tools")["load_skill"]
        listing = await skill_tool.execute({"list": True})
        assert listing.success
        assert set(skill_tool.skills) == {"imagegen"}
        loaded = await skill_tool.execute({"skill_name": "imagegen"})
        assert loaded.success
        assert Path(loaded.output["skill_directory"]) == ROOT / "skills/imagegen"
        assert "unknown" in loaded.output["content"]
        assert "actual path and SHA-256" in loaded.output["content"]
    finally:
        if cleanup:
            await cleanup()
        await session.cleanup()
