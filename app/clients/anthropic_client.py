from __future__ import annotations

from anthropic import APIError, AsyncAnthropic

from app.config import Settings, get_settings
from app.constants import (
    ANTHROPIC_MISSING_PARSED_OUTPUT_MESSAGE,
    ANTHROPIC_REFUSAL_MESSAGE,
)
from app.exceptions import AnthropicClientError
from app.extraction.schemas import ConsultationDocuments


class AnthropicClient:
    def __init__(
        self,
        settings: Settings | None = None,
        sdk: AsyncAnthropic | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._sdk = sdk or AsyncAnthropic(
            api_key=self._settings.anthropic_api_key,
            base_url=self._settings.anthropic_base_url,
        )

    async def parse(self, *, system: str, user: str) -> ConsultationDocuments:
        try:
            response = await self._sdk.messages.parse(
                model=self._settings.anthropic_model,
                max_tokens=self._settings.anthropic_max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=ConsultationDocuments,
            )
        except APIError as exc:
            raise AnthropicClientError(f"anthropic request failed: {exc}") from exc
        if response.stop_reason == "refusal":
            raise AnthropicClientError(ANTHROPIC_REFUSAL_MESSAGE)
        parsed = response.parsed_output
        if parsed is None or not isinstance(parsed, ConsultationDocuments):
            raise AnthropicClientError(ANTHROPIC_MISSING_PARSED_OUTPUT_MESSAGE)
        return parsed
