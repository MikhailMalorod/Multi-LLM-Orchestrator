"""Tests for the LLM Router module."""

import pytest
from unittest.mock import Mock, AsyncMock

# Add src to path for testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator.router import LLMRouter


class TestLLMRouter:
    """Test cases for the LLMRouter class."""
    
    def test_init_default(self) -> None:
        """Test router initialization with default config."""
        router = LLMRouter()
        assert router.config == {}
        assert router.providers == {}
        
    def test_init_with_config(self) -> None:
        """Test router initialization with custom config."""
        config = {"test_key": "test_value"}
        router = LLMRouter(config)
        assert router.config == config
        assert router.providers == {}
        
    def test_add_provider(self) -> None:
        """Test adding a provider to the router."""
        router = LLMRouter()
        mock_provider = Mock()
        
        router.add_provider("test_provider", mock_provider)
        
        assert "test_provider" in router.providers
        assert router.providers["test_provider"] == mock_provider
        
    @pytest.mark.asyncio
    async def test_chat_not_implemented(self) -> None:
        """Test that chat method raises NotImplementedError."""
        router = LLMRouter()
        
        with pytest.raises(NotImplementedError):
            await router.chat("Hello, world!")
            
    def test_multiple_providers(self) -> None:
        """Test adding multiple providers."""
        router = LLMRouter()
        provider1 = Mock()
        provider2 = Mock()
        
        router.add_provider("provider1", provider1)
        router.add_provider("provider2", provider2)
        
        assert len(router.providers) == 2
        assert router.providers["provider1"] == provider1
        assert router.providers["provider2"] == provider2


class TestRouterConfiguration:
    """Test cases for router configuration handling."""
    
    def test_empty_config_handling(self) -> None:
        """Test that empty config is handled properly."""
        router = LLMRouter({})
        assert router.config == {}
        
    def test_none_config_handling(self) -> None:
        """Test that None config defaults to empty dict."""
        router = LLMRouter(None)
        assert router.config == {}
        
    def test_config_persistence(self) -> None:
        """Test that config is stored correctly."""
        original_config = {
            "api_key": "test_key", 
            "timeout": 30,
            "retries": 3
        }
        router = LLMRouter(original_config)
        
        # Ensure config is not modified by router
        assert router.config == original_config
        assert router.config is not original_config  # Should be a copy or reference


# Fixtures for testing (if needed in the future)
@pytest.fixture
def mock_config():
    """Provide a mock configuration for testing."""
    return {
        "default_provider": "test",
        "timeout": 30,
        "max_retries": 3
    }


@pytest.fixture
def router_with_config(mock_config):
    """Provide a router instance with mock configuration."""
    return LLMRouter(mock_config)
