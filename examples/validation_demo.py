"""
Demo: API Key Validation

Demonstrates how to validate GigaChat and YandexGPT API keys
before using them in production.

Usage:
    python examples/validation_demo.py
"""

import asyncio
from orchestrator.validators import (
    GigaChatValidator,
    YandexGPTValidator,
    ErrorCode,
)


async def main():
    print("=" * 60)
    print("API Key Validation Demo")
    print("=" * 60)
    
    # GigaChat validation
    print("\n### GigaChat Validation ###")
    print("Replace 'YOUR_GIGACHAT_KEY' with your actual API key")
    
    gc_validator = GigaChatValidator(verify_ssl=False)  # For Russian CA
    
    # Example: Valid key
    # result = await gc_validator.validate(
    #     api_key="YOUR_GIGACHAT_KEY",
    #     scope="GIGACHAT_API_PERS"
    # )
    # 
    # if result.valid:
    #     print(f"✅ Valid! Scope: {result.details.get('scope')}")
    # else:
    #     print(f"❌ Error: {result.error_code.value}")
    #     print(f"   Message: {result.message}")
    #     if result.retry_after:
    #         print(f"   Retry after: {result.retry_after}s")
    
    print("(Uncomment code above and add your API key to test)")
    
    # YandexGPT validation
    print("\n### YandexGPT Validation ###")
    print("Replace 'YOUR_IAM_TOKEN' and 'YOUR_FOLDER_ID' with actual values")
    
    yc_validator = YandexGPTValidator()
    
    # Example: Valid key
    # result = await yc_validator.validate(
    #     api_key="YOUR_IAM_TOKEN",
    #     folder_id="YOUR_FOLDER_ID"
    # )
    # 
    # if result.valid:
    #     print("✅ Valid!")
    # elif result.error_code == ErrorCode.PERMISSION_DENIED:
    #     print(f"❌ No access to folder_id: {result.details.get('folder_id')}")
    #     if result.details.get('request_id'):
    #         print(f"   Request ID: {result.details['request_id']}")
    # else:
    #     print(f"❌ Error: {result.error_code.value}")
    #     print(f"   Message: {result.message}")
    
    print("(Uncomment code above and add your credentials to test)")
    
    print("\n" + "=" * 60)
    print("For more examples, see the validators documentation.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
