from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    rubrics: list[str]
    text: str
    created_date: datetime

    class Config:
        from_attributes = True
