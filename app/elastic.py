import os
from elasticsearch import AsyncElasticsearch


# URL берем из переменной окружения Docker
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_NAME = "documents"

# Инициализируем асинхронный клиент Elasticsearch
es_client = AsyncElasticsearch(ELASTICSEARCH_URL)

async def init_es():
    """Создает поисковый индекс с русским анализатором, если его нет"""
    exists = await es_client.indices.exists(index=INDEX_NAME)
    if not exists:
        await es_client.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
                    "properties": {
                        "id": {"type": "integer"},
                        # Используем русский анализатор для умного полнотекстового поиска
                        "text": {"type": "text", "analyzer": "russian"}
                    }
                }
            }
        )
        print(f"✅Индекс '{INDEX_NAME}' успешно создан в Elasticsearch.")
