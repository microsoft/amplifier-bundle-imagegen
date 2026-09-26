"""Tests for image generation API clients."""

import base64
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from amplifier_module_tool_image.clients import DalleClient
from amplifier_module_tool_image.clients import GptImageClient
from amplifier_module_tool_image.clients import ImagenClient


@pytest.fixture
def temp_output_path(tmp_path):
    """Provide a temporary output path."""
    return tmp_path / "test_image.png"


class TestImagenClient:
    """Tests for ImagenClient."""

    @pytest.fixture
    def mock_genai(self):
        """Mock the Google genai module."""
        with patch("amplifier_module_tool_image.clients.genai") as mock:
            with patch("amplifier_module_tool_image.clients.GENAI_AVAILABLE", True):
                yield mock

    def test_init_with_api_key(self, mock_genai, monkeypatch):
        """Test client initialization with API key."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        client = ImagenClient()

        assert client.configured
        assert client.api_key == "test-key"
        mock_genai.Client.assert_called_once_with(api_key="test-key")

    def test_init_without_api_key(self, monkeypatch):
        """Test client initialization without API key."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        client = ImagenClient()

        assert not client.configured
        assert client.client is None

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_genai, monkeypatch, temp_output_path):
        """Test successful image generation."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        # Mock response
        mock_image_data = b"fake-image-data"
        mock_response = MagicMock()
        mock_response.generated_images = [MagicMock(image=MagicMock(image_bytes=mock_image_data))]

        mock_client = MagicMock()
        mock_client.models.generate_images.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        client = ImagenClient()
        url, cost = await client.generate("test prompt", temp_output_path)

        assert url == f"file://{temp_output_path}"
        assert cost == ImagenClient.COST_PER_IMAGE
        assert temp_output_path.exists()
        assert temp_output_path.read_bytes() == mock_image_data

    @pytest.mark.asyncio
    async def test_generate_not_configured(self, temp_output_path, monkeypatch):
        """Test generation fails when not configured."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        client = ImagenClient()

        with pytest.raises(ValueError, match="Google API key not configured"):
            await client.generate("test prompt", temp_output_path)

    @pytest.mark.asyncio
    async def test_check_availability_configured(self, mock_genai, monkeypatch):
        """Test availability check when configured."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.models.list.return_value = []
        mock_genai.Client.return_value = mock_client

        client = ImagenClient()
        available = await client.check_availability()

        assert available

    @pytest.mark.asyncio
    async def test_check_availability_not_configured(self, monkeypatch):
        """Test availability check when not configured."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        client = ImagenClient()

        available = await client.check_availability()

        assert not available


class TestDalleClient:
    """Tests for DalleClient."""

    @pytest.fixture
    def mock_openai(self):
        """Mock the OpenAI client."""
        with patch("amplifier_module_tool_image.clients.AsyncOpenAI") as mock:
            yield mock

    def test_init_with_api_key(self, mock_openai, monkeypatch):
        """Test client initialization with API key."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        client = DalleClient()

        assert client.configured
        assert client.api_key == "test-key"
        mock_openai.assert_called_once_with(api_key="test-key")

    def test_init_without_api_key(self, monkeypatch):
        """Test client initialization without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = DalleClient()

        assert not client.configured
        assert client.client is None

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_openai, monkeypatch, temp_output_path):
        """Test successful image generation."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(url="https://example.com/image.png")]

        mock_client = MagicMock()
        mock_client.images.generate = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        # Mock aiohttp download
        mock_image_data = b"fake-image-data"
        with patch("amplifier_module_tool_image.clients.aiohttp.ClientSession") as mock_session:
            mock_response_obj = MagicMock()
            mock_response_obj.read = AsyncMock(return_value=mock_image_data)
            mock_response_obj.raise_for_status = MagicMock()
            mock_get = AsyncMock()
            mock_get.__aenter__.return_value = mock_response_obj
            mock_session_instance = AsyncMock()
            mock_session_instance.__aenter__.return_value.get = MagicMock(return_value=mock_get)
            mock_session.return_value = mock_session_instance

            client = DalleClient()
            url, cost = await client.generate("test prompt", temp_output_path)

        assert url == "https://example.com/image.png"
        assert cost == DalleClient.COST_PER_IMAGE["standard"]
        assert temp_output_path.exists()
        assert temp_output_path.read_bytes() == mock_image_data

    @pytest.mark.asyncio
    async def test_generate_not_configured(self, temp_output_path, monkeypatch):
        """Test generation fails when not configured."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = DalleClient()

        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            await client.generate("test prompt", temp_output_path)

    @pytest.mark.asyncio
    async def test_check_availability_configured(self, mock_openai, monkeypatch):
        """Test availability check when configured."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        client = DalleClient()

        available = await client.check_availability()

        assert available

    @pytest.mark.asyncio
    async def test_check_availability_not_configured(self, monkeypatch):
        """Test availability check when not configured."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = DalleClient()

        available = await client.check_availability()

        assert not available


class TestGptImageClient:
    """Tests for GptImageClient."""

    @pytest.fixture
    def mock_openai(self):
        """Mock the OpenAI client."""
        with patch("amplifier_module_tool_image.clients.AsyncOpenAI") as mock:
            yield mock

    def test_init_with_api_key(self, mock_openai, monkeypatch):
        """Test client initialization with API key."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        client = GptImageClient()

        assert client.configured
        assert client.api_key == "test-key"
        mock_openai.assert_called_once_with(api_key="test-key")

    def test_init_without_api_key(self, monkeypatch):
        """Test client initialization without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = GptImageClient()

        assert not client.configured
        assert client.client is None

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_openai, monkeypatch, temp_output_path):
        """Test successful image generation."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Mock OpenAI response with base64 data
        mock_image_data = b"fake-image-data"
        mock_b64_data = base64.b64encode(mock_image_data).decode()

        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json=mock_b64_data)]

        mock_client = MagicMock()
        mock_client.images.generate = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        client = GptImageClient()
        url, cost = await client.generate("test prompt", temp_output_path)

        assert url == f"file://{temp_output_path}"
        assert cost == GptImageClient.COST_PER_IMAGE["medium"]
        assert temp_output_path.exists()
        assert temp_output_path.read_bytes() == mock_image_data

    @pytest.mark.asyncio
    async def test_generate_not_configured(self, temp_output_path, monkeypatch):
        """Test generation fails when not configured."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = GptImageClient()

        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            await client.generate("test prompt", temp_output_path)

    @pytest.mark.asyncio
    async def test_check_availability_configured(self, mock_openai, monkeypatch):
        """Test availability check when configured."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        client = GptImageClient()

        available = await client.check_availability()

        assert available

    @pytest.mark.asyncio
    async def test_check_availability_not_configured(self, monkeypatch):
        """Test availability check when not configured."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = GptImageClient()

        available = await client.check_availability()

        assert not available
