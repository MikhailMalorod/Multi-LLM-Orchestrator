# ЭТАП 1: ПОНИМАНИЕ ЗАДАЧИ - ОТЧЕТ

**Дата:** 2026-01-XX  
**Задача:** Issue #7 - Hybrid Usage Callback API  
**Версия:** v0.7.5 → v0.7.6  
**Deadline:** Jan 10, 2026 EOD

---

## 📋 ИЗУЧЕННЫЕ МАТЕРИАЛЫ

### GitHub Issues
- ✅ **Issue #7:** Прочитан полностью, включая комментарий от Platform SaaS Team с hybrid API proposal
- ✅ **Issue #5:** Прочитан для контекста (router.update_providers() - PRIORITY 1, доставлен досрочно)

### Код проекта
- ✅ `src/orchestrator/router.py` (922 строки) - полный анализ
- ✅ `tests/test_router.py` (460 строк) - изучены паттерны тестирования
- ✅ `src/orchestrator/providers/base.py` - структура ProviderConfig
- ✅ `src/orchestrator/pricing.py` - функция calculate_cost()
- ✅ `src/orchestrator/tokenization.py` - функция count_tokens()
- ✅ `pyproject.toml` - зависимости и конфигурация

---

## 🎯 ОТВЕТЫ НА ВОПРОСЫ

### 1. Архитектура Router

#### 1.1. Router.__init__() - текущая структура
**Файл:** `src/orchestrator/router.py`, строки 63-105

```python
def __init__(self, strategy: str = "round-robin") -> None:
    # Validation
    if strategy not in VALID_STRATEGIES:
        raise ValueError(...)
    
    self.strategy = strategy
    self.providers: list[BaseProvider] = []
    self.metrics: dict[str, ProviderMetrics] = {}
    self._current_index: int = 0
    self.logger = logging.getLogger("orchestrator.router")
    
    # Prometheus exporter (v0.7.0+)
    self._prometheus_exporter: PrometheusExporter | None = None
    self._metrics_update_task: asyncio.Task[None] | None = None
```

**Ответ:**
- **Текущие параметры:** только `strategy: str = "round-robin"`
- **Где добавить:** После `strategy` параметра, перед валидацией
- **Logger:** ✅ Да, есть `self.logger = logging.getLogger("orchestrator.router")` (строка 99)

---

### 2. Integration Points

#### 2.1. route() - Token Counting
**Файл:** `src/orchestrator/router.py`, строки 365-375

```python
# Count tokens (v0.7.0+)
prompt_tokens = count_tokens(prompt)           # Строка 366
completion_tokens = count_tokens(result)        # Строка 367
total_tokens = prompt_tokens + completion_tokens # Строка 368

# Calculate cost (v0.7.0+)
cost = calculate_cost(                          # Строка 371
    provider_name=provider.config.name,         # Строка 372
    model=provider.config.model,                # Строка 373
    total_tokens=total_tokens,                 # Строка 374
)                                               # Строка 375
```

**Ответ:**
- **Token counting:** Строки 366-368 (после получения `result`, до обновления metrics)
- **Cost calculation:** Строки 371-375 (используется `calculate_cost()` из `pricing.py`)
- **Integration point для callback (success):** После строки 402 (после `_log_request_event()`, перед `return result`)

#### 2.2. route() - Exception Handler
**Файл:** `src/orchestrator/router.py`, строки 408-435

```python
except Exception as e:
    # Calculate latency even for failed requests
    latency_ms = (time.perf_counter() - start_time) * 1000  # Строка 410
    
    # Update metrics (строки 412-419)
    metrics = self.metrics.get(provider.config.name)
    if metrics is None:
        metrics = ProviderMetrics()
        self.metrics[provider.config.name] = metrics
    metrics.record_error(latency_ms, datetime.now(UTC))  # Строка 418
    
    # Log failure event (строки 422-429)
    self._log_request_event(...)
    
    # Continue to next provider (строки 431-434)
    self.logger.warning(...)
    last_error = e
    continue
```

**Ответ:**
- **Exception handler:** Строки 408-435
- **Integration point для callback (error):** После строки 429 (после `_log_request_event()`, перед `continue`)
- **Важно:** В случае ошибки `prompt_tokens=0`, `completion_tokens=0`, `cost=0.0` (как в ТЗ)

#### 2.3. route_stream() - существование и структура
**Файл:** `src/orchestrator/router.py`, строки 618-812

**Ответ:**
- ✅ **Метод существует:** `async def route_stream()` начинается на строке 618
- **Success path:** После успешного streaming (строки 714-763)
  - Token counting: строки 722-724
  - Cost calculation: строки 727-731
  - Metrics update: строки 740-745
  - Logging: строки 748-758
  - **Integration point:** После строки 758 (после `_log_request_event()`, перед `return`)
- **Error path:** Внутренний exception handler (строки 765-799)
  - **Integration point:** После строки 786 (после `_log_request_event()`, перед `raise`)

---

### 3. Dependencies

#### 3.1. httpx в зависимостях
**Файл:** `pyproject.toml`, строка 35

```toml
httpx = "^0.27.0"
```

**Ответ:**
- ✅ **httpx уже в зависимостях:** `httpx = "^0.27.0"` (production dependency)
- ✅ **pytest-httpx для тестов:** `pytest-httpx = "^0.30.0"` (dev dependency, строка 52)

#### 3.2. Python версия
**Файл:** `pyproject.toml`, строки 33, 78

```toml
python = "^3.11"
[tool.mypy]
python_version = "3.11"
```

**Ответ:**
- ✅ **Python 3.11+:** Поддерживает `str | None` синтаксис (не нужен `Optional[str]`)

#### 3.3. datetime.now(UTC) в проекте
**Файл:** `src/orchestrator/router.py`, строки 8, 418, 775

```python
from datetime import UTC, datetime
# ...
metrics.record_error(latency_ms, datetime.now(UTC))  # Строка 418
```

**Ответ:**
- ✅ **Уже используется:** `datetime.now(UTC)` используется в проекте (строки 418, 775)
- ✅ **Импорт:** `from datetime import UTC, datetime` (строка 8)

---

### 4. Testing Infrastructure

#### 4.1. Test Framework
**Файл:** `pyproject.toml`, строки 49-52

```toml
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
pytest-httpx = "^0.30.0"
```

**Ответ:**
- ✅ **Framework:** pytest
- ✅ **Async support:** pytest-asyncio с `asyncio_mode = "auto"` (строка 93)
- ✅ **HTTP mocking:** pytest-httpx (используется в `test_gigachat_provider.py`, `test_yandexgpt_provider.py`)

#### 4.2. Примеры async тестов
**Файл:** `tests/test_router.py`, примеры:
- `test_round_robin_cycles_through_providers()` (строка 94) - `@pytest.mark.asyncio`
- `test_router_updates_metrics_on_success()` (строка 314) - `@pytest.mark.asyncio`

**Ответ:**
- ✅ **Паттерн:** `@pytest.mark.asyncio` + `async def test_...()`
- ✅ **Примеры:** Множество async тестов в `test_router.py`

#### 4.3. Моки
**Файл:** `tests/test_gigachat_provider.py`, пример:

```python
async def test_generate_success(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
    httpx_mock.add_response(...)
```

**Ответ:**
- ✅ **Библиотека:** pytest-httpx для HTTP моков
- ✅ **Паттерн:** `httpx_mock: pytest_httpx.HTTPXMock` как параметр теста
- ✅ **Для httpx.AsyncClient:** Можно мокать через `httpx_mock.add_response()` или `httpx_mock.add_callback()`

---

### 5. Token Counting & Cost Calculation

#### 5.1. count_tokens()
**Файл:** `src/orchestrator/tokenization.py`, строка 25

```python
def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens using tiktoken with fallback to word-based estimation."""
    # ...
```

**Ответ:**
- ✅ **Функция существует:** `count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int`
- ✅ **Используется в route():** Строки 366-367
- ✅ **Fallback:** Есть fallback на word-based estimation если tiktoken не работает

#### 5.2. calculate_cost()
**Файл:** `src/orchestrator/pricing.py`, строка 93

```python
def calculate_cost(
    provider_name: str, model: str | None, total_tokens: int
) -> float:
    """Calculate cost in RUB for LLM request."""
    # ...
```

**Ответ:**
- ✅ **Функция существует:** `calculate_cost(provider_name, model, total_tokens) -> float`
- ✅ **Используется в route():** Строки 371-375
- ✅ **Возвращает:** Cost в RUB (float)

#### 5.3. provider.config.name и provider.config.model
**Файл:** `src/orchestrator/providers/base.py`, строки 21-106

```python
class ProviderConfig(BaseModel):
    name: str = Field(..., description="Provider identifier")
    model: str | None = Field(None, description="Model name or version")
```

**Ответ:**
- ✅ **Доступны:** `provider.config.name` (str) и `provider.config.model` (str | None)
- ✅ **Используются в route():** Строки 372-373, 394, 424
- ✅ **Типы:** `name` всегда str, `model` может быть None

---

### 6. Error Handling

#### 6.1. Типы исключений в route()
**Файл:** `src/orchestrator/router.py`, строки 318-324, 408

```python
Raises:
    ProviderError: If no providers are registered
    TimeoutError: If all providers timeout
    RateLimitError: If all providers hit rate limit
    AuthenticationError: If all providers fail authentication
    InvalidRequestError: If all providers receive invalid requests
    Exception: Any other exception from the last failed provider
```

**Ответ:**
- **Исключения:** ProviderError, TimeoutError, RateLimitError, AuthenticationError, InvalidRequestError, Exception
- **Обработка:** Все ловятся в `except Exception as e:` (строка 408)
- **error_type для callback:** `type(e).__name__` (строка 428)

#### 6.2. Порядок: callback vs metrics
**Текущий порядок в route() (success):**
1. Token counting (366-368)
2. Cost calculation (371-375)
3. Metrics update (384-389)
4. Logging (392-402)
5. **→ CALLBACK ЗДЕСЬ (после logging, перед return)**

**Текущий порядок в route() (error):**
1. Latency calculation (410)
2. Metrics update (412-419)
3. Logging (422-429)
4. **→ CALLBACK ЗДЕСЬ (после logging, перед continue)**

**Ответ:**
- ✅ **Callback ПОСЛЕ metrics:** Правильно, чтобы metrics обновлялись даже если callback упадет
- ✅ **Callback ПОСЛЕ logging:** Правильно, для consistency

---

### 7. Code Style

#### 7.1. Docstrings
**Файл:** `src/orchestrator/router.py`, пример (строки 20-60):

```python
class Router:
    """Router for managing LLM provider selection and request routing.

    The Router handles intelligent routing of requests to appropriate
    LLM providers based on configurable routing strategies.
    ...
    """
```

**Ответ:**
- ✅ **Google-style docstrings:** Используются везде (классы, методы)
- ✅ **Формат:** Triple-quoted strings с Args, Returns, Raises, Example

#### 7.2. Type Hints
**Файл:** `pyproject.toml`, строки 77-81

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

**Ответ:**
- ✅ **mypy strict mode:** Включен (`strict = true`)
- ✅ **Type hints:** Обязательны для всех функций/методов
- ✅ **Синтаксис:** `str | None` (Python 3.11+), не `Optional[str]`

#### 7.3. Ruff (Linting)
**Файл:** `pyproject.toml`, строки 61-75

```toml
[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP"]
ignore = ["E501"]  # Line too long
```

**Ответ:**
- ✅ **Ruff используется:** Включены правила E, W, F, I, B, C4, UP
- ✅ **Line length:** 88 символов (Black-compatible)
- ✅ **Игнорируется:** E501 (line too long)

---

### 8. Backward Compatibility

#### 8.1. Существующие пользователи
**Контекст:**
- Issue #5 (PRIORITY 1) был доставлен для Platform SaaS Team
- telegram-bot-universal использует Router
- Есть downstream consumers (Platform SaaS)

**Ответ:**
- ✅ **Есть пользователи:** Platform SaaS, telegram-bot-universal
- ✅ **Backward compatibility критична:** Все новые параметры должны быть optional с `None` default

#### 8.2. Опциональность параметров
**Текущий __init__():**
```python
def __init__(self, strategy: str = "round-robin") -> None:
```

**Предлагаемый __init__():**
```python
def __init__(
    self,
    strategy: str = "round-robin",
    usage_callback: UsageCallback | None = None,  # NEW, optional
    callback_url: str | None = None,              # NEW, optional
    tenant_id: str | None = None,                  # NEW, optional
    platform_key_id: str | None = None,           # NEW, optional
) -> None:
```

**Ответ:**
- ✅ **Все параметры optional:** `None` default для всех новых параметров
- ✅ **Backward compatible:** Существующий код `Router(strategy="round-robin")` продолжит работать

---

## 📍 ТОЧНЫЕ INTEGRATION POINTS

### route() - Success Path
**Файл:** `src/orchestrator/router.py`

**После строки 402** (после `_log_request_event()`, перед `return result`):

```python
# Строка 402: self._log_request_event(...)

# NEW: Invoke usage callback (success)
await self._invoke_usage_callback(
    provider_name=provider.config.name,
    model=provider.config.model,
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    cost=cost,
    latency_ms=latency_ms,
    success=True,
    streaming=False,
)

# Строка 407: return result
```

### route() - Error Path
**Файл:** `src/orchestrator/router.py`

**После строки 429** (после `_log_request_event()`, перед `continue`):

```python
# Строка 429: self._log_request_event(...)

# NEW: Invoke usage callback (error)
await self._invoke_usage_callback(
    provider_name=provider.config.name,
    model=provider.config.model,
    prompt_tokens=0,
    completion_tokens=0,
    cost=0.0,
    latency_ms=latency_ms,
    success=False,
    streaming=False,
    error_type=type(e).__name__,
)

# Строка 431: self.logger.warning(...)
# Строка 434: continue
```

### route_stream() - Success Path
**Файл:** `src/orchestrator/router.py`

**После строки 758** (после `_log_request_event()`, перед `return`):

```python
# Строка 758: self._log_request_event(...)

# NEW: Invoke usage callback (success, streaming)
await self._invoke_usage_callback(
    provider_name=provider.config.name,
    model=provider.config.model,
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    cost=cost,
    latency_ms=latency_ms,
    success=True,
    streaming=True,
)

# Строка 763: return
```

### route_stream() - Error Path
**Файл:** `src/orchestrator/router.py`

**После строки 786** (после `_log_request_event()`, перед `raise`):

```python
# Строка 786: self._log_request_event(...)

# NEW: Invoke usage callback (error, streaming)
await self._invoke_usage_callback(
    provider_name=provider.config.name,
    model=provider.config.model,
    prompt_tokens=0,
    completion_tokens=0,
    cost=0.0,
    latency_ms=latency_ms,
    success=False,
    streaming=True,
    error_type=type(stream_error).__name__,
)

# Строка 796: raise
```

---

## ⚠️ ПОТЕНЦИАЛЬНЫЕ РИСКИ / НЕЯСНОСТИ

### 1. HTTP Callback Timeout
**Вопрос:** ТЗ предлагает `timeout=5.0` для httpx.AsyncClient. Это достаточно?

**Рекомендация:**
- ✅ 5.0 секунд разумно для billing API
- ⚠️ **Уточнить:** Нужна ли возможность настройки timeout через параметр?

### 2. HTTP Callback Retry Logic
**Вопрос:** Нужны ли retries для HTTP callback? ТЗ не упоминает.

**Рекомендация:**
- ✅ **Fail-silent подход правильный:** Не retry, просто log warning
- ✅ **Обоснование:** Billing API должен быть надежным, если он недоступен - это проблема инфраструктуры, не orchestrator

### 3. UsageData Dataclass Location
**Вопрос:** Где разместить `UsageData` dataclass?

**Варианты:**
- `src/orchestrator/router.py` (вместе с Router)
- `src/orchestrator/types.py` (новый файл для типов)
- `src/orchestrator/__init__.py` (для публичного API)

**Рекомендация:**
- ✅ **router.py:** Логично, так как используется только в Router
- ⚠️ **Альтернатива:** Если планируется использовать в других модулях - создать `types.py`

### 4. Callback Invocation Order в Fallback
**Вопрос:** Если происходит fallback (provider1 fails → provider2 succeeds), вызывать callback для обоих?

**Текущее понимание:**
- ✅ **Вызывать для обоих:** provider1 (error) + provider2 (success)
- ✅ **Обоснование:** Platform SaaS нужен полный audit trail

**Уточнение:** Подтвердить в Issue #7 комментарии.

### 5. tenant_id и platform_key_id Validation
**Вопрос:** Нужна ли валидация этих полей (формат, длина)?

**Рекомендация:**
- ✅ **Минимальная валидация:** Проверка что это не пустая строка (если не None)
- ⚠️ **Или:** Оставить без валидации, Platform SaaS сам контролирует формат

### 6. HTTP Callback Payload Schema
**Вопрос:** ТЗ использует snake_case (`prompt_tokens`), но некоторые API предпочитают camelCase (`promptTokens`).

**Рекомендация:**
- ✅ **Оставить snake_case:** Consistency с Python codebase
- ✅ **Если нужен camelCase:** Platform SaaS может трансформировать на своей стороне

### 7. Callback Error Logging Level
**Вопрос:** ТЗ предлагает `self.logger.warning()`. Достаточно ли?

**Рекомендация:**
- ✅ **warning() правильно:** Не критично для основного flow, но важно для мониторинга
- ✅ **Альтернатива:** Можно добавить `error()` если callback падает несколько раз подряд (но это усложнение)

---

## 💡 ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ API

### 1. Naming Conventions
**Текущее предложение:**
- `usage_callback` ✅
- `callback_url` ✅
- `tenant_id` ✅
- `platform_key_id` ✅

**Альтернативы (если нужна ясность):**
- `http_callback_url` вместо `callback_url` (более явно)
- `usage_callback_url` вместо `callback_url` (более специфично)

**Рекомендация:** Оставить как в ТЗ, названия понятные.

### 2. Error Handling Strategy
**Текущее предложение:** Fail-silent (log warning, не raise).

**Альтернатива:** Добавить опциональный `raise_on_callback_error: bool = False`.

**Рекомендация:** Оставить fail-silent, это правильный подход для billing callbacks.

### 3. Test Coverage Strategy
**Минимальный набор (из ТЗ):**
- ✅ Python callback (success)
- ✅ Python callback (error)
- ✅ HTTP POST callback (success, mocked)
- ✅ HTTP POST callback (error, mocked)
- ✅ Validation (cannot specify both)
- ✅ tenant_id/platform_key_id inclusion
- ✅ Fail-silent behavior

**Дополнительные тесты (рекомендуется):**
- ✅ Callback в fallback scenario (provider1 error → provider2 success)
- ✅ Callback в route_stream() (success + error)
- ✅ Callback с None model (provider.config.model = None)
- ✅ HTTP callback timeout simulation
- ✅ HTTP callback network error simulation

---

## ✅ КРИТЕРИИ ЗАВЕРШЕНИЯ ЭТАПА 1

- [x] Прочитан Issue #7 и все комментарии
- [x] Изучен код `orchestrator/router.py` (Router class)
- [x] Изучены существующие тесты `tests/test_router.py`
- [x] Даны ответы на все 8 категорий вопросов
- [x] Определены точные integration points (номера строк)
- [x] Перечислены потенциальные риски/неясности
- [x] Готов список вопросов для координатора (если есть неясности)

---

## 📝 ВОПРОСЫ ДЛЯ КООРДИНАТОРА

### 1. HTTP Callback Timeout
**Вопрос:** Нужна ли возможность настройки timeout для HTTP callback (сейчас 5.0 сек hardcoded)?

**Варианты:**
- A) Оставить 5.0 сек hardcoded
- B) Добавить параметр `callback_timeout: float = 5.0` в `__init__()`

### 2. UsageData Location
**Вопрос:** Где разместить `UsageData` dataclass?

**Варианты:**
- A) `router.py` (вместе с Router)
- B) `types.py` (новый файл для типов)
- C) `__init__.py` (для публичного API)

### 3. Callback в Fallback
**Вопрос:** Если происходит fallback (provider1 fails → provider2 succeeds), вызывать callback для обоих провайдеров?

**Варианты:**
- A) Да, оба (provider1 error + provider2 success)
- B) Нет, только для финального успешного провайдера

### 4. tenant_id/platform_key_id Validation
**Вопрос:** Нужна ли валидация этих полей (формат, длина)?

**Варианты:**
- A) Минимальная валидация (не пустая строка если не None)
- B) Без валидации (Platform SaaS сам контролирует)

---

## 🎯 ГОТОВНОСТЬ К ЭТАПУ 2

**Статус:** ✅ **ГОТОВ**

Все вопросы изучены, integration points определены, риски выявлены. Готов к получению **Промпта 2** для составления детального плана реализации.

---

**Следующий шаг:** Ожидание ответов на вопросы (если нужны уточнения) → Получение Промпта 2 → Составление `plan.md`

