"""Decrypted file artifacts."""

from datetime import datetime, timezone
from pathlib import Path


class DecryptedFile:
    """Artifact representing a decrypted temporary file."""

    def __init__(
        self,
        path: Path,
        filename: str,
        file_format: str,
        size_bytes: int | None = None,
        audit_metadata: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize decrypted file artifact.

        Args:
            path: Path to the decrypted file
            filename: Original filename
            file_format: File extension (.xlsx, .pdf, etc.)
            size_bytes: Size of decrypted file (if known)
            audit_metadata: Safe audit metadata
        """
        self.path = path
        self.filename = filename
        self.file_format = file_format
        self.size_bytes = size_bytes
        self.audit_metadata = audit_metadata or {}
        self.decryption_timestamp = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"DecryptedFile(path={self.path}, filename={self.filename})"


class FileInfo:
    """Metadata about a protected file."""

    def __init__(
        self,
        is_protected: bool,
        label_id: str | None,
        tenant_id: str | None,
        file_format: str,
        protection_type: str,
        usage_rights: list[str],
        can_decrypt: bool,
        sdk_version: str,
        helper_version: str,
    ) -> None:
        """
        Initialize file info.

        Args:
            is_protected: Whether file is MIP-protected
            label_id: Sensitivity label ID (if available)
            tenant_id: Tenant ID where file is protected
            file_format: File extension
            protection_type: Type of protection (azure_rms, etc.)
            usage_rights: Available rights for current user
            can_decrypt: Whether current config can decrypt
            sdk_version: MIP SDK version
            helper_version: Helper version
        """
        self.is_protected = is_protected
        self.label_id = label_id
        self.tenant_id = tenant_id
        self.file_format = file_format
        self.protection_type = protection_type
        self.usage_rights = usage_rights
        self.can_decrypt = can_decrypt
        self.sdk_version = sdk_version
        self.helper_version = helper_version

    def __repr__(self) -> str:
        return (
            f"FileInfo(protected={self.is_protected}, "
            f"label={self.label_id}, rights={self.usage_rights})"
        )
