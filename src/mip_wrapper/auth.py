"""Authentication configuration."""

from abc import ABC, abstractmethod
from pathlib import Path

from mip_wrapper.exceptions import InvalidConfigurationError


class AuthBase(ABC):
    """Base class for authentication methods."""

    tenant_id: str
    client_id: str

    @abstractmethod
    def validate(self) -> None:
        """Validate configuration is complete."""
        pass


class CertificateAuth(AuthBase):
    """Certificate-based authentication (recommended)."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        certificate_path: str,
        certificate_password_path: str | None = None,
    ) -> None:
        """
        Configure certificate-based authentication.

        Args:
            tenant_id: Azure AD tenant ID (UUID or domain)
            client_id: App registration client ID (UUID)
            certificate_path: Path to .pfx certificate file
            certificate_password_path: Path to file containing certificate password
                                       (optional if cert has no password)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.certificate_path = certificate_path
        self.certificate_password_path = certificate_password_path

    def validate(self) -> None:
        """Validate certificate paths exist."""
        if not self.tenant_id or not self.client_id:
            raise InvalidConfigurationError(
                "tenant_id and client_id are required",
                error_code="MissingAuth",
            )

        cert_path = Path(self.certificate_path)
        if not cert_path.exists():
            raise InvalidConfigurationError(
                f"Certificate file not found: {self.certificate_path}",
                error_code="CertificateNotFound",
            )

        if self.certificate_password_path:
            pwd_path = Path(self.certificate_password_path)
            if not pwd_path.exists():
                raise InvalidConfigurationError(
                    f"Certificate password file not found: {self.certificate_password_path}",
                    error_code="PasswordFileNotFound",
                )


class ClientSecretAuth(AuthBase):
    """Client secret authentication (less secure, for development)."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        secret_provider: callable,
    ) -> None:
        """
        Configure client secret authentication.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: App registration client ID
            secret_provider: Callable that returns the client secret

        Note:
            Client secrets should be stored securely (Key Vault, etc.)
            This method is less secure than certificate authentication.
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.secret_provider = secret_provider

    def validate(self) -> None:
        """Validate configuration."""
        if not self.tenant_id or not self.client_id:
            raise InvalidConfigurationError(
                "tenant_id and client_id are required",
                error_code="MissingAuth",
            )
