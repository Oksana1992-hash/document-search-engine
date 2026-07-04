import asyncio
import os
import ast
import time
import socket
import pandas as pd
from elasticsearch import Elasticsearch
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

CSV_PATH = "posts.csv"
DB_URL = "postgresql+asyncpg://search_user:search_password@db:5432/search_db"
ES_URL = "http://elasticsearch:9200"
INDEX_NAME = "documents"


def wait_for_elasticsearch(host="elasticsearch", port=9200, timeout=60):
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

    print("📖 Чтение оригинального CSV-файла...")
    # Читаем CSV с автоматическим определением разделителя
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", sep=None, engine="python")

    # Очищаем имена колонок от пробелов и приводим к нижнему регистру
    df.columns = df.columns.str.strip().str.lower()
    print(f"📋 Обнаруженные колонки в файле: {df.columns.tolist()}")

    # --- АВТОГЕНЕРАЦИЯ ID ЕСЛИ КОЛОНКА ОТСУТСТВУЕТ ---
    if 'id' not in df.columns:
        print("ℹ️ Колонка 'id' отсутствует в CSV. Генерируем уникальные последовательные ID...")
        # Создаем индекс от 1 до количества строк
        df['id'] = range(1, len(df) + 1)
    else:
        df['id'] = pd.to_numeric(df['id'], errors='coerce')
        df = df.dropna(subset=['id'])
        df['id'] = df['id'].astype(int)

    print("🧹 Преобразование данных и очистка...")

    # Безопасный парсинг рубрик
    def parse_rubrics(val):
        if not isinstance(val, str):
            return []
        val = val.strip()
        if (val.startswith('[') and val.endswith(']')) or (val.startswith('{') and val.endswith('}')):
            try:
                return list(ast.literal_eval(val))
            except Exception:
                pass
        # Если рубрики записаны просто через запятую
        return [r.strip() for r in val.replace('{', '').replace('}', '').replace('[', '').replace(']', '').split(',') if
                r.strip()]

    if 'rubrics' in df.columns:
        df['rubrics'] = df['rubrics'].apply(parse_rubrics)
    else:
        df['rubrics'] = [[] for _ in range(len(df))]

    print("💾 Загрузка данных в PostgreSQL...")
    engine = create_async_engine(DB_URL)

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE documents RESTART IDENTITY;"))

        for _, row in df.iterrows():
            # Обработка даты создания
            raw_date = row.get('created_date')
            try:
                parsed_date = pd.to_datetime(raw_date)
                if pd.isna(parsed_date):
                    parsed_date = pd.Timestamp.utcnow()
            except Exception:
                parsed_date = pd.Timestamp.utcnow()

            await conn.execute(
                text(
                    "INSERT INTO documents (id, rubrics, text, created_date) VALUES (:id, :rubrics, :text, :created_date)"),
                {
                    "id": int(row['id']),
                    "rubrics": row['rubrics'],
                    "text": str(row.get('text', '')),
                    "created_date": parsed_date
                }
            )
    await engine.dispose()
    print("✅ Данные успешно загружены в Postgres!")

    if not wait_for_elasticsearch():
        return

    print("🔍 Индексация данных в Elasticsearch...")
    os.environ["ELASTICSEARCH_URL"] = ES_URL
    from app.elastic import init_es, es_client

    await init_es()

    es = Elasticsearch(ES_URL)
    for _, row in df.iterrows():
        es.index(
            index=INDEX_NAME,
            body={
                "id": int(row['id']),
                "text": str(row.get('text', ''))
            }
        )
    print(f"✅ Успешно проиндексировано {len(df)} документов из posts.csv в Elasticsearch!")
    await es_client.close()


if __name__ == "__main__":
    asyncio.run(import_data_async())
