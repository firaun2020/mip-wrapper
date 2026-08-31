"""Tests for helper executable discovery."""

import os
from unittest.mock import patch

import pytest

from mip_wrapper import MipClient, MissingRuntimeError
from mip_wrapper.exceptions import InvalidConfigurationError


class TestHelperDiscovery:
    """Test helper executable discovery mechanisms."""

    def test_explicit_helper_path(self, test_auth, mock_helper_path):
        """Test explicit helper_path parameter works."""
        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            helper_path=str(mock_helper_path),
        )
        assert client.helper_path == mock_helper_path

    def test_environment_variable_helper_path(self, test_auth, mock_helper_path, monkeypatch):
        """Test MIP_WRAPPER_HELPER_PATH environment variable works."""
        monkeypatch.setenv("MIP_WRAPPER_HELPER_PATH", str(mock_helper_path))

        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
        )
        assert client.helper_path == mock_helper_path

    def test_missing_helper_raises_clear_error(self, test_auth, monkeypatch, tmp_path):
        """Test missing helper discovery raises MissingRuntimeError with clear instructions."""
        # When no explicit path or env var is set, and helper is not found
        monkeypatch.delenv("MIP_WRAPPER_HELPER_PATH", raising=False)
        monkeypatch.chdir(str(tmp_path))  # Change to empty temp directory

        with pytest.raises(MissingRuntimeError) as exc_info:
            MipClient(
                auth=test_auth,
                authorization_mode="delegated_reader",
                delegated_user="user@example.com",
                # Don't specify helper_path, will search and fail
            )

        error = exc_info.value
        assert "MipWrapper.Helper" in error.message
        assert "dotnet publish" in error.message
        assert "BUILD_LOCALLY.md" in error.message
        assert error.error_code == "HelperNotFound"

    def test_environment_variable_nonexistent_file(self, test_auth, monkeypatch, caplog):
        """Test warning when environment variable points to nonexistent file."""
        monkeypatch.setenv("MIP_WRAPPER_HELPER_PATH", "/nonexistent/path")

        with pytest.raises(MissingRuntimeError):
            MipClient(
                auth=test_auth,
                authorization_mode="delegated_reader",
                delegated_user="user@example.com",
            )

        # Should have warning about env var pointing to nonexistent file
        assert any("MIP_WRAPPER_HELPER_PATH" in record.message for record in caplog.records)
