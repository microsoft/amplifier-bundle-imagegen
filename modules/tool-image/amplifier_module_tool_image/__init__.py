"""Multi-provider AI image generation for Amplifier applications.

This module provides both a standalone library interface and an Amplifier Tool protocol interface.

Library Usage (Direct Import):
    >>> from amplifier_module_tool_image import ImageGenerator
    >>> generator = ImageGenerator()
    >>> result = await generator.generate(
    ...     prompt="A serene landscape",
    ...     output_path=Path("output/image.png")
    ... )

Tool Usage (Via Amplifier):
    >>> from amplifier_module_tool_image import ImageGenerationTool
    >>> tool = ImageGenerationTool()
    >>> result = await tool.execute({
    ...     "operation": "generate",
    ...     "prompt": "A serene landscape",
    ...     "output_path": "output/image.png"
    ... })
"""

from .generator import ImageGenerator
from .models import ImageGenerationError, ImageResult
from .tool import ImageGenerationTool

__version__ = "0.1.0"
__amplifier_module_type__ = "tool"
__all__ = [
    "ImageGenerationError",
    "ImageGenerationTool",
    "ImageGenerator",
    "ImageResult",
    "mount",
]


async def mount(coordinator, config=None):
    """Mount the workspace-safe tool; legacy library APIs remain independent.

    Import tool-only dependencies here so using the library does not require
    Core. Pillow validates mounted-tool artifacts. Optional built-in backends are
    explicitly selected and owned by this mount; existing host registrations are
    never overwritten.
    """
    from .backends import register_builtin
    from .workspace import WorkspaceImageTool

    config = dict(config or {})
    cleanup = register_builtin(coordinator, config)
    try:
        tool = WorkspaceImageTool(coordinator, config)
        await coordinator.mount("tools", tool, name=tool.name)
    except BaseException:
        await cleanup()
        raise
    return cleanup
