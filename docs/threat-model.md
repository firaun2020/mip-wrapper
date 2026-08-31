# MIP Wrapper Threat Model

## Scope

This threat model covers MIP Wrapper v1.x running in user-controlled compute environments (containers, VMs, CI jobs, local development). 

**Assumptions:**
- Python and .NET helper run in **separate OS processes** within the same **deployment boundary** (container, VM, CI job)
- Processes communicate via JSON protocol over subprocess stdin/stdout (not network)
- The host OS and hypervisor are trusted (threat model starts here)
- Both processes have access to shared file systems and the same temporary directory
- Temporary files are created with 0o700 (owner-only) permissions on Unix-like systems

**Out of Scope:**
- Network security between compute and Azure services (assumed TLS)
- Azure Data Lake or Blob Storage security (assumed Microsoft-managed)
- Compromised host operating system or hypervisor
- Physical theft of hardware
- Insider threats with administrative OS access
- Cryptographic weaknesses in Azure RMS (delegate to Microsoft)

## Threat Categories

### 1. Credential and Authentication Threats

#### 1.1 Certificate Private Key Compromise

**Threat:** Certificate private key is stolen, exposed in logs, or leaked through memory.

**Attack Scenarios:**
- Attacker reads certificate from disk before it is loaded
- Attacker dumps process memory and extracts private key
- Certificate path is logged in plaintext
- Certificate password is logged or passed via argv
- Certificate is copied to a shared or non-encrypted location

**Mitigations:**
- Certificate path and password are never logged or passed as CLI arguments
- Certificate path is validated to be on a secure filesystem (implementation later)
- Certificate is loaded directly by .NET helper (Python does not load it)
- Use a password-provider callback (not inline passwords)
- Clear certificate from memory after use (delegated to .NET/MIP SDK)
- Document that certificate storage security is the user's responsibility
- Support integration with Azure Key Vault (future: v1.5)

**Residual Risk:**
- Compromised container image could contain the certificate
- Compromised VM could intercept certificate loading
- High-confidence mitigations reduce risk to acceptable level for unattended service scenarios

---

#### 1.2 Token Leakage

**Threat:** OAuth2 access token is intercepted, logged, or left in memory.

**Attack Scenarios:**
- Token is logged in exception messages
- Token is serialized into a configuration file
- Token appears in STDERR during debugging
- Token passed through plaintext subprocess communication
- Token cached insecurely between requests

**Mitigations:**
- Tokens are acquired and managed entirely by .NET helper
- Python never handles raw access tokens
- Tokens are never passed from Python to .NET
- Tokens do NOT appear in response JSON (only success/failure status)
- Protocol handshake keeps tokens internal to the .NET process
- Token refresh is handled by MSAL (standard practice)
- Exceptions redact sensitive token material

**Residual Risk:**
- .NET helper logs (if enabled) could leak tokens
- Acceptable: .NET helper logging is disabled by default; caller controls telemetry opt-in

---

#### 1.3 Client Secret Exposure

**Threat:** For certificate-less scenarios, client secrets are exposed during transmission or storage.

**Attack Scenarios:**
- Secret passed as command-line argument
- Secret included in configuration file
- Secret logged in diagnostic output
- Secret left in environment variables

**Mitigations:**
- Client-secret authentication is supported but marked as less secure
- Secret is never passed via argv
- Secret is acquired from a secret-provider callback (like password provider)
- Secret is never logged
- Documentation strongly recommends certificates over secrets
- Secret provider callback design allows Key Vault integration

**Residual Risk:**
- Callback implementation is caller's responsibility
- Acceptable: Clear documentation and examples for secure patterns

---

### 2. Authorization and Permissions Threats

#### 2.1 Abuse of Application Super-User Mode

**Threat:** Application misuses super-user mode to decrypt files the delegated user does not have rights to.

**Attack Scenarios:**
- Service principal gets Content.SuperUser permission unintentionally
- Application defaults to super-user when delegated access fails
- Delegated user permissions are not checked, only application permission
- Super-user access is used to decrypt all tenant files indiscriminately

**Mitigations:**
- Super-user mode is NOT the default authorization mode
- Super-user requires explicit caller acknowledgement: `acknowledge_tenant_wide_access=True`
- Super-user mode fails fast if acknowledgement is absent
- Super-user is never selected as fallback after delegated access fails
- Documentation clearly explains that super-user may allow decryption of all tenant files
- Audit logs record when super-user mode was used
- Tenant admin must explicitly configure Content.SuperUser permission (not automatic)
- Package never modifies tenant configuration

**Residual Risk:**
- Tenant admin could misconfigure Content.SuperUser permission
- Acceptable: Admin responsibility clearly documented; package does not enable it

---

#### 2.2 Confusion Between Application Permissions and Document Rights

**Threat:** Application holds the necessary permission (e.g., Content.DelegatedReader) but the delegated user lacks the document's required usage right (Export).

**Attack Scenarios:**
- Delegated user cannot decrypt a file, but application tries to bypass by upgrading permission mode
- Application assumes Content.DelegatedReader implicitly grants Export to all documents
- Application does not check document-specific usage rights
- Error handling masks the permission denial

**Mitigations:**
- Package explicitly checks usage rights before decryption (Export or Owner)
- Usage rights are checked per-document, not per-user globally
- PermissionDeniedError is raised when usage rights are absent
- Error message explains which right is missing
- No automatic fallback to broader permissions
- Documentation clearly separates application permission from document rights
- Example scenarios document the difference

**Residual Risk:**
- Caller could catch PermissionDeniedError and implement unsafe retry logic
- Acceptable: Clear error message and documentation guide correct behavior

---

#### 2.3 Delegated User Identity Misconfiguration

**Threat:** Wrong user UPN is configured as the delegated user, allowing decryption on behalf of the wrong identity.

**Attack Scenarios:**
- Configuration typo: `delegated_user="alice@corp.com"` when intent was `bob@corp.com`
- Script hardcodes a shared service account instead of the intended user
- User's UPN changes, but configuration is not updated
- No validation that delegated user actually exists or has rights

**Mitigations:**
- Delegated user UPN is required and validated to be non-empty
- Delegated user is included in audit logs (safe metadata)
- Package does not validate that user exists (MIP SDK will fail at token time)
- Documentation emphasizes the importance of correct UPN
- Example configuration includes validation checks for caller

**Residual Risk:**
- Configuration validation is caller's responsibility
- Acceptable: Clear documentation and examples reduce risk

---

### 3. File Security Threats

#### 3.1 Path Traversal in Temporary Decryption

**Threat:** Attacker provides a source path like `../../../sensitive.xlsx` or output path with `..` components, causing decryption to occur outside the intended directory.

**Attack Scenarios:**
- Attacker controls the `source_path` parameter to `client.decrypted_file()`
- Attacker controls the output path in `client.decrypt()`
- Symlink points outside the intended temp directory
- Relative paths are resolved unsafely

**Mitigations:**
- Python layer validates all input paths
- Paths are converted to absolute paths
- Path traversal sequences (`..`, `~`, symlinks) are detected and rejected
- Output paths are validated to not exist (unless `overwrite=True`)
- Source and output paths are checked to not be the same file
- Temporary directories are created in secure system temp location
- Temporary directories use random unique names (not predictable)
- Symbolic links in temporary paths are not followed
- All path validation happens before passing to .NET helper

**Residual Risk:**
- Time-of-check-time-of-use (TOCTTOU) race if paths change between validation and use
- Acceptable: Paths are in temp directories controlled by the process; TOCTTOU window is minimal

---

#### 3.2 Symbolic Link Attacks

**Threat:** Attacker creates a symbolic link pointing to sensitive files, and the package follows it.

**Attack Scenarios:**
- Cleanup deletes symlink target instead of the symlink itself
- Decrypted output follows symlink to another location
- Temp directory cleanup follows symlinks to parent directories

**Mitigations:**
- Temporary directories are not navigable from symlinks
- Cleanup uses safe file deletion that does NOT follow symlinks
- If symlinks are detected in temp paths, they are reported and not followed
- Output paths cannot be symlinks (checked before decryption)
- Documentation warns against using symlinks in decryption paths

**Residual Risk:**
- Filesystem race if symlinks are created during cleanup
- Acceptable: Temp directories are unique and isolated per operation

---

#### 3.3 Malicious Filenames

**Threat:** A protected file has a specially crafted filename designed to cause issues.

**Attack Scenarios:**
- Filename is extremely long and causes buffer overflow
- Filename contains null bytes, control characters, or special shell escapes
- Filename is `..` or `.` and confuses path logic
- Filename causes logging code to be bypassed

**Mitigations:**
- Filenames are not used for cleanup (temp directory is deleted as a whole)
- Filenames are not passed to shell (subprocess uses argument list, shell=False)
- Path validation rejects filenames that are `..`, `.`, or empty
- Long filenames are handled by OS/filesystem limits
- Special characters in filenames are preserved (not escaped)
- Filenames are redacted in logs (show hash or placeholder instead)

**Residual Risk:**
- Minimal; filenames are treated as opaque byte sequences

---

#### 3.4 Corrupted or Malicious Protected File

**Threat:** A corrupted or malicious protected file causes the MIP SDK to crash or exhibit undefined behavior.

**Attack Scenarios:**
- Corrupted file headers cause MIP SDK buffer overflow
- File is not actually MIP-protected (wrong format)
- File is designed to exploit MIP SDK vulnerability
- Parsing fails and leaves half-decrypted data on disk

**Mitigations:**
- The MIP SDK is responsible for validating and safely handling file formats
- Package does not attempt to parse protected files directly
- Package validates that files are actually protected (metadata check)
- Errors from MIP SDK are caught and reported
- Partial output files are cleaned up on error
- Timeouts prevent infinite hangs from corrupted files

**Residual Risk:**
- MIP SDK vulnerabilities are Microsoft's responsibility
- Acceptable: Trust the official SDK; stay up-to-date with patches

---

### 4. Temporary File Security Threats

#### 4.1 Plaintext Leakage Through Temporary Files

**Threat:** Decrypted content is left on disk after processing.

**Attack Scenarios:**
- Cleanup fails silently, leaving decrypted file on disk
- Exception during processing prevents cleanup
- Context manager is not used (explicit `cleanup=False`)
- Temporary directory is on a shared or monitored filesystem

**Mitigations:**
- Temporary files are cleaned by default (cleanup=True)
- Cleanup runs in a finally block (always runs, even on exception)
- Cleanup failure is reported in audit metadata
- Cleanup failure does NOT hide the original exception
- Explicit decryption requires caller to request `cleanup=False`
- Temporary directories are created in system temp location (owned by user)
- Context managers enforce cleanup via `__exit__` method

**Residual Risk:**
- Filesystem journal/recovery could preserve deleted data
- Acceptable: Documented honestly; appropriate for data classification

---

#### 4.2 Race Conditions in Temporary Directory Creation

**Threat:** Temporary directory is created with weak permissions or is predictable, allowing other processes to access it.

**Attack Scenarios:**
- Temp directory is created with default world-readable permissions
- Temp directory name is predictable (not random)
- Other processes create symlinks pointing into the temp directory
- Concurrent operations create collisions

**Mitigations:**
- Temporary directories are created with restrictive permissions (0o700, owner-only)
- Directory names are generated using cryptographically secure randomness
- Directory creation is atomic (fails if exists)
- Each operation gets its own unique temp directory
- Concurrent operations do not share temp paths
- Permissions are set at creation time, not after

**Residual Risk:**
- Minimal; strong mitigations in place

---

#### 4.3 Cleanup Failure Cascades

**Threat:** Cleanup failure prevents subsequent operations from running or leaves data on disk.

**Attack Scenarios:**
- Cleanup raises exception, masking the original operation
- Partial cleanup leaves some files on disk
- Cleanup tries to delete files it does not own
- Cleanup follows symlinks to delete wrong files

**Mitigations:**
- Cleanup is idempotent (safe to run multiple times)
- Cleanup failures are caught and reported, not re-raised
- Original exception takes priority (cleanup failure does not hide it)
- Cleanup only deletes files the package created
- Cleanup outcome is included in audit metadata
- Cleanup skips files that do not exist or are not owned

**Residual Risk:**
- Minimal; comprehensive mitigations

---

### 5. Process and Memory Threats

#### 5.1 Plaintext Leakage Through Logging

**Threat:** Decrypted content, tokens, or sensitive metadata appear in logs.

**Attack Scenarios:**
- Exception message includes file content
- Debug logs include tokens or keys
- Full path to certificate file is logged
- Publishing licence material is logged
- Decrypted bytes are logged during memory operations

**Mitigations:**
- Logging is configured by the caller (Python logging framework)
- Sensitive fields are redacted in exceptions
- Package does not log decrypted content
- Package does not log raw tokens or publishing licences
- Paths are sanitized or hashed in logs
- Debug output from .NET helper is disabled by default
- Caller can enable debug logging, but is responsible for privacy

**Residual Risk:**
- Caller could enable debug logging improperly
- Acceptable: Clear documentation; user owns debug configuration

---

#### 5.2 Plaintext Leakage Through Crash Dumps

**Threat:** Process crash dump includes plaintext content, tokens, or keys in memory.

**Attack Scenarios:**
- Container crashes and dump is accessible
- Debugger attaches and dumps process memory
- System crash dump includes the MIP Wrapper process

**Mitigations:**
- Package does not retain plaintext longer than necessary
- Temporary decrypted files are written to disk, not retained in memory
- Token handling is delegated to .NET helper (cleared after use)
- Documentation acknowledges that process dumps may leak data
- Use appropriate data classification for sensitive files
- Use container security features to prevent dump access

**Residual Risk:**
- Beyond package control; depends on OS and deployment environment
- Acceptable: Documented; user configures security appropriately

---

#### 5.3 Memory Exhaustion (decrypt_bytes)

**Threat:** An attacker provides a huge protected file, causing memory exhaustion.

**Attack Scenarios:**
- Caller requests `decrypt_bytes()` on a multi-GB file
- Memory usage grows unbounded, causing OOM kill
- Other processes on the host are starved

**Mitigations:**
- `decrypt_bytes` has a maximum file size (default 100 MB)
- Size limit is configurable but has a reasonable maximum
- Files larger than the limit are rejected before decryption
- Error message explains the limit
- Documentation recommends using the context manager (writes to temp disk) for large files
- Caller can increase limit, but accepts responsibility

**Residual Risk:**
- Caller can misconfigure the limit
- Acceptable: Clear documentation and default limits prevent most abuse

---

### 6. Upload and Destination Threats

#### 6.1 Uploading to Wrong Destination

**Threat:** Unprotected content is uploaded to an unintended location.

**Attack Scenarios:**
- Configuration typo in destination path
- Environment variable is wrong
- Symlink points to a different container/storage account
- Race condition changes destination between check and upload

**Mitigations:**
- Destination path is required and validated
- Destination must be explicitly passed to pipeline/upload functions
- Package does NOT default to any destination
- Destination path is included in audit logs
- Upload is rejected if output destination already exists (unless overwrite=True)
- Destination adapter validates the path before upload

**Residual Risk:**
- Configuration errors are caller's responsibility
- Acceptable: Clear API and documentation

---

#### 6.2 Partial Upload Failure

**Threat:** Upload fails partway through, leaving partial decrypted data in the destination.

**Attack Scenarios:**
- Network connection drops during upload
- Destination quota exceeded mid-upload
- Container is deleted during upload
- Destination adapter crashes

**Mitigations:**
- Upload failures do not leave partial files (atomic or cleanup)
- Azure SDKs handle transient retries
- Caller is responsible for deciding whether to retry
- Audit metadata indicates whether upload succeeded
- Package does not cleanup destination on failure (only source/temp)
- Caller can implement retry logic with exponential backoff

**Residual Risk:**
- Azure SDK behavior determines atomicity
- Acceptable: Documented; caller implements retry strategy

---

#### 6.3 Uploading Unprotected Content Without Acknowledgement

**Threat:** Decrypted or plaintext content is uploaded without the caller acknowledging the security implications.

**Attack Scenarios:**
- `allow_unprotected_output=False` is the default
- Caller forgets to set it to True
- API returns confusing error (wrong error message)

**Mitigations:**
- `allow_unprotected_output` is a required explicit parameter
- Default is False (upload rejected)
- Error message explains why upload failed
- Documentation prominently warns about unprotected output
- Example code includes the parameter
- No implicit silent failures

**Residual Risk:**
- Minimal; explicit parameter design prevents accidents

---

### 7. Dependency and Supply Chain Threats

#### 7.1 Compromised Native Binary (MIP SDK)

**Threat:** The official Microsoft MIP SDK binary is compromised or contains a vulnerability.

**Attack Scenarios:**
- Attacker publishes a malicious version of the MIP SDK
- NuGet package is compromised
- Man-in-the-middle intercepts the binary
- Binary contains an unpatched vulnerability

**Mitigations:**
- Use official Microsoft NuGet packages (signed, verified)
- Pin specific MIP SDK versions in pyproject.toml
- Regularly check for security updates and patch
- Verify package signatures (NuGet supports signed packages)
- Monitor Microsoft security bulletins
- Use dependency scanning in CI

**Residual Risk:**
- Trust the official Microsoft supply chain
- Acceptable: Best-practice dependency management

---

#### 7.2 Compromised Python Dependency

**Threat:** A Python dependency is compromised or contains a vulnerability.

**Attack Scenarios:**
- Attacker publishes malicious version of a dependency
- Dependency has unpatched security vulnerability
- Transitive dependency is compromised

**Mitigations:**
- Keep dependencies minimal (only required packages)
- Pin dependency versions in requirements
- Use `pip-audit` or similar for vulnerability scanning
- Review dependency changes before updating
- Monitor PyPI security advisories
- Use hashes for package verification (where possible)

**Residual Risk:**
- Standard package management practices mitigate most risk

---

### 8. Protocol Threats

#### 8.1 Protocol Injection or Manipulation

**Threat:** Attacker modifies the JSON protocol messages between Python and .NET helper.

**Attack Scenarios:**
- Attacker injects malicious JSON fields
- Attacker modifies protocol version to force downgrade
- Attacker changes paths or parameters mid-communication
- Malformed JSON causes undefined behavior

**Mitigations:**
- Protocol version is checked in every request and response
- Unsupported versions are rejected
- JSON schema validation on responses from .NET helper
- Input validation on all parameters before passing to helper
- Unknown fields in responses are ignored (forward-compatibility)
- Helper process is spawned by Python (not a network service)
- Communication is over stdin/stdout of a subprocess (not network)

**Residual Risk:**
- If Python process is compromised, attacker can modify messages
- Acceptable: Threat model assumes process boundary is trusted

---

#### 8.2 Malformed Helper Response

**Threat:** .NET helper returns invalid or unexpected JSON.

**Attack Scenarios:**
- Helper crashes and outputs error text instead of JSON
- Helper is killed mid-operation, stdout is partial
- Helper returns field types that don't match schema
- Helper returns nonsensical error codes

**Mitigations:**
- Response JSON is parsed and validated
- Missing required fields are detected and reported
- Type mismatches cause ProtocolError
- Timeout is enforced if helper is unresponsive
- Partial responses are rejected
- Error codes are enumerated (unknown codes are reported as unexpected)

**Residual Risk:**
- Minimal; comprehensive validation

---

#### 8.3 Helper Process Termination During Operation

**Threat:** The .NET helper process is killed or terminates unexpectedly during decryption.

**Attack Scenarios:**
- Container is terminated while decryption is in progress
- Helper hits an out-of-memory error
- System kills the process due to resource limits
- Helper crashes on corrupted input
- Network connection between Python and helper is broken

**Mitigations:**
- Helper process state is managed by Python
- Timeout is enforced on all operations
- If helper terminates unexpectedly, NativeRuntimeError is raised
- Partial output files are cleaned up (or reported in error)
- Caller is responsible for implementing retry logic
- Audit metadata indicates whether operation completed

**Residual Risk:**
- Container termination may leave files on disk
- Acceptable: Caller implements cleanup in container shutdown handlers

---

### 9. Azure Destination Threats

#### 9.1 Uploading to Unintended Azure Destination

**Threat:** Unprotected content is uploaded to the wrong storage account, container, or directory.

**Attack Scenarios:**
- Configuration typo in Azure storage URL
- Environment variable is wrong
- Access control on destination is misconfigured (readable by others)
- Destination path is predictable or guessable

**Mitigations:**
- Destination URL is required and validated
- Destination is never inferred or defaulted
- Destination URL is logged (safe metadata)
- Azure SDK validates the URL format
- Caller is responsible for RBAC on the storage account
- Example code shows secure destination patterns

**Residual Risk:**
- Configuration and RBAC are caller's responsibility
- Acceptable: Clear API and documentation

---

#### 9.2 Credentials Leakage to Azure Destination

**Threat:** Storage account key, SAS token, or other credential is exposed.

**Attack Scenarios:**
- Credential is logged in plaintext
- Credential is included in audit metadata
- Credential is passed via argv or environment variable
- Credential appears in exception message

**Mitigations:**
- Credentials are never logged (passed directly to Azure SDK)
- Credentials are never returned in response objects
- Use DefaultAzureCredential (managed identity, no explicit secret)
- Use SAS tokens with limited scope and lifetime
- Do NOT use storage account keys (documented as anti-pattern)
- Support Azure Key Vault for certificate/secret storage

**Residual Risk:**
- Caller could misconfigure credentials
- Acceptable: Documentation and examples guide secure patterns

---

#### 9.3 Missing Encryption at Rest Validation

**Threat:** Caller assumes ADLS or Blob Storage encryption at rest equals MIP file-level protection.

**Attack Scenarios:**
- Unencrypted plaintext is uploaded, then encrypted at rest by Azure
- Caller assumes the data is protected the same way as the original MIP-protected file
- Exported data loses the original label and protection

**Mitigations:**
- Documentation clearly explains that Azure encryption at rest is different from MIP file-level protection
- Documentation warns that exported plaintext is no longer MIP-protected
- `allow_unprotected_output` parameter requires explicit acknowledgement
- Audit metadata indicates that content was exported/plaintext
- Caller owns the decision to upload plaintext

**Residual Risk:**
- Caller misconception
- Acceptable: Clear documentation prevents most confusion

---

## Risk Summary

**Status:** Mitigations are proposed but unvalidated. Residual risk will be reassessed after implementation, integration testing, and security review.

| Category | Risk | Mitigation | Status |
|----------|------|-----------|--------|
| Credential Compromise | High | Never log/pass certs, passwords, or tokens | Designed; unvalidated |
| Token Leakage | High | Tokens only in .NET process | Designed; unvalidated |
| Super-User Abuse | Medium | Require explicit ack, fail fast | Designed; deferred to v1.1+ |
| Permission Confusion | Medium | Check rights per-document, typed errors | Designed; unvalidated |
| Path Traversal | Medium | Validate all paths, no symlinks | Designed; unvalidated |
| Temp File Leakage | Medium | Always cleanup, randomize names | Designed; unvalidated |
| Memory Exhaustion | Low | Size limits on memory APIs | Designed; unvalidated |
| Logging Leakage | Medium | Redact sensitive fields | Designed; unvalidated |
| Inter-Process Communication | Medium | JSON protocol, no plaintext secrets | Designed; unvalidated |
| Process Compromise | High | Outside threat model | Accept |
| MIP SDK Vuln | High | Trust Microsoft updates | Monitor |
| Protocol Injection | Low | Over subprocess, not network | Designed; unvalidated |
| Upload to Wrong Dest | Medium | Explicit param, no default | Designed; deferred to v2 |
| Config Errors | Medium | Clear docs, examples | Accept |

## Implementation Priorities

### Must Have (v1.0)
- ✓ Path validation (no traversal)
- ✓ Temp file security (random names, 0o700 perms)
- ✓ Rights checking (Export or Owner)
- ✓ Cleanup in finally block
- ✓ No logging of secrets
- ✓ Redacted exceptions
- ✓ Protocol versioning

### Should Have (v1.0)
- ✓ Permission-denied typed errors
- ✓ Timeout enforcement
- ✓ Audit metadata
- ✓ Documented limits (decrypt_bytes max size)

### Nice to Have (v1.1+)
- Dependency vulnerability scanning
- Signed release artifacts
- SBOM generation
- Azure Key Vault integration
- Certificate path validation (secure FS)

## Assumptions

1. The Python and .NET helper run in separate OS processes within the same deployment boundary (not separated by network).
2. The compute environment is trusted (container, VM, CI job owned by the user).
3. The user owns the responsibility for certificate and secret storage security (file permissions, protected mounts).
4. The user understands the difference between MIP file-level protection and Azure storage encryption at rest.
5. The MIP SDK is periodically updated to address vulnerabilities.
6. The user does not misconfigure delegated-user UPN or destination paths.
7. Temporary directories are on a filesystem with appropriate Unix permissions (not world-readable).
8. Processes cannot be trivially escaped (OS-level isolation is in place).

## Out of Scope

- Cryptographic validation of Azure RMS (trust Microsoft)
- Forensic erasure of plaintext (acknowledge filesystem journal/recovery)
- Network security between compute and Azure (assume TLS)
- Compromised host OS or hypervisor
- Physical theft of hardware
- Insider threats with administrative access
