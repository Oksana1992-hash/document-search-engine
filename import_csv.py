import asyncio
import os
import ast
import time
import socket
import pandas as pd
from elasticsearch import Elasticsearch
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


# Настройки для запуска внутри сети Docker
CSV_PATH = "posts.csv"
DB_URL = "postgresql+asyncpg://search_user:search_password@db:5432/search_db"
ES_URL = "http://elasticsearch:9200"
INDEX_NAME = "documents"


def wait_for_elasticsearch(host="elasticsearch", port=9200, timeout=60):
    """Ожидает, пока порт Elasticsearch станет доступен для подключения"""
    print(f"⏳ Ожидание запуска Elasticsearch на {host}:{port}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                print("🚀 Elasticsearch успешно запустился и готов к работе!")
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(2)
    print("❌ Превышено время ожидания запуска Elasticsearch.")
    return False


async def import_data_async():
    if not os.path.exists(CSV_PATH):
        print(f"❌ Файл {CSV_PATH} не найден!")
        return

    print("📖 Чтение CSV-файла...")
    df = pd.read_csv(CSV_PATH)

    print("🧹 Преобразование данных...")
    df['rubrics'] = df['rubrics'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

    # 1. Загрузка в PostgreSQL через асинхронный движок
    print("💾 Загрузка данных в PostgreSQL...")
    engine = create_async_engine(DB_URL)

    async with engine.begin() as conn:
        # Очищаем таблицу перед импортом
        await conn.execute(text("TRUNCATE TABLE documents RESTART IDENTITY;"))

        # Вставляем строки пакетно через асинхронное подключение
        for _, row in df.iterrows():
            await conn.execute(
                text(
                    "INSERT INTO documents (id, rubrics, text, created_date) VALUES (:id, :rubrics, :text, :created_date)"),
                {
                    "id": int(row['id']),
                    "rubrics": row['rubrics'],
                    "text": str(row['text']),
                    "created_date": pd.to_datetime(row['created_date'])
                }
            )
    await engine.dispose()
    print("✅ Данные успешно загружены в Postgres!")

    # 2. Ожидание и инициализация Elasticsearch
    if not wait_for_elasticsearch():
        return

    print("🔍 Индексация данных в Elasticsearch...")
    os.environ["ELASTICSEARCH_URL"] = ES_URL
    from app.elastic import init_es, es_client

    # Создаем индекс с русским анализатором
    await init_es()

    # Наполняем индекс документами
    es = Elasticsearch(ES_URL)
    for _, row in df.iterrows():
        es.index(
            index=INDEX_NAME,
            body={
                "id": int(row['id']),
                "text": str(row['text'])
            }
        )
    print(f"✅ Успешно проиндексировано {len(df)} документов в Elasticsearch!")
    await es_client.close()


if __name__ == "__main__":
    asyncio.run(import_data_async())
