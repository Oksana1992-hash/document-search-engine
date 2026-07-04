import pytest
from httpx import AsyncClient
from app.main import app


# Настраиваем pytest для работы с асинхронным кодом
pytestmark = pytest.mark.asyncio


async def test_search_successful():
    """Проверяем, что поиск возвращает документы и статус"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/search", params={"query": "интеллект"})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Так как мы уже загрузили тестовые данные, список не должен быть пустым
    assert len(data) > 0
    # Проверяем структуру первого вернувшегося документа
    assert "id" in data[0]
    assert "rubrics" in data[0]
    assert "text" in data[0]


async def test_search_empty_query():
    """Проверяем, что пустой запрос возвращает пустой список"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/search", params={"query": "   "})

    assert response.status_code == 200
    assert response.json() == []


async def test_delete_non_existent_document():
    """Проверяем, что при удалении несуществующего ID
    возвращается 404 ошибка"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete("/document/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Документ не найден в базе данных"
