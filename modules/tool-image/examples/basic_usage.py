"""
Basic usage examples for amplifier-module-tool-image.

These examples show common usage patterns.
"""

import asyncio
from pathlib import Path

from amplifier_module_tool_image import ImageGenerator


async def example_basic_generation():
    """Generate a single image with default settings."""
    generator = ImageGenerator()

    result = await generator.generate(
        prompt="A serene mountain landscape at sunset with autumn colors",
        output_path=Path("output/mountain.png"),
    )

    if result.success:
        print(f"✓ Generated with {result.api_used}")
        print(f"  Cost: ${result.cost:.2f}")
        print(f"  Saved to: {result.local_path}")
    else:
        print(f"✗ Generation failed: {result.error}")


async def example_preferred_api():
    """Generate with a preferred API provider."""
    generator = ImageGenerator()

    # Prefer Imagen for photorealistic quality
    result = await generator.generate(
        prompt="Professional headshot photo of a software engineer",
        output_path=Path("output/headshot.png"),
        preferred_api="imagen",
    )

    print(f"Used API: {result.api_used}")


async def example_custom_parameters():
    """Generate with custom quality and size parameters."""
    generator = ImageGenerator()

    # High quality, vertical format with DALL-E
    result = await generator.generate(
        prompt="Detailed technical architecture diagram",
        output_path=Path("output/architecture.png"),
        preferred_api="dalle",
        params={"quality": "hd", "size": "1024x1792"},
    )

    print(f"Generated HD image: {result.local_path}")


async def example_batch_generation():
    """Generate multiple images efficiently."""
    generator = ImageGenerator()

    prompts = [
        "Abstract representation of distributed computing",
        "Minimalist diagram of microservices architecture",
        "Watercolor illustration of data flow",
    ]

    results = []
    total_cost = 0.0

    for i, prompt in enumerate(prompts, 1):
        print(f"Generating {i}/{len(prompts)}...")

        result = await generator.generate(
            prompt=prompt,
            output_path=Path(f"output/image_{i}.png"),
        )

        results.append(result)
        total_cost += result.cost

    print(f"\n✓ Generated {len(results)} images")
    print(f"  Total cost: ${total_cost:.2f}")


async def example_cost_limit():
    """Generate images with budget limit."""
    generator = ImageGenerator()
    budget = 1.00  # $1 budget
    total_cost = 0.0

    prompts = [
        "Technical diagram 1",
        "Technical diagram 2",
        "Technical diagram 3",
        "Technical diagram 4",
        "Technical diagram 5",
    ]

    for i, prompt in enumerate(prompts, 1):
        if total_cost >= budget:
            print(f"Budget limit reached: ${total_cost:.2f}")
            break

        result = await generator.generate(
            prompt=prompt,
            output_path=Path(f"output/diagram_{i}.png"),
        )

        total_cost += result.cost
        print(f"Generated {i}: ${total_cost:.2f} total")


async def example_error_handling():
    """Handle generation failures gracefully."""
    generator = ImageGenerator()

    result = await generator.generate(
        prompt="Test image",
        output_path=Path("output/test.png"),
    )

    if not result.success:
        if "API key" in (result.error or ""):
            print("Error: Configure API keys in environment")
            print("  export OPENAI_API_KEY=your_key")
            print("  export GOOGLE_API_KEY=your_key")
        elif "rate limit" in (result.error or ""):
            print("Error: Rate limit exceeded, wait before retrying")
        else:
            print(f"Unexpected error: {result.error}")
    else:
        print(f"Success: {result.local_path}")


async def example_with_capability_registry():
    """Use with Amplifier capability registry pattern."""
    # This would be in an Amplifier app with coordinator available
    # Shown here for documentation purposes

    # Try capability first (when in Amplifier app)
    generator = None  # coordinator.get_capability("image_generation.orchestrator")

    # Fall back to direct import if not registered
    if not generator:
        generator = ImageGenerator()

    result = await generator.generate(
        prompt="Example image",
        output_path=Path("output/example.png"),
    )

    print(f"Generated: {result.success}")


if __name__ == "__main__":
    # Run all examples
    print("=== Basic Generation ===")
    asyncio.run(example_basic_generation())

    print("\n=== Preferred API ===")
    asyncio.run(example_preferred_api())

    print("\n=== Custom Parameters ===")
    asyncio.run(example_custom_parameters())

    print("\n=== Batch Generation ===")
    asyncio.run(example_batch_generation())

    print("\n=== Cost Limit ===")
    asyncio.run(example_cost_limit())

    print("\n=== Error Handling ===")
    asyncio.run(example_error_handling())

    print("\n=== Capability Registry Pattern ===")
    asyncio.run(example_with_capability_registry())
