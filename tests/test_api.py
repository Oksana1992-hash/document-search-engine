import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# Подавляем предупреждение о переопределении event_loop для чистоты вывода
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.filterwarnings(
        "ignore:The event_loop fixture provided by "
        "pytest-asyncio has been redefined"
    )
]


async def test_search_successful():
    """Проверяем, что поиск возвращает документы и статус"""
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
    ) as ac:
        response = await ac.get("/search", params={"query": "Джесси"})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Так как мы уже загрузили тестовые данные, список не должен быть пустым
    assert len(data) > 0
    # Проверяем структуру первого вернувшегося документа
    first_doc = data[0]
    assert "id" in first_doc
    assert "rubrics" in first_doc
    assert "text" in first_doc


async def test_search_empty_query():
    """Проверяем, что пустой запрос возвращает пустой список"""
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
    ) as ac:
        response = await ac.get("/search", params={"query": "   "})

    assert response.status_code == 200
    assert response.json() == []


async def test_delete_non_existent_document():
    """Проверяем, что при удалении несуществующего ID
    возвращается 404 ошибка"""
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
    ) as ac:
        response = await ac.delete("/document/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Документ не найден в базе данных"
