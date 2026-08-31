# MIP Wrapper Python API (Stage 1 Design)

## Module Structure

```python
from mip_wrapper import MipClient
from mip_wrapper.auth import CertificateAuth, ClientSecretAuth
from mip_wrapper.exceptions import (
    MipError,
    AuthenticationError,
    AuthorizationError,
    PermissionDeniedError,
    UnsupportedProtectionError,
    UnsupportedFileTypeError,
    InvalidConfigurationError,
    NativeRuntimeError,
    ProtocolError,
    DecryptionError,
    DestinationError,
    CleanupError,
)
from mip_wrapper.artifacts import DecryptedFile, FileInfo
from mip_wrapper.results import DecryptionResult, PipelineResult
```

## Exception Hierarchy

```
MipError (base)
├── AuthenticationError
├── AuthorizationError
├── PermissionDeniedError (subclass of AuthorizationError)
├── UnsupportedProtectionError
├── UnsupportedFileTypeError
├── InvalidConfigurationError
├── NativeRuntimeError
│   ├── ProtocolError
│   ├── DecryptionError
│   └── CleanupError
└── DestinationError
```

### Exception Details

Each exception includes:
- A descriptive message (free of secrets, tokens, content)
- An optional `error_code` for programmatic handling
- An optional `audit_metadata` dict with safe audit information

```python
try:
    client.decrypted_file("protected.xlsx")
except PermissionDeniedError as e:
    print(e.message)  # "User lacks Export right for this file."
    print(e.error_code)  # "INSUFFICIENT_RIGHTS"
    print(e.audit_metadata)  # {"required_right": "Export"}
```

## Authentication

### Certificate Authentication (Recommended)

```python
from mip_wrapper.auth import CertificateAuth

def get_certificate_password() -> str:
    """Return certificate password from secure storage."""
    # Example: read from Key Vault, prompted input, env var, etc.
    import keyring
    return keyring.get_password("mipwrapper", "cert_password")

auth = CertificateAuth(
    tenant_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    client_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    certificate_path="/secure/path/to/certificate.pfx",
    certificate_password_provider=get_certificate_password,
)
```

**Parameters:**
- `tenant_id` (str, required): Azure AD tenant ID (UUID or domain)
- `client_id` (str, required): Registered application client ID (UUID)
- `certificate_path` (str, required): Path to .pfx certificate file
- `certificate_password_provider` (Callable[[], str], optional): Function that returns certificate password. If None, assume no password.

**Behavior:**
- Certificate is loaded by the .NET helper (not by Python)
- Password is requested via the callback only when needed
- Password is never logged or passed as an argument
- Fails fast if certificate is not found or password is invalid

---

### Client Secret Authentication (Less Secure)

```python
from mip_wrapper.auth import ClientSecretAuth

def get_client_secret() -> str:
    """Return client secret from secure storage."""
    import azure.keyvault.secrets
    # Example: retrieve from Key Vault
    client = azure.keyvault.secrets.SecretClient(...)
    return client.get_secret("mip-wrapper-secret").value

auth = ClientSecretAuth(
    tenant_id="...",
    client_id="...",
    secret_provider=get_client_secret,
)
```

**Parameters:**
- `tenant_id` (str, required): Azure AD tenant ID
- `client_id` (str, required): Registered application client ID
- `secret_provider` (Callable[[], str], optional): Function that returns client secret. If None, assume interactive auth.

**Behavior:**
- Secret is acquired via callback and used by .NET helper
- Secret is never logged or passed as an argument
- Documented as less secure than certificate authentication
- Appropriate for development and testing only

**Documentation Note:**
> Client secret authentication is less secure than certificate-based authentication and is not recommended for production services. Prefer CertificateAuth. If you must use ClientSecretAuth, ensure the secret is stored in Azure Key Vault or a secure secret manager, not in plaintext configuration files or environment variables.

---

## Client and Configuration

### MipClient

```python
from mip_wrapper import MipClient

client = MipClient(
    auth=auth,
    authorization_mode="delegated_reader",
    delegated_user="integration-user@company.com",
    correlation_id=None,  # Optional; auto-generated if not provided
    timeout_seconds=30,
)
```

**Parameters:**
- `auth` (CertificateAuth | ClientSecretAuth, required): Authentication configuration
- `authorization_mode` (str, required): `"delegated_reader"` or `"super_user"`
- `delegated_user` (str, optional): User UPN for delegated_reader mode (required if mode is delegated_reader)
- `correlation_id` (str, optional): Correlation ID for audit/logging (UUID format recommended)
- `timeout_seconds` (int, optional): Default timeout for operations (default 30)

**Exceptions:**
- `InvalidConfigurationError` if required parameters are missing or invalid

---

### Authorization Modes

#### Delegated Reader

```python
client = MipClient(
    auth=auth,
    authorization_mode="delegated_reader",
    delegated_user="alice@company.com",
)
```

**Semantics:**
- Application uses `Content.DelegatedReader` permission
- Operations are performed on behalf of the delegated user
- Document usage rights are checked per-file
- User must have Export or Owner right to decrypt

**Documentation:**
- Required Azure AD application permission: `Content.DelegatedReader`
- Tenant admin must grant this permission (admin consent required)
- Each file is decrypted on behalf of `delegated_user`
- `delegated_user` must have the appropriate usage rights for each file
- If `delegated_user` lacks Export right, PermissionDeniedError is raised

---

#### Super-User (Privileged)

```python
client = MipClient(
    auth=auth,
    authorization_mode="super_user",
    acknowledge_tenant_wide_access=True,
)
```

**Parameters:**
- `acknowledge_tenant_wide_access` (bool, required): Must be explicitly `True`

**Semantics:**
- Application uses elevated `Content.SuperUser` permission
- All MIP-protected files in the tenant may be decrypted
- Document usage rights are NOT checked (super-user bypass)
- Intended for compliance and audit scenarios

**Behavior:**
- Fails fast if `acknowledge_tenant_wide_access` is not True
- Error message explains that super-user may decrypt all tenant files
- Never selected as automatic fallback from delegated mode
- Requires explicit tenant admin configuration (not automatic)

**Documentation:**
- Requires Azure AD application permission: `Content.SuperUser`
- Tenant admin must explicitly enable this permission
- Super-user should be used only for legitimate compliance/audit scenarios
- All super-user operations are logged by the MIP SDK
- **Warning:** This mode bypasses document usage-right checks and may allow decryption of all tenant-protected files

---

## Core Operations

### Inspect File

```python
info = client.inspect("protected.xlsx")
```

**Return Type:** `FileInfo`

**Fields:**
- `is_protected` (bool): Whether file is MIP-protected
- `label_id` (str | None): Sensitivity label ID (if available)
- `tenant_id` (str | None): Tenant ID where file is protected
- `file_format` (str): File extension (.xlsx, .pdf, etc.)
- `protection_type` (str): "azure_rms", "ad_rms", "generic", or "none"
- `usage_rights` (list[str]): Available usage rights for current user (e.g., ["Edit", "Export"])
- `can_decrypt` (bool): Whether the current configuration appears capable of decrypting this file
- `sdk_version` (str): MIP SDK version (e.g., "1.18.124")
- `helper_version` (str): Native helper version

**Exceptions:**
- `DecryptionError` if file cannot be accessed or is corrupted
- `UnsupportedFileTypeError` if format is not supported
- `NativeRuntimeError` if helper fails

**Note:**
Inspection may require a network request to acquire the publishing licence if it's not embedded in the file. Decryption without the correct usage rights will fail with PermissionDeniedError.

---

### Temporary Decryption (Context Manager)

```python
with client.decrypted_file("protected.xlsx") as artifact:
    print(artifact.path)
    # artifact.path is a Path object pointing to the unprotected file
    # File is in a private temp directory
    
    # Safe to use with openpyxl, pandas, etc.
    import openpyxl
    wb = openpyxl.load_workbook(artifact.path)
    # ... process ...

# Temp file is automatically deleted after the context exits
```

**Return Type:** Context manager yielding `DecryptedFile`

**DecryptedFile Fields:**
- `path` (pathlib.Path): Path to the decrypted file in a temporary directory
- `filename` (str): Original filename (from protected file metadata or inferred)
- `file_format` (str): File extension (.xlsx, .pdf, etc.)
- `size_bytes` (int | None): Size of decrypted file
- `decryption_timestamp` (datetime): When decryption completed
- `audit_metadata` (dict[str, str]): Safe metadata for audit/logging

**Behavior:**
- Creates a private temporary directory (0o700 permissions, owner-only)
- Decrypts into that directory
- Checks that the user has the Export (or Owner) usage right
- Raises PermissionDeniedError if rights are insufficient
- Yields the artifact to the caller
- Automatically deletes temporary directory after context exits (even on exception)

**Exceptions:**
- `PermissionDeniedError` if user lacks Export right
- `DecryptionError` if decryption fails
- `NativeRuntimeError` if helper fails
- `CleanupError` if temp files cannot be deleted (raised after the operation completes)

**Example:**

```python
try:
    with client.decrypted_file("protected.xlsx") as artifact:
        import openpyxl
        wb = openpyxl.load_workbook(artifact.path)
        print(f"Sheet names: {wb.sheetnames}")
except PermissionDeniedError:
    print("User does not have permission to decrypt this file")
except CleanupError as e:
    print(f"File was decrypted but cleanup failed: {e}")
    print(f"Temp path: {e.temp_path} (manually delete later)")
```

---

### Explicit Decryption (Persistent Output)

```python
result = client.decrypt(
    source="protected.xlsx",
    output="decrypted.xlsx",
    overwrite=False,
    cleanup=True,
    allow_unprotected_output=True,
)
```

**Parameters:**
- `source` (str | Path, required): Path to protected file
- `output` (str | Path, required): Path where decrypted output will be written
- `overwrite` (bool, optional): If False (default), fail if output already exists
- `cleanup` (bool, optional): If True (default), delete source file after successful decryption
- `allow_unprotected_output` (bool, optional): Must be explicitly `True` to create unprotected output

**Return Type:** `DecryptionResult`

**DecryptionResult Fields:**
- `output_path` (Path): Path to decrypted file
- `size_bytes` (int): Size of decrypted output
- `audit_metadata` (dict[str, str]): Safe metadata

**Behavior:**
- Validates input and output paths (no traversal)
- Checks source and output are different files
- Fails if output exists and `overwrite=False`
- Fails if `allow_unprotected_output` is not True
- Decrypts to the output path
- Does NOT delete temp files by default (caller owns the output)
- If `cleanup=True`, deletes the source file after successful decryption
- Returns structured result with metadata

**Exceptions:**
- `InvalidConfigurationError` if `allow_unprotected_output` is False or missing
- `PermissionDeniedError` if user lacks Export right
- `DecryptionError` if decryption fails
- `NativeRuntimeError` if helper fails

**Example:**

```python
result = client.decrypt(
    source="protected.xlsx",
    output="decrypted.xlsx",
    cleanup=False,  # Keep the protected source file
    allow_unprotected_output=True,
)
print(f"Decrypted to: {result.output_path}")
print(f"Size: {result.size_bytes} bytes")
```

---

### Decrypt to Bytes (Deferred to v0.3+)

**Status:** Not implemented in v0.1-v0.2.

Returning decrypted content over the JSON protocol would require:
- Base64 encoding (overhead)
- Memory buffer in Python process (erasure limitations)
- Proper IPC design for large files

This API will be designed and implemented separately after core decryption is stable and security-reviewed.

---

## Logging and Observability

### Configuring Logging

MIP Wrapper uses Python's standard `logging` module. Do NOT configure logging automatically.

```python
import logging

logger = logging.getLogger("mip_wrapper")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logger.addHandler(handler)
```

**Log Levels:**
- `DEBUG`: Detailed operational information (helper communication, paths)
- `INFO`: Significant operational events (inspect, decrypt started)
- `WARNING`: Concerning but recoverable conditions (cleanup failures)
- `ERROR`: Error conditions (permission denied, protocol error)

**Sensitive Field Redaction:**
- File paths may be shortened (show hash instead of full path in some contexts)
- Certificate paths are never logged
- Access tokens are never logged
- Publishing licences are never logged
- Decrypted file content is never logged

---

## Audit Metadata

Every result object includes `audit_metadata`:

```python
with client.decrypted_file("protected.xlsx") as artifact:
    print(artifact.audit_metadata)
```

**Safe Audit Fields:**
- `correlation_id` (str): Correlation ID for tracing
- `source_reference` (str): Safe reference to source (filename or hash)
- `destination_reference` (str | None): Safe reference to destination
- `label_id` (str | None): Sensitivity label ID
- `tenant_id` (str | None): Tenant ID
- `authorization_mode` (str): "delegated_reader" or "super_user"
- `file_format` (str): Original file extension
- `bytes_written` (int): Size of decrypted output
- `decryption_timestamp` (datetime): When operation completed
- `helper_version` (str): Native helper version
- `sdk_version` (str): MIP SDK version
- `package_version` (str): MIP Wrapper version
- `cleanup_completed` (bool): Whether temp cleanup succeeded

**Sensitive Fields NOT Included:**
- Access tokens
- Certificate passwords
- Publishing licence material
- Decrypted content
- Full file paths (use hash or reference instead)

---

## Version 1 Scope Limitations

The following are NOT supported in v1:

- **Source adapters** - Only local file paths; no SharePoint, ADLS, or Blob Storage as input
- **Azure destinations** - No automatic upload to ADLS or Blob Storage (v2+)
- **Pipeline API** - No processor callback support (v2+)
- **Double Key Encryption** - Not supported until officially validated
- **HYOK scenarios** - On-premises RMS without modern features
- **Password-protected Office files** - Separate from MIP protection
- **Username/password authentication** - Not supported
- **Interactive/device-code auth** - Not supported
- **Token provider authentication** - Not supported (defer to v2 with threat modeling)

---

## Example: Complete Delegated-Reader Flow

```python
from mip_wrapper import MipClient
from mip_wrapper.auth import CertificateAuth

# 1. Get certificate password from secure storage
def get_password():
    import keyring
    return keyring.get_password("mipwrapper", "cert")

# 2. Configure authentication
auth = CertificateAuth(
    tenant_id="tenant-uuid",
    client_id="app-uuid",
    certificate_path="/secure/cert.pfx",
    certificate_password_provider=get_password,
)

# 3. Create client with delegated-reader mode
client = MipClient(
    auth=auth,
    authorization_mode="delegated_reader",
    delegated_user="integration-user@company.com",
    correlation_id="job-12345",
)

# 4. Inspect file
info = client.inspect("protected.xlsx")
if info.is_protected and "Export" in info.usage_rights:
    print(f"File is protected with label {info.label_id}")
    
    # 5. Decrypt temporarily
    try:
        with client.decrypted_file("protected.xlsx") as artifact:
            import openpyxl
            wb = openpyxl.load_workbook(artifact.path)
            for row in wb.active.iter_rows():
                print([cell.value for cell in row])
    except PermissionDeniedError:
        print("User lacks Export right")
```

---

## Future Versions

Anticipated v2+ features (NOT in v1):

- `client.run_pipeline(source, processor, destination, ...)`
- DataLake and Blob destination adapters
- SharePoint source adapter
- Managed Identity authentication
- Token provider authentication (after threat modeling)
- Interactive authentication (for local development)
- Certificate path validation (filesystem security)
- Azure Key Vault integration
- Certificate rotation support
- Double Key Encryption support (when validated)
