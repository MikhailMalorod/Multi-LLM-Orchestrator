"""Multi-LLM Orchestrator

A unified interface for orchestrating multiple Large Language Model providers.
"""

__version__ = "0.1.0"
__author__ = "Multi-LLM Orchestrator Contributors"

from .router import LLMRouter
from .config import Config

__all__ = ["LLMRouter", "Config"]
