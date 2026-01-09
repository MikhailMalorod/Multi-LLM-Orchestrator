"""
Platform SaaS Integration Example

Demonstrates how to integrate GigaChat auto-detection with progress tracking
and error mapping for Platform SaaS applications.

Usage:
    python examples/platform_saas_integration.py
"""

import asyncio
from orchestrator.validators import GigaChatValidator, ErrorCode


def map_to_russian(error_code: ErrorCode) -> str:
    """Map ErrorCode to Russian user-friendly message."""
    mapping = {
        ErrorCode.SUCCESS: "Ключ валиден",
        ErrorCode.INVALID_API_KEY: "Неверный или истекший ключ API",
        ErrorCode.SCOPE_MISMATCH: "Не удалось определить тип ключа. Проверьте ключ в GigaChat Studio.",
        ErrorCode.RATE_LIMIT_EXCEEDED: "Превышен лимит запросов. Попробуйте позже.",
        ErrorCode.NETWORK_TIMEOUT: "Таймаут соединения. Проверьте интернет.",
        ErrorCode.PROVIDER_ERROR: "Ошибка сервера GigaChat. Попробуйте позже.",
        ErrorCode.VALIDATION_ERROR: "Неожиданная ошибка при валидации.",
    }
    return mapping.get(error_code, "Неизвестная ошибка")


async def validate_key_with_ui_feedback(api_key: str):
    """Validate GigaChat key with UI progress tracking."""
    validator = GigaChatValidator(verify_ssl=False)
    
    # Track progress for UI
    progress_messages = []
    
    def on_progress(scope: str, current: int, total: int):
        message = f"Проверяем {scope} ({current}/{total})..."
        progress_messages.append(message)
        print(f"  {message}")  # In real app, update UI here
    
    # Validate with auto-detection
    result = await validator.validate(api_key, on_scope_attempt=on_progress)
    
    # Map to Russian for UI
    russian_message = map_to_russian(result.error_code)
    
    # Return structured response for Platform SaaS
    return {
        "valid": result.valid,
        "message": russian_message,
        "error_code": result.error_code.value,
        "details": {
            "detected_scope": result.details.get("detected_scope"),
            "auto_detection_used": result.details.get("auto_detection_used", False),
            "attempts_count": result.details.get("attempts_count"),
            "total_time_ms": result.details.get("total_time_ms"),
            "progress_messages": progress_messages,
        },
        "retry_after": result.retry_after,
    }


async def main():
    print("=" * 60)
    print("Platform SaaS Integration Example")
    print("=" * 60)
    print("\nThis example demonstrates:")
    print("  1. Auto-detection with progress tracking")
    print("  2. Error mapping to Russian messages")
    print("  3. Structured response for Platform SaaS")
    print("\n" + "=" * 60)
    
    # Example: Replace with actual API key
    api_key = "YOUR_GIGACHAT_KEY"  # <<< REPLACE WITH YOUR KEY
    
    if api_key == "YOUR_GIGACHAT_KEY":
        print("\n⚠️  Please replace 'YOUR_GIGACHAT_KEY' with your actual API key")
        print("\nExample usage:")
        print("  result = await validate_key_with_ui_feedback('your_key_here')")
        print("  print(result)")
        return
    
    print(f"\nValidating key: {api_key[:10]}...")
    result = await validate_key_with_ui_feedback(api_key)
    
    print("\n" + "=" * 60)
    print("Validation Result:")
    print("=" * 60)
    print(f"Valid: {result['valid']}")
    print(f"Message: {result['message']}")
    print(f"Error Code: {result['error_code']}")
    print(f"\nDetails:")
    print(f"  Detected Scope: {result['details'].get('detected_scope', 'N/A')}")
    print(f"  Auto-detection Used: {result['details'].get('auto_detection_used')}")
    print(f"  Attempts: {result['details'].get('attempts_count', 'N/A')}")
    print(f"  Time: {result['details'].get('total_time_ms', 'N/A')}ms")
    print(f"  Progress Messages: {len(result['details'].get('progress_messages', []))}")
    
    if result.get("retry_after"):
        print(f"\nRetry After: {result['retry_after']}s")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
