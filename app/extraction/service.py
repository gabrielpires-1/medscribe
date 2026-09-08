from app.clients.anthropic_client import AnthropicClient
from app.config import Settings, get_settings
from app.extraction.prompts import EXTRACTION_SYSTEM_PROMPT
from app.extraction.schemas import ConsultationDocuments


class ExtractionService:
    def __init__(
        self,
        client: AnthropicClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        resolved_settings = settings or get_settings()
        self._client = client or AnthropicClient(settings=resolved_settings)

    async def extract(self, transcript: str) -> ConsultationDocuments:
        return await self._client.parse(
            system=EXTRACTION_SYSTEM_PROMPT,
            user=transcript,
        )
