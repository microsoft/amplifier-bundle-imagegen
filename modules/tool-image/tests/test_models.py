"""Tests for image generation models."""

from pathlib import Path

from amplifier_module_tool_image.models import GeneratedImage
from amplifier_module_tool_image.models import ImageAlternatives
from amplifier_module_tool_image.models import ImageResult


def test_image_result_success():
    """Test creating a successful ImageResult."""
    result = ImageResult(
        success=True,
        api_used="gptimage",
        cost=0.04,
        local_path=Path("test.png"),
        error=None,
    )

    assert result.success
    assert result.api_used == "gptimage"
    assert result.cost == 0.04
    assert result.local_path == Path("test.png")
    assert result.error is None


def test_image_result_failure():
    """Test creating a failed ImageResult."""
    result = ImageResult(
        success=False,
        api_used="dalle",
        cost=0.0,
        local_path=Path("failed.png"),
        error="API rate limit exceeded",
    )

    assert not result.success
    assert result.api_used == "dalle"
    assert result.cost == 0.0
    assert result.error == "API rate limit exceeded"


def test_image_result_with_high_cost():
    """Test ImageResult with high quality/cost."""
    result = ImageResult(
        success=True,
        api_used="dalle",
        cost=0.08,
        local_path=Path("hd_image.png"),
        error=None,
    )

    assert result.success
    assert result.cost == 0.08


def test_generated_image_creation():
    """Test creating a GeneratedImage."""
    image = GeneratedImage(
        prompt_id="prompt-123",
        api="gptimage",
        url="file:///output/image.png",
        local_path=Path("output/image.png"),
        generation_params={"quality": "medium", "size": "1024x1024"},
        cost_estimate=0.04,
    )

    assert image.prompt_id == "prompt-123"
    assert image.api == "gptimage"
    assert image.url == "file:///output/image.png"
    assert image.local_path == Path("output/image.png")
    assert image.generation_params["quality"] == "medium"
    assert image.cost_estimate == 0.04


def test_generated_image_different_apis():
    """Test GeneratedImage with different API values."""
    apis = ["imagen", "dalle", "gptimage"]

    for api in apis:
        image = GeneratedImage(
            prompt_id=f"prompt-{api}",
            api=api,  # type: ignore[arg-type]
            url=f"file:///{api}.png",
            local_path=Path(f"{api}.png"),
            generation_params={},
            cost_estimate=0.05,
        )
        assert image.api == api


def test_image_alternatives_single():
    """Test ImageAlternatives with single primary image."""
    primary = GeneratedImage(
        prompt_id="prompt-123",
        api="gptimage",
        url="file:///primary.png",
        local_path=Path("primary.png"),
        generation_params={},
        cost_estimate=0.04,
    )

    alternatives = ImageAlternatives(
        illustration_id="illustration-1",
        primary=primary,
        alternatives=[],
        selection_reason=None,
    )

    assert alternatives.illustration_id == "illustration-1"
    assert alternatives.primary.api == "gptimage"
    assert len(alternatives.alternatives) == 0
    assert alternatives.selection_reason is None


def test_image_alternatives_with_alternatives():
    """Test ImageAlternatives with multiple alternative images."""
    primary = GeneratedImage(
        prompt_id="prompt-123",
        api="gptimage",
        url="file:///primary.png",
        local_path=Path("primary.png"),
        generation_params={},
        cost_estimate=0.04,
    )

    alt1 = GeneratedImage(
        prompt_id="prompt-123",
        api="dalle",
        url="file:///alt1.png",
        local_path=Path("alt1.png"),
        generation_params={},
        cost_estimate=0.04,
    )

    alt2 = GeneratedImage(
        prompt_id="prompt-123",
        api="imagen",
        url="file:///alt2.png",
        local_path=Path("alt2.png"),
        generation_params={},
        cost_estimate=0.035,
    )

    alternatives = ImageAlternatives(
        illustration_id="illustration-1",
        primary=primary,
        alternatives=[alt1, alt2],
        selection_reason="Best quality-to-cost ratio",
    )

    assert alternatives.illustration_id == "illustration-1"
    assert alternatives.primary.api == "gptimage"
    assert len(alternatives.alternatives) == 2
    assert alternatives.alternatives[0].api == "dalle"
    assert alternatives.alternatives[1].api == "imagen"
    assert alternatives.selection_reason == "Best quality-to-cost ratio"


def test_image_result_path_types():
    """Test that ImageResult handles Path correctly."""
    str_path = "test/image.png"
    result = ImageResult(
        success=True,
        api_used="gptimage",
        cost=0.04,
        local_path=Path(str_path),
        error=None,
    )

    assert isinstance(result.local_path, Path)
    assert str(result.local_path) == str_path
