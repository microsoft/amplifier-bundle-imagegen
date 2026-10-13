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

from .models import ImageGenerationError, ImageResult

__version__ = "0.1.0"
__amplifier_module_type__ = "tool"
__all__ = [
    "ImageGenerationError",
    "ImageGenerationTool",
    "ImageGenerator",
    "ImageResult",
    "mount",
]

def __getattr__(name):
    # Historical convenience APIs remain importable, but routed mounting does
    # not import either vendor SDK or initialize a legacy client.
    if name == "ImageGenerator":
        from .generator import ImageGenerator
        return ImageGenerator
    if name == "ImageGenerationTool":
        from .tool import ImageGenerationTool
        return ImageGenerationTool
    raise AttributeError(name)


async def mount(coordinator, config=None):
    """Mount the workspace-safe tool; legacy library APIs remain independent.

    Import tool-only dependencies here so using the library does not require
    Core. Pillow validates mounted-tool artifacts. Optional built-in backends are
    explicitly selected and owned by this mount; existing host registrations are
    never overwritten.
    """
    from .workspace import WorkspaceImageTool
    from .routed import RoutedImageTool

    config = dict(config or {})
    async def cleanup():
        pass
    if config.get("builtin"):
        from .backends import register_builtin
        cleanup = register_builtin(coordinator, config)
    try:
        # A saved explicit backend is a compatibility choice, never discarded
        # merely because the newly composed behavior defaults to routing.
        cls = WorkspaceImageTool if config.get("backend") else RoutedImageTool
        tool = cls(coordinator, config)
        await coordinator.mount("tools", tool, name=tool.name)
    except BaseException:
        await cleanup()
        raise
    return cleanup
