"""Tests for protocol serialization and parsing."""

import json
import pytest

from mip_wrapper.bridge.protocol import (
    ProtocolRequest,
    ProtocolResponse,
    InspectResult,
    DecryptResult,
)


class TestProtocolRequest:
    """Test protocol request serialization."""

    def test_inspect_request(self):
        """Test inspect request serialization."""
        request = ProtocolRequest(
            command="inspect",
            tenant_id="tenant123",
            client_id="client123",
            certificate_path="/path/to/cert.pfx",
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            source_path="/path/to/file.xlsx",
        )

        json_str = request.to_json()
        data = json.loads(json_str)

        assert data["command"] == "inspect"
        assert data["tenant_id"] == "tenant123"
        assert data["authorization_mode"] == "delegated_reader"

    def test_decrypt_request(self):
        """Test decrypt request serialization."""
        request = ProtocolRequest(
            command="decrypt",
            tenant_id="tenant123",
            client_id="client123",
            certificate_path="/path/to/cert.pfx",
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            source_path="/path/to/file.xlsx",
            output_path="/tmp/output.xlsx",
            timeout_seconds=60,
        )

        json_str = request.to_json()
        data = json.loads(json_str)

        assert data["command"] == "decrypt"
        assert data["output_path"] == "/tmp/output.xlsx"
        assert data["timeout_seconds"] == 60

    def test_super_user_request_preserves_mode_without_delegated_user(self):
        request = ProtocolRequest(
            command="inspect",
            tenant_id="tenant123",
            client_id="client123",
            authorization_mode="super_user",
            source_path="/path/to/file.xlsx",
        )

        data = json.loads(request.to_json())

        assert data["authorization_mode"] == "super_user"
        assert "delegated_user" not in data

    def test_request_has_protocol_version(self):
        """Test request includes protocol version."""
        request = ProtocolRequest(command="inspect")
        json_str = request.to_json()
        data = json.loads(json_str)

        assert data["protocol_version"] == "1.0"

    def test_request_has_request_id(self):
        """Test request has unique request_id."""
        request = ProtocolRequest(command="inspect")
        json_str = request.to_json()
        data = json.loads(json_str)

        assert "request_id" in data
        assert len(data["request_id"]) > 0


class TestProtocolResponse:
    """Test protocol response parsing."""

    def test_success_response(self):
        """Test parsing successful response."""
        json_str = json.dumps({
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": True,
            "result": {
                "is_protected": True,
                "label_id": "label123",
            }
        })

        response = ProtocolResponse.from_json(json_str)

        assert response.success
        assert response.result["is_protected"] is True

    def test_error_response(self):
        """Test parsing error response."""
        json_str = json.dumps({
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": False,
            "error": {
                "code": "PermissionDenied",
                "message": "User lacks Export right",
            }
        })

        response = ProtocolResponse.from_json(json_str)

        assert not response.success
        assert response.error["code"] == "PermissionDenied"

    def test_version_validation(self):
        """Test protocol version validation."""
        json_str = json.dumps({
            "protocol_version": "2.0",
            "request_id": "req-123",
            "success": True,
        })

        response = ProtocolResponse.from_json(json_str)

        with pytest.raises(ValueError, match="Unsupported protocol version"):
            response.validate_version()

    def test_ensure_success_raises_on_error(self):
        """Test ensure_success raises on error responses."""
        json_str = json.dumps({
            "protocol_version": "1.0",
            "request_id": "req-123",
            "success": False,
            "error": {
                "code": "DecryptionError",
                "message": "Decryption failed",
            }
        })

        response = ProtocolResponse.from_json(json_str)

        from mip_wrapper.exceptions import DecryptionError

        with pytest.raises(DecryptionError, match="Decryption failed"):
            response.ensure_success()


class TestInspectResult:
    """Test InspectResult parsing."""

    def test_from_response(self):
        """Test creating InspectResult from response data."""
        data = {
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

        result = InspectResult.from_response(data)

        assert result.is_protected
        assert result.file_format == "xlsx"
        assert "Export" in result.usage_rights
        assert result.sdk_version == "1.18.124"


class TestDecryptResult:
    """Test DecryptResult parsing."""

    def test_from_response(self):
        """Test creating DecryptResult from response data."""
        data = {
            "output_path": "/tmp/output.xlsx",
            "size_bytes": 12345,
            "file_format": "xlsx",
        }

        result = DecryptResult.from_response(data)

        assert result.output_path == "/tmp/output.xlsx"
        assert result.size_bytes == 12345
        assert result.file_format == "xlsx"
