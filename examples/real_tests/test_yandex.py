import asyncio
import os

from dotenv import load_dotenv

from orchestrator.providers import ProviderConfig, YandexGPTProvider

load_dotenv()

async def main():
    print("🧪 Тест YandexGPT...")

    config = ProviderConfig(
        name="yandexgpt",
        api_key=os.getenv("YANDEXGPT_API_KEY"),
        folder_id=os.getenv("YANDEXGPT_FOLDER_ID"),
        model="yandexgpt/latest"
    )

    provider = YandexGPTProvider(config)

    # 1. Health check
    print("1. Проверка доступности...")
    is_healthy = await provider.health_check()
    print(f"   Статус: {'✅ OK' if is_healthy else '❌ FAIL'}")

    if not is_healthy:
        print("   YandexGPT недоступен!")
        return

    # 2. Простой запрос
    print("\n2. Простой запрос...")
    response = await provider.generate("Привет! Как дела?")
    print(f"   Ответ: {response[:100]}...")

    # 3. Тест yandexgpt-lite
    print("\n3. Тест yandexgpt-lite/latest...")
    config.model = "yandexgpt-lite/latest"
    provider_lite = YandexGPTProvider(config)
    response = await provider_lite.generate("Что такое Python?")
    print(f"   Ответ: {response[:100]}...")

    print("\n✅ YandexGPT работает!")

if __name__ == "__main__":
    asyncio.run(main())

