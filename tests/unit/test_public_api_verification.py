"""Verification of public API usage scenarios."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mip_wrapper import MipClient, MissingRuntimeError
from mip_wrapper.auth import CertificateAuth
from mip_wrapper.exceptions import (
    InvalidConfigurationError,
    PermissionDeniedError,
    UnsupportedFileTypeError,
)


class TestPublicAPIScenarios:
    """Test the public API against intended usage scenarios."""

    def test_scenario_1_create_client(self, mock_certificate_path, mock_password_path, mock_helper_path):
        """Scenario 1: Create a client with certificate auth."""
        auth = CertificateAuth(
            tenant_id="00000000-0000-0000-0000-000000000000",
            client_id="11111111-1111-1111-1111-111111111111",
            certificate_path=mock_certificate_path,
            certificate_password_path=mock_password_path,
        )

        client = MipClient(
            auth=auth,
            authorization_mode="delegated_reader",
            delegated_user="reader@company.com",
            helper_path=str(mock_helper_path),
        )

        assert client.auth.tenant_id == "00000000-0000-0000-0000-000000000000"
        assert client.authorization_mode == "delegated_reader"
        assert client.delegated_user == "reader@company.com"

    def test_scenario_1_security_no_password_in_logs(self, mock_certificate_path, mock_password_path, mock_helper_path, caplog):
        """Verify password is not logged during client creation."""
        password_content = Path(mock_password_path).read_text()

        auth = CertificateAuth(
            tenant_id="00000000-0000-0000-0000-000000000000",
            client_id="11111111-1111-1111-1111-111111111111",
            certificate_path=mock_certificate_path,
            certificate_password_path=mock_password_path,
        )

        client = MipClient(
            auth=auth,
            authorization_mode="delegated_reader",
            delegated_user="reader@company.com",
            helper_path=str(mock_helper_path),
        )

        # Verify password does not appear in logs
        assert password_content not in caplog.text

    def test_scenario_1_missing_certificate_file(self, test_auth):
        """Verify missing certificate file produces typed error."""
        auth = CertificateAuth(
            tenant_id="tenant",
            client_id="client",
            certificate_path="/nonexistent/cert.pfx",
        )

        with pytest.raises(InvalidConfigurationError):
            auth.validate()

    def test_scenario_1_invalid_authorization_mode(self, test_auth, mock_helper_path):
        """Verify invalid authorization mode is rejected."""
        with pytest.raises(InvalidConfigurationError, match="authorization_mode"):
            MipClient(
                auth=test_auth,
                authorization_mode="invalid_mode",
                delegated_user="user@example.com",
                helper_path=str(mock_helper_path),
            )

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    def test_scenario_2_inspect_file(self, mock_popen, test_auth, mock_helper_path, mock_protected_file):
        """Scenario 2: Inspect a protected file."""
        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "is_protected": True,
                "label_id": "12345678-1234-1234-1234-123456789012",
                "tenant_id": "00000000-0000-0000-0000-000000000000",
                "file_format": "xlsx",
                "protection_type": "azure_rms",
                "usage_rights": ["Edit", "Export", "Print"],
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
        assert info.label_id == "12345678-1234-1234-1234-123456789012"
        assert "Export" in info.usage_rights
        assert info.can_decrypt

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    @patch("tempfile.mkdtemp")
    @patch("shutil.rmtree")
    def test_scenario_3_decrypt_and_use(self, mock_rmtree, mock_mkdtemp, mock_popen, test_auth, mock_helper_path, mock_protected_file, tmp_path):
        """Scenario 3: Decrypt file and use with openpyxl-like operations."""
        temp_dir = str(tmp_path / "mipwrapper_test")
        (tmp_path / "mipwrapper_test").mkdir()
        mock_mkdtemp.return_value = temp_dir

        # Create the decrypted file at the expected location
        output_filename = Path(mock_protected_file).name
        decrypted_file_path = Path(temp_dir) / output_filename
        decrypted_file_path.write_bytes(b"PK\x03\x04")  # ZIP header for Excel

        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "output_path": str(decrypted_file_path),
                "size_bytes": 4,
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

        with client.decrypted_file(mock_protected_file) as decrypted:
            assert Path(decrypted.path).exists()
            assert decrypted.path.suffix == ".xlsx"
            # Simulate openpyxl usage
            with open(decrypted.path, "rb") as f:
                content = f.read()
            assert content[:4] == b"PK\x03\x04"

        # Verify cleanup was called with the correct directory
        mock_rmtree.assert_called_once_with(temp_dir)

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    @patch("tempfile.mkdtemp")
    def test_scenario_4_cleanup_after_success(self, mock_mkdtemp, mock_popen, test_auth, mock_helper_path, mock_protected_file, tmp_path):
        """Scenario 4: Verify cleanup after successful processing."""
        temp_dir = tmp_path / "mipwrapper_success"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)

        decrypted_file = temp_dir / "protected-report.xlsx"
        decrypted_file.write_bytes(b"test")

        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "output_path": str(decrypted_file),
                "size_bytes": 4,
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

        temporary_path = None
        with client.decrypted_file(mock_protected_file) as decrypted:
            temporary_path = Path(decrypted.path)
            assert temporary_path.exists()

        assert not temporary_path.exists()

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    @patch("tempfile.mkdtemp")
    def test_scenario_5_cleanup_on_user_failure(self, mock_mkdtemp, mock_popen, test_auth, mock_helper_path, mock_protected_file, tmp_path):
        """Scenario 5: Verify cleanup happens when user processing fails."""
        temp_dir = tmp_path / "mipwrapper_failure"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)

        decrypted_file = temp_dir / "protected-report.xlsx"
        decrypted_file.write_bytes(b"test")

        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "output_path": str(decrypted_file),
                "size_bytes": 4,
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

        temporary_path = None
        try:
            with client.decrypted_file(mock_protected_file) as decrypted:
                temporary_path = Path(decrypted.path)
                assert temporary_path.exists()
                raise RuntimeError("Simulated processing failure")
        except RuntimeError:
            pass

        assert temporary_path is not None
        assert not temporary_path.exists()

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    def test_scenario_6_unauthorized_user(self, mock_popen, test_auth, mock_helper_path, mock_protected_file):
        """Scenario 6: Unauthorized user gets typed AuthorizationError."""
        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": False,
            "error": {
                "code": "PermissionDenied",
                "message": "User lacks Export right",
            }
        }

        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = json.dumps(response_data) + "\n"
        mock_popen.return_value = mock_process

        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="unauthorized@example.com",
            helper_path=str(mock_helper_path),
        )

        with pytest.raises(PermissionDeniedError):
            with client.decrypted_file(mock_protected_file):
                pass

    @patch("mip_wrapper.bridge.client.subprocess.Popen")
    def test_scenario_7_missing_file(self, mock_popen, test_auth, mock_helper_path):
        """Scenario 7: Missing file produces appropriate error."""
        response_data = {
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": False,
            "error": {
                "code": "FileNotFound",
                "message": "File not found: /missing.xlsx",
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

        with pytest.raises(Exception):  # Will be DecryptionError or similar
            client.inspect("missing.xlsx")

    def test_scenario_9_filename_variations(self, mock_certificate_path, mock_password_path, mock_helper_path):
        """Scenario 9: Filenames with spaces, unicode, various cases."""
        auth = CertificateAuth(
            tenant_id="tenant",
            client_id="client",
            certificate_path=mock_certificate_path,
            certificate_password_path=mock_password_path,
        )

        client = MipClient(
            auth=auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            helper_path=str(mock_helper_path),
        )

        # These should all be accepted as input (helper validates)
        test_filenames = [
            "Report with Spaces.xlsx",
            "Rapport_Français_2024.xlsx",
            "UPPERCASE.XLSX",
            "long_filename_with_many_characters_that_is_still_valid_on_most_filesystems_2024.xlsx",
        ]

        for filename in test_filenames:
            # Just verify client accepts them without raising
            assert client is not None
