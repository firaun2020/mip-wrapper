"""MIP Wrapper exception hierarchy."""

from typing import Any


class MipError(Exception):
    """Base exception for all MIP Wrapper errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        audit_metadata: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.audit_metadata = audit_metadata or {}


class AuthenticationError(MipError):
    """Authentication failed (certificate, token, etc.)."""

    pass


class AuthorizationError(MipError):
    """Authorization check failed."""

    pass


class PermissionDeniedError(AuthorizationError):
    """User lacks required usage right."""

    pass


class UnsupportedProtectionError(MipError):
    """File protection type is not supported."""

    pass


class UnsupportedFileTypeError(MipError):
    """File format is not supported."""

    pass


class InvalidConfigurationError(MipError):
    """Configuration is invalid or incomplete."""

    pass


class NativeRuntimeError(MipError):
    """Native helper (MipWrapper.Helper) error."""

    pass


class ProtocolError(NativeRuntimeError):
    """Protocol communication or parsing error."""

    pass


class DecryptionError(NativeRuntimeError):
    """File decryption failed."""

    pass


class CleanupError(NativeRuntimeError):
    """Cleanup of temporary files failed."""

    pass


class DestinationError(MipError):
    """Error uploading to destination."""

    pass


class MissingRuntimeError(MipError):
    """MipWrapper.Helper or required runtime not available."""

    pass
