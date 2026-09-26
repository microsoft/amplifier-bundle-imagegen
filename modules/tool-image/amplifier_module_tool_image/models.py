"""Data models for image generation operations."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class ImageGenerationError(Exception):
    """Raised when image generation fails across all providers."""


@dataclass
class ImageResult:
    """Result of an image generation operation.

    This is the primary public API result returned by ImageGenerator.generate().

    Attributes:
        success: Whether the image generation succeeded
        api_used: Which provider was used (imagen, dalle, gptimage)
        cost: Estimated cost in USD for this generation
        local_path: Path where the generated image was saved
        error: Error message if generation failed, None otherwise

    Example:
        >>> result = ImageResult(
        ...     success=True,
        ...     api_used="gptimage",
        ...     cost=0.04,
        ...     local_path=Path("output/image.png"),
        ...     error=None
        ... )
        >>> assert result.success
        >>> assert result.api_used == "gptimage"
        >>> assert result.cost == 0.04
    """

    success: bool
    api_used: str
    cost: float
    local_path: Path
    error: str | None = None


@dataclass
class GeneratedImage:
    """Internal model representing a single generated image from an API.

    Used internally for multi-provider comparison and alternative generation.
    Not part of the public API.

    Attributes:
        prompt_id: Identifier linking this image to its prompt
        api: Which API generated this image
        url: URL or file path to the image
        local_path: Local filesystem path where image is saved
        generation_params: Provider-specific parameters used
        cost_estimate: Estimated cost for this generation
    """

    prompt_id: str
    api: Literal["imagen", "dalle", "gptimage"]
    url: str
    local_path: Path
    generation_params: dict
    cost_estimate: float


@dataclass
class ImageAlternatives:
    """Internal model for tracking primary image with alternatives.

    Used when generating multiple versions of the same image with different
    providers for comparison. Not part of the public API.

    Attributes:
        illustration_id: Identifier for the illustration point
        primary: The selected primary image
        alternatives: Other generated alternatives
        selection_reason: Why this primary was chosen over alternatives
    """

    illustration_id: str
    primary: GeneratedImage
    alternatives: list[GeneratedImage]
    selection_reason: str | None = None
