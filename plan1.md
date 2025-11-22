# План реализации MockProvider

**Общий прогресс: 100%**

## Задачи

### ✅ Шаг 1: Создать файл `src/orchestrator/providers/mock.py`
- ✅ Создать файл с базовой структурой модуля
- ✅ Добавить импорты: `asyncio`, `BaseProvider`, `ProviderConfig`, `GenerationParams`, исключения
- ✅ Добавить module-level docstring

### ✅ Шаг 2: Реализовать класс `MockProvider`
- ✅ Объявить класс `MockProvider(BaseProvider)`
- ✅ Добавить class-level docstring с описанием и примерами использования
- ✅ Реализовать `__init__(config: ProviderConfig)`
  - ✅ Вызвать `super().__init__(config)`
  - ✅ Определить `actual_mode = config.model or "mock-normal"`
  - ✅ Залогировать режим: `self.logger.info(f"MockProvider initialized in mode: {actual_mode}")`

### ✅ Шаг 3: Реализовать метод `async generate()`
- ✅ Реализовать сигнатуру: `async def generate(prompt: str, params: Optional[GenerationParams] = None) -> str`
- ✅ Добавить Google-style docstring с описанием, Args, Returns, Raises, Example
- ✅ Определить режим: `mode = (config.model or "mock-normal").lower()`
- ✅ Реализовать логику режимов:
  - ✅ `mock-timeout` → `raise TimeoutError("Mock timeout simulation")`
  - ✅ `mock-ratelimit` → `raise RateLimitError("Mock rate limit simulation")`
  - ✅ `mock-auth-error` → `raise AuthenticationError("Mock authentication failure")`
  - ✅ `mock-invalid-request` → `raise InvalidRequestError("Mock invalid request")`
  - ✅ Иначе (normal mode):
    - ✅ `await asyncio.sleep(0.1)`
    - ✅ `response = f"Mock response to: {prompt}"`
    - ✅ Обрезать по `max_tokens` (символы) если указан
    - ✅ `self.logger.debug(f"Generating mock response for prompt: {prompt[:50]}...")`
    - ✅ `return response`

### ✅ Шаг 4: Реализовать метод `async health_check()`
- ✅ Реализовать сигнатуру: `async def health_check(self) -> bool`
- ✅ Добавить Google-style docstring с описанием, Returns, Example
- ✅ Реализовать логику:
  - ✅ Проверить `if "unhealthy" in (config.model or "").lower(): return False`
  - ✅ Иначе `return True`

### ✅ Шаг 5: Экспортировать `MockProvider` в `__init__.py`
- ✅ Открыть `src/orchestrator/providers/__init__.py`
- ✅ Добавить импорт: `from .mock import MockProvider`
- ✅ Добавить `MockProvider` в список `__all__`

### ✅ Шаг 6: Проверка интеграции и соответствия стилю
- ✅ Проверить соответствие Google-style docstrings
- ✅ Проверить type hints для всех методов
- ✅ Проверить соответствие стилю кода в `base.py`
- ✅ Убедиться, что все исключения импортированы из `base.py`
- ✅ Проверить, что логирование использует `self.logger` из `BaseProvider`

---

## Технические детали реализации

### Режимы работы (через `config.model`):
- `mock-normal` (по умолчанию) — нормальный ответ с задержкой 0.1с
- `mock-timeout` — выбрасывает `TimeoutError`
- `mock-ratelimit` — выбрасывает `RateLimitError`
- `mock-auth-error` — выбрасывает `AuthenticationError`
- `mock-invalid-request` — выбрасывает `InvalidRequestError`
- Любой режим с `unhealthy` в названии → `health_check()` возвращает `False`

### Особенности:
- Проверка режимов: без учета регистра, точное совпадение
- Проверка `unhealthy`: без учета регистра, частичное совпадение
- `max_tokens` интерпретируется как лимит символов
- Задержка только для нормального режима (0.1с)
- Минимальное логирование через `self.logger`

