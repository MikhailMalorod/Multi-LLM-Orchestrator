
### 👋 Привет, команда Multi-LLM-Orchestrator!

Обращается к вам команда **Platform SaaS** (https://ubpl.ru) — мы используем Multi-LLM-Orchestrator как core-библиотеку для работы с российскими LLM-провайдерами (GigaChat, YandexGPT) в нашей SaaS-платформе для создания RAG-ботов в Telegram.

Мы столкнулись с задачей, которая повлияет на надёжность и качество пользовательского опыта обеих систем — **валидация API-ключей**. Сейчас у нас дублируется логика валидации между платформой и оркестратором, что создаёт проблемы:

- ❌ **Code Duplication**: Одинаковая логика HTTP-запросов к провайдерам в двух местах
- ❌ **Inconsistency**: Разные способы обработки ошибок (401, 403, 429, 500)
- ❌ **Maintenance Overhead**: Изменения нужно синхронизировать вручную
- ❌ **Missing Features**: Автоопределение scope для GigaChat (PERS/B2B/CORP) реализовано только частично


### 🎯 Что мы предлагаем

Создать в Multi-LLM-Orchestrator **отдельный модуль `validators`**, который станет **единым источником правды** (DRY principle) для валидации API-ключей.

**Преимущества для всех**:

- ✅ Оркестратор: Новый публичный API для validation (полезен не только нам)
- ✅ Platform SaaS: Избавимся от дублирования, улучшим UX
- ✅ Сообщество: Open-source решение для валидации российских LLM API

***

## 📋 Техническая задача

### 1️⃣ Что нужно реализовать

Создать новый модуль `src/orchestrator/validators/` со следующими компонентами:

```
Multi-LLM-Orchestrator/
├── src/orchestrator/
│   ├── validators/                    # ← NEW MODULE
│   │   ├── __init__.py               # Public API exports
│   │   ├── base.py                   # BaseValidator (abstract class)
│   │   ├── errors.py                 # ValidationResult, ErrorCode
│   │   ├── gigachat.py               # GigaChatValidator
│   │   └── yandexgpt.py              # YandexGPTValidator
│   │
│   └── providers/                     # Existing (может использовать validators)
│       ├── gigachat.py
│       └── yandexgpt.py
│
├── tests/validators/                  # ← NEW TESTS
│   ├── test_base.py
│   ├── test_gigachat_validator.py
│   └── test_yandexgpt_validator.py
│
├── pyproject.toml                     # Version bump: 0.7.6 → 1.3.0
└── README.md                          # Add validators section
```


***

### 2️⃣ Архитектура: Разделение ответственности

#### Multi-LLM-Orchestrator (Core Validation Logic)

**Ответственность**:

- ✅ HTTP запросы к провайдерам (httpx)
- ✅ Парсинг ответов (status codes, error codes)
- ✅ Автоопределение scope для GigaChat (brute-force detection)
- ✅ Структурированные ошибки (ValidationResult dataclass)
- ✅ Retry логика (rate limiting, timeouts)
- ✅ Логирование (debug info)

**НЕ включает** (platform-specific):

- ❌ HTTPException (FastAPI-specific)
- ❌ UI-тексты на русском
- ❌ Audit logging
- ❌ Database операции


#### Platform SaaS (Integration Layer)

Мы на своей стороне будем:

- ✅ Импортировать validators из Multi-LLM-Orchestrator
- ✅ Маппить `ValidationResult` → `HTTPException` (FastAPI)
- ✅ Добавлять UI-тексты на русском
- ✅ Логировать в audit trail
- ✅ Проверять квоты (два уровня: platform key + tenant)

***

### 3️⃣ Детальные требования к API

#### A. `errors.py` — Типы ошибок

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ErrorCode(str, Enum):
    """Validation error codes."""
    # Success
    SUCCESS = "success"
    
    # Client errors (4xx)
    INVALID_API_KEY = "invalid_api_key"              # 401
    SCOPE_MISMATCH = "scope_mismatch"                # 400 (GigaChat code:7)
    PERMISSION_DENIED = "permission_denied"          # 403 (YandexGPT)
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"      # 429
    
    # Network errors (5xx)
    NETWORK_TIMEOUT = "network_timeout"              # 504
    PROVIDER_ERROR = "provider_error"                # 500
    
    # Internal errors
    VALIDATION_ERROR = "validation_error"            # Unexpected error

@dataclass
class ValidationResult:
    """Result of API key validation."""
    valid: bool
    error_code: ErrorCode
    provider: str                        # "gigachat", "yandexgpt"
    message: str                         # English message (for logs)
    details: Optional[dict] = None       # Extra info (e.g., detected_scope)
    http_status: Optional[int] = None    # Original HTTP status
    retry_after: Optional[int] = None    # Seconds to wait (rate limit)

@dataclass
class GigaChatValidationResult(ValidationResult):
    """GigaChat-specific result."""
    detected_scope: Optional[str] = None  # "GIGACHAT_API_PERS", "B2B", "CORP"

@dataclass
class YandexGPTValidationResult(ValidationResult):
    """YandexGPT-specific result."""
    request_id: Optional[str] = None      # For Yandex support
```


***

#### B. `base.py` — Базовый класс

```python
from abc import ABC, abstractmethod
import httpx
from .errors import ValidationResult

class BaseValidator(ABC):
    """Base class for API key validators."""
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
    
    @abstractmethod
    async def validate(self, api_key: str, **kwargs) -> ValidationResult:
        """Validate API key. Returns ValidationResult."""
        pass
    
    def _handle_timeout(self, provider: str) -> ValidationResult:
        """Handle httpx.TimeoutException."""
        return ValidationResult(
            valid=False,
            error_code=ErrorCode.NETWORK_TIMEOUT,
            provider=provider,
            message=f"{provider} API validation timeout",
            http_status=504,
        )
    
    def _handle_exception(self, provider: str, exc: Exception) -> ValidationResult:
        """Handle unexpected exceptions."""
        return ValidationResult(
            valid=False,
            error_code=ErrorCode.VALIDATION_ERROR,
            provider=provider,
            message=str(exc),
            http_status=500,
        )
```


***

#### C. `gigachat.py` — GigaChat валидатор

**Ключевые требования**:

1. **Endpoint**: `GET https://gigachat.devices.sberbank.ru/api/v1/models`
2. **Автоопределение scope** (если не передан):
    - Пробуем все 3 scope: `GIGACHAT_API_PERS`, `GIGACHAT_API_B2B`, `GIGACHAT_API_CORP`
    - При успехе (200) — возвращаем `detected_scope`
    - При 400 + code:7 (scope mismatch) — пробуем следующий
    - При 401 — прекращаем попытки (invalid key)
3. **Error handling**:
    - 200 → `SUCCESS` + `detected_scope`
    - 401 → `INVALID_API_KEY`
    - 400 + code:7 → `SCOPE_MISMATCH` (при известном scope)
    - 429 → `RATE_LIMIT_EXCEEDED` + `retry_after=30`
    - 500+ → `PROVIDER_ERROR`
    - Timeout → `NETWORK_TIMEOUT`

**Пример API**:

```python
validator = GigaChatValidator()

# Auto-detect scope
result = await validator.validate("YOUR_API_KEY")
if result.valid:
    print(f"Valid! Scope: {result.detected_scope}")

# With known scope (faster)
result = await validator.validate("YOUR_API_KEY", scope="GIGACHAT_API_B2B")
```


***

#### D. `yandexgpt.py` — YandexGPT валидатор

**Ключевые требования**:

1. **Endpoint**: `POST https://llm.api.cloud.yandex.net/foundationModels/v1/completion`
2. **Minimal token cost**: Используем `maxTokens: 1` для валидации
3. **folder_id validation**: Проверяем права доступа к folder_id
4. **Error handling**:
    - 200 → `SUCCESS`
    - 401 → `INVALID_API_KEY` (UNAUTHENTICATED)
    - 403 → `PERMISSION_DENIED` (нет доступа к folder_id)
    - 429 → `RATE_LIMIT_EXCEEDED` + `retry_after=10`
    - 500+ → `PROVIDER_ERROR` + extract `request_id` (из google.rpc.RequestInfo)
    - Timeout → `NETWORK_TIMEOUT`

**Пример API**:

```python
validator = YandexGPTValidator()
result = await validator.validate(
    api_key="AQVN...",
    folder_id="b1g..."
)

if result.valid:
    print("Valid!")
elif result.error_code == ErrorCode.PERMISSION_DENIED:
    print(f"No access to folder_id {result.details['folder_id']}")
    print(f"Yandex request_id: {result.request_id}")
```


***

#### E. `__init__.py` — Public API

```python
"""API key validators for LLM providers.

Example:
    from orchestrator.validators import GigaChatValidator, ErrorCode
    
    validator = GigaChatValidator()
    result = await validator.validate("YOUR_KEY")
    
    if result.valid:
        print(f"Valid! Scope: {result.detected_scope}")
    elif result.error_code == ErrorCode.RATE_LIMIT_EXCEEDED:
        print(f"Rate limited, retry after {result.retry_after}s")
    else:
        print(f"Error: {result.message}")
"""

from .base import BaseValidator
from .errors import (
    ErrorCode,
    ValidationResult,
    GigaChatValidationResult,
    YandexGPTValidationResult,
)
from .gigachat import GigaChatValidator
from .yandexgpt import YandexGPTValidator

__all__ = [
    "BaseValidator",
    "GigaChatValidator",
    "YandexGPTValidator",
    "ValidationResult",
    "GigaChatValidationResult",
    "YandexGPTValidationResult",
    "ErrorCode",
]
```


***

### 4️⃣ Тестирование

**Coverage: 90%+**

```python
# tests/validators/test_gigachat_validator.py

import pytest
from orchestrator.validators import GigaChatValidator, ErrorCode

@pytest.mark.asyncio
async def test_gigachat_valid_key(httpx_mock):
    """Test valid GigaChat key with scope detection."""
    httpx_mock.add_response(
        method="GET",
        url="https://gigachat.devices.sberbank.ru/api/v1/models",
        status_code=200,
        json={"data": [{"id": "GigaChat"}]},
    )
    
    validator = GigaChatValidator()
    result = await validator.validate("test_key")
    
    assert result.valid is True
    assert result.error_code == ErrorCode.SUCCESS
    assert result.detected_scope == "GIGACHAT_API_PERS"

@pytest.mark.asyncio
async def test_gigachat_invalid_key(httpx_mock):
    """Test invalid GigaChat key (401)."""
    httpx_mock.add_response(
        method="GET",
        url="https://gigachat.devices.sberbank.ru/api/v1/models",
        status_code=401,
    )
    
    validator = GigaChatValidator()
    result = await validator.validate("invalid_key")
    
    assert result.valid is False
    assert result.error_code == ErrorCode.INVALID_API_KEY
    assert result.http_status == 401

# И так далее для всех сценариев...
```

**Требуемые тесты**:

- ✅ Valid key (200)
- ✅ Invalid key (401)
- ✅ Scope mismatch (400 + code:7)
- ✅ Rate limit (429)
- ✅ Server error (500+)
- ✅ Timeout (httpx.TimeoutException)
- ✅ Scope auto-detection (3 попытки)
- ✅ YandexGPT permission denied (403)

***

### 5️⃣ Документация

#### A. Обновить `README.md`

Добавить новый раздел:

```markdown
## API Key Validation

Multi-LLM-Orchestrator provides validators for checking API keys before usage:

### Quick Start

```python
from orchestrator.validators import GigaChatValidator, YandexGPTValidator

# GigaChat (with auto-detection)
validator = GigaChatValidator()
result = await validator.validate("YOUR_API_KEY")

if result.valid:
    print(f"✅ Valid! Detected scope: {result.detected_scope}")
else:
    print(f"❌ Error: {result.error_code.value}")
```


### Supported Providers

- **GigaChat**: Auto-detects scope (PERS/B2B/CORP)
- **YandexGPT**: Validates folder_id permissions
- **OpenAI**: _(Coming soon)_
- **Anthropic**: _(Coming soon)_


### Error Codes

- `SUCCESS`: Key is valid
- `INVALID_API_KEY`: 401 Unauthorized
- `SCOPE_MISMATCH`: GigaChat scope conflict
- `PERMISSION_DENIED`: YandexGPT folder_id access denied
- `RATE_LIMIT_EXCEEDED`: 429 Too Many Requests
- `NETWORK_TIMEOUT`: Request timeout (10s)
- `PROVIDER_ERROR`: 500+ Server error

```

***

### 6️⃣ Релиз (Version 1.3.0)

#### A. `pyproject.toml`

```toml
[tool.poetry]
name = "multi-llm-orchestrator"
version = "1.3.0"  # ← Bump from 0.7.6
description = "Unified interface for Russian LLMs with intelligent routing and API key validation"
```


#### B. Changelog

Создать `CHANGELOG.md` (если ещё нет):

```markdown
# Changelog

## [1.3.0] - 2026-01-XX

### Added
- **API Key Validators** module (`orchestrator.validators`)
  - `GigaChatValidator` with automatic scope detection
  - `YandexGPTValidator` with folder_id permission check
  - Structured error types (`ValidationResult`, `ErrorCode`)
  - Comprehensive test coverage (90%+)

### Changed
- Bumped version to 1.3.0 (minor feature release)

### Documentation
- Added "API Key Validation" section to README
- Added docstrings to all validators
```


***

## 🚀 Следующие шаги

### Для вас (Orchestrator Team)

1. **Week 20** (5 дней):
    - Day 1-2: Core infrastructure (`errors.py`, `base.py`)
    - Day 3: GigaChat validator + tests
    - Day 4: YandexGPT validator + tests
    - Day 5: Integration, docs, release v1.3.0
2. **Release**:
    - Git tag: `v1.3.0`
    - Publish to PyPI: `poetry publish`
    - GitHub Release notes

### Для нас (Platform Team)

3. **Week 21** (4 дня):
    - Обновим `requirements.txt`: `multi-llm-orchestrator==1.3.0`
    - Рефакторинг `platform_saas/services/key_validator.py` (использовать ваши валидаторы)
    - Добавим маппинг `ValidationResult` → FastAPI `HTTPException`
    - Тесты + deploy
4. **Week 22** (3 дня):
    - Обновим UI для отображения новых ошибок
    - E2E тесты
    - Production deploy

***

## 📊 Метрики успеха

| Метрика | Target | Measurement |
| :-- | :-- | :-- |
| **Test Coverage** | 90%+ | `pytest --cov=orchestrator/validators` |
| **Response Time** | <500ms | Benchmark (httpx mocks) |
| **Error Rate** | 0% | All tests pass |
| **Deploy Time** | <10 min | CI/CD pipeline |


***

## 🤝 Вопросы и обратная связь

**Если что-то неясно**:

- Telegram: @MikhailMalorod (Mikhail, Platform SaaS founder)
- GitHub Issues: https://github.com/MikhailMalorod/platform/issues
- Email: MikhailMalorod@users.noreply.github.com

**Мы готовы помочь**:

- Code review (если нужно)
- Тестирование (у нас production keys для GigaChat/YandexGPT)
- Документация (примеры использования)

***

## 📎 Приложения

### A. Полный код (reference)

Мы подготовили детальный roadmap с полным кодом всех модулей:

- [ERROR-VALIDATION-ROADMAP.md](link) — 45KB, 700+ строк кода


### B. Error Matrix

Таблица всех error codes с HTTP status, UI-текстами, действиями:

- [ERROR-MATRIX.md](link) — референс для UI-интеграции


### C. Platform SaaS docs

Для контекста:

- [strategy_hybrid_model.md](link) — бизнес-модель (roadmap Week 1-11)
- [semantic_core_ru_v1.1.md](link) — UI-тексты на русском (мы добавим их на своей стороне)

***

## ✅ TL;DR

**Что просим**:

1. Создать модуль `src/orchestrator/validators/` с GigaChatValidator + YandexGPTValidator
2. Публичный API: `ValidationResult` (dataclass) + `ErrorCode` (enum)
3. Coverage 90%+, docs в README, релиз v1.3.0 на PyPI
4. Timeline: 5 дней (Week 20)

**Что даём взамен**:

- ✅ Open-source вклад (ваша библиотека станет ещё полезнее)
- ✅ Production testing (у нас реальные пользователи, найдём баги быстрее)
- ✅ Community contribution (другие проекты смогут использовать validators)

**Почему это важно**:

- DRY principle (единый источник правды для валидации)
- Лучший UX (пользователи Platform SaaS получат понятные сообщения об ошибках)
- Ecosystem synergy (взаимная выгода двух проектов)

***

**Спасибо за внимание! 🙏**

Готовы начать, как только получим подтверждение.

**С уважением,**
**Platform SaaS Team**
https://ubpl.ru | https://github.com/MikhailMalorod/platform

***

<span style="display:none">[^1][^10][^11][^12][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: ERROR-VALIDATION-ROADMAP.md

[^2]: semantic_core_ru_v1.1.md

[^3]: strategy_hybrid_model.md

[^4]: UI_SCREENS_STRATEGIC_MAP_v1.0.0.md

[^5]: DOCUMENTATION_INDEX.md

[^6]: AUTH_ARCHITECTURE_TOKENS.md

[^7]: AUTH_HYBRID_MODEL.md

[^8]: WEEK9_COMPLETE_UI_DESIGN_SYSTEM.md

[^9]: prompt3.md

[^10]: prompt2.md

[^11]: prompt1.md

[^12]: ERROR-MATRIX.md

