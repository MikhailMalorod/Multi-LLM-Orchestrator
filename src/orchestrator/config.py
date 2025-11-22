"""Configuration management for Multi-LLM Orchestrator."""

import os
from typing import Dict, Any, Optional
from pathlib import Path

from pydantic import BaseModel, Field
from dotenv import load_dotenv


class Config(BaseModel):
    """Configuration model for the Multi-LLM Orchestrator.
    
    Handles loading and validation of configuration from environment
    variables and configuration files.
    """
    
    # API Keys
    gigachat_api_key: Optional[str] = Field(None, description="GigaChat API key")
    yandexgpt_api_key: Optional[str] = Field(None, description="YandexGPT API key")
    
    # General settings
    log_level: str = Field("INFO", description="Logging level")
    default_provider: str = Field("auto", description="Default LLM provider")
    max_retries: int = Field(3, description="Maximum retry attempts")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")
    
    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Config":
        """Load configuration from environment variables.
        
        Args:
            env_file: Optional path to .env file
            
        Returns:
            Config instance with loaded values
        """
        if env_file and env_file.exists():
            load_dotenv(env_file)
        elif Path(".env").exists():
            load_dotenv(".env")
            
        return cls(
            gigachat_api_key=os.getenv("GIGACHAT_API_KEY"),
            yandexgpt_api_key=os.getenv("YANDEXGPT_API_KEY"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            default_provider=os.getenv("DEFAULT_PROVIDER", "auto"),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout_seconds=int(os.getenv("TIMEOUT_SECONDS", "30")),
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return self.model_dump()
