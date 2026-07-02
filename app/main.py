from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from contextlib import asynccontextmanager
from app.database import get_db, engine, Base
from app.models import Document
from app.schemas import DocumentResponse
from app.elastic import es_client, init_es, INDEX_NAME


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте приложения создаем таблицы в БД, если их нет
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Инициализируем индекс в ElasticSearch
    await init_es()
    yield
    # При остановке закрываем соединение с Elastic
    await es_client.close()

app = FastAPI(
    title="Document Search Engine",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get(
    "/search",
    response_model=list[DocumentResponse],
    summary="Полнотекстовый поиск документов",
)
async def search_documents(
    query: str = Query(..., description="Текстовый запрос для поиска"),
    db: AsyncSession = Depends(get_db)
):
    # Если запрос пустой, сразу возвращаем пустой список
    if not query.strip():
        return []

    # Поиск совпадений в Elassticsearch
    search_query = {
        "query": {
            "match": {
                "text": query
            }
        },
        "size": 100
    }

    es_result = await es_client.search(index=INDEX_NAME, body=search_query)
    hits = es_result["hits"]["hits"]

    if not hits:
        return []

    # Собираем ID найденных документов
    doc_ids = [hit["_source"]["id"] for hit in hits]

    # Извлекаем полные данные из PostgreSQL с сортировкой по дате
    stmt = (
        select(Document)
        .where(Document.id.in_(doc_ids))
        .order_by(Document.created_date.desc())
        .limit(20)
    )

    result = await db.execute(stmt)
    documents = result.scalars().all()

    return documents

@app.delete(
    "/document/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление документа",
)
async def delete_document(doc_id: int, db: AsyncSession=Depends(get_db)):
    # Проверяем, существует ли документ в Postgres
    stmt = select(Document).where(Document.id == doc_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Документ не найден в базе данных",
        )

    # Удаляем из PostgreSQL
    await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()

    # Удаляем из Elasticsearch по внутреннему полю id
    delete_query = {
        "query": {
            "term": {
                "id": doc_id
            }
        }
    }
    await es_client.delete_by_query(index=INDEX_NAME, body=delete_query)

    return None
