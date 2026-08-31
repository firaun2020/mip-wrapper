"""Pytest configuration and fixtures."""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mock_helper_path(tmp_path):
    """Create a mock helper path."""
    helper = tmp_path / "MipWrapper.Helper"
    helper.touch()
    return helper


@pytest.fixture
def mock_certificate_path(tmp_path):
    """Create a mock certificate file."""
    cert = tmp_path / "test.pfx"
    cert.write_bytes(b"mock certificate data")
    return str(cert)


@pytest.fixture
def mock_password_path(tmp_path):
    """Create a mock password file."""
    pwd = tmp_path / "cert.password"
    pwd.write_text("testpassword123")
    pwd.chmod(0o600)
    return str(pwd)


@pytest.fixture
def mock_protected_file(tmp_path):
    """Create a mock protected file."""
    file = tmp_path / "protected.xlsx"
    file.write_bytes(b"mock protected xlsx")
    return str(file)


@pytest.fixture
def test_auth(mock_certificate_path, mock_password_path):
    """Create test authentication."""
    from mip_wrapper.auth import CertificateAuth

    return CertificateAuth(
        tenant_id="00000000-0000-0000-0000-000000000000",
        client_id="11111111-1111-1111-1111-111111111111",
        certificate_path=mock_certificate_path,
        certificate_password_path=mock_password_path,
    )
