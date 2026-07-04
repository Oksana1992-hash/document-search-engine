from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    # Уникальный ID для каждого документа
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Массив рубрик (текстовые теги/категории)
    rubrics: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    # Текст документа
    text: Mapped[str] = mapped_column(String, nullable=False)

    # Дата создания документа
    created_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
