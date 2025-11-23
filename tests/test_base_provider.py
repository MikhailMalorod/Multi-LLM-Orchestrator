"""Unit tests for BaseProvider models and validation.

This module tests Pydantic model validation for:
- ProviderConfig (name, timeout, max_retries validation)
- GenerationParams (temperature, max_tokens, top_p validation)
- Default values and optional fields
"""

import pytest
from pydantic import ValidationError

from orchestrator.providers.base import GenerationParams, ProviderConfig


class TestProviderConfigValidation:
    """Test ProviderConfig Pydantic model validation."""

    def test_provider_config_name_required(self) -> None:
        """Test that name is a required field in ProviderConfig.
        
        Verifies that creating ProviderConfig without name raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProviderConfig()  # Missing required field 'name'
        
        with pytest.raises(ValidationError):
            ProviderConfig(timeout=30)  # Missing required field 'name'

    def test_provider_config_timeout_validation(self) -> None:
        """Test timeout validation (1-300 seconds).
        
        Verifies that timeout accepts values in range [1, 300] and
        rejects values outside this range.
        """
        # Valid values
        config_min = ProviderConfig(name="test", timeout=1)
        assert config_min.timeout == 1
        
        config_max = ProviderConfig(name="test", timeout=300)
        assert config_max.timeout == 300
        
        config_middle = ProviderConfig(name="test", timeout=150)
        assert config_middle.timeout == 150
        
        # Invalid values
        with pytest.raises(ValidationError):
            ProviderConfig(name="test", timeout=0)  # Below minimum
        
        with pytest.raises(ValidationError):
            ProviderConfig(name="test", timeout=301)  # Above maximum
        
        with pytest.raises(ValidationError):
            ProviderConfig(name="test", timeout=-1)  # Negative

    def test_provider_config_max_retries_validation(self) -> None:
        """Test max_retries validation (0-10).
        
        Verifies that max_retries accepts values in range [0, 10] and
        rejects values outside this range.
        """
        # Valid values
        config_min = ProviderConfig(name="test", max_retries=0)
        assert config_min.max_retries == 0
        
        config_max = ProviderConfig(name="test", max_retries=10)
        assert config_max.max_retries == 10
        
        config_middle = ProviderConfig(name="test", max_retries=5)
        assert config_middle.max_retries == 5
        
        # Invalid values
        with pytest.raises(ValidationError):
            ProviderConfig(name="test", max_retries=-1)  # Below minimum
        
        with pytest.raises(ValidationError):
            ProviderConfig(name="test", max_retries=11)  # Above maximum

    def test_provider_config_default_values(self) -> None:
        """Test ProviderConfig default values.
        
        Verifies that ProviderConfig uses correct default values:
        - timeout: 30
        - max_retries: 3
        - api_key: None
        - base_url: None
        - model: None
        """
        config = ProviderConfig(name="test")
        
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.api_key is None
        assert config.base_url is None
        assert config.model is None


class TestGenerationParamsValidation:
    """Test GenerationParams Pydantic model validation."""

    def test_generation_params_temperature_validation(self) -> None:
        """Test temperature validation (0.0-2.0).
        
        Verifies that temperature accepts values in range [0.0, 2.0] and
        rejects values outside this range.
        """
        # Valid values
        params_min = GenerationParams(temperature=0.0)
        assert params_min.temperature == 0.0
        
        params_max = GenerationParams(temperature=2.0)
        assert params_max.temperature == 2.0
        
        params_middle = GenerationParams(temperature=1.0)
        assert params_middle.temperature == 1.0
        
        # Invalid values
        with pytest.raises(ValidationError):
            GenerationParams(temperature=-0.1)  # Below minimum
        
        with pytest.raises(ValidationError):
            GenerationParams(temperature=2.1)  # Above maximum

    def test_generation_params_max_tokens_validation(self) -> None:
        """Test max_tokens validation (>=1).
        
        Verifies that max_tokens accepts values >= 1 and
        rejects values < 1.
        """
        # Valid values
        params_min = GenerationParams(max_tokens=1)
        assert params_min.max_tokens == 1
        
        params_large = GenerationParams(max_tokens=10000)
        assert params_large.max_tokens == 10000
        
        # Invalid values
        with pytest.raises(ValidationError):
            GenerationParams(max_tokens=0)  # Below minimum
        
        with pytest.raises(ValidationError):
            GenerationParams(max_tokens=-1)  # Negative

    def test_generation_params_top_p_validation(self) -> None:
        """Test top_p validation (0.0-1.0).
        
        Verifies that top_p accepts values in range [0.0, 1.0] and
        rejects values outside this range.
        """
        # Valid values
        params_min = GenerationParams(top_p=0.0)
        assert params_min.top_p == 0.0
        
        params_max = GenerationParams(top_p=1.0)
        assert params_max.top_p == 1.0
        
        params_middle = GenerationParams(top_p=0.5)
        assert params_middle.top_p == 0.5
        
        # Invalid values
        with pytest.raises(ValidationError):
            GenerationParams(top_p=-0.1)  # Below minimum
        
        with pytest.raises(ValidationError):
            GenerationParams(top_p=1.1)  # Above maximum

    def test_generation_params_default_values(self) -> None:
        """Test GenerationParams default values.
        
        Verifies that GenerationParams uses correct default values:
        - temperature: 0.7
        - max_tokens: 1000
        - top_p: 1.0
        - stop: None
        """
        params = GenerationParams()
        
        assert params.temperature == 0.7
        assert params.max_tokens == 1000
        assert params.top_p == 1.0
        assert params.stop is None

    def test_generation_params_stop_sequences(self) -> None:
        """Test that stop sequences can be None or List[str].
        
        Verifies that stop field accepts None or a list of strings.
        """
        # None (default)
        params_none = GenerationParams()
        assert params_none.stop is None
        
        # List of strings
        params_list = GenerationParams(stop=["\n\n", "END"])
        assert params_list.stop == ["\n\n", "END"]
        
        # Empty list
        params_empty = GenerationParams(stop=[])
        assert params_empty.stop == []

