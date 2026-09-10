from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest
from anthropic import APIError, APITimeoutError
from pytest_mock import MockerFixture

from app.clients.anthropic_client import AnthropicClient
from app.config import Settings
from app.constants import (
    ANTHROPIC_MISSING_PARSED_OUTPUT_MESSAGE,
    ANTHROPIC_REFUSAL_MESSAGE,
)
from app.exceptions import AnthropicClientError
from app.extraction.schemas import ConsultationDocuments
from tests.fakes import fake_consultation_documents


def _settings() -> Settings:
    return Settings(
        pyannote_api_key="fake-api-key",
        anthropic_api_key="fake-anthropic-key",
    )


def _request() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def _patch_sdk(mocker: MockerFixture, parse: AsyncMock) -> MagicMock:
    sdk = MagicMock()
    sdk.messages.parse = parse
    mocker.patch("app.clients.anthropic_client.AsyncAnthropic", return_value=sdk)
    return sdk


async def test_parse_passes_consultation_documents(mocker: MockerFixture) -> None:
    documents = fake_consultation_documents()
    response = MagicMock()
    response.parsed_output = documents
    response.stop_reason = "end_turn"
    parse = AsyncMock(return_value=response)
    _patch_sdk(mocker, parse)
    result = await AnthropicClient(settings=_settings()).parse(
        system="fake-system-prompt",
        user="[SPEAKER_00] fake-turn-one",
    )
    assert result == documents
    parse.assert_awaited_once()
    assert parse.await_args is not None
    kwargs = parse.await_args.kwargs
    assert kwargs["output_format"] is ConsultationDocuments
    assert kwargs["system"] == "fake-system-prompt"
    assert kwargs["messages"] == [
        {"role": "user", "content": "[SPEAKER_00] fake-turn-one"}
    ]
    assert kwargs["model"] == "claude-sonnet-4-5"
    assert kwargs["max_tokens"] == 8192


async def test_parse_maps_api_error(mocker: MockerFixture) -> None:
    parse = AsyncMock(
        side_effect=APIError("upstream-failed", _request(), body=None),
    )
    _patch_sdk(mocker, parse)
    with pytest.raises(AnthropicClientError) as exc_info:
        await AnthropicClient(settings=_settings()).parse(
            system="fake-system-prompt",
            user="[SPEAKER_00] fake-turn-one",
        )
    assert "upstream-failed" in exc_info.value.message


async def test_parse_maps_timeout(mocker: MockerFixture) -> None:
    parse = AsyncMock(side_effect=APITimeoutError(_request()))
    _patch_sdk(mocker, parse)
    with pytest.raises(AnthropicClientError):
        await AnthropicClient(settings=_settings()).parse(
            system="fake-system-prompt",
            user="[SPEAKER_00] fake-turn-one",
        )


async def test_parse_maps_refusal(mocker: MockerFixture) -> None:
    response = MagicMock()
    response.parsed_output = None
    response.stop_reason = "refusal"
    parse = AsyncMock(return_value=response)
    _patch_sdk(mocker, parse)
    with pytest.raises(AnthropicClientError) as exc_info:
        await AnthropicClient(settings=_settings()).parse(
            system="fake-system-prompt",
            user="[SPEAKER_00] fake-turn-one",
        )
    assert exc_info.value.message == ANTHROPIC_REFUSAL_MESSAGE


async def test_parse_maps_missing_parsed_output(mocker: MockerFixture) -> None:
    response = MagicMock()
    response.parsed_output = None
    response.stop_reason = "end_turn"
    parse = AsyncMock(return_value=response)
    _patch_sdk(mocker, parse)
    with pytest.raises(AnthropicClientError) as exc_info:
        await AnthropicClient(settings=_settings()).parse(
            system="fake-system-prompt",
            user="[SPEAKER_00] fake-turn-one",
        )
    assert exc_info.value.message == ANTHROPIC_MISSING_PARSED_OUTPUT_MESSAGE
