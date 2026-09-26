"""Prove actual SDK timeout and connection-error behavior without a network."""

import base64
import io

import httpx
import pytest
from openai import AsyncOpenAI
from PIL import Image

from amplifier_module_tool_image.backends import ClientBackend
from amplifier_module_tool_image.clients import GptImageClient


def png():
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(output, format="PNG")
    return output.getvalue()


async def test_openai_explicit_none_overrides_sdk_timeout_default():
    seen = []

    async def transport(request):
        seen.append(request)
        return httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
        )

    sdk = AsyncOpenAI(
        api_key="synthetic",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)),
    )
    client = GptImageClient.__new__(GptImageClient)
    client.configured, client.client = True, sdk
    try:
        await client.generate_bytes(
            action="generate",
            model="model",
            prompt="square",
            images=[],
            size="1024x1024",
            quality="low",
            background="opaque",
            timeout=None,
        )
        (request,) = seen
        assert set(request.extensions["timeout"].values()) == {None}
    finally:
        await sdk.close()


@pytest.mark.parametrize("connection_failure", [False, True])
async def test_mounted_imagen_owns_httpx_without_implicit_timeout_or_connect_retry(
    monkeypatch, connection_failure
):
    monkeypatch.setenv("GOOGLE_API_KEY", "synthetic")
    # An ambient project must not switch explicit API-key mode to ADC.
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "synthetic-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "synthetic-location")
    from google.genai import _api_client

    def adc_forbidden(*args, **kwargs):
        raise AssertionError("API-key mode must not discover ADC")

    monkeypatch.setattr(_api_client, "load_auth", adc_forbidden)
    seen = []

    async def transport(request):
        seen.append(request)
        if connection_failure:
            raise httpx.ConnectError("synthetic connection error", request=request)
        return httpx.Response(
            200,
            json={
                "predictions": [
                    {
                        "bytesBase64Encoded": base64.b64encode(png()).decode(),
                        "mimeType": "image/png",
                    }
                ]
            },
        )

    transports = []

    def transport_factory(*, retries):
        assert retries == 0
        result = httpx.MockTransport(transport)
        transports.append(result)
        return result

    monkeypatch.setattr(httpx, "AsyncHTTPTransport", transport_factory)
    backend = ClientBackend("imagen", "explicit-model", vertexai=True)
    assert backend.timeout is None and backend.client is None
    try:
        call = backend.generate(
            action="generate",
            prompt="square",
            images=[],
            size="1024x1024",
            quality="standard",
            background="opaque",
        )
        if connection_failure:
            with pytest.raises(httpx.ConnectError):
                await call
        else:
            assert (await call)["data"] == png()
        (request,) = seen
        assert request.url.host == "aiplatform.googleapis.com"
        assert request.headers["x-goog-api-key"] == "synthetic"
        assert set(request.extensions["timeout"].values()) == {None}
        assert len(transports) == 1
    finally:
        await backend.close()
    assert backend.closed
    assert backend.client.client._api_client._async_httpx_client.is_closed


@pytest.mark.parametrize("timeout", [0, -1, True, float("inf"), float("nan")])
def test_explicit_invalid_timeout_is_rejected_before_client(timeout):
    with pytest.raises(ValueError, match="timeout"):
        ClientBackend("gptimage", "model", timeout)


def test_explicit_long_timeout_has_no_arbitrary_adapter_cap():
    assert ClientBackend("gptimage", "model", 3600).timeout == 3600
