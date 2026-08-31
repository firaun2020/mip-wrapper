"""Protocol v1.0: JSON communication between Python and .NET helper."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


PROTOCOL_VERSION = "1.0"


@dataclass
class ProtocolRequest:
    """Request to send to helper."""

    protocol_version: str = PROTOCOL_VERSION
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command: str = ""
    tenant_id: str = ""
    client_id: str = ""
    certificate_path: str = ""
    authorization_mode: str = ""
    delegated_user: str | None = None
    source_path: str | None = None
    output_path: str | None = None
    timeout_seconds: int = 30

    def to_json(self) -> str:
        """Serialize to JSON."""
        data = asdict(self)
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProtocolRequest":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProtocolResponse:
    """Response from helper."""

    protocol_version: str
    request_id: str
    success: bool
    result: dict[str, Any] | None = None
    error: dict[str, str] | None = None

    @classmethod
    def from_json(cls, json_str: str) -> "ProtocolResponse":
        """Parse from JSON."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}") from e

        return cls(
            protocol_version=data.get("protocol_version", ""),
            request_id=data.get("request_id", ""),
            success=data.get("success", False),
            result=data.get("result"),
            error=data.get("error"),
        )

    def validate_version(self) -> None:
        """Validate protocol version matches."""
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError(
                f"Unsupported protocol version: {self.protocol_version} "
                f"(expected {PROTOCOL_VERSION})"
            )

    def ensure_success(self) -> dict[str, Any]:
        """Raise if not successful."""
        if not self.success:
            error = self.error or {}
            code = error.get("code", "UnknownError")
            message = error.get("message", "Unknown error")
            raise ValueError(f"Helper error [{code}]: {message}")
        return self.result or {}


@dataclass
class InspectResult:
    """Result of inspect command."""

    is_protected: bool
    label_id: str | None
    tenant_id: str | None
    file_format: str
    protection_type: str
    usage_rights: list[str]
    can_decrypt: bool
    sdk_version: str
    helper_version: str

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "InspectResult":
        """Create from protocol response."""
        return cls(
            is_protected=data.get("is_protected", False),
            label_id=data.get("label_id"),
            tenant_id=data.get("tenant_id"),
            file_format=data.get("file_format", ""),
            protection_type=data.get("protection_type", ""),
            usage_rights=data.get("usage_rights", []),
            can_decrypt=data.get("can_decrypt", False),
            sdk_version=data.get("sdk_version", ""),
            helper_version=data.get("helper_version", ""),
        )


@dataclass
class DecryptResult:
    """Result of decrypt command."""

    output_path: str
    size_bytes: int
    file_format: str

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "DecryptResult":
        """Create from protocol response."""
        return cls(
            output_path=data.get("output_path", ""),
            size_bytes=data.get("size_bytes", 0),
            file_format=data.get("file_format", ""),
        )
