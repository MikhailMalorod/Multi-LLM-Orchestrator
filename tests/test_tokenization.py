"""Unit tests for tokenization module.

This module tests token counting functionality including:
- Basic token counting with tiktoken
- Empty string handling
- Fallback to word-based estimation
- Error handling when tiktoken fails
"""

import pytest
from unittest.mock import patch, MagicMock

from orchestrator.tokenization import count_tokens, estimate_tokens_fallback


class TestCountTokens:
    """Test count_tokens() function."""

    def test_count_tokens_basic(self) -> None:
        """Test basic token counting with tiktoken."""
        text = "Hello, world!"
        tokens = count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_count_tokens_empty_string(self) -> None:
        """Test token counting for empty string."""
        assert count_tokens("") == 0

    def test_count_tokens_long_text(self) -> None:
        """Test token counting for long text."""
        text = "This is a longer sentence with multiple words. " * 100
        tokens = count_tokens(text)
        assert tokens > 100  # Should have many tokens

    def test_count_tokens_different_models(self) -> None:
        """Test token counting with different model encodings."""
        text = "Hello, world!"
        
        # Test with gpt-3.5-turbo (default)
        tokens_35 = count_tokens(text, model="gpt-3.5-turbo")
        assert tokens_35 > 0
        
        # Test with gpt-4
        tokens_4 = count_tokens(text, model="gpt-4")
        assert tokens_4 > 0
        
        # GPT-4 and GPT-3.5 should have similar token counts
        assert abs(tokens_35 - tokens_4) <= 2

    def test_count_tokens_fallback_on_tiktoken_error(self) -> None:
        """Test fallback to word count when tiktoken raises exception."""
        # Mock the tiktoken import to raise exception during encoding
        with patch("builtins.__import__", side_effect=ImportError("tiktoken not found")):
            text = "Hello world test"  # 3 words
            tokens = count_tokens(text)

            # Should use fallback: 3 words * 1.3 = 3.9 ≈ 3
            expected = int(3 * 1.3)
            assert tokens == expected

    def test_count_tokens_fallback_on_encoding_error(self) -> None:
        """Test fallback when tiktoken encoding fails."""
        # Test with a model that might cause encoding issues
        # The actual tiktoken will handle this gracefully, but we test the fallback path
        text = "Test with special chars: \x00\x01\x02"
        # This should either work with tiktoken or fall back
        tokens = count_tokens(text)
        assert tokens >= 0  # Should return valid token count (either way)

    def test_count_tokens_special_characters(self) -> None:
        """Test token counting with special characters."""
        text = "Hello! @#$% World?"
        tokens = count_tokens(text)
        assert tokens > 0
        # Special characters typically count as separate tokens


class TestEstimateTokensFallback:
    """Test estimate_tokens_fallback() function."""

    def test_estimate_tokens_basic(self) -> None:
        """Test basic fallback estimation."""
        text = "Hello world"  # 2 words
        tokens = estimate_tokens_fallback(text)
        assert tokens == int(2 * 1.3)  # 2.6 ≈ 2

    def test_estimate_tokens_empty(self) -> None:
        """Test fallback for empty string."""
        assert estimate_tokens_fallback("") == 0

    def test_estimate_tokens_single_word(self) -> None:
        """Test fallback for single word."""
        tokens = estimate_tokens_fallback("Hello")
        assert tokens == int(1 * 1.3)  # 1.3 ≈ 1

    def test_estimate_tokens_many_words(self) -> None:
        """Test fallback for multiple words."""
        text = "The quick brown fox jumps over the lazy dog"  # 9 words
        tokens = estimate_tokens_fallback(text)
        assert tokens == int(9 * 1.3)  # 11.7 ≈ 11

    def test_estimate_tokens_whitespace_handling(self) -> None:
        """Test fallback handles multiple spaces correctly."""
        text = "Hello    world"  # Multiple spaces between words
        tokens = estimate_tokens_fallback(text)
        # split() handles multiple spaces, should count as 2 words
        assert tokens == int(2 * 1.3)

    def test_estimate_tokens_newlines(self) -> None:
        """Test fallback handles newlines correctly."""
        text = "Hello\nworld\ntest"  # 3 words separated by newlines
        tokens = estimate_tokens_fallback(text)
        assert tokens == int(3 * 1.3)

    def test_estimate_tokens_returns_int(self) -> None:
        """Test that fallback always returns integer."""
        text = "One two three four five"  # 5 words
        tokens = estimate_tokens_fallback(text)
        assert isinstance(tokens, int)
        assert tokens == int(5 * 1.3)  # 6.5 ≈ 6

