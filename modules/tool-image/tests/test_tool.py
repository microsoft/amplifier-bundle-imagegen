"""Tests for ImageGenerationTool protocol implementation."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from amplifier_module_tool_image import ImageGenerationTool, ImageResult
from amplifier_core import ToolResult


@pytest.fixture
def tool():
    """Create tool instance for testing."""
    return ImageGenerationTool()


@pytest.fixture
def mock_image_result_success():
    """Mock successful ImageResult."""
    return ImageResult(
        success=True,
        api_used="gptimage",
        cost=0.04,
        local_path=Path("output/test.png"),
        error=None
    )


@pytest.fixture
def mock_image_result_failure():
    """Mock failed ImageResult."""
    return ImageResult(
        success=False,
        api_used="none",
        cost=0.0,
        local_path=Path("output/test.png"),
        error="All providers failed"
    )


class TestToolProtocol:
    """Test Tool protocol implementation."""
    
    def test_tool_has_name_property(self, tool):
        """Tool should have name property."""
        assert hasattr(tool, "name")
        assert tool.name == "image-generation"
    
    def test_tool_has_description_property(self, tool):
        """Tool should have description property."""
        assert hasattr(tool, "description")
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0
    
    def test_tool_has_execute_method(self, tool):
        """Tool should have execute method."""
        assert hasattr(tool, "execute")
        assert callable(tool.execute)


class TestGenerateOperation:
    """Test generate operation."""
    
    @pytest.mark.asyncio
    async def test_generate_success(self, tool, mock_image_result_success):
        """Test successful image generation."""
        with patch.object(
            tool._generator, 
            "generate", 
            return_value=mock_image_result_success
        ):
            result = await tool.execute({
                "operation": "generate",
                "prompt": "A test image",
                "output_path": "output/test.png"
            })
            
            assert isinstance(result, ToolResult)
            assert result.success is True
            assert result.output["success"] is True
            assert result.output["api_used"] == "gptimage"
            assert result.output["cost"] == 0.04
            assert "test.png" in result.output["local_path"]
    
    @pytest.mark.asyncio
    async def test_generate_failure(self, tool, mock_image_result_failure):
        """Test failed image generation."""
        with patch.object(
            tool._generator,
            "generate",
            return_value=mock_image_result_failure
        ):
            result = await tool.execute({
                "operation": "generate",
                "prompt": "A test image",
                "output_path": "output/test.png"
            })
            
            assert isinstance(result, ToolResult)
            assert result.success is False
            assert "All providers failed" in result.error["message"]
    
    @pytest.mark.asyncio
    async def test_generate_missing_prompt(self, tool):
        """Test generate with missing prompt."""
        result = await tool.execute({
            "operation": "generate",
            "output_path": "output/test.png"
        })
        
        assert result.success is False
        assert "prompt" in result.error["message"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_missing_output_path(self, tool):
        """Test generate with missing output_path."""
        result = await tool.execute({
            "operation": "generate",
            "prompt": "A test image"
        })
        
        assert result.success is False
        assert "output_path" in result.error["message"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_with_preferred_api(self, tool, mock_image_result_success):
        """Test generate with preferred API."""
        with patch.object(
            tool._generator,
            "generate",
            return_value=mock_image_result_success
        ) as mock_generate:
            await tool.execute({
                "operation": "generate",
                "prompt": "A test image",
                "output_path": "output/test.png",
                "preferred_api": "imagen"
            })
            
            # Verify preferred_api was passed through
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs["preferred_api"] == "imagen"
    
    @pytest.mark.asyncio
    async def test_generate_maps_openai_to_dalle(self, tool, mock_image_result_success):
        """Test that 'openai' is mapped to 'dalle' for convenience."""
        with patch.object(
            tool._generator,
            "generate",
            return_value=mock_image_result_success
        ) as mock_generate:
            await tool.execute({
                "operation": "generate",
                "prompt": "A test image",
                "output_path": "output/test.png",
                "preferred_api": "openai"
            })
            
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs["preferred_api"] == "dalle"
    
    @pytest.mark.asyncio
    async def test_generate_maps_google_to_imagen(self, tool, mock_image_result_success):
        """Test that 'google' is mapped to 'imagen' for convenience."""
        with patch.object(
            tool._generator,
            "generate",
            return_value=mock_image_result_success
        ) as mock_generate:
            await tool.execute({
                "operation": "generate",
                "prompt": "A test image",
                "output_path": "output/test.png",
                "preferred_api": "google"
            })
            
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs["preferred_api"] == "imagen"
    
    @pytest.mark.asyncio
    async def test_generate_with_params(self, tool, mock_image_result_success):
        """Test generate with custom parameters."""
        with patch.object(
            tool._generator,
            "generate",
            return_value=mock_image_result_success
        ) as mock_generate:
            await tool.execute({
                "operation": "generate",
                "prompt": "A test image",
                "output_path": "output/test.png",
                "params": {"quality": "hd", "size": "1024x1792"}
            })
            
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs["params"] == {"quality": "hd", "size": "1024x1792"}


class TestCheckAvailabilityOperation:
    """Test check_availability operation."""
    
    @pytest.mark.asyncio
    async def test_check_availability_available(self, tool):
        """Test checking availability for an available provider."""
        mock_client = MagicMock()
        mock_client.check_availability = AsyncMock(return_value=True)
        tool._generator.clients = {"imagen": mock_client}
        
        result = await tool.execute({
            "operation": "check_availability",
            "provider": "imagen"
        })
        
        assert result.success is True
        assert result.output["provider"] == "imagen"
        assert result.output["available"] is True
    
    @pytest.mark.asyncio
    async def test_check_availability_unavailable(self, tool):
        """Test checking availability for an unavailable provider."""
        mock_client = MagicMock()
        mock_client.check_availability = AsyncMock(return_value=False)
        tool._generator.clients = {"dalle": mock_client}
        
        result = await tool.execute({
            "operation": "check_availability",
            "provider": "dalle"
        })
        
        assert result.success is True
        assert result.output["provider"] == "dalle"
        assert result.output["available"] is False
    
    @pytest.mark.asyncio
    async def test_check_availability_missing_provider(self, tool):
        """Test check_availability with missing provider field."""
        result = await tool.execute({
            "operation": "check_availability"
        })
        
        assert result.success is False
        assert "provider" in result.error["message"].lower()
    
    @pytest.mark.asyncio
    async def test_check_availability_unknown_provider(self, tool):
        """Test check_availability with unknown provider."""
        tool._generator.clients = {"imagen": MagicMock()}
        
        result = await tool.execute({
            "operation": "check_availability",
            "provider": "unknown"
        })
        
        assert result.success is False
        assert "unknown provider" in result.error["message"].lower()


class TestGetCostEstimateOperation:
    """Test get_cost_estimate operation."""
    
    @pytest.mark.asyncio
    async def test_cost_estimate_imagen(self, tool):
        """Test cost estimate for Imagen."""
        mock_client = MagicMock()
        mock_client.COST_PER_IMAGE = 0.035
        tool._generator.clients = {"imagen": mock_client}
        
        result = await tool.execute({
            "operation": "get_cost_estimate",
            "provider": "imagen"
        })
        
        assert result.success is True
        assert result.output["provider"] == "imagen"
        assert result.output["cost_per_image"] == 0.035
        assert result.output["currency"] == "USD"
    
    @pytest.mark.asyncio
    async def test_cost_estimate_dalle_standard(self, tool):
        """Test cost estimate for DALL-E with standard quality."""
        mock_client = MagicMock()
        mock_client.COST_PER_IMAGE = {"standard": 0.040, "hd": 0.080}
        tool._generator.clients = {"dalle": mock_client}
        
        result = await tool.execute({
            "operation": "get_cost_estimate",
            "provider": "dalle",
            "params": {"quality": "standard"}
        })
        
        assert result.success is True
        assert result.output["cost_per_image"] == 0.040
    
    @pytest.mark.asyncio
    async def test_cost_estimate_dalle_hd(self, tool):
        """Test cost estimate for DALL-E with HD quality."""
        mock_client = MagicMock()
        mock_client.COST_PER_IMAGE = {"standard": 0.040, "hd": 0.080}
        tool._generator.clients = {"dalle": mock_client}
        
        result = await tool.execute({
            "operation": "get_cost_estimate",
            "provider": "dalle",
            "params": {"quality": "hd"}
        })
        
        assert result.success is True
        assert result.output["cost_per_image"] == 0.080
    
    @pytest.mark.asyncio
    async def test_cost_estimate_gptimage(self, tool):
        """Test cost estimate for GPT-Image-1."""
        mock_client = MagicMock()
        mock_client.COST_PER_IMAGE = {
            "low": 0.020,
            "medium": 0.040,
            "high": 0.080,
            "auto": 0.040
        }
        tool._generator.clients = {"gptimage": mock_client}
        
        result = await tool.execute({
            "operation": "get_cost_estimate",
            "provider": "gptimage",
            "params": {"quality": "high"}
        })
        
        assert result.success is True
        assert result.output["cost_per_image"] == 0.080
    
    @pytest.mark.asyncio
    async def test_cost_estimate_missing_provider(self, tool):
        """Test cost estimate with missing provider field."""
        result = await tool.execute({
            "operation": "get_cost_estimate"
        })
        
        assert result.success is False
        assert "provider" in result.error["message"].lower()


class TestOperationRouting:
    """Test operation routing and error handling."""
    
    @pytest.mark.asyncio
    async def test_missing_operation(self, tool):
        """Test execute with missing operation field."""
        result = await tool.execute({
            "prompt": "A test image"
        })
        
        assert result.success is False
        assert "operation" in result.error["message"].lower()
        assert "valid_operations" in result.error
    
    @pytest.mark.asyncio
    async def test_unknown_operation(self, tool):
        """Test execute with unknown operation."""
        result = await tool.execute({
            "operation": "unknown_op"
        })
        
        assert result.success is False
        assert "unknown operation" in result.error["message"].lower()
        assert "valid_operations" in result.error
    
    @pytest.mark.asyncio
    async def test_exception_handling(self, tool):
        """Test that exceptions are caught and returned as ToolResult errors."""
        with patch.object(
            tool._generator,
            "generate",
            side_effect=RuntimeError("Test error")
        ):
            result = await tool.execute({
                "operation": "generate",
                "prompt": "A test image",
                "output_path": "output/test.png"
            })
            
            assert result.success is False
            assert "Test error" in result.error["message"]
            assert result.error["type"] == "RuntimeError"


class TestLibraryBackwardCompatibility:
    """Test that library usage still works."""
    
    @pytest.mark.asyncio
    async def test_library_import(self):
        """Test that ImageGenerator can still be imported directly."""
        from amplifier_module_tool_image import ImageGenerator
        
        generator = ImageGenerator()
        assert generator is not None
    
    @pytest.mark.asyncio
    async def test_tool_wraps_generator(self, tool):
        """Test that tool uses ImageGenerator internally."""
        from amplifier_module_tool_image import ImageGenerator
        
        assert isinstance(tool._generator, ImageGenerator)
