import asyncio
import os
from dotenv import load_dotenv
from orchestrator import Router
from orchestrator.providers import GigaChatProvider, ProviderConfig

load_dotenv()

async def main():
    print("🧪 Тест GigaChat...")
    
    config = ProviderConfig(
        name="gigachat",
        api_key=os.getenv("GIGACHAT_API_KEY"),
        scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        model="GigaChat",
        timeout=30.0,
        verify_ssl=False  # Disable SSL verification for GigaChat with self-signed certificates
    )
    
    provider = GigaChatProvider(config)
    
    # 1. Health check
    print("1. Проверка доступности...")
    is_healthy = await provider.health_check()
    print(f"   Статус: {'✅ OK' if is_healthy else '❌ FAIL'}")
    
    if not is_healthy:
        print("   GigaChat недоступен!")
        return
    
    # 2. Простой запрос
    print("\n2. Простой запрос...")
    response = await provider.generate("Привет! Как дела?")
    print(f"   Ответ: {response[:100]}...")
    
    # 3. Запрос с параметрами
    print("\n3. Запрос с temperature...")
    from orchestrator.providers.base import GenerationParams
    params = GenerationParams(temperature=0.8, max_tokens=50)
    response = await provider.generate("Расскажи шутку про Python", params)
    print(f"   Ответ: {response}")
    
    print("\n✅ GigaChat работает!")

if __name__ == "__main__":
    asyncio.run(main())
