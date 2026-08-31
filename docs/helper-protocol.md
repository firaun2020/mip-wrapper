# MIP Wrapper Helper Protocol (v1.0)

## Overview

The Python layer communicates with the .NET MipWrapper.Helper process using a versioned JSON protocol over stdin/stdout.

**Key Principles:**
- Each request is a JSON object on stdin (newline-terminated)
- Each response is a JSON object on stdout (newline-terminated)
- Protocol version is checked in every request and response
- Sensitive data (tokens, passwords) are NOT passed via JSON
- Stderr is used only for diagnostic output (not parsed)
- Helper process is spawned by Python using subprocess (shell=False)

## Protocol Version

**Current Version:** `1.0`

All requests and responses include `protocol_version: "1.0"`.

If Python receives a response with an unsupported protocol version:
- Raise `ProtocolError`
- Reject the response
- Terminate the helper

If Python sends a request with `protocol_version` different from what the helper expects:
- Helper responds with `error.code: "UnsupportedProtocolVersion"`
- Python raises `ProtocolError`

## Request Format

All requests are sent to helper stdin as a single newline-terminated JSON object:

```json
{
  "protocol_version": "1.0",
  "request_id": "unique-id-for-correlation",
  "command": "inspect|decrypt|decrypt_bytes|shutdown",
  "tenant_id": "...",
  "client_id": "...",
  "certificate_path": "/path/to/certificate.pfx",
  "authorization_mode": "delegated_reader|super_user",
  "delegated_user": "user@company.com",
  "source_path": "/path/to/protected.xlsx",
  "output_path": "/path/to/output.xlsx",
  "max_size_mb": 100,
  "timeout_seconds": 30
}
```

### Common Fields

- **protocol_version** (string, required): Must be "1.0"
- **request_id** (string, required): Unique correlation ID (recommend UUID format)
- **command** (string, required): "inspect", "decrypt", or "shutdown"
- **tenant_id** (string, required): Azure AD tenant ID (GUID or domain)
- **client_id** (string, required): App registration client ID (GUID)
- **certificate_path** (string, required): Absolute path to .pfx certificate file
- **authorization_mode** (string, required): "delegated_reader" or "super_user"
- **timeout_seconds** (integer, optional): Operation timeout (default 30)

### Command-Specific Fields

#### inspect

```json
{
  "protocol_version": "1.0",
  "request_id": "req-001",
  "command": "inspect",
  "tenant_id": "...",
  "client_id": "...",
  "certificate_path": "...",
  "authorization_mode": "delegated_reader",
  "delegated_user": "user@company.com",
  "source_path": "/path/to/protected.xlsx"
}
```

**Result fields:** See response format below

---

#### decrypt

```json
{
  "protocol_version": "1.0",
  "request_id": "req-002",
  "command": "decrypt",
  "tenant_id": "...",
  "client_id": "...",
  "certificate_path": "...",
  "authorization_mode": "delegated_reader",
  "delegated_user": "user@company.com",
  "source_path": "/path/to/protected.xlsx",
  "output_path": "/path/to/output.xlsx"
}
```

**Output behavior:**
- Helper writes decrypted content to `output_path`
- Path is validated by Python first (no traversal)
- Helper must not follow symlinks
- Helper must write ONLY to the specified path
- Helper must create the file only if decryption succeeds

---

#### shutdown

```json
{
  "protocol_version": "1.0",
  "request_id": "req-shutdown",
  "command": "shutdown"
}
```

**Behavior:**
- Helper performs final cleanup
- Helper disposes MIP SDK resources
- Helper exits with code 0
- Response indicates success
- Python uses this to gracefully shutdown the helper

---

## Response Format

All responses are sent to helper stdout as a single newline-terminated JSON object:

### Success Response

```json
{
  "protocol_version": "1.0",
  "request_id": "req-001",
  "success": true,
  "result": {
    "is_protected": true,
    "label_id": "abc123-uuid",
    "tenant_id": "tenant-uuid",
    "file_format": "xlsx",
    "protection_type": "azure_rms",
    "usage_rights": ["Edit", "Export", "Print"],
    "can_decrypt": true,
    "sdk_version": "1.18.124",
    "helper_version": "1.0.0"
  }
}
```

### Error Response

```json
{
  "protocol_version": "1.0",
  "request_id": "req-001",
  "success": false,
  "error": {
    "code": "PermissionDenied|UnsupportedFormat|UnexpectedError",
    "message": "User lacks Export right",
    "details": "Additional context (may be empty)"
  }
}
```

### Response Fields

**Top-level:**
- **protocol_version** (string): "1.0"
- **request_id** (string): Echo of request ID
- **success** (boolean): true if command succeeded, false otherwise

**If success=true:**
- **result** (object): Command-specific result fields

**If success=false:**
- **error** (object):
  - **code** (string): Enumerated error code (see below)
  - **message** (string): Human-readable error message
  - **details** (string): Additional context (may be empty)

---

## Result Field Definitions

### Inspect Result

```json
{
  "is_protected": true,
  "label_id": "abc123",
  "tenant_id": "tenant-uuid",
  "file_format": "xlsx",
  "protection_type": "azure_rms",
  "usage_rights": ["Edit", "Export", "Print"],
  "can_decrypt": true,
  "sdk_version": "1.18.124",
  "helper_version": "1.0.0"
}
```

- **is_protected** (boolean): Whether file is MIP-protected
- **label_id** (string | null): Sensitivity label ID (if available)
- **tenant_id** (string | null): Tenant ID where file is protected (if available)
- **file_format** (string): File extension (.xlsx, .pdf, .docx, etc.)
- **protection_type** (string): "azure_rms", "ad_rms", "generic", or "none"
- **usage_rights** (array of strings): Rights available to the current user for this file
  - Possible values: "Owner", "Edit", "Export", "Print", "Copy", "ForwardDelegated", "ViewRightsData"
- **can_decrypt** (boolean): Whether current configuration can decrypt this file
  - False if user lacks Export right, permissions are insufficient, or file format is unsupported
- **sdk_version** (string): MIP SDK version being used by helper
- **helper_version** (string): Helper binary version

---

### Decrypt Result

```json
{
  "output_path": "/path/to/output.xlsx",
  "size_bytes": 45678,
  "file_format": "xlsx"
}
```

- **output_path** (string): Path where decrypted file was written (same as request input)
- **size_bytes** (integer): Size of decrypted file
- **file_format** (string): File format (.xlsx, .pdf, etc.)

---

## Error Codes

| Code | Meaning | HTTP Analogue | Retry? |
|------|---------|---------------|--------|
| `PermissionDenied` | User lacks required usage right (Export) | 403 Forbidden | No |
| `Unauthorized` | Authentication failed (cert, token, etc.) | 401 Unauthorized | No |
| `UnsupportedFormat` | File format not supported by MIP SDK | 400 Bad Request | No |
| `UnsupportedProtectionType` | Protection type not supported (HYOK, etc.) | 400 Bad Request | No |
| `FileNotFound` | Source file does not exist | 404 Not Found | No |
| `OutputAlreadyExists` | Output file exists (should not happen) | 409 Conflict | No |
| `ConfigurationError` | Missing/invalid tenant_id, client_id, etc. | 400 Bad Request | No |
| `CertificateNotFound` | Certificate file not found | 400 Bad Request | No |
| `CertificateLoadError` | Cannot load certificate (wrong password, etc.) | 400 Bad Request | No |
| `TokenAcquisitionError` | Failed to acquire OAuth2 token | 503 Service Unavailable | Yes |
| `ProtocolError` | JSON parse error, missing fields, etc. | 400 Bad Request | No |
| `DecryptionError` | MIP SDK decryption failed (corrupted file, etc.) | 500 Internal Server Error | No |
| `ProtectionEngineError` | Failed to create/initialize MIP engine | 500 Internal Server Error | No |
| `TimeoutError` | Operation exceeded timeout | 504 Gateway Timeout | Yes |
| `UnexpectedError` | Uncaught exception in helper | 500 Internal Server Error | Yes |

---

## Authentication Challenge Protocol

The .NET helper must respond to token acquisition requests from the MIP SDK using MSAL (Microsoft Authentication Library).

**Token Acquisition Flow:**

1. Helper initializes MipContext with an IAuthDelegate
2. Helper creates FileProfile (which triggers MIP SDK auth delegate calls)
3. MIP SDK calls `AcquireToken()` on the auth delegate
4. Helper acquires OAuth2 token using MSAL with:
   - Tenant ID (from request)
   - Client ID (from request)
   - Certificate (from certificate_path)
   - Authority: `https://login.microsoftonline.com/{tenant_id}`
   - Scope: Determined by MIP SDK token request (e.g., `https://aadrm.com/.default`)

5. Helper returns token to MIP SDK
6. MIP SDK uses token to communicate with RMS service

**Important:**
- Python does NOT handle token acquisition
- Certificate password is requested from Python only once (via callback, not in every request)
- MSAL caching is handled by .NET helper
- Token refresh is handled by MSAL (transparent to Python)

---

## Process Lifecycle

### Startup

Python spawns helper process:

```python
import subprocess

process = subprocess.Popen(
    ["/path/to/MipWrapper.Helper"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
```

Helper initializes:
- Loads configuration
- Initializes MIP SDK (if needed)
- Ready to receive requests

### Operation

1. Python sends request JSON to stdin
2. Python waits for response on stdout
3. Helper processes request
4. Helper sends response JSON to stdout
5. Python parses response
6. Repeat for each operation

### Shutdown

Python sends `shutdown` command:

```json
{
  "protocol_version": "1.0",
  "request_id": "shutdown-001",
  "command": "shutdown"
}
```

Helper responds with success, then:
- Disposes MIP SDK resources
- Clears sensitive data from memory
- Exits with code 0

Python waits for process termination.

---

## Error Handling in Python

### Malformed Response

If helper returns invalid JSON:
1. Python logs error (sanitized)
2. Python raises `ProtocolError`
3. Python terminates helper process
4. Python returns error to caller

### Timeout

If helper does not respond within `timeout_seconds`:
1. Python logs timeout warning
2. Python terminates helper process
3. Python raises `ProtocolError` with "Timeout"
4. Python returns error to caller

### Unexpected Exit

If helper process exits without response:
1. Python reads stderr (if available)
2. Python raises `NativeRuntimeError`
3. If partial output on stdout, attempt to parse (may recover)
4. Otherwise, return error to caller

### Partial Response

If helper crashes mid-response:
1. Incomplete JSON on stdout
2. Python attempts to parse (will fail)
3. Python raises `ProtocolError`
4. Python does not retry

---

## Security Considerations

### No Secrets in JSON

The protocol NEVER includes:
- Plaintext certificate passwords
- Access tokens
- Refresh tokens
- Client secrets
- Publishing licences
- Decrypted content (for decrypt_bytes, use base64 encoding)

### Sensitive Fields

Request fields that are security-relevant:
- `certificate_path` - Not logged; path is validated by Python
- `source_path`, `output_path` - Not logged; validated by Python
- `delegated_user` - Not secret, included in logs for audit

### Logging

Helper must not log:
- Full certificate file content
- Raw tokens or publishing licences
- Decrypted content
- Password material

Helper may log:
- Request/response protocol version
- Command names
- Error codes and messages
- Sanitized paths (hash or filename only)
- Version information

### Response Validation

Python must validate all responses:
- Parse JSON (fail on malformed JSON)
- Check protocol version matches
- Verify required fields present
- Type-check numeric and boolean fields
- Reject unknown error codes
- Redact sensitive content from errors before returning to caller

---

## Example Exchange: Inspect

**Request:**

```json
{
  "protocol_version": "1.0",
  "request_id": "req-abc123",
  "command": "inspect",
  "tenant_id": "contoso-tenant-uuid",
  "client_id": "myapp-client-id",
  "certificate_path": "/secure/cert.pfx",
  "authorization_mode": "delegated_reader",
  "delegated_user": "alice@contoso.com",
  "source_path": "/data/protected.xlsx",
  "timeout_seconds": 30
}
```

**Response (Success):**

```json
{
  "protocol_version": "1.0",
  "request_id": "req-abc123",
  "success": true,
  "result": {
    "is_protected": true,
    "label_id": "e8eb5f13-fcf0-4b8f-a8c5-abc1234567890",
    "tenant_id": "contoso-tenant-uuid",
    "file_format": "xlsx",
    "protection_type": "azure_rms",
    "usage_rights": ["Edit", "Export", "Print"],
    "can_decrypt": true,
    "sdk_version": "1.18.124",
    "helper_version": "1.0.0"
  }
}
```

---

## Example Exchange: Decrypt (Permission Denied)

**Request:**

```json
{
  "protocol_version": "1.0",
  "request_id": "req-def456",
  "command": "decrypt",
  "tenant_id": "contoso-tenant-uuid",
  "client_id": "myapp-client-id",
  "certificate_path": "/secure/cert.pfx",
  "authorization_mode": "delegated_reader",
  "delegated_user": "bob@contoso.com",
  "source_path": "/data/confidential.xlsx",
  "output_path": "/tmp/mipwrapper_xyz/output.xlsx",
  "timeout_seconds": 30
}
```

**Response (Error):**

```json
{
  "protocol_version": "1.0",
  "request_id": "req-def456",
  "success": false,
  "error": {
    "code": "PermissionDenied",
    "message": "User lacks Export right for this file",
    "details": "Required right: Export. Available rights: [Print, Copy]"
  }
}
```

Python raises:

```python
raise PermissionDeniedError(
    "User lacks Export right for this file",
    error_code="PermissionDenied",
    audit_metadata={"required_right": "Export"},
)
```

---

## Version Compatibility

### Future Changes

If MIP Wrapper needs to support new operations or fields in the future:

1. **Backwards Compatible Change:** Add optional field, increment patch version (1.0.1)
   - Helper must ignore unknown fields
   - Python must handle missing optional result fields

2. **Breaking Change:** New command or required field, increment minor version (1.1.0)
   - Version check ensures old clients reject new protocol
   - Old clients cannot communicate with new helper
   - New clients cannot communicate with old helper

3. **Major Change:** Complete redesign, increment major version (2.0.0)
   - Full protocol redesign
   - Clear migration path

Current version is 1.0.0. Next breaking change would be 1.1.0 or 2.0.0 depending on scope.
