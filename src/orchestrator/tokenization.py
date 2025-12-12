"""Token counting utilities for LLM requests.

This module provides centralized token counting with tiktoken integration
and fallback to word-based estimation when tiktoken is unavailable or fails.

Example:
    ```python
    from orchestrator.tokenization import count_tokens

    # Exact count via tiktoken
    tokens = count_tokens("Hello, world!")
    print(tokens)  # 4

    # Fallback for unsupported models
    tokens = count_tokens("Привет, мир!", model="unsupported")
    print(tokens)  # ~3 (estimated via word count * 1.3)
    ```
"""

import logging

logger = logging.getLogger("orchestrator.tokenization")


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens using tiktoken with fallback to word-based estimation.

    This function attempts to count tokens using tiktoken's encoding for
    the specified model. If tiktoken fails (e.g., unsupported model,
    unsupported characters, or library not installed), it falls back to
    word-based estimation (word_count * 1.3).

    Args:
        text: Input text to tokenize
        model: Model name for tiktoken encoding (default: gpt-3.5-turbo).
              Common models: gpt-3.5-turbo, gpt-4, text-davinci-003

    Returns:
        Token count as integer. Exact count via tiktoken or estimated
        via word count * 1.3 if tiktoken fails.

    Example:
        ```python
        # Exact tokenization
        count = count_tokens("Hello, world!")
        # Returns: 4 (exact via tiktoken)

        # With custom model
        count = count_tokens("Hello!", model="gpt-4")
        # Returns: 3 (exact via tiktoken for GPT-4)

        # Fallback estimation
        count = count_tokens("Привет, мир!", model="unknown")
        # Returns: 3 (estimated: 2 words * 1.3 ≈ 3 tokens)
        ```

    Note:
        The fallback estimation (word_count * 1.3) is approximate.
        For English text, 1 token ≈ 0.75 words, so 1 word ≈ 1.3 tokens.
        Accuracy varies for non-English languages.
    """
    try:
        import tiktoken

        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        # Fallback to word-based estimation
        logger.warning(
            f"tiktoken failed for model '{model}': {e}. "
            f"Using fallback estimation (word_count * 1.3)"
        )
        return estimate_tokens_fallback(text)


def estimate_tokens_fallback(text: str) -> int:
    """Fallback token estimation using word count * 1.3.

    This function provides a rough approximation of token count when
    tiktoken is unavailable or fails. It uses a simple heuristic:
    count words and multiply by 1.3.

    Args:
        text: Input text to estimate tokens for

    Returns:
        Estimated token count (word_count * 1.3, rounded to int)

    Example:
        ```python
        # Simple estimation
        tokens = estimate_tokens_fallback("Hello world")
        # Returns: 2 (2 words * 1.3 = 2.6 ≈ 2)

        # Empty string
        tokens = estimate_tokens_fallback("")
        # Returns: 0

        # Multiple words
        tokens = estimate_tokens_fallback("The quick brown fox")
        # Returns: 5 (4 words * 1.3 = 5.2 ≈ 5)
        ```

    Note:
        This is a rough approximation based on English text characteristics.
        For English: 1 token ≈ 0.75 words, therefore 1 word ≈ 1.3 tokens.
        Accuracy may vary significantly for:
        - Non-English languages (different word/token ratios)
        - Technical text with many special characters
        - Code snippets
    """
    word_count = len(text.split())
    return int(word_count * 1.3)

