"""Tests for validation error types."""


from orchestrator.validators.errors import ErrorCode, ValidationResult


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_error_code_values(self):
        """Test that all error codes have correct string values."""
        assert ErrorCode.SUCCESS == "success"
        assert ErrorCode.INVALID_API_KEY == "invalid_api_key"
        assert ErrorCode.SCOPE_MISMATCH == "scope_mismatch"
        assert ErrorCode.PERMISSION_DENIED == "permission_denied"
        assert ErrorCode.RATE_LIMIT_EXCEEDED == "rate_limit_exceeded"
        assert ErrorCode.NETWORK_TIMEOUT == "network_timeout"
        assert ErrorCode.PROVIDER_ERROR == "provider_error"
        assert ErrorCode.VALIDATION_ERROR == "validation_error"


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_success_result(self):
        """Test success validation result."""
        result = ValidationResult(
            valid=True,
            error_code=ErrorCode.SUCCESS,
            provider="gigachat",
            message="API key is valid",
            details={"scope": "GIGACHAT_API_PERS"},
            http_status=200,
        )

        assert result.valid is True
        assert result.error_code == ErrorCode.SUCCESS
        assert result.provider == "gigachat"
        assert result.message == "API key is valid"
        assert result.details == {"scope": "GIGACHAT_API_PERS"}
        assert result.http_status == 200
        assert result.retry_after is None

    def test_error_result(self):
        """Test error validation result."""
        result = ValidationResult(
            valid=False,
            error_code=ErrorCode.SCOPE_MISMATCH,
            provider="gigachat",
            message="Scope mismatch",
            details={"provided_scope": "GIGACHAT_API_PERS"},
            http_status=400,
        )

        assert result.valid is False
        assert result.error_code == ErrorCode.SCOPE_MISMATCH
        assert result.http_status == 400

    def test_rate_limit_result(self):
        """Test rate limit result with retry_after."""
        result = ValidationResult(
            valid=False,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            provider="gigachat",
            message="Rate limit exceeded",
            http_status=429,
            retry_after=30,
        )

        assert result.retry_after == 30
