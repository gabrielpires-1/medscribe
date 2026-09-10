from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.exceptions import AnthropicClientError
from app.extraction.prompts import EXTRACTION_SYSTEM_PROMPT
from app.extraction.service import ExtractionService
from tests.fakes import fake_consultation_documents


def _settings() -> Settings:
    return Settings(
        pyannote_api_key="fake-api-key",
        anthropic_api_key="fake-anthropic-key",
    )


async def test_extract_returns_documents() -> None:
    documents = fake_consultation_documents()
    client = MagicMock()
    client.parse = AsyncMock(return_value=documents)
    result = await ExtractionService(client=client, settings=_settings()).extract(
        "[SPEAKER_00] fake-turn-one"
    )
    assert result == documents
    client.parse.assert_awaited_once_with(
        system=EXTRACTION_SYSTEM_PROMPT,
        user="[SPEAKER_00] fake-turn-one",
    )


async def test_extract_maps_client_errors() -> None:
    client = MagicMock()
    client.parse = AsyncMock(side_effect=AnthropicClientError("upstream-failed"))
    with pytest.raises(AnthropicClientError) as exc_info:
        await ExtractionService(client=client, settings=_settings()).extract(
            "[SPEAKER_00] fake-turn-one"
        )
    assert exc_info.value.message == "upstream-failed"
