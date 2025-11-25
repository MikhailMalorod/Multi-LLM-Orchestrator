"""Multi-LLM Orchestrator

A unified interface for orchestrating multiple Large Language Model providers.

This package provides:
    - Router: Intelligent routing and fallback for multiple LLM providers
    - Providers: GigaChat, YandexGPT, Ollama, and Mock providers
    - LangChain Integration: Optional compatibility layer for LangChain
        (requires: pip install multi-llm-orchestrator[langchain])
"""

__version__ = "0.1.0"
__author__ = "Multi-LLM Orchestrator Contributors"

from .config import Config
from .router import Router

# Backward compatibility
LLMRouter = Router

# Optional LangChain integration
try:
    from .langchain import MultiLLMOrchestrator

    __all__ = ["Router", "LLMRouter", "Config", "MultiLLMOrchestrator"]
except ImportError:
    # langchain-core not installed, skip MultiLLMOrchestrator export
    __all__ = ["Router", "LLMRouter", "Config"]
