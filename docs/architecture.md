# MIP Wrapper Architecture

## Overview

MIP Wrapper is a security-first Python package that provides a clean, typed interface for inspecting and decrypting files protected by Microsoft Purview Information Protection (Azure Rights Management).

The package uses a process-bridge architecture:

```
┌────────────────────────────────────────────────────────────┐
│  Python Application                                        │
│  ├── mip_wrapper.MipClient                               │
│  ├── mip_wrapper.auth (authentication config)            │
│  └── mip_wrapper.destinations (optional Azure upload)    │
└────────────────────────────┬───────────────────────────────┘
                             │ JSON over stdin/stdout
                             │
┌────────────────────────────▼───────────────────────────────┐
│  MipWrapper.Helper (.NET process bridge)                   │
│  ├── Protocol handler (versioned JSON)                    │
│  ├── Authentication (MSAL, certificate OAuth2)           │
│  ├── Protection profile and engine                        │
│  └── File protection operations                           │
└────────────────────────────┬───────────────────────────────┘
                             │ Imports
                             │
┌────────────────────────────▼───────────────────────────────┐
│  Official Microsoft MIP SDK (.NET)                         │
│  NuGet Package: Microsoft.InformationProtection.File      │
│  (version 1.18.124 or later)                             │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────┐
│  Official Microsoft MIP Native SDK (C++)                   │
│  ├── Windows DLLs / Linux .so / macOS .dylib             │
│  └── Azure Rights Management Service                      │
└────────────────────────────────────────────────────────────┘
```

## Trust Boundaries

### Separate Processes, Shared Deployment
The Python application and MIP Wrapper.Helper run in **separate OS processes** within the **same trusted compute boundary** (container, VM, CI job).

- No network-based decryption service
- File decryption happens in user-controlled compute (container job, function, VM, CI environment)
- Python process and .NET helper process are separate with isolated memory and lifecycle
- They share a deployment boundary (same container/VM) but have distinct process-level isolation
- IPC between processes uses stdin/stdout with JSON protocol (not network sockets)
- Each process has its own memory, crash behavior, and security constraints
- Certificate and token material does not cross process boundaries in plaintext

### Supported Execution Environments
- Azure Container Apps Jobs
- Azure Functions (where the .NET runtime is available)
- Kubernetes jobs
- Virtual machines
- Local development machines
- CI/batch processing environments

### Unsupported Execution Patterns
- Network-accessible decryption API (do not implement)
- Third-party decryption services
- Remote procedure calls to external MIP handlers

## Component Responsibilities

### Python Layer (`mip_wrapper`)

**Responsibilities:**
- Provide a clean, typed Python API
- Manage authentication configuration (non-secret parts)
- Validate user inputs (paths, parameters)
- Spawn and manage the .NET helper process
- Serialize requests to the helper using the versioned protocol
- Deserialize and interpret responses
- Manage temporary files and cleanup
- Implement context managers for safe resource management
- Enforce permissions checking before allowing unprotected output
- Redact sensitive values from exceptions and logs
- Interface with Azure destinations (optional)
- Provide structured audit metadata

**Does NOT:**
- Acquire access tokens (delegated to .NET helper)
- Directly access the MIP SDK
- Store or manipulate certificate passwords
- Log raw tokens, licences, or decrypted content

### MipWrapper.Helper (.NET)

**Responsibilities:**
- Initialize the official Microsoft MIP SDK
- Implement the `IAuthDelegate` interface
- Acquire OAuth2 tokens using MSAL
- Create MipContext, FileProfile, and FileEngine
- Respond to token-acquisition requests from the MIP SDK
- Apply delegated-user configuration where requested
- Inspect file protection metadata
- Check application permissions and document usage rights
- Decrypt protected files only when authorized
- Write output to explicitly supplied secure paths
- Return structured results (metadata, errors)
- Dispose SDK resources cleanly
- Report protocol version and SDK versions

**Does NOT:**
- Log sensitive licence material
- Return decrypted content via stdout/stderr
- Upload files
- Modify tenant permissions
- Implement business logic or transformations
- Serve HTTP endpoints

### Official Microsoft MIP SDK

The Python wrapper is built entirely on top of the official Microsoft Information Protection SDK:

- **NuGet Package:** `Microsoft.InformationProtection.File` (1.18.124)
- **Platform Support:** Windows, Ubuntu 20.04/22.04/24.04, RHEL/CentOS, macOS
- **Language:** C++ native SDK with official .NET managed wrapper (NuGet)
- **Authentication:** OAuth2 delegate pattern via MSAL
- **Protection:** Azure Rights Management (RMS) decryption

MIP Wrapper does not reimplement, reverse-engineer or reproduce any RMS functionality.

## Runtime and Helper Distribution (v0.1: Private Container)

**v0.1 Scope:** Internal private proof-of-concept only. Not for public distribution.

### MVP Model for Stage 2

A single private container image containing:
- Python 3.11+
- .NET 6.0+ Runtime
- MIP Wrapper Python package (`mip_wrapper`)
- Compiled `MipWrapper.Helper` (.NET executable)
- Microsoft MIP SDK (from NuGet restore during build)

**Target Runtime:** Azure Container Apps Job

**Execution:**
```bash
# User deploys the private container to their Azure subscription
az containerapp job create \
  --image <private-registry>/mip-wrapper:v0.1 \
  --environment <container-apps-environment>
```

**Container Contents:**
- `/app/mip_wrapper/` – Python package
- `/app/MipWrapper.Helper` – .NET helper executable
- All dependencies obtained via NuGet during Docker build

**Certificate and Password Handling:**
- Supplied via mounted volume or environment-mounted secrets
- Paths passed as configuration to the container
- Helper reads directly from mounted paths
- Never embedded in container image

**What This Design Provides:**
- Complete self-contained proof-of-concept
- No public API or distribution
- All dependencies resolved at build time
- Simple deployment (single container image)
- Clear separation from public release decisions

### Future Distribution Models (Post-IPIA)

After Microsoft clarifies IPIA and binary-redistribution requirements:

**Option 1: Public PyPI + Helper Package**
- Python package on PyPI (`mip-wrapper`)
- Separate helper package or binary
- Requires IPIA approval

**Option 2: Public Container Image**
- Container in public registry (GitHub, Docker Hub)
- Complete with all dependencies
- Requires IPIA approval for binary redistribution

**Option 3: Other Approach**
- Based on Microsoft's specific requirements

**Current Decision:** v0.1 uses private container. Final distribution model is deferred until IPIA clarification.

## Authentication Ownership

Authentication responsibility is split between Python and .NET helper:

### Python Layer Provides
- Tenant ID
- Client ID (app registration)
- Path to certificate file (or reference to secret provider)
- Selected authorization mode (`delegated_reader` or `super_user`)
- Delegated user UPN (for delegated-reader mode)
- Correlation ID (for audit and logging)
- Timeout settings

### .NET Helper Owns
- Loading the certificate (from the supplied path)
- Acquiring the certificate password (from the supplied password provider callback)
- Constructing MSAL confidential client with certificate credentials
- Acquiring and refreshing OAuth2 tokens
- Responding to MIP SDK token acquisition requests
- Using supplied tokens with the correct authority, resource, and scopes

### Certificate Password Delivery (v0.1: File-Based)

**Challenge:** Certificate password must not appear in command-line arguments, JSON protocol, logs, environment variables, or crash dumps. Python and helper are separate processes.

**v0.1 Model:**

Certificate and password are supplied as separate files at runtime. Container mounts them as read-only volumes.

```
Runtime Configuration:
  Certificate file:  /mnt/secrets/cert.pfx (read-only, 0o600)
  Password file:     /mnt/secrets/cert.password (read-only, 0o600)

Container startup:
  1. Container receives mounted volume with certificate and password files
  2. Python reads paths from configuration (e.g., env vars, config file)
  3. Python validates file existence and basic permissions
  4. Python passes paths to helper via JSON protocol
  5. Helper reads password file directly (not from Python)
  6. Helper loads certificate using the password from file
  7. Password is cleared from memory after certificate loads
  8. Python and helper never retain unnecessary copies

Logging:
  - Paths may be logged (non-sensitive)
  - Passwords are never logged
  - Certificate material is never logged
```

**Constraints for v0.1:**
- Certificate file must not be built into container image (mounted only)
- Password file must not be built into container image (mounted only)
- Files are NOT deleted by the package (platform/deployment owns them)
- Filesystem permissions are enforced by the OS (0o600 = owner-read-only)
- Works for containerized environments (Azure Container Apps, AKS)
- Works for local development with protected directories

**Deployment Responsibility:**
- Azure deployments: Use Azure Key Vault with container identity
- CI/CD: Use secret-injection from CI/CD platform
- Local development: Use protected directories with appropriate permissions
- This is the **deployment platform's responsibility**, not the package's

**Future Enhancements (Deferred to v1.5+):**
- Azure Key Vault integration (helper retrieves certificate/password via Managed Identity)
- OS certificate store (Windows DPAPI, Linux certificate managers)
- Bidirectional IPC callback for secrets (requires detailed threat modeling)

**This approach:**
- ✅ Prevents password leakage in arguments, JSON, logs, env vars
- ✅ Works with standard container orchestration (ACI, AKS)
- ✅ Aligns with industry-standard secret provisioning (mounted volumes)
- ✅ Simple to understand and audit
- ✅ Does NOT require cross-process callbacks or complex IPC

## File Protection Operations

### Inspection

```
Input: source_path
↓
.NET Helper:
  ├── Open file (check format)
  ├── Query MIP SDK for protection metadata
  ├── Extract: label ID, tenant ID, protection type, file format
  ├── Check application permissions
  ├── Determine if decryption is feasible
  └── Return structured metadata
↓
Output: FileInfo object
  (safe metadata, no tokens or content keys)
```

### Temporary Decryption (with context manager)

```
Input: source_path
↓
Python Layer:
  ├── Create unique private temp directory (/tmp/mipwrapper_XXXXXX)
  ├── Apply restrictive permissions (0o700, owner-only)
  └── Pass to .NET Helper
       ↓
       .NET Helper:
         ├── Acquire publishing licence from protected file
         ├── Check Export (or Owner) usage right
         ├── Decrypt using official MIP SDK
         ├── Write only to supplied temp path
         └── Return success or error
       ↓
Python Layer:
  ├── Yield temp file artifact to caller
  └── (caller uses openpyxl, pandas, etc.)
       ↓
       (caller finishes or raises exception)
       ↓
Python Layer:
  ├── finally block: delete temp directory
  └── Return or re-raise exception
↓
Output: Decrypted file in temp location, cleaned after context exit
```

### Explicit Decryption (persistent output)

```
Input: source_path, output_path, allow_unprotected_output=True
↓
Python Layer:
  ├── Validate input and output paths (no traversal)
  ├── Check allow_unprotected_output (fail if False)
  └── Pass to .NET Helper
       ↓
       .NET Helper:
         ├── Check usage rights (Export or Owner)
         ├── Decrypt
         ├── Write to output_path
         └── Return success or error
       ↓
Python Layer:
  └── Return result (no cleanup unless caller requests it)
↓
Output: Decrypted file at caller's specified location
```

## Cleanup Model

### Automatic Cleanup (Default)
Temporary files created by the package are automatically removed:

- Temporary decrypted files (context manager exit)
- Temporary processing output (after upload or error)
- Cleanup runs after success
- Cleanup runs after failure
- Cleanup failure does NOT hide the original exception

### Manual Cleanup Control
Caller can request cleanup=False for explicit decryption:

```python
result = client.decrypt(source, output, cleanup=False)
# Caller owns the output file; it is not deleted
```

### Safe Cleanup Practices
- Do NOT follow symbolic links (prevent escape)
- Do NOT traverse parent directories (prevent traversal)
- Only delete files/directories that the package created
- Verify ownership before deletion
- Never delete caller-provided files
- Report cleanup failures in audit metadata

### Not Guaranteed Erasure
Deletion from filesystem does not guarantee forensic erasure. Document:

- Modern filesystems may journal deletes
- SSDs may retain data in wear-leveling areas
- Cloud storage may retain deleted objects temporarily
- Python cannot guarantee all in-memory copies are overwritten

Use appropriate threat model for your data classification.

## Authorization and Usage Rights

### Concepts
- **Authentication** proves *who* is calling
- **Application Permissions** define *what* the application may request from MIP services
- **Document Usage Rights** define *what* the user may do with a specific protected file

These are separate and must not be confused.

### Example
A service principal might have:
- Authentication: Valid certificate and OAuth2 token (proven)
- Application Permission: `Content.DelegatedReader` (allowed to consume on behalf of a user)
- Document Right: MISSING Export right (user cannot decrypt *this* file)

Result: **Deny access** to decrypt. Don't upgrade to super-user or bypass the right.

### Required Rights

**To Decrypt and Decrypt to Bytes:**
- Export usage right (or Owner)
- Checked by: MIP SDK's `ProtectionHandler->AccessCheck(rights::Export())`

**To Remove Protection from a File:**
- Export usage right (or Owner)
- Checked before writing unprotected output

**To Use Application Super-User Mode:**
- Tenant admin must configure `Content.SuperUser` permission
- Application must use correct authority/resource/scopes
- Must be explicitly enabled in package (not default)
- Must be explicitly acknowledged by the caller

### Permission-Denied Behavior
If the user lacks required rights:

```python
raise PermissionDeniedError(
    "User lacks Export right for this file. "
    "Only users with Export or Owner rights can decrypt."
)
```

Do not:
- Retry with different permissions
- Remove protection without the right
- Upload partial plaintext
- Fall back to super-user mode
- Hide the denial behind a generic exception

## Versioned Helper Protocol

Communication between Python and the .NET helper uses a versioned JSON protocol over stdin/stdout.

### Protocol Version
Current: `1.0`

Every request includes `protocol_version: "1.0"`.
Every response includes `protocol_version: "1.0"`.

Future changes increment the version. Mismatched versions are rejected.

### Request Format

```json
{
  "protocol_version": "1.0",
  "request_id": "correlation-id",
  "command": "inspect|decrypt|decrypt_bytes|shutdown",
  "tenant_id": "...",
  "client_id": "...",
  "certificate_path": "...",
  "authorization_mode": "delegated_reader|super_user",
  "delegated_user": "user@example.com (if delegated_reader)",
  "source_path": "/path/to/protected.xlsx",
  "output_path": "/path/to/temp/output.xlsx (if decrypt)",
  "max_size_mb": 100 (if decrypt_bytes),
  "timeout_seconds": 30
}
```

Sensitive fields (tokens, passwords, secret values) are NOT passed as command-line arguments or JSON fields.

### Response Format

```json
{
  "protocol_version": "1.0",
  "request_id": "correlation-id",
  "success": true,
  "result": {
    "is_protected": true,
    "label_id": "uuid",
    "tenant_id": "uuid",
    "file_format": "xlsx",
    "protection_type": "azure_rms",
    "usage_rights": ["Edit", "Export", "Print"],
    "can_decrypt": true,
    "sdk_version": "1.18.124",
    "helper_version": "1.0.0"
  }
}
```

Or on error:

```json
{
  "protocol_version": "1.0",
  "request_id": "correlation-id",
  "success": false,
  "error": {
    "code": "PermissionDenied|UnsupportedFormat|UnexpectedError",
    "message": "User lacks Export right",
    "details": "..."
  }
}
```

### Command Reference

- `inspect` - Inspect file protection metadata
- `decrypt` - Decrypt to a file at supplied path
- `decrypt_bytes` - Decrypt entire file into memory (with size limit)
- `shutdown` - Clean shutdown of helper process

## Supported Platforms (Version 1)

### Windows
- Windows 10 / Windows 11 / Windows Server 2016, 2019, 2022
- x64 architecture
- Requires: .NET Runtime 5.0+ OR .NET Framework 4.8+
- Requires: Visual C++ 2022 Runtime

### Linux
- Ubuntu 20.04 LTS, Ubuntu 22.04 LTS, Ubuntu 24.04 LTS
- x64 architecture
- Requires: .NET Runtime 5.0+
- Requires: curl, libsecret, OpenSSL, UUID

### macOS
- Supported versions (Intel or Apple Silicon via x64 emulation)
- Requires: .NET Runtime 5.0+

## Out of Scope for Version 1

- C++ pybind11 extension (implement in later version if needed)
- Standalone application (build on top of this library)
- SharePoint downloading (local files only)
- Double Key Encryption (until officially supported and tested)
- HYOK (hybrid on-premises) scenarios
- Username/password authentication
- Hardcoded credentials
- Password-protected Office files (separate from MIP protection)
- Reimplementation of Azure RMS encryption
- Hosted decryption API

## Version 1 Success Criteria

The first implementation milestone is complete when:

1. A protected test Excel file can be decrypted using certificate-based authentication
2. Delegated-reader authorization mode works correctly
3. The delegated user has the required document usage rights
4. The decrypted file exists only inside a private temporary directory
5. The decrypted file can be opened by standard libraries (openpyxl)
6. The temporary file is removed after the context exits
7. Cleanup also occurs when the library (openpyxl) raises an exception
8. An unauthorized identity receives a typed PermissionDeniedError
9. Missing Export or equivalent rights produce a typed PermissionDeniedError
10. No token, secret, certificate password or decrypted content appears in logs
11. Unit tests pass
12. One opt-in integration test passes against a dedicated test tenant
13. Architecture, threat model and documentation accurately describe the implementation
