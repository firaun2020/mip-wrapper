# MIP Wrapper

Unofficial Python wrapper for Microsoft Information Protection (MIP) file decryption and inspection.

**Status:** Alpha (v0.1.0) – Internal development use only

```python
from mip_wrapper import MipClient
from mip_wrapper.auth import CertificateAuth

# Configure authentication
auth = CertificateAuth(
    tenant_id="your-tenant-id",
    client_id="your-app-id",
    certificate_path="path/to/certificate.pfx",
    certificate_password_path="path/to/cert.password",
)

# Create client with delegated-reader authorization
client = MipClient(
    auth=auth,
    authorization_mode="delegated_reader",
    delegated_user="service-account@company.com",
)

# Inspect protected file
info = client.inspect("protected.xlsx")
print(f"Protected: {info.is_protected}, Label: {info.label_id}")

# Decrypt temporarily
with client.decrypted_file("protected.xlsx") as artifact:
    # artifact.path points to decrypted file in secure temp location
    import openpyxl
    wb = openpyxl.load_workbook(artifact.path)
    # Process workbook...
    # Temp file is automatically deleted when context exits
```

## What It Does

- **Inspects** Microsoft Purview-protected files to retrieve metadata (label, tenant, format, usage rights)
- **Decrypts** files protected by Azure Rights Management when the user has Export rights
- **Manages** secure temporary files with automatic cleanup
- **Enforces** usage rights before allowing decryption
- **Provides** typed exceptions for clear error handling
- **Works** with Python application code, not as a standalone service

## What It Does NOT Do

- ❌ Reverse-engineer or reimplement Azure RMS encryption
- ❌ Bypass document rights or DRM protections
- ❌ Act as a network-accessible decryption service
- ❌ Store credentials in project configuration
- ❌ Automatically download or manage native binaries
- ❌ Support password-protected Office files (separate from MIP)
- ❌ Support HYOK (hybrid on-premises) scenarios yet
- ❌ Support super-user mode in v0.1 (planned for v1.1+)

## How It Works

```
Your Python Code
    ↓
mip_wrapper (Python package)
    ↓ (JSON protocol)
MipWrapper.Helper (.NET console app)
    ↓
Official Microsoft MIP SDK
    ↓
Azure Rights Management Service
```

The Python package handles configuration, validation, and file operations. The .NET helper bridges to the official Microsoft MIP SDK, which performs actual decryption using Azure Rights Management.

## Installation

```bash
# Development installation
pip install -e .

# Build the .NET helper
cd native/MipWrapper.Helper
dotnet publish -c Release -o ../../helper-bin
cd ../..

# Make helper discoverable
export MIP_WRAPPER_HELPER_PATH=$(pwd)/helper-bin/MipWrapper.Helper
# On Windows: set MIP_WRAPPER_HELPER_PATH=%cd%\helper-bin\MipWrapper.Helper
```

## Helper Discovery

The Python package locates the .NET helper using this search order:

1. **Explicit `helper_path` parameter** to `MipClient(...)`
2. **`MIP_WRAPPER_HELPER_PATH` environment variable**
3. **Current directory** or `helper-bin/` subdirectory
4. **Package installation location** (future: when bundled)

If the helper is not found, a `MissingRuntimeError` provides clear setup instructions.

## Authentication

### Certificate-Based (Recommended)

```python
from mip_wrapper.auth import CertificateAuth

auth = CertificateAuth(
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="11111111-1111-1111-1111-111111111111",
    certificate_path="/secure/cert.pfx",
    certificate_password_path="/secure/cert.password",
)
```

Certificates must be stored securely:
- **File permissions:** 0o600 (owner-read-only)
- **Not in version control:** Add to `.gitignore`
- **Not in container images:** Mount at runtime

### Client Secret (Less Secure)

```python
from mip_wrapper.auth import ClientSecretAuth

def get_secret():
    return os.environ.get("CLIENT_SECRET")

auth = ClientSecretAuth(
    tenant_id="...",
    client_id="...",
    secret_provider=get_secret,
)
```

Document recommends certificate authentication for production.

## Authorization Modes

### Delegated Reader (Default)

```python
client = MipClient(
    auth=auth,
    authorization_mode="delegated_reader",
    delegated_user="alice@company.com",
)
```

Decrypts files on behalf of the delegated user. The user must have Export rights to each file.

**Requires:**
- Azure AD app permission: `Content.DelegatedReader`
- Delegated user's usage rights on specific files

## Core API

### Inspect Files

```python
info = client.inspect("protected.xlsx")
# Returns: FileInfo with metadata (label, format, rights, etc.)
```

### Temporary Decryption

```python
with client.decrypted_file("protected.xlsx") as artifact:
    print(artifact.path)  # pathlib.Path to decrypted file
    # Use with openpyxl, pandas, etc.
    # Automatic cleanup when context exits
```

Raises:
- `PermissionDeniedError` – user lacks Export right
- `UnsupportedFileTypeError` – unsupported format
- `UnsupportedProtectionError` – unsupported protection type

### Explicit Decryption

```python
result = client.decrypt(
    source="protected.xlsx",
    output="decrypted.xlsx",
    allow_unprotected_output=True,
)
```

Requires explicit acknowledgement that output is unprotected.

## Exceptions

```python
from mip_wrapper import (
    MipError,
    AuthenticationError,
    PermissionDeniedError,
    UnsupportedProtectionError,
    UnsupportedFileTypeError,
    InvalidConfigurationError,
    MissingRuntimeError,
)
```

All exceptions are typed and include:
- `message` – Human-readable description
- `error_code` – Machine-readable identifier
- `audit_metadata` – Safe contextual information

## Testing

### Unit Tests (No Tenant Required)

```bash
pip install pytest
pytest tests/unit/ -v
```

23+ unit tests mock the .NET helper and don't require:
- Azure credentials
- Real certificates
- Real protected files

### Integration Tests (Tenant Required)

See `INTEGRATION_TESTS.md` (not yet available in v0.1).

Integration tests run against a real Azure tenant with:
- MIP protection enabled
- Test protected Excel file
- App registration with certificate
- Appropriate Azure AD permissions

## Version Compatibility

The package validates:
- **Python version** – 3.11+
- **Protocol version** – v1.0 (between Python and helper)
- **Helper version** – 1.0.0+ (semantic versioning)

Version mismatches raise `InvalidConfigurationError` with clear remediation steps.

## Project Status

**v0.1.0 (Internal Alpha)**
- ✅ Certificate authentication
- ✅ Delegated-reader mode
- ✅ File inspection
- ✅ Temporary decryption with automatic cleanup
- ✅ Typed exceptions
- ✅ Unit tests

**v0.2.0 (Planned)**
- Hardened error handling
- Redacted logging
- Extended test coverage
- Documentation updates

**v0.3.0 (Planned)**
- Azure Data Lake destination support
- Blob Storage destination support
- Processing pipeline API

**v1.0.0 (Planned)**
- After Microsoft confirms IPIA and redistribution requirements
- Possible binary bundling in wheels
- Stable public API

## Platform Support

**Tested:**
- Python 3.11+ on Windows and Linux
- .NET 6.0 SDK

**Untested:**
- macOS (architecture in place, needs testing)
- Python 3.10 or older (may work, not officially supported)

## Legal and Licensing

**This is an unofficial community project**, not developed, maintained, or endorsed by Microsoft.

- **MIP Wrapper license:** MIT
- **Microsoft MIP SDK:** Licensed by Microsoft under their terms
- **Public distribution:** Requires Information Protection Integration Agreement (IPIA) with Microsoft

See `docs/distribution-and-licensing.md` for details.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) – Design and component responsibilities
- [`docs/threat-model.md`](docs/threat-model.md) – Security analysis
- [`docs/helper-protocol.md`](docs/helper-protocol.md) – JSON protocol v1.0
- [`BUILD_LOCALLY.md`](BUILD_LOCALLY.md) – Development setup

## Getting Help

- **Setup issues:** Check `BUILD_LOCALLY.md` and ensure helper is built
- **Authentication:** Verify certificate path and permissions
- **Decryption errors:** Confirm user has Export rights in Azure AD
- **Missing helper:** Set `MIP_WRAPPER_HELPER_PATH` or build with `dotnet publish`

## Contributing

This is an internal development project. Public contributions will be considered after v1.0 release.

## License

MIT – See LICENSE file

---

**⚠️ Important:** This is a community wrapper around the official Microsoft MIP SDK. Microsoft provides the actual file protection and decryption. Verify all cryptographic and legal requirements with Microsoft directly.
