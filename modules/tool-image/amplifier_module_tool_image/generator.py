"""Image generation orchestration."""

import asyncio
import logging
from pathlib import Path

from .clients import DalleClient
from .clients import GptImageClient
from .clients import ImagenClient
from .models import GeneratedImage
from .models import ImageAlternatives
from .models import ImageResult

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Orchestrates image generation across multiple APIs."""

    def __init__(self, coordinator=None):
        """Initialize image generator.

        Args:
            coordinator: Optional capability coordinator for registration
        """
        self.coordinator = coordinator
        self.total_cost = 0.0

        # Initialize all available clients
        self.clients = {
            "imagen": ImagenClient(),
            "dalle": DalleClient(),
            "gptimage": GptImageClient(),
        }

        # Register capabilities if coordinator available
        if coordinator:
            coordinator.register_capability("image_generation.orchestrator", self)
            coordinator.register_capability("image_generation.providers", list(self.clients.keys()))

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        *,
        preferred_api: str | None = None,
        params: dict | None = None,
    ) -> ImageResult:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            output_path: Path where the generated image should be saved
            preferred_api: Optional preferred API to try first (imagen, dalle, gptimage)
            params: Optional generation parameters (quality, size, style)

        Returns:
            ImageResult with generation outcome

        Raises:
            ImageGenerationError: If all providers fail
        """
        output_path = output_path.expanduser()
        params = params or {}

        # Determine API order
        if preferred_api and preferred_api in self.clients:
            api_order = [preferred_api] + [api for api in self.clients.keys() if api != preferred_api]
        else:
            api_order = list(self.clients.keys())

        # Try each API in order
        last_error = None
        for api_name in api_order:
            client = self.clients[api_name]

            # Check availability
            try:
                if not await client.check_availability():
                    logger.warning(f"{api_name} not available, trying next provider")
                    continue
            except Exception as e:
                logger.warning(f"Failed to check {api_name} availability: {e}")
                continue

            # Try generation
            try:
                logger.info(f"Attempting generation with {api_name}")
                url, cost = await client.generate(prompt, output_path, params)

                self.total_cost += cost

                return ImageResult(
                    success=True,
                    api_used=api_name,
                    cost=cost,
                    local_path=output_path,
                    error=None,
                )

            except Exception as e:
                last_error = e
                logger.warning(f"Generation failed with {api_name}: {e}")
                continue

        # All providers failed
        error_msg = f"All providers failed. Last error: {last_error}"
        logger.error(error_msg)

        return ImageResult(
            success=False,
            api_used="none",
            cost=0.0,
            local_path=output_path,
            error=error_msg,
        )

    async def generate_alternatives(
        self,
        prompt: str,
        output_dir: Path,
        illustration_id: str,
        cost_limit: float | None = None,
    ) -> ImageAlternatives | None:
        """Generate multiple images from different APIs for comparison.

        This is an advanced feature for generating alternatives from multiple
        providers to compare quality and style.

        Args:
            prompt: Text description of the image to generate
            output_dir: Directory for output images
            illustration_id: Identifier for this illustration
            cost_limit: Optional cost limit

        Returns:
            ImageAlternatives with primary and alternative images, or None if all failed
        """
        output_dir = output_dir.expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Check cost limit
        if cost_limit and self.total_cost >= cost_limit:
            logger.warning(f"Cost limit reached: ${self.total_cost:.2f}")
            return None

        # Generate from each available API in parallel
        tasks = []
        for api_name, client in self.clients.items():
            if not await client.check_availability():
                logger.warning(f"{api_name} not available, skipping")
                continue

            output_path = output_dir / f"{illustration_id}-{api_name}.png"
            tasks.append(self._generate_single(client, api_name, prompt, illustration_id, output_path, {}))

        if not tasks:
            logger.error("No APIs available for generation")
            return None

        # Run generations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        generated_images = []
        for result in results:
            if isinstance(result, GeneratedImage):
                generated_images.append(result)
                self.total_cost += result.cost_estimate
            else:
                logger.error(f"Generation failed: {result}")

        if not generated_images:
            return None

        # Select primary image (first successful one)
        primary = generated_images[0]
        alternatives = generated_images[1:] if len(generated_images) > 1 else []

        return ImageAlternatives(
            illustration_id=illustration_id,
            primary=primary,
            alternatives=alternatives,
            selection_reason="First successfully generated image",
        )

    async def _generate_single(
        self,
        client,
        api_name: str,
        prompt: str,
        prompt_id: str,
        output_path: Path,
        params: dict,
    ) -> GeneratedImage:
        """Generate a single image from one API.

        Args:
            client: API client
            api_name: Name of the API
            prompt: Image prompt text
            prompt_id: Prompt identifier
            output_path: Output file path
            params: Generation parameters

        Returns:
            Generated image

        Raises:
            Exception: If generation fails
        """
        logger.info(f"Generating {api_name} image: {prompt[:50]}...")

        try:
            url, cost = await client.generate(
                prompt=prompt,
                output_path=output_path,
                params=params,
            )

            return GeneratedImage(
                prompt_id=prompt_id,
                api=api_name,
                url=url,
                local_path=output_path,
                generation_params=params,
                cost_estimate=cost,
            )

        except Exception as e:
            logger.error(f"Failed to generate {api_name} image: {e}")
            raise
