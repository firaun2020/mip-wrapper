"""Tests for authentication configuration."""

import pytest

from mip_wrapper.auth import CertificateAuth, ClientSecretAuth
from mip_wrapper.exceptions import InvalidConfigurationError


class TestCertificateAuth:
    """Test certificate authentication."""

    def test_valid_configuration(self, mock_certificate_path, mock_password_path):
        """Test valid certificate configuration."""
        auth = CertificateAuth(
            tenant_id="00000000-0000-0000-0000-000000000000",
            client_id="11111111-1111-1111-1111-111111111111",
            certificate_path=mock_certificate_path,
            certificate_password_path=mock_password_path,
        )

        auth.validate()  # Should not raise

    def test_missing_tenant_id(self, mock_certificate_path):
        """Test validation fails without tenant_id."""
        auth = CertificateAuth(
            tenant_id="",
            client_id="11111111-1111-1111-1111-111111111111",
            certificate_path=mock_certificate_path,
        )

        with pytest.raises(InvalidConfigurationError):
            auth.validate()

    def test_missing_certificate_file(self):
        """Test validation fails if certificate file doesn't exist."""
        auth = CertificateAuth(
            tenant_id="00000000-0000-0000-0000-000000000000",
            client_id="11111111-1111-1111-1111-111111111111",
            certificate_path="/nonexistent/cert.pfx",
        )

        with pytest.raises(InvalidConfigurationError, match="Certificate file not found"):
            auth.validate()

    def test_missing_password_file(self, mock_certificate_path):
        """Test validation fails if password file doesn't exist."""
        auth = CertificateAuth(
            tenant_id="00000000-0000-0000-0000-000000000000",
            client_id="11111111-1111-1111-1111-111111111111",
            certificate_path=mock_certificate_path,
            certificate_password_path="/nonexistent/cert.password",
        )

        with pytest.raises(InvalidConfigurationError, match="Certificate password file not found"):
            auth.validate()


class TestClientSecretAuth:
    """Test client secret authentication."""

    def test_valid_configuration(self):
        """Test valid client secret configuration."""
        auth = ClientSecretAuth(
            tenant_id="00000000-0000-0000-0000-000000000000",
            client_id="11111111-1111-1111-1111-111111111111",
            secret_provider=lambda: "secret123",
        )

        auth.validate()  # Should not raise

    def test_missing_tenant_id(self):
        """Test validation fails without tenant_id."""
        auth = ClientSecretAuth(
            tenant_id="",
            client_id="11111111-1111-1111-1111-111111111111",
            secret_provider=lambda: "secret",
        )

        with pytest.raises(InvalidConfigurationError):
            auth.validate()
