# Contributing to Multi-LLM Orchestrator

Thank you for your interest in contributing to Multi-LLM Orchestrator! This guide will help you get started.

## Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/MikhailMalorod/Multi-LLM-Orchestrator.git
   cd Multi-LLM-Orchestrator
   ```

2. Install dependencies:

   ```bash
   poetry install
   ```

3. Run tests:

   ```bash
   pytest tests/ -v
   ```

## Code Style

All code must pass the following checks:

- **Type checking:** `mypy src/ --strict` (0 errors)
- **Linting:** `ruff check src/ examples/` (0 warnings)
- **Test coverage:** `pytest --cov=src --cov-report=term` (>= 87%)
- **Formatting:** Follow existing code style (Google-style docstrings)

Run before committing:

```bash
mypy src/ --strict
ruff check src/ examples/
pytest tests/ --cov=src
```

## Adding New Provider

See [Creating Custom Provider](docs/providers/custom_provider.md) for a step-by-step guide.

**Requirements:**

- Inherit from `BaseProvider`
- Implement `generate()` and `health_check()` methods
- Add comprehensive tests (unit + integration)
- Document in `docs/providers/your_provider.md`

## Running Tests

```bash
# Unit tests
pytest tests/ -v

# Real tests (requires API keys in .env)
cd examples/real_tests/
python test_gigachat.py
python test_router.py
```

## Pull Request Process

1. Create a feature branch

2. Make changes with tests

3. Ensure all checks pass

4. Submit PR with clear description

5. Address review feedback

Thank you for contributing! 🚀

