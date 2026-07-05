import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Создает единый Event Loop на всю сессию тестов,
    предотвращая RuntimeError в asyncpg"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def pytest_configure(config):
    """Отключаем встроенное автоматическое переопределение циклов"""
    config.option.asyncio_mode = "auto"
