"""MIP Wrapper: Python interface for Microsoft Information Protection decryption."""

from mip_wrapper.client import MipClient
from mip_wrapper.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CleanupError,
    DecryptionError,
    DestinationError,
    InvalidConfigurationError,
    MipError,
    NativeRuntimeError,
    PermissionDeniedError,
    ProtocolError,
    UnsupportedFileTypeError,
    UnsupportedProtectionError,
)
from mip_wrapper.auth import AuthBase, CertificateAuth, ClientSecretAuth
from mip_wrapper.artifacts import DecryptedFile, FileInfo

__version__ = "0.1.0"

__all__ = [
    "MipClient",
    "MipError",
    "AuthenticationError",
    "AuthorizationError",
    "PermissionDeniedError",
    "UnsupportedProtectionError",
    "UnsupportedFileTypeError",
    "InvalidConfigurationError",
    "NativeRuntimeError",
    "ProtocolError",
    "DecryptionError",
    "CleanupError",
    "DestinationError",
    "AuthBase",
    "CertificateAuth",
    "ClientSecretAuth",
    "DecryptedFile",
    "FileInfo",
]
