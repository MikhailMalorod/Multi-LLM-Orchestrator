"""Tests for BaseValidator."""

import pytest

from orchestrator.validators.base import BaseValidator
from orchestrator.validators.errors import ErrorCode


class ConcreteValidator(BaseValidator):
    """Concrete validator for testing."""

    async def validate(self, api_key: str, **kwargs):
        from orchestrator.validators.errors import ErrorCode, ValidationResult
        return ValidationResult(
            valid=True,
            error_code=ErrorCode.SUCCESS,
            provider="test",
            message="Test",
        )


class TestBaseValidator:
    """Test BaseValidator functionality."""

    def test_init(self):
        """Test validator initialization."""
        validator = ConcreteValidator(timeout=5.0)
        assert validator.timeout == 5.0

    def test_default_timeout(self):
        """Test default timeout."""
        validator = ConcreteValidator()
        assert validator.timeout == 10.0

    def test_handle_timeout(self):
        """Test _handle_timeout helper."""
        validator = ConcreteValidator()
        result = validator._handle_timeout("test_provider")

        assert result.valid is False
        assert result.error_code == ErrorCode.NETWORK_TIMEOUT
        assert result.provider == "test_provider"
        assert result.http_status == 504

    def test_handle_exception(self):
        """Test _handle_exception helper."""
        validator = ConcreteValidator()
        exc = ValueError("Test error")
        result = validator._handle_exception("test_provider", exc)

        assert result.valid is False
        assert result.error_code == ErrorCode.VALIDATION_ERROR
        assert result.provider == "test_provider"
        assert result.message == "Test error"
        assert result.http_status == 500

    @pytest.mark.asyncio
    async def test_validate_abstract(self):
        """Test that validate() is abstract."""
        validator = ConcreteValidator()
        result = await validator.validate("test_key")
        assert result.valid is True
