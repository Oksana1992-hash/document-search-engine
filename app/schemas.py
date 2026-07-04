from pydantic import BaseModel, ConfigDict
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    rubrics: list[str]
    text: str
    created_date: datetime

    # Конфигурация в стиле Pydantic v2
    model_config = ConfigDict(from_attributes=True)
