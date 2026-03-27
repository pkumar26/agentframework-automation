"""Unit tests for AgentBaseConfig."""

import os
from unittest.mock import patch

import pytest

from agents._base.config import AgentBaseConfig


class TestAgentBaseConfig:
    """Tests for the base configuration class."""

    def test_loads_from_env_vars(self):
        """Config should load from environment variables."""
        env = {
            "AZURE_AI_PROJECT_ENDPOINT": "https://test.services.ai.azure.com/api/projects/test",
            "ENVIRONMENT": "qa",
        }
        with patch.dict(os.environ, env, clear=False):
            config = AgentBaseConfig()
            assert config.azure_ai_project_endpoint == "https://test.services.ai.azure.com/api/projects/test"
            assert config.environment == "qa"

    def test_default_values(self):
        """Config should use defaults when env vars are not set."""
        env = {"AZURE_AI_PROJECT_ENDPOINT": "https://test.services.ai.azure.com/api/projects/test"}
        with patch.dict(os.environ, env, clear=False):
            config = AgentBaseConfig()
            assert config.environment == "dev"

    def test_missing_required_field_raises(self):
        """Config should fail when required fields are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):
                AgentBaseConfig(_env_file=None)
