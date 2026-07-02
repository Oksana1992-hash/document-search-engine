import asyncio
import os
import ast
import time
import socket
import pandas as pd
from elasticsearch import Elasticsearch
from sqlalchemy import create_engine


# Настройки
CSV_PATH = "data.csv"
DB_URL = "postgresql://search_user:search_password@localhost:5433/search_db"
ES_URL = "http://localhost:9200"
INDEX_NAME = "documents"


def wait_for_elasticsearch(host="localhost", port=9200, timeout=60):
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


def import_data():
    if not os.path.exists(CSV_PATH):
        print(f"❌ Файл {CSV_PATH} не найден!")
        return

    print("📖 Чтение CSV-файла...")
    df = pd.read_csv(CSV_PATH)

    print("🧹 Преобразование данных...")
    df['rubrics'] = df['rubrics'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

    print("💾 Загрузка данных в PostgreSQL...")
    engine = create_engine(DB_URL)
    df.to_sql('documents', engine, if_exists='replace', index=False)
    print("✅ Данные успешно загружены в Postgres!")

    # Перед подключением дождемся готовности Elasticsearch
    if not wait_for_elasticsearch():
        return

    print("🔍 Индексация данных в Elasticsearch...")
    os.environ["ELASTICSEARCH_URL"] = ES_URL
    from app.elastic import init_es, es_client

    # Создаем индекс
    asyncio.run(init_es())

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

    asyncio.run(es_client.close())


if __name__ == "__main__":
    import_data()
