import asyncio
import os

from dotenv import load_dotenv

from orchestrator import Router
from orchestrator.providers import GigaChatProvider, ProviderConfig, YandexGPTProvider

load_dotenv()

async def main():
    print("🧪 Тест Router с двумя провайдерами...")

    # Создаем роутер
    router = Router(strategy="round-robin")

    # 1. Настраиваем GigaChat
    gigachat_config = ProviderConfig(
        name="gigachat",
        api_key=os.getenv("GIGACHAT_API_KEY"),
        scope=os.getenv("GIGACHAT_SCOPE"),
        model="GigaChat",
        timeout=30.0,
        verify_ssl=False  # Disable SSL verification for GigaChat with self-signed certificates
    )

    # Создаем провайдера
    gc_provider = GigaChatProvider(gigachat_config)

    # Добавляем уже готовый провайдер в роутер
    router.add_provider(gc_provider)

    # 2. Настраиваем YandexGPT (ему хак не нужен)
    yandex_config = ProviderConfig(
        name="yandexgpt",
        api_key=os.getenv("YANDEXGPT_API_KEY"),
        folder_id=os.getenv("YANDEXGPT_FOLDER_ID"),
        model="yandexgpt/latest"
    )
    # Можно добавить через конфиг (роутер сам создаст) или вручную
    router.add_provider(YandexGPTProvider(yandex_config))

    # 1. Несколько запросов (должны чередоваться)
    print("\n1. Round-robin (3 запроса)...")
    for i in range(3):
        try:
            # Добавим небольшую паузу, чтобы API не ругались
            await asyncio.sleep(1)
            response = await router.route(f"Запрос {i+1}: Привет!")
            print(f"   Ответ {i+1}: {response[:50]}...")
        except Exception as e:
            print(f"   Ошибка запроса {i+1}: {e}")

    # 2. Проверка всех провайдеров
    print("\n2. Проверка health check всех провайдеров...")
    for provider in router.providers:
        try:
            is_healthy = await provider.health_check()
            print(f"   {provider.config.name}: {'✅ OK' if is_healthy else '❌ FAIL'}")
        except Exception as e:
            print(f"   {provider.config.name}: Ошибка {e}")

    print("\n✅ Router работает!")

if __name__ == "__main__":
    asyncio.run(main())

