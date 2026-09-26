"""Amplifier Tool protocol wrapper for ImageGenerator.

This module provides a thin wrapper that exposes the ImageGenerator library
through the Amplifier Tool protocol, enabling orchestration use while preserving
the ability to use ImageGenerator directly as a library.

Note: This module requires amplifier-core to be installed. Install with:
    pip install amplifier-module-tool-image[tool]
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import of amplifier_core - only needed when using tool protocol
try:
    from amplifier_core import ToolResult
    _HAS_AMPLIFIER_CORE = True
except ImportError:
    _HAS_AMPLIFIER_CORE = False
    ToolResult = None  # type: ignore

from .generator import ImageGenerator


class ImageGenerationTool:
    """Tool protocol wrapper for image generation.
    
    Wraps the ImageGenerator library to expose it through the Amplifier Tool protocol.
    This enables both standalone library usage and orchestrated tool usage.
    
    Requires: amplifier-core (install with [tool] extra)
    
    Operations:
        - generate: Generate an image from a prompt
        - check_availability: Check if a provider is available
        - get_cost_estimate: Get cost estimate for a provider
    
    Example (as tool):
        >>> tool = ImageGenerationTool()
        >>> result = await tool.execute({
        ...     "operation": "generate",
        ...     "prompt": "A serene landscape",
        ...     "output_path": "output/image.png"
        ... })
        
    Example (library usage):
        >>> from amplifier_module_tool_image import ImageGenerator
        >>> generator = ImageGenerator()
        >>> result = await generator.generate(prompt, output_path)
    """
    
    def __init__(self):
        """Initialize the tool wrapper.
        
        Raises:
            ImportError: If amplifier-core is not installed
        """
        if not _HAS_AMPLIFIER_CORE:
            raise ImportError(
                "amplifier-core is required to use ImageGenerationTool. "
                "Install with: pip install amplifier-module-tool-image[tool]"
            )
        self._generator = ImageGenerator()
    
    @property
    def name(self) -> str:
        """Tool name for invocation."""
        return "image-generation"
    
    @property
    def description(self) -> str:
        """Human-readable tool description."""
        return (
            "Generate images using multiple AI providers (DALL-E, Imagen, GPT-Image-1). "
            "Supports automatic fallback, cost tracking, and provider availability checking."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        """Schema for the historical direct wrapper, not the safe mounted tool."""
        return {
            "type": "object",
            "properties": {
                "operation": {"enum": ["generate", "check_availability", "get_cost_estimate"]},
                "prompt": {"type": "string"},
                "output_path": {"type": "string"},
                "preferred_api": {"enum": ["openai", "google", "imagen", "dalle", "gptimage"]},
                "provider": {"enum": ["openai", "google", "imagen", "dalle", "gptimage"]},
                "params": {"type": "object"},
            },
            "required": ["operation"],
            "additionalProperties": False,
        }
    
    async def execute(self, input: dict[str, Any]) -> ToolResult:
        """Execute tool operation.
        
        Args:
            input: Operation parameters with required 'operation' field
                
        Operations:
            generate:
                - prompt (str): Image description
                - output_path (str): Where to save the image
                - preferred_api (str, optional): "openai", "google", "imagen", "dalle", "gptimage"
                - params (dict, optional): Provider-specific parameters
                
            check_availability:
                - provider (str): Provider name to check ("imagen", "dalle", "gptimage")
                
            get_cost_estimate:
                - provider (str): Provider name ("imagen", "dalle", "gptimage")
                - params (dict, optional): Generation parameters
        
        Returns:
            ToolResult with operation outcome
        """
        operation = input.get("operation")
        
        if not operation:
            return ToolResult(
                success=False,
                error={
                    "message": "Missing 'operation' field in input",
                    "valid_operations": ["generate", "check_availability", "get_cost_estimate"]
                }
            )
        
        try:
            if operation == "generate":
                return await self._execute_generate(input)
            elif operation == "check_availability":
                return await self._execute_check_availability(input)
            elif operation == "get_cost_estimate":
                return await self._execute_get_cost_estimate(input)
            else:
                return ToolResult(
                    success=False,
                    error={
                        "message": f"Unknown operation: {operation}",
                        "valid_operations": ["generate", "check_availability", "get_cost_estimate"]
                    }
                )
        except Exception as e:
            logger.exception(f"Tool execution failed for operation '{operation}'")
            return ToolResult(
                success=False,
                error={
                    "message": str(e),
                    "operation": operation,
                    "type": type(e).__name__
                }
            )
    
    async def _execute_generate(self, input: dict[str, Any]) -> ToolResult:
        """Execute image generation operation.
        
        Args:
            input: Generation parameters
            
        Returns:
            ToolResult with generation outcome
        """
        # Validate required fields
        prompt = input.get("prompt")
        output_path_str = input.get("output_path")
        
        if not prompt:
            return ToolResult(
                success=False,
                error={"message": "Missing required field: 'prompt'"}
            )
        
        if not output_path_str:
            return ToolResult(
                success=False,
                error={"message": "Missing required field: 'output_path'"}
            )
        
        # Parse optional fields
        output_path = Path(output_path_str)
        preferred_api = input.get("preferred_api")
        params = input.get("params")
        
        # Map "openai" to "dalle" and "google" to "imagen" for convenience
        if preferred_api == "openai":
            preferred_api = "dalle"
        elif preferred_api == "google":
            preferred_api = "imagen"
        
        # Generate the image
        result = await self._generator.generate(
            prompt=prompt,
            output_path=output_path,
            preferred_api=preferred_api,
            params=params
        )
        
        # Convert ImageResult to ToolResult
        if result.success:
            return ToolResult(
                success=True,
                output={
                    "success": True,
                    "api_used": result.api_used,
                    "cost": result.cost,
                    "local_path": str(result.local_path),
                    "message": f"Image generated successfully with {result.api_used} (${result.cost:.3f})"
                }
            )
        else:
            return ToolResult(
                success=False,
                error={
                    "message": result.error or "Image generation failed",
                    "api_used": result.api_used,
                    "cost": result.cost
                }
            )
    
    async def _execute_check_availability(self, input: dict[str, Any]) -> ToolResult:
        """Check if a provider is available.
        
        Args:
            input: Contains 'provider' field
            
        Returns:
            ToolResult with availability status
        """
        provider = input.get("provider")
        
        if not provider:
            return ToolResult(
                success=False,
                error={"message": "Missing required field: 'provider'"}
            )
        
        # Map friendly names
        if provider == "openai":
            provider = "dalle"
        elif provider == "google":
            provider = "imagen"
        
        # Check if provider exists
        if provider not in self._generator.clients:
            return ToolResult(
                success=False,
                error={
                    "message": f"Unknown provider: {provider}",
                    "available_providers": list(self._generator.clients.keys())
                }
            )
        
        # Check availability
        client = self._generator.clients[provider]
        is_available = await client.check_availability()
        
        return ToolResult(
            success=True,
            output={
                "provider": provider,
                "available": is_available,
                "message": f"{provider} is {'available' if is_available else 'not available'}"
            }
        )
    
    async def _execute_get_cost_estimate(self, input: dict[str, Any]) -> ToolResult:
        """Get cost estimate for a provider.
        
        Args:
            input: Contains 'provider' and optional 'params'
            
        Returns:
            ToolResult with cost estimate
        """
        provider = input.get("provider")
        
        if not provider:
            return ToolResult(
                success=False,
                error={"message": "Missing required field: 'provider'"}
            )
        
        # Map friendly names
        if provider == "openai":
            provider = "dalle"
        elif provider == "google":
            provider = "imagen"
        
        # Check if provider exists
        if provider not in self._generator.clients:
            return ToolResult(
                success=False,
                error={
                    "message": f"Unknown provider: {provider}",
                    "available_providers": list(self._generator.clients.keys())
                }
            )
        
        # Get cost estimate based on provider
        client = self._generator.clients[provider]
        params = input.get("params", {})
        
        # Calculate cost based on provider type
        if provider == "imagen":
            cost = client.COST_PER_IMAGE
        elif provider == "dalle":
            quality = params.get("quality", "standard")
            cost = client.COST_PER_IMAGE.get(quality, client.COST_PER_IMAGE["standard"])
        elif provider == "gptimage":
            quality = params.get("quality", "auto")
            # Map DALL-E quality names to GPT-Image names
            if quality == "standard":
                quality = "medium"
            elif quality == "hd":
                quality = "high"
            cost = client.COST_PER_IMAGE.get(quality, client.COST_PER_IMAGE["auto"])
        else:
            cost = 0.0
        
        return ToolResult(
            success=True,
            output={
                "provider": provider,
                "cost_per_image": cost,
                "currency": "USD",
                "params": params,
                "message": f"{provider} estimated cost: ${cost:.3f} per image"
            }
        )
