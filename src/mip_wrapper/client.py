"""Main MIP Wrapper client."""

import logging
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from mip_wrapper.artifacts import DecryptedFile, FileInfo
from mip_wrapper.auth import AuthBase, CertificateAuth
from mip_wrapper.bridge.client import HelperClient
from mip_wrapper.exceptions import (
    InvalidConfigurationError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


class MipClient:
    """Client for MIP file operations."""

    def __init__(
        self,
        auth: AuthBase,
        authorization_mode: str,
        delegated_user: str | None = None,
        helper_path: str | None = None,
        correlation_id: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """
        Initialize MipClient.

        Args:
            auth: Authentication configuration (CertificateAuth, ClientSecretAuth)
            authorization_mode: "delegated_reader" or "super_user"
            delegated_user: User UPN for delegated_reader mode (required if using that mode)
            helper_path: Path to MipWrapper.Helper executable
            correlation_id: Correlation ID for audit/logging
            timeout_seconds: Operation timeout
        """
        auth.validate()

        if authorization_mode not in ("delegated_reader", "super_user"):
            raise InvalidConfigurationError(
                f"Invalid authorization_mode: {authorization_mode}",
                error_code="InvalidAuthMode",
            )

        if authorization_mode == "delegated_reader" and not delegated_user:
            raise InvalidConfigurationError(
                "delegated_user is required for delegated_reader mode",
                error_code="MissingDelegatedUser",
            )

        self.auth = auth
        self.authorization_mode = authorization_mode
        self.delegated_user = delegated_user
        self.correlation_id = correlation_id or ""
        self.timeout_seconds = timeout_seconds

        # Find helper executable
        if helper_path:
            self.helper_path = Path(helper_path)
        else:
            self.helper_path = self._find_helper()

        self.helper = HelperClient(self.helper_path, timeout_seconds)

    def _find_helper(self) -> Path:
        """Find MipWrapper.Helper executable."""
        # Try common locations
        candidates = [
            Path.cwd() / "MipWrapper.Helper",
            Path.cwd() / "MipWrapper.Helper.exe",
            Path(__file__).parent.parent.parent / "native" / "MipWrapper.Helper",
            Path(__file__).parent.parent.parent / "native" / "MipWrapper.Helper.exe",
        ]

        for candidate in candidates:
            if candidate.exists():
                logger.debug(f"Found helper at: {candidate}")
                return candidate

        raise InvalidConfigurationError(
            "MipWrapper.Helper executable not found. "
            "Specify helper_path parameter or ensure it's in PATH.",
            error_code="HelperNotFound",
        )

    def inspect(self, source_path: str) -> FileInfo:
        """
        Inspect file protection metadata.

        Args:
            source_path: Path to protected file

        Returns:
            FileInfo with metadata
        """
        logger.info(f"Inspecting file: {source_path}")

        result = self.helper.inspect(
            tenant_id=self.auth.tenant_id,
            client_id=self.auth.client_id,
            certificate_path=self.auth.certificate_path
            if isinstance(self.auth, CertificateAuth)
            else "",
            authorization_mode=self.authorization_mode,
            delegated_user=self.delegated_user,
            source_path=source_path,
        )

        return FileInfo(
            is_protected=result.is_protected,
            label_id=result.label_id,
            tenant_id=result.tenant_id,
            file_format=result.file_format,
            protection_type=result.protection_type,
            usage_rights=result.usage_rights,
            can_decrypt=result.can_decrypt,
            sdk_version=result.sdk_version,
            helper_version=result.helper_version,
        )

    @contextmanager
    def decrypted_file(self, source_path: str) -> Generator[DecryptedFile, None, None]:
        """
        Context manager for temporary file decryption.

        Automatically cleans up after use.

        Args:
            source_path: Path to protected file

        Yields:
            DecryptedFile artifact with temporary file path

        Raises:
            PermissionDeniedError: If user lacks Export right
        """
        temp_dir = None
        try:
            # Create secure temporary directory
            temp_dir = tempfile.mkdtemp(prefix="mipwrapper_", dir=None)
            logger.debug(f"Created temp directory: {temp_dir}")
            temp_path = Path(temp_dir)
            temp_path.chmod(0o700)

            # Get source filename
            source = Path(source_path)
            output_filename = source.name
            output_path = str(temp_path / output_filename)

            # Decrypt
            logger.info(f"Decrypting to temp: {source_path}")
            result = self.helper.decrypt(
                tenant_id=self.auth.tenant_id,
                client_id=self.auth.client_id,
                certificate_path=self.auth.certificate_path
                if isinstance(self.auth, CertificateAuth)
                else "",
                authorization_mode=self.authorization_mode,
                delegated_user=self.delegated_user,
                source_path=source_path,
                output_path=output_path,
            )

            # Yield artifact
            artifact = DecryptedFile(
                path=Path(result.output_path),
                filename=output_filename,
                file_format=result.file_format,
                size_bytes=result.size_bytes,
                audit_metadata={
                    "source": source_path,
                    "authorization_mode": self.authorization_mode,
                    "correlation_id": self.correlation_id,
                },
            )
            yield artifact

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

        finally:
            # Cleanup
            if temp_dir:
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temp directory: {temp_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"Cleanup failed: {cleanup_error}")
