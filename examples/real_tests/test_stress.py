import asyncio
import os
import time

from dotenv import load_dotenv

from orchestrator import Router
from orchestrator.providers import GigaChatProvider, ProviderConfig, YandexGPTProvider

load_dotenv()

async def main():
    print("🧪 Стресс-тест (10 запросов)...")

    router = Router(strategy="round-robin")

    # Добавляем оба провайдера
    router.add_provider(GigaChatProvider(
        ProviderConfig(
            name="gigachat",
            api_key=os.getenv("GIGACHAT_API_KEY"),
            scope=os.getenv("GIGACHAT_SCOPE"),
            timeout=30.0
        )
    ))

    router.add_provider(YandexGPTProvider(
        ProviderConfig(
            name="yandexgpt",
            api_key=os.getenv("YANDEXGPT_API_KEY"),
            folder_id=os.getenv("YANDEXGPT_FOLDER_ID")
        )
    ))

    # 10 параллельных запросов
    start_time = time.time()

    tasks = [
        router.route(f"Вопрос {i+1}: Что такое AI?")
        for i in range(10)
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time

    # Анализ результатов
    success = sum(1 for r in responses if not isinstance(r, Exception))
    failed = sum(1 for r in responses if isinstance(r, Exception))

    print(f"\n✅ Успешно: {success}/10")
    print(f"❌ Ошибок: {failed}/10")
    print(f"⏱️  Время: {elapsed:.2f}s (среднее: {elapsed/10:.2f}s на запрос)")

    if failed > 0:
        print("\nОшибки:")
        for i, r in enumerate(responses):
            if isinstance(r, Exception):
                print(f"  Запрос {i+1}: {r}")

if __name__ == "__main__":
    asyncio.run(main())

