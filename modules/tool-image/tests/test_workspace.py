import asyncio
import hashlib
import io
import json
import os
import stat
from types import SimpleNamespace

import pytest
from PIL import Image

from amplifier_module_tool_image import mount
from amplifier_module_tool_image.workspace import WorkspaceImageTool as ImageTool


def png(color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color).save(buffer, format="PNG")
    return buffer.getvalue()


class Backend:
    def __init__(self):
        self.calls = []
        self.error = None
        self.wait = None

    def describe(self):
        return {
            "configured": True,
            "model": "fixture",
            "operations": ["generate", "edit"],
        }

    async def generate(self, **args):
        self.calls.append(args)
        if self.wait:
            await self.wait.wait()
        if self.error:
            raise self.error
        return {
            "data": png("blue" if args["action"] == "edit" else "red"),
            "request_id": "fixture-call",
        }


@pytest.fixture
def setup(tmp_path):
    backend = Backend()
    capabilities = {
        "session.working_dir": str(tmp_path),
        "image.backends": {"fixture": backend},
    }
    coordinator = SimpleNamespace(get_capability=capabilities.get)
    tool = ImageTool(coordinator, {"allow_paid": True, "backend": "fixture"})
    return tool, backend, tmp_path, capabilities


def request(identity="first", **kwargs):
    return {
        "action": "generate",
        "request_id": identity,
        "prompt": "An original red square.",
        **kwargs,
    }


async def test_generation_edit_lineage_exact_bytes_and_no_replay_after_restart(setup):
    tool, backend, root, capabilities = setup
    first = await tool.execute(request())
    assert first.success, first.error
    receipt = first.output
    path = root / receipt["artifact"]["path"]
    original = path.read_bytes()
    assert original == png()
    assert hashlib.sha256(original).hexdigest() == receipt["artifact"]["sha256"]
    restarted = ImageTool(SimpleNamespace(get_capability=capabilities.get), tool.config)
    assert (await restarted.execute(request())).output == receipt
    assert len(backend.calls) == 1
    edit = await restarted.execute(
        request(
            "second",
            action="edit",
            prompt="Make it blue.",
            images=[
                {
                    "path": str(path.relative_to(root)),
                    "sha256": receipt["artifact"]["sha256"],
                }
            ],
        )
    )
    assert edit.success, edit.error
    assert edit.output["inputs"][0] == {
        "path": str(path.relative_to(root)),
        "sha256": receipt["artifact"]["sha256"],
        "role": "target",
    }
    assert backend.calls[1]["images"][0]["data"] == original
    assert path.read_bytes() == original
    assert (root / edit.output["artifact"]["path"]).read_bytes() == png("blue")
    assert (
        await restarted.execute({"action": "status", "request_id": "second"})
    ).output == edit.output
    changed = await restarted.execute(request(prompt="A different request"))
    assert not changed.success and "different" in changed.error["message"]
    assert len(backend.calls) == 2


async def test_preflight_capability_and_validation_fail_before_any_paid_call(setup):
    tool, backend, root, capabilities = setup
    tool.config["allow_paid"] = False
    report = await tool.execute({"action": "capabilities"})
    assert report.success and not report.output["ready"]
    assert not (await tool.execute(request())).success
    tool.config["allow_paid"] = True
    capabilities["image.backends"] = {}
    assert not (await tool.execute(request())).success
    capabilities["image.backends"] = {"fixture": backend}
    (root / "input.png").write_bytes(png())
    for args in [
        request(size="99999x1"),
        request(quality="max"),
        request(action="edit"),
        request(request_id="../escape"),
        request(extra="unknown"),
        request(action="edit", images=[{"path": "input.png", "sha256": "0" * 64}]),
        request(action="generate", images=[{"path": "input.png", "sha256": "0" * 64}]),
    ]:
        assert not (await tool.execute(args)).success
    assert backend.calls == []
    assert not (root / "artifacts").exists()


async def test_denied_paths_symlink_and_non_regular_input_are_rejected(setup, tmp_path):
    tool, backend, root, _ = setup
    tool.config["denied_write_paths"] = ["artifacts/images"]
    denied = await tool.execute(request())
    assert not denied.success and "Access denied" in denied.error["message"]
    tool.config.pop("denied_write_paths")
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    (root / "artifacts").symlink_to(outside, target_is_directory=True)
    assert not (await tool.execute(request())).success
    (root / "artifacts").unlink()
    (root / "input.png").symlink_to(outside / "secret.png")
    assert not (
        await tool.execute(
            request(action="edit", images=[{"path": "input.png", "sha256": "0" * 64}])
        )
    ).success
    assert not (
        await tool.execute(
            request(
                action="edit",
                images=[{"path": str(outside / "secret.png"), "sha256": "0" * 64}],
            )
        )
    ).success
    assert not backend.calls


async def test_timeout_cancellation_and_concurrent_duplicate_never_replay(setup):
    tool, backend, _root, _capabilities = setup
    backend.error = TimeoutError("secret provider error must not be exposed")
    failed = await tool.execute(request())
    assert not failed.success and failed.output["status"] == "unknown"
    assert "secret" not in json.dumps(failed.model_dump())
    assert (await tool.execute(request())).output["status"] == "unknown"
    assert len(backend.calls) == 1
    backend.error = None
    backend.wait = asyncio.Event()
    task = asyncio.create_task(tool.execute(request("pending")))
    await asyncio.sleep(0)
    duplicate = await tool.execute(request("pending"))
    assert duplicate.output["status"] == "unknown" and len(backend.calls) == 2
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (await tool.execute({"action": "status", "request_id": "pending"})).output[
        "status"
    ] == "unknown"
    assert len(backend.calls) == 2


async def test_corrupt_output_and_partial_claim_do_not_generate_again(setup):
    tool, backend, root, _ = setup
    first = await tool.execute(request())
    (root / first.output["artifact"]["path"]).write_bytes(b"changed")
    assert not (await tool.execute(request())).success
    partial = root / "artifacts/images/interrupted"
    partial.mkdir()
    assert (
        await tool.execute({"action": "status", "request_id": "interrupted"})
    ).output["status"] == "unknown"
    assert (await tool.execute(request("interrupted"))).output["status"] == "unknown"
    assert len(backend.calls) == 1


async def test_mount_with_real_kernel(tmp_path):
    from amplifier_core import AmplifierSession

    session = AmplifierSession(
        {
            "session": {
                "orchestrator": {"module": "fixture"},
                "context": {"module": "fixture"},
            }
        }
    )
    session.coordinator.register_capability("session.working_dir", str(tmp_path))
    cleanup = await mount(session.coordinator, {})
    tool = session.coordinator.get("tools")["image_generate"]
    result = await tool.execute({"action": "capabilities"})
    assert result.success and not result.output["ready"]
    await cleanup()
    await session.cleanup()


async def test_mkdir_race_checks_winners_request_identity(setup, monkeypatch):
    tool, backend, _root, _ = setup
    original = tool.directory_fd

    def race(path, *, create=False):
        fd = original(path, create=create)
        if create:
            winner = path / "first"
            winner.mkdir()
            (winner / "request.json").write_text(
                json.dumps({"requestHash": "other-request"})
            )
        return fd

    monkeypatch.setattr(tool, "directory_fd", race)
    result = await tool.execute(request())
    assert not result.success and "different image request" in result.error["message"]
    assert not backend.calls


async def test_claim_and_new_ancestor_entries_are_synced_before_effect(
    setup, monkeypatch
):
    tool, backend, root, _ = setup
    synced = []
    fsync = os.fsync

    def sync(fd):
        info = os.fstat(fd)
        if stat.S_ISDIR(info.st_mode):
            synced.append(info.st_ino)
        fsync(fd)

    original = backend.generate

    async def effect(**kwargs):
        for path in (
            root,
            root / "artifacts",
            root / "artifacts/images",
            root / "artifacts/images/first",
        ):
            assert path.stat().st_ino in synced
        return await original(**kwargs)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(backend, "generate", effect)
    result = await tool.execute(request())
    assert result.success, result.error


async def test_read_policy_denies_upload_before_backend_or_output_claim(setup):
    tool, backend, root, _ = setup
    target = root / "private.png"
    target.write_bytes(png())
    tool.config["denied_read_paths"] = ["private.png"]
    edit = request(
        "edit",
        action="edit",
        images=[{"path": "private.png", "sha256": hashlib.sha256(png()).hexdigest()}],
    )
    result = await tool.execute(edit)
    assert not result.success and "Access denied" in result.error["message"]
    tool.config.pop("denied_read_paths")
    tool.config["allowed_read_paths"] = ["public"]
    assert not (await tool.execute(edit)).success
    assert not backend.calls and not (root / "artifacts").exists()


async def test_automatic_selection_records_actual_model_without_changing_request_identity(setup):
    tool, backend, root, capabilities = setup
    backend.describe = lambda: {"configured": True, "model": "auto", "operations": ["generate", "edit"]}
    original_generate = backend.generate
    selected_model = "fixture-1"

    async def generate(**args):
        return {**await original_generate(**args), "model": selected_model}

    backend.generate = generate
    first = await tool.execute(request())
    assert first.success and first.output["model"] == "fixture-1"
    selected_model = "fixture-2"
    restarted = ImageTool(SimpleNamespace(get_capability=capabilities.get), tool.config)
    assert (await restarted.execute(request())).output == first.output
    assert len(backend.calls) == 1
    second = await restarted.execute(request("second"))
    assert second.success and second.output["model"] == "fixture-2"
    assert second.output["requestHash"] == first.output["requestHash"]
    assert len(backend.calls) == 2


@pytest.mark.parametrize("model", [None, "", " ", 123, "x" * 201])
async def test_invalid_resolved_model_preserves_unknown_effect_without_replay(setup, model):
    tool, backend, root, capabilities = setup
    original_generate = backend.generate

    async def generate(**args):
        return {**await original_generate(**args), "model": model}

    backend.generate = generate
    result = await tool.execute(request())
    assert not result.success and result.output["status"] == "unknown"
    assert (await tool.execute(request())).output == result.output
    assert len(backend.calls) == 1


async def test_backend_automatic_controls_and_accompanying_text_are_durable(setup):
    tool, backend, root, capabilities = setup
    backend.describe = lambda: {
        'configured': True, 'model': 'auto', 'operations': ['generate', 'edit'],
        'defaults': dict(size='auto', quality='auto', background='auto'),
        'options': dict(size=['auto'], quality=['auto'], background=['auto']),
    }
    original_generate = backend.generate
    async def generate(**args):
        return {**await original_generate(**args), 'model': 'resolved-image-model', 'text': 'A red square.'}
    backend.generate = generate
    first = await tool.execute(request())
    assert first.success, first.error
    assert first.output['text'] == 'A red square.'
    assert first.output['options'] == dict(size='auto', quality='auto', background='auto')
    assert backend.calls[0]['quality'] == 'auto'
    assert (await tool.execute(request())).output == first.output
    assert len(backend.calls) == 1
    rejected = await tool.execute(request('unsupported', quality='high'))
    assert not rejected.success and len(backend.calls) == 1


@pytest.mark.parametrize('text', [42, 'x' * 32001])
async def test_invalid_accompanying_text_is_unknown_and_never_replayed(setup, text):
    tool, backend, root, capabilities = setup
    original_generate = backend.generate
    async def generate(**args):
        return {**await original_generate(**args), 'text': text}
    backend.generate = generate
    first = await tool.execute(request())
    assert not first.success and first.output['status'] == 'unknown'
    assert (await tool.execute(request())).output['status'] == 'unknown'
    assert len(backend.calls) == 1
