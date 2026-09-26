"""Protocol definition for image generation providers.

This protocol defines the interface that all image generation providers
must implement to work with the ImageGenerator orchestrator.
"""

from pathlib import Path
from typing import Protocol


class ImageProviderProtocol(Protocol):
    """Protocol for image generation API clients.

    All image providers (DALL-E, Imagen, GPT-Image-1, etc.) must implement
    this protocol to be usable by the ImageGenerator orchestrator.

    The protocol ensures consistent behavior across different providers
    while allowing provider-specific configuration and behavior.

    Attributes:
        api_name: Unique identifier for this provider (e.g., "imagen", "dalle")
    """

    api_name: str

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        params: dict | None = None,
    ) -> tuple[str, float]:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            output_path: Where to save the generated image file
            params: Optional provider-specific parameters (quality, size, etc.)

        Returns:
            Tuple of (image_url, estimated_cost_usd)
            - image_url: URL or file:// path to the generated image
            - estimated_cost_usd: Estimated cost in USD for this generation

        Raises:
            ValueError: If required API credentials are not configured
            RuntimeError: If image generation fails
            TimeoutError: If generation exceeds timeout limits

        Example:
            >>> client = DalleClient()
            >>> url, cost = await client.generate(
            ...     "A serene mountain landscape",
            ...     Path("output/mountain.png"),
            ...     params={"quality": "hd"}
            ... )
            >>> assert cost > 0
            >>> assert Path("output/mountain.png").exists()
        """
        ...

    async def check_availability(self) -> bool:
        """Check if the API is available and configured.

        Verifies that:
        1. Required API credentials are configured
        2. The API service is reachable (optional quick check)
        3. The provider is ready to generate images

        Returns:
            True if the provider is available and ready, False otherwise

        Example:
            >>> client = ImagenClient()
            >>> is_ready = await client.check_availability()
            >>> if is_ready:
            ...     print("Imagen is configured and ready")
        """
        ...
