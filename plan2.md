# План реализации Basic Router

**Общий прогресс: 100%**

## Задачи

### ✅ Шаг 1: Обновить импорты и зависимости
- [x] Добавить импорт `logging`
- [x] Добавить импорт `random`
- [x] Обновить импорты из `typing`: `List`, `Optional`
- [x] Добавить импорты из `providers.base`: `BaseProvider`, `GenerationParams`, `ProviderError`
- [x] Удалить неиспользуемые импорты (`Dict`, `Any`)

### ✅ Шаг 2: Переименовать класс и обновить `__init__`
- [x] Переименовать `LLMRouter` → `Router`
- [x] Изменить сигнатуру `__init__`: `__init__(strategy: str = "round-robin")`
- [x] Удалить параметр `config` и атрибут `self.config`
- [x] Добавить валидацию стратегии (выбрасывать `ValueError` если неверная)
- [x] Инициализировать `self.strategy: str`
- [x] Инициализировать `self.providers: List[BaseProvider] = []`
- [x] Инициализировать `self._current_index: int = 0`
- [x] Инициализировать `self.logger = logging.getLogger("orchestrator.router")`
- [x] Добавить логирование инициализации: `"Router initialized with strategy: {strategy}"`
- [x] Добавить Google-style docstring для `__init__`

### ✅ Шаг 3: Реализовать метод `add_provider`
- [x] Изменить сигнатуру: `add_provider(provider: BaseProvider) -> None`
- [x] Удалить параметр `name`
- [x] Добавить провайдер в `self.providers` (append в список)
- [x] Добавить логирование: `"Added provider: {provider.config.name}"`
- [x] Добавить Google-style docstring для `add_provider`
- [x] Удалить старую реализацию с `Dict[str, Any]`

### ✅ Шаг 4: Реализовать логику выбора провайдера по стратегии
- [x] Создать приватный метод `_select_provider()` или встроить логику в `route()`
- [x] Реализовать стратегию `round-robin`:
  - [x] Использовать `self.providers[self._current_index % len(self.providers)]`
  - [x] Увеличить `self._current_index += 1`
  - [x] Залогировать выбор: `"Selected provider: {name} (strategy: round-robin)"`
- [x] Реализовать стратегию `random`:
  - [x] Использовать `random.choice(self.providers)`
  - [x] Залогировать выбор: `"Selected provider: {name} (strategy: random)"`
- [x] Реализовать стратегию `first-available`:
  - [x] Цикл по `self.providers` с проверкой `await provider.health_check()`
  - [x] Вернуть первого здорового
  - [x] Если все unhealthy → `selected = None` (будет обработано в fallback)
  - [x] Залогировать выбор: `"Selected provider: {name} (strategy: first-available)"` или `"No healthy providers found, will try all"`

### ✅ Шаг 5: Реализовать метод `route` с fallback механизмом
- [x] Изменить сигнатуру: `async def route(prompt: str, params: Optional[GenerationParams] = None) -> str`
- [x] Удалить старый метод `chat()`
- [x] Добавить проверку пустого списка провайдеров → `ProviderError("No providers registered")`
- [x] Выбрать провайдер по стратегии (использовать логику из Шага 4)
- [x] Найти индекс выбранного провайдера: `selected_index = self.providers.index(selected_provider)`
- [x] Реализовать fallback цикл:
  - [x] `for i in range(len(self.providers)):`
  - [x] `index = (selected_index + i) % len(self.providers)`
  - [x] `provider = self.providers[index]`
  - [x] `try: result = await provider.generate(prompt, params)`
  - [x] `except Exception as e: логирование + сохранение last_error`
  - [x] При успехе: логирование и `return result`
- [x] Обработать случай, когда все провайдеры упали:
  - [x] Залогировать ошибку: `"All providers failed"`
  - [x] Выбросить последнее исключение (`raise last_error`)
- [x] Добавить Google-style docstring с секцией `Raises`

### ✅ Шаг 6: Добавить логирование во все критические точки
- [x] Логирование в `__init__`: `INFO` уровень
- [x] Логирование в `add_provider`: `INFO` уровень
- [x] Логирование выбора провайдера: `INFO` уровень
- [x] Логирование fallback попыток: `WARNING` уровень
- [x] Логирование успешного выполнения: `INFO` уровень
- [x] Логирование финальной ошибки: `ERROR` уровень

### ✅ Шаг 7: Обновить `__init__.py` для экспорта
- [x] Изменить импорт: `from .router import Router`
- [x] Добавить alias: `LLMRouter = Router` (обратная совместимость)
- [x] Обновить `__all__`: добавить `"Router"` и `"LLMRouter"`

### ✅ Шаг 8: Финальная проверка и валидация
- [x] Проверить все docstrings (Google-style)
- [x] Проверить type hints для всех публичных методов
- [x] Убедиться, что все исключения корректно обрабатываются
- [x] Проверить, что логирование работает на всех уровнях
- [x] Убедиться, что код соответствует стилю из `base.py` и `mock.py`
- [x] Удалить весь старый код (старая реализация `LLMRouter`)

---

## Технические детали

### Исключения для обработки:
- `ProviderError` (базовое)
- `TimeoutError`
- `RateLimitError`
- `AuthenticationError`
- `InvalidRequestError`
- Любые другие исключения от провайдеров

### Логирование:
- Логгер: `logging.getLogger("orchestrator.router")`
- Уровни: `INFO`, `WARNING`, `ERROR`

### Fallback логика:
- Пробовать всех провайдеров по порядку, начиная с выбранного
- Формула индекса: `(selected_index + i) % len(providers)`
- Выбрасывать последнее исключение, если все упали

### Стратегии:
- `round-robin`: циклический выбор с сохранением состояния
- `random`: случайный выбор из всех провайдеров
- `first-available`: первый здоровый провайдер (или все, если все unhealthy)

