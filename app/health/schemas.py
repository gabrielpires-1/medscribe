from pydantic import BaseModel, Field


class HealthRead(BaseModel):
    status: str = Field(..., min_length=1, examples=["ok"])
