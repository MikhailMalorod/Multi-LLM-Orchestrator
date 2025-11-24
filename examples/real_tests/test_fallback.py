import asyncio
import os
from dotenv import load_dotenv
from orchestrator import Router
from orchestrator.providers import GigaChatProvider, YandexGPTProvider, MockProvider, ProviderConfig

load_dotenv()

async def main():
    print("🧪 Тест Fallback (автоматическое переключение)...")
    
    router = Router(strategy="first-available")
    
    # Добавляем Mock с режимом таймаута (будет падать)
    mock_config = ProviderConfig(name="mock-fail", model="mock-timeout")
    router.add_provider(MockProvider(mock_config))
    
    # Добавляем реальные провайдеры (они подхватят запрос)
    gigachat_config = ProviderConfig(
        name="gigachat",
        api_key=os.getenv("GIGACHAT_API_KEY"),
        scope=os.getenv("GIGACHAT_SCOPE"),
        model="GigaChat"
    )
    router.add_provider(GigaChatProvider(gigachat_config))
    
    yandex_config = ProviderConfig(
        name="yandexgpt",
        api_key=os.getenv("YANDEXGPT_API_KEY"),
        folder_id=os.getenv("YANDEXGPT_FOLDER_ID"),
        model="yandexgpt/latest"
    )
    router.add_provider(YandexGPTProvider(yandex_config))
    
    # Запрос должен автоматически переключиться на рабочий провайдер
    print("\n1. Запрос (mock-fail → gigachat → yandex)...")
    response = await router.route("Привет! Как дела?")
    print(f"   Ответ: {response[:100]}...")
    print("   ✅ Fallback сработал!")

if __name__ == "__main__":
    asyncio.run(main())

