"""Test environment configuration loading."""

import pytest
from pathlib import Path
from config import Config


def test_list_environments():
    """Test listing available environments."""
    envs = Config.list_environments()

    assert isinstance(envs, dict)
    assert len(envs) > 0

    # Check structure of returned data
    for env_name, settings in envs.items():
        assert "description" in settings
        assert "source_dir" in settings
        assert "is_default" in settings


def test_load_default_environment():
    """Test loading default environment."""
    # Reset to defaults first
    Config.SOURCE_DIR = Path(".")

    env_name = Config.load_environment()

    assert env_name is not None
    assert Config.CURRENT_ENVIRONMENT == env_name
    assert Config.SOURCE_DIR != Path(".")


def test_load_specific_environment():
    """Test loading a specific environment."""
    envs = Config.list_environments()
    available_envs = list(envs.keys())

    if len(available_envs) > 0:
        test_env = available_envs[0]
        env_name = Config.load_environment(test_env)

        assert env_name == test_env
        assert Config.CURRENT_ENVIRONMENT == test_env


def test_invalid_environment():
    """Test loading non-existent environment raises error."""
    with pytest.raises(ValueError, match="not found"):
        Config.load_environment("nonexistent_environment_xyz")


def test_environment_source_dir_exists():
    """Test that loaded environment has valid source directory setting."""
    Config.load_environment()

    # Check that SOURCE_DIR is set to a valid path object
    assert isinstance(Config.SOURCE_DIR, Path)

    # Note: We don't check if it exists because it might not on this machine
    # That's what the check_environment script is for


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
