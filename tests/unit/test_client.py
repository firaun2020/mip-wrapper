"""Tests for MipClient."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from mip_wrapper import MipClient, PermissionDeniedError
from mip_wrapper.exceptions import InvalidConfigurationError


class TestMipClientInitialization:
    """Test MipClient initialization."""

    def test_delegated_reader_requires_user(self, test_auth, mock_helper_path):
        """Test delegated_reader mode requires delegated_user."""
        with pytest.raises(InvalidConfigurationError, match="delegated_user is required"):
            MipClient(
                auth=test_auth,
                authorization_mode="delegated_reader",
                delegated_user=None,
                helper_path=str(mock_helper_path),
            )

    def test_valid_initialization(self, test_auth, mock_helper_path):
        """Test valid client initialization."""
        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            helper_path=str(mock_helper_path),
        )

        assert client.auth == test_auth
        assert client.authorization_mode == "delegated_reader"
        assert client.delegated_user == "user@example.com"

    def test_invalid_authorization_mode(self, test_auth, mock_helper_path):
        """Test invalid authorization_mode is rejected."""
        with pytest.raises(InvalidConfigurationError, match="Invalid authorization_mode"):
            MipClient(
                auth=test_auth,
                authorization_mode="invalid_mode",
                delegated_user="user@example.com",
                helper_path=str(mock_helper_path),
            )


class TestMipClientInspect:
    """Test file inspection."""

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    def test_inspect_protected_file(self, mock_popen, test_auth, mock_helper_path, mock_protected_file):
        """Test inspecting a protected file."""
        # Mock helper response
        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "is_protected": True,
                "label_id": "label-uuid",
                "tenant_id": "tenant-uuid",
                "file_format": "xlsx",
                "protection_type": "azure_rms",
                "usage_rights": ["Edit", "Export"],
                "can_decrypt": True,
                "sdk_version": "1.18.124",
                "helper_version": "1.0.0",
            }
        }

        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = json.dumps(response_data) + "\n"
        mock_popen.return_value = mock_process

        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            helper_path=str(mock_helper_path),
        )

        info = client.inspect(mock_protected_file)

        assert info.is_protected
        assert info.file_format == "xlsx"
        assert "Export" in info.usage_rights
        assert info.can_decrypt

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    def test_inspect_unprotected_file(self, mock_popen, test_auth, mock_helper_path, mock_protected_file):
        """Test inspecting an unprotected file."""
        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "is_protected": False,
                "label_id": None,
                "tenant_id": None,
                "file_format": "xlsx",
                "protection_type": "none",
                "usage_rights": [],
                "can_decrypt": False,
                "sdk_version": "1.18.124",
                "helper_version": "1.0.0",
            }
        }

        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = json.dumps(response_data) + "\n"
        mock_popen.return_value = mock_process

        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            helper_path=str(mock_helper_path),
        )

        info = client.inspect(mock_protected_file)

        assert not info.is_protected
        assert info.can_decrypt is False


class TestMipClientDecryptedFile:
    """Test temporary file decryption."""

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    @patch("tempfile.mkdtemp")
    def test_decrypted_file_cleanup(self, mock_mkdtemp, mock_popen, test_auth, mock_helper_path, mock_protected_file, tmp_path):
        """Test temporary file is cleaned up after context exit."""
        # Create a temp dir for our mock
        temp_dir = tmp_path / "mipwrapper_test"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)

        output_file = temp_dir / "protected.xlsx"
        output_file.write_bytes(b"decrypted content")

        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "output_path": str(output_file),
                "size_bytes": 17,
                "file_format": "xlsx",
            }
        }

        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = json.dumps(response_data) + "\n"
        mock_popen.return_value = mock_process

        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            helper_path=str(mock_helper_path),
        )

        with client.decrypted_file(mock_protected_file) as artifact:
            assert artifact.path.exists()

        # Temp directory should be cleaned up
        assert not temp_dir.exists()

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    @patch("tempfile.mkdtemp")
    def test_decrypted_file_cleanup_on_exception(self, mock_mkdtemp, mock_popen, test_auth, mock_helper_path, mock_protected_file, tmp_path):
        """Test temporary file is cleaned up even if an exception occurs."""
        # Create a temp dir for our mock
        temp_dir = tmp_path / "mipwrapper_test_ex"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)

        output_file = temp_dir / "protected.xlsx"
        output_file.write_bytes(b"decrypted content")

        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "output_path": str(output_file),
                "size_bytes": 17,
                "file_format": "xlsx",
            }
        }

        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = json.dumps(response_data) + "\n"
        mock_popen.return_value = mock_process

        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            helper_path=str(mock_helper_path),
        )

        try:
            with client.decrypted_file(mock_protected_file) as artifact:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Temp directory should still be cleaned up
        assert not temp_dir.exists()
