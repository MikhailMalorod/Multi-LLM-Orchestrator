# План реализации: Routing Demo

**Общий прогресс:** 100%

---

## Задачи

### ✅ Шаг 1: Подготовка структуры файла
- [x] Создать файл `examples/routing_demo.py`
- [x] Добавить shebang и docstring с описанием демо
- [x] Настроить импорты:
  - [x] `asyncio`, `logging`, `time`, `sys`, `Path`
  - [x] Rich компоненты: `Console`, `Table`, `Panel`
  - [x] Router и провайдеры через `sys.path.insert(0, ...)`
- [x] Настроить логирование: `logging.basicConfig(level=logging.WARNING)`
- [x] Определить константу `PROMPTS` (5 промптов)

### ✅ Шаг 2: Вспомогательные функции для Rich вывода
- [x] Функция `create_providers_table(providers)`:
  - [x] Создает таблицу с колонками: Name, Mode, Health Check
  - [x] Вызывает `health_check()` для каждого провайдера (async)
  - [x] Добавляет эмодзи статусов (✅/❌)
- [x] Функция `create_results_table()`:
  - [x] Создает таблицу с колонками: Request, Provider, Status, Time
  - [x] Возвращает таблицу для заполнения

### ✅ Шаг 3: Сценарий 1 - Round-Robin (нормальная работа)
- [x] Создать функцию `demo_round_robin(console: Console)`
- [x] Инициализировать Router с `strategy="round-robin"`
- [x] Добавить 3 провайдера (`mock-normal`)
- [x] Вывести панель с заголовком сценария
- [x] Вывести таблицу провайдеров
- [x] Выполнить 5 запросов:
  - [x] Измерять время каждого `route()` вызова
  - [x] Записывать результаты в таблицу
- [x] Вывести таблицу результатов
- [x] Добавить комментарии к каждому шагу

### ✅ Шаг 4: Сценарий 2 - Random (нормальная работа)
- [x] Создать функцию `demo_random(console: Console)`
- [x] Инициализировать Router с `strategy="random"`
- [x] Добавить 3 провайдера (`mock-normal`)
- [x] Вывести панель с заголовком
- [x] Вывести таблицу провайдеров
- [x] Выполнить 5 запросов с измерением времени
- [x] Вывести таблицу результатов
- [x] Добавить комментарии

### ✅ Шаг 5: Сценарий 3 - First-Available (нормальная работа)
- [x] Создать функцию `demo_first_available(console: Console)`
- [x] Инициализировать Router с `strategy="first-available"`
- [x] Добавить провайдеры: `mock-unhealthy`, `mock-normal`, `mock-normal`
- [x] Вывести панель с заголовком
- [x] Вывести таблицу провайдеров (с health check)
- [x] Выполнить 3 запроса с измерением времени
- [x] Вывести информационное сообщение о выборе провайдера
- [x] Вывести таблицу результатов
- [x] Добавить комментарии

### ✅ Шаг 6: Сценарий 4 - Fallback при Timeout
- [x] Создать функцию `demo_fallback_timeout(console: Console)`
- [x] Инициализировать Router с `strategy="round-robin"`
- [x] Добавить провайдеры: `mock-timeout`, `mock-normal`, `mock-normal`
- [x] Вывести панель с заголовком
- [x] Вывести таблицу провайдеров
- [x] Выполнить 1 запрос:
  - [x] Измерить время
  - [x] Записать результат (⚠️ Fallback если был)
- [x] Вывести таблицу результатов с указанием fallback
- [x] Добавить комментарии

### ✅ Шаг 7: Сценарий 5 - Fallback с Unhealthy + Timeout
- [x] Создать функцию `demo_fallback_unhealthy(console: Console)`
- [x] Инициализировать Router с `strategy="first-available"`
- [x] Добавить провайдеры: `mock-unhealthy`, `mock-unhealthy`, `mock-timeout`
- [x] Вывести панель с заголовком
- [x] Вывести таблицу провайдеров (с health check)
- [x] Выполнить 1 запрос:
  - [x] Измерить время
  - [x] Записать результат с указанием fallback
- [x] Вывести информационное сообщение о процессе fallback
- [x] Вывести таблицу результатов
- [x] Добавить комментарии

### ✅ Шаг 8: Сценарий 6 - Все провайдеры упали
- [x] Создать функцию `demo_all_failed(console: Console)`
- [x] Инициализировать Router с `strategy="round-robin"`
- [x] Добавить 3 провайдера (`mock-timeout`)
- [x] Вывести панель с заголовком
- [x] Вывести таблицу провайдеров
- [x] Выполнить 1 запрос в `try/except`:
  - [x] Поймать исключение
  - [x] Вывести красную панель с ошибкой через `Panel`
  - [x] Показать тип ошибки и сообщение
- [x] Добавить комментарии

### ✅ Шаг 9: Главная функция и запуск
- [x] Создать функцию `async def main()`
- [x] Инициализировать `Console()`
- [x] Вывести главную панель с заголовком демо
- [x] Вызвать все 6 сценариев последовательно:
  - [x] `demo_round_robin(console)`
  - [x] `demo_random(console)`
  - [x] `demo_first_available(console)`
  - [x] `demo_fallback_timeout(console)`
  - [x] `demo_fallback_unhealthy(console)`
  - [x] `demo_all_failed(console)`
- [x] Вывести итоговую панель с завершением демо
- [x] Добавить `if __name__ == "__main__":` с `asyncio.run(main())`

### ✅ Шаг 10: Тестирование и проверка
- [x] Запустить скрипт: `python examples/routing_demo.py`
- [x] Проверить корректность вывода всех таблиц
- [x] Проверить цветовую схему (green/red/yellow/blue)
- [x] Проверить эмодзи статусов (✅/❌/⚠️/ℹ️)
- [x] Проверить измерение времени (формат: `123ms`)
- [x] Проверить обработку ошибок в сценарии 6
- [x] Убедиться, что логи Router не выводятся (WARNING уровень подавлен)
- [x] Проверить, что все 6 сценариев выполняются последовательно

---

## Технические детали

### Цветовая схема Rich
- **Green (✅)**: Success
- **Red (❌)**: Error/Failed
- **Yellow (⚠️)**: Warning/Fallback
- **Blue (ℹ️)**: Info

### Формат времени
- Миллисекунды: `int((end - start) * 1000)`
- Отображение: `"123ms"`

### Структура импортов
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.orchestrator import Router
from src.orchestrator.providers.base import ProviderConfig
from src.orchestrator.providers.mock import MockProvider
```

