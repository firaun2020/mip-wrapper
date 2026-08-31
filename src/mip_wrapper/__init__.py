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
    MissingRuntimeError,
    NativeRuntimeError,
    PermissionDeniedError,
    ProtocolError,
    UnsupportedFileTypeError,
    UnsupportedProtectionError,
)
from mip_wrapper.auth import AuthBase, CertificateAuth, ClientSecretAuth
from mip_wrapper.artifacts import DecryptedFile, FileInfo
from mip_wrapper.version import PACKAGE_VERSION, PROTOCOL_VERSION

__version__ = PACKAGE_VERSION

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
    "MissingRuntimeError",
    "AuthBase",
    "CertificateAuth",
    "ClientSecretAuth",
    "DecryptedFile",
    "FileInfo",
    "PACKAGE_VERSION",
    "PROTOCOL_VERSION",
]
