# План внедрения OllamaProvider

Общий прогресс: 33%

## Задачи

- ✅ Шаг 1: Подготовить каркас `OllamaProvider`
  - ✅ Создать `src/orchestrator/providers/ollama.py`, наследовать `BaseProvider`, валидировать `model`, применять default `base_url`.
  - ✅ Реализовать `generate()` с маппингом `GenerationParams` → `options` (`temperature`, `num_predict`, `top_p`), игнорируя `stop`, и обработкой 404/500/connection через профильтрованные исключения.
  - ✅ Добавить `health_check()` с GET `{base_url}/api/tags`, фиксированный 5s timeout, и экспорт в `providers/__init__.py`.

- ⬜️ Шаг 2: Покрыть функциональность тестами
  - ⬜️ Создать `tests/test_ollama_provider.py` (~18 кейсов) с `pytest-httpx`, проверяющими конфигурацию, маппинг параметров, успешную генерацию, ошибки 404/500/connection, таймауты, health-check pass/fail.

- ⬜️ Шаг 3: Обновить документацию
  - ⬜️ Добавить `docs/providers/ollama.md` по аналогии с существующими провайдерами (overview, конфигурация, параметры, health-check, ошибки).
  - ⬜️ Расширить `README.md`: перечислить Ollama в поддерживаемых провайдерах, добавить секцию «Local Models with Ollama» и пример использования Router.


