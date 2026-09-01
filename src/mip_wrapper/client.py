"""Main MIP Wrapper client."""

import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from mip_wrapper.artifacts import DecryptedFile, FileInfo
from mip_wrapper.auth import AuthBase, CertificateAuth, ClientSecretAuth
from mip_wrapper.bridge.client import HelperClient
from mip_wrapper.exceptions import (
    CleanupError,
    InvalidConfigurationError,
    MissingRuntimeError,
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
        timeout_seconds: int = 120,
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

        if authorization_mode != "delegated_reader":
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
        self._version_checked = False

    def _check_version_compatibility(self, helper_version: str) -> None:
        """Check helper version compatibility on first use."""
        if self._version_checked:
            return

        from mip_wrapper.version import check_helper_version

        try:
            check_helper_version(helper_version)
            self._version_checked = True
            logger.info(f"Helper version {helper_version} is compatible")
        except ValueError as e:
            raise InvalidConfigurationError(
                str(e),
                error_code="VersionMismatch",
            ) from e

    def _find_helper(self) -> Path:
        """
        Find MipWrapper.Helper executable using search order:
        1. MIP_WRAPPER_HELPER_PATH environment variable
        2. Current working directory
        3. Package installation directory (future)
        """
        # 1. Check environment variable
        env_path = os.environ.get("MIP_WRAPPER_HELPER_PATH")
        if env_path:
            path = Path(env_path)
            if path.exists():
                logger.debug(f"Found helper via MIP_WRAPPER_HELPER_PATH: {path}")
                return path
            logger.warning(f"MIP_WRAPPER_HELPER_PATH set but file not found: {env_path}")

        # 2. Try common locations
        candidates = [
            Path.cwd() / "MipWrapper.Helper",
            Path.cwd() / "MipWrapper.Helper.exe",
            Path.cwd() / "helper-bin" / "MipWrapper.Helper",
            Path.cwd() / "helper-bin" / "MipWrapper.Helper.exe",
            Path(__file__).parent.parent.parent / "helper-bin" / "MipWrapper.Helper",
            Path(__file__).parent.parent.parent / "helper-bin" / "MipWrapper.Helper.exe",
        ]

        for candidate in candidates:
            if candidate.exists():
                logger.debug(f"Found helper at: {candidate}")
                return candidate

        # 3. Provide clear error with instructions
        raise MissingRuntimeError(
            "MipWrapper.Helper executable not found. "
            "\n\nTo use mip_wrapper, you must:\n"
            "1. Build the .NET helper:\n"
            "   cd native/MipWrapper.Helper\n"
            "   dotnet publish -c Release -o ../../helper-bin\n"
            "\n2. Make it discoverable:\n"
            "   - Set MIP_WRAPPER_HELPER_PATH=/path/to/MipWrapper.Helper\n"
            "   - Or place in current directory or helper-bin/\n"
            "   - Or pass helper_path parameter to MipClient()\n"
            "\nSee BUILD_LOCALLY.md for detailed instructions.",
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

        # Get client secret if using ClientSecretAuth
        client_secret = None
        if isinstance(self.auth, ClientSecretAuth):
            client_secret = self.auth.secret_provider()

        result = self.helper.inspect(
            tenant_id=self.auth.tenant_id,
            client_id=self.auth.client_id,
            certificate_path=self.auth.certificate_path
            if isinstance(self.auth, CertificateAuth)
            else "",
            authorization_mode=self.authorization_mode,
            delegated_user=self.delegated_user,
            source_path=source_path,
            client_secret=client_secret,
        )

        # Check version compatibility on first use
        self._check_version_compatibility(result.helper_version)

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

            # Get client secret if using ClientSecretAuth
            client_secret = None
            if isinstance(self.auth, ClientSecretAuth):
                client_secret = self.auth.secret_provider()

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
                client_secret=client_secret,
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
                    raise CleanupError(
                        f"Failed to remove temporary plaintext directory: {temp_dir}",
                        error_code="CleanupFailed",
                    ) from cleanup_error
