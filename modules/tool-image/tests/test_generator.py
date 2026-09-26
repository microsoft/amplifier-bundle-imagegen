"""Tests for image generator orchestration."""

from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from amplifier_module_tool_image.generator import ImageGenerator
from amplifier_module_tool_image.models import ImageResult


@pytest.fixture
def temp_output_path(tmp_path):
    """Provide a temporary output path."""
    return tmp_path / "test_image.png"


@pytest.fixture
def mock_clients():
    """Mock all client classes."""
    with (
        patch("amplifier_module_tool_image.generator.ImagenClient") as mock_imagen,
        patch("amplifier_module_tool_image.generator.DalleClient") as mock_dalle,
        patch("amplifier_module_tool_image.generator.GptImageClient") as mock_gptimage,
    ):
        yield {
            "imagen": mock_imagen,
            "dalle": mock_dalle,
            "gptimage": mock_gptimage,
        }


class TestImageGenerator:
    """Tests for ImageGenerator orchestration."""

    def test_init_without_coordinator(self, mock_clients):
        """Test initialization without capability coordinator."""
        generator = ImageGenerator()

        assert generator.coordinator is None
        assert generator.total_cost == 0.0
        assert len(generator.clients) == 3
        assert "imagen" in generator.clients
        assert "dalle" in generator.clients
        assert "gptimage" in generator.clients

    def test_init_with_coordinator(self, mock_clients):
        """Test initialization with capability coordinator."""
        mock_coordinator = MagicMock()
        generator = ImageGenerator(coordinator=mock_coordinator)

        assert generator.coordinator is mock_coordinator
        mock_coordinator.register_capability.assert_any_call("image_generation.orchestrator", generator)
        mock_coordinator.register_capability.assert_any_call(
            "image_generation.providers", ["imagen", "dalle", "gptimage"]
        )

    @pytest.mark.asyncio
    async def test_generate_success_first_provider(self, mock_clients, temp_output_path):
        """Test successful generation with first provider."""
        # Mock imagen client
        mock_imagen_instance = MagicMock()
        mock_imagen_instance.check_availability = AsyncMock(return_value=True)
        mock_imagen_instance.generate = AsyncMock(return_value=("file:///image.png", 0.04))
        mock_clients["imagen"].return_value = mock_imagen_instance

        # Mock other clients as unavailable
        mock_dalle_instance = MagicMock()
        mock_dalle_instance.check_availability = AsyncMock(return_value=False)
        mock_clients["dalle"].return_value = mock_dalle_instance

        mock_gptimage_instance = MagicMock()
        mock_gptimage_instance.check_availability = AsyncMock(return_value=False)
        mock_clients["gptimage"].return_value = mock_gptimage_instance

        generator = ImageGenerator()
        result = await generator.generate("test prompt", temp_output_path)

        assert isinstance(result, ImageResult)
        assert result.success
        assert result.api_used == "imagen"
        assert result.cost == 0.04
        assert result.error is None

    @pytest.mark.asyncio
    async def test_generate_fallback_to_second_provider(self, mock_clients, temp_output_path):
        """Test fallback when first provider fails."""
        # Mock imagen client - fails
        mock_imagen_instance = MagicMock()
        mock_imagen_instance.check_availability = AsyncMock(return_value=True)
        mock_imagen_instance.generate = AsyncMock(side_effect=Exception("API error"))
        mock_clients["imagen"].return_value = mock_imagen_instance

        # Mock dalle client - succeeds
        mock_dalle_instance = MagicMock()
        mock_dalle_instance.check_availability = AsyncMock(return_value=True)
        mock_dalle_instance.generate = AsyncMock(return_value=("https://example.com/image.png", 0.08))
        mock_clients["dalle"].return_value = mock_dalle_instance

        # Mock gptimage client
        mock_gptimage_instance = MagicMock()
        mock_gptimage_instance.check_availability = AsyncMock(return_value=False)
        mock_clients["gptimage"].return_value = mock_gptimage_instance

        generator = ImageGenerator()
        result = await generator.generate("test prompt", temp_output_path)

        assert result.success
        assert result.api_used == "dalle"
        assert result.cost == 0.08

    @pytest.mark.asyncio
    async def test_generate_all_providers_fail(self, mock_clients, temp_output_path):
        """Test when all providers fail."""
        # Mock all clients to fail
        for client_name, mock_client in mock_clients.items():
            mock_instance = MagicMock()
            mock_instance.check_availability = AsyncMock(return_value=True)
            mock_instance.generate = AsyncMock(side_effect=Exception(f"{client_name} error"))
            mock_client.return_value = mock_instance

        generator = ImageGenerator()
        result = await generator.generate("test prompt", temp_output_path)

        assert not result.success
        assert result.api_used == "none"
        assert result.cost == 0.0
        assert "All providers failed" in result.error

    @pytest.mark.asyncio
    async def test_generate_with_preferred_api(self, mock_clients, temp_output_path):
        """Test generation with preferred API."""
        # Mock gptimage client - should be tried first
        mock_gptimage_instance = MagicMock()
        mock_gptimage_instance.check_availability = AsyncMock(return_value=True)
        mock_gptimage_instance.generate = AsyncMock(return_value=("file:///image.png", 0.04))
        mock_clients["gptimage"].return_value = mock_gptimage_instance

        # Mock other clients
        mock_imagen_instance = MagicMock()
        mock_clients["imagen"].return_value = mock_imagen_instance

        mock_dalle_instance = MagicMock()
        mock_clients["dalle"].return_value = mock_dalle_instance

        generator = ImageGenerator()
        result = await generator.generate("test prompt", temp_output_path, preferred_api="gptimage")

        assert result.success
        assert result.api_used == "gptimage"
        mock_gptimage_instance.check_availability.assert_called_once()
        mock_gptimage_instance.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_tracks_cost(self, mock_clients, temp_output_path):
        """Test that cost tracking accumulates across generations."""
        # Mock imagen client
        mock_imagen_instance = MagicMock()
        mock_imagen_instance.check_availability = AsyncMock(return_value=True)
        mock_imagen_instance.generate = AsyncMock(return_value=("file:///image.png", 0.04))
        mock_clients["imagen"].return_value = mock_imagen_instance

        # Mock other clients
        for client_name in ["dalle", "gptimage"]:
            mock_instance = MagicMock()
            mock_instance.check_availability = AsyncMock(return_value=False)
            mock_clients[client_name].return_value = mock_instance

        generator = ImageGenerator()

        # First generation
        result1 = await generator.generate("test prompt 1", temp_output_path)
        assert generator.total_cost == 0.04

        # Second generation
        result2 = await generator.generate("test prompt 2", temp_output_path)
        assert generator.total_cost == 0.08

    @pytest.mark.asyncio
    async def test_generate_alternatives_success(self, mock_clients, tmp_path):
        """Test generating alternatives from multiple providers."""
        output_dir = tmp_path / "outputs"

        # Mock all clients to succeed
        mock_imagen_instance = MagicMock()
        mock_imagen_instance.check_availability = AsyncMock(return_value=True)
        mock_imagen_instance.generate = AsyncMock(return_value=("file:///imagen.png", 0.035))
        mock_clients["imagen"].return_value = mock_imagen_instance

        mock_dalle_instance = MagicMock()
        mock_dalle_instance.check_availability = AsyncMock(return_value=True)
        mock_dalle_instance.generate = AsyncMock(return_value=("https://dalle.png", 0.04))
        mock_clients["dalle"].return_value = mock_dalle_instance

        mock_gptimage_instance = MagicMock()
        mock_gptimage_instance.check_availability = AsyncMock(return_value=True)
        mock_gptimage_instance.generate = AsyncMock(return_value=("file:///gptimage.png", 0.04))
        mock_clients["gptimage"].return_value = mock_gptimage_instance

        generator = ImageGenerator()
        alternatives = await generator.generate_alternatives("test prompt", output_dir, "test-id")

        assert alternatives is not None
        assert alternatives.illustration_id == "test-id"
        assert alternatives.primary is not None
        assert len(alternatives.alternatives) == 2
        assert generator.total_cost > 0

    @pytest.mark.asyncio
    async def test_generate_alternatives_all_fail(self, mock_clients, tmp_path):
        """Test alternatives generation when all providers fail."""
        output_dir = tmp_path / "outputs"

        # Mock all clients to fail
        for client_name, mock_client in mock_clients.items():
            mock_instance = MagicMock()
            mock_instance.check_availability = AsyncMock(return_value=True)
            mock_instance.generate = AsyncMock(side_effect=Exception(f"{client_name} error"))
            mock_client.return_value = mock_instance

        generator = ImageGenerator()
        alternatives = await generator.generate_alternatives("test prompt", output_dir, "test-id")

        assert alternatives is None

    @pytest.mark.asyncio
    async def test_generate_alternatives_cost_limit(self, mock_clients, tmp_path):
        """Test alternatives generation respects cost limit."""
        output_dir = tmp_path / "outputs"

        generator = ImageGenerator()
        generator.total_cost = 1.0  # Set cost at limit

        alternatives = await generator.generate_alternatives("test prompt", output_dir, "test-id", cost_limit=1.0)

        assert alternatives is None

    @pytest.mark.asyncio
    async def test_generate_path_expansion(self, mock_clients, tmp_path):
        """Test that paths with ~ are expanded."""
        # Mock imagen client
        mock_imagen_instance = MagicMock()
        mock_imagen_instance.check_availability = AsyncMock(return_value=True)
        mock_imagen_instance.generate = AsyncMock(return_value=("file:///image.png", 0.04))
        mock_clients["imagen"].return_value = mock_imagen_instance

        # Mock other clients
        for client_name in ["dalle", "gptimage"]:
            mock_instance = MagicMock()
            mock_instance.check_availability = AsyncMock(return_value=False)
            mock_clients[client_name].return_value = mock_instance

        generator = ImageGenerator()

        # Use path with ~
        path_with_tilde = Path("~/test_image.png")
        result = await generator.generate("test prompt", path_with_tilde)

        # Verify that generate was called with expanded path (positional arg)
        called_path = mock_imagen_instance.generate.call_args[0][1]
        assert "~" not in str(called_path)
