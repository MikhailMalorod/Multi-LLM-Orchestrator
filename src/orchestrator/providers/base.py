"""Base provider interface for LLM implementations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseProvider(ABC):
    """Abstract base class for LLM providers.
    
    All LLM provider implementations should inherit from this class
    and implement the required abstract methods.
    """
    
    def __init__(self, api_key: str, **kwargs: Any) -> None:
        """Initialize the provider.
        
        Args:
            api_key: API key for the provider
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.config = kwargs
        
    @abstractmethod
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> str:
        """Send a chat message to the provider.
        
        Args:
            message: The user message
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters
            
        Returns:
            The provider's response
        """
        pass
        
    @abstractmethod
    async def chat_stream(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Any:
        """Stream a chat response from the provider.
        
        Args:
            message: The user message
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters
            
        Yields:
            Response chunks as they become available
        """
        pass
        
    @abstractmethod
    def get_models(self) -> List[str]:
        """Get list of available models for this provider.
        
        Returns:
            List of model names/identifiers
        """
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the provider name.
        
        Returns:
            Human-readable provider name
        """
        pass
