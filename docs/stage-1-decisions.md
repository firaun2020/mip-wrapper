# Stage 1 Design Decisions

Quick reference for architectural and implementation choices made during Stage 1.

---

## Architecture

| Decision | Choice | Rationale | Trade-offs |
|----------|--------|-----------|-----------|
| **Process Bridge Type** | .NET via subprocess | Official .NET wrapper exists; MSAL integration straightforward | Requires .NET runtime; slight interop overhead |
| **IPC Protocol** | JSON over stdin/stdout | Simple, debuggable, no network exposure | No streaming; JSON parsing overhead |
| **Sensitivity Secret Handling** | Callback-based password provider | Prevents password leakage to JSON, logs, argv | Extra API complexity |
| **Binary Distribution (v1)** | Separate SDK installation (not bundled) | Resolves IPIA redistribution uncertainty | Less convenient than bundled; requires documentation |
| **File Operations** | Temporary directory context manager | Enforces cleanup; safe resource management | Context manager required (good practice anyway) |
| **Error Model** | Typed exception hierarchy | Clear error distinction; easier handling | More exception classes to maintain |
| **Audit Logging** | Safe metadata (no tokens/secrets) | Audit trail without security risk | May require hashing/referencing instead of full paths |

---

## Authentication

| Decision | Choice | Rationale | Trade-offs |
|----------|--------|-----------|-----------|
| **Primary Auth Mode** | Certificate-based | Production-grade; no hardcoded secrets | Requires certificate management |
| **Secondary Auth Mode** | Client secret (via callback) | Compatibility; not recommended | Less secure; documented as development-only |
| **Certificate Password** | Password provider callback | Prevents leakage; allows Key Vault later | More complex than inline password |
| **Token Acquisition** | MSAL in .NET helper | Official Microsoft library; cache handling | Not in Python layer; requires protocol bridge |
| **Interactive Auth (v1)** | Not supported | Focus on unattended service scenarios | Users need certificate for v1 |
| **Managed Identity (v1)** | Not supported | MIP SDK token requirements unclear | Planned for v1.5+ after research |

---

## Authorization

| Decision | Choice | Rationale | Trade-offs |
|----------|--------|-----------|-----------|
| **Primary Mode (v1)** | Delegated-reader | Least privilege; most common scenario | Requires per-user rights checking |
| **Secondary Mode** | Application super-user | Needed for audit/compliance scenarios | Must be explicitly requested; requires tenant config |
| **Rights Checking** | Per-document, before decryption | Prevents DRM bypass; explicit failures | No automatic fallback to broader permissions |
| **Fallback Strategy** | None - fail if rights insufficient | Security priority | More restrictive; requires correct setup |

---

## API Design

| Decision | Choice | Rationale | Trade-offs |
|----------|--------|-----------|-----------|
| **Temporary Decryption** | Context manager (with statement) | Enforces cleanup; idiomatic Python | Requires context manager usage |
| **Explicit Decryption** | `allow_unprotected_output=True` required | Explicit acknowledgement prevents accidents | Extra parameter; no silent defaults |
| **Bytes Decryption** | Memory size limit (default 100 MB) | Prevents OOM; documentation honest about limits | Caller must check file size or handle errors |
| **Inspection Result** | Safe metadata only (no keys/tokens) | No security leakage; safe for logging | May require hashing/references |
| **Correlation ID** | Optional caller-provided UUID | Enables tracing; audit trail | Optional but recommended |
| **Logging** | Caller configures (Python logging) | No automatic log noise; caller controls sensitivity | Caller responsible for secret redaction |

---

## Security

| Decision | Choice | Rationale | Trade-offs |
|----------|--------|-----------|-----------|
| **Temp Directory Permissions** | 0o700 (owner-only) | Prevents other users on same system from accessing | Only on Unix-like systems (Windows ACLs different) |
| **Temp Directory Names** | Random, unique per operation | Prevents predictability; concurrent op collision | Slightly longer paths |
| **Symlink Handling** | Do NOT follow; report as error | Prevents symlink escape attacks | May fail on systems with symlinks in paths |
| **Path Traversal** | Reject `..`, `~`, absolute paths in relative context | Validates before passing to .NET | May require path normalization |
| **Cleanup on Exception** | Always (finally block) | Cleanup failure doesn't hide original error | Cleanup failure is reported after operation |
| **Plaintext Retention** | Minimal (no cache, no in-memory copies) | Honesty about memory erasure limitations | Documented as non-guaranteed |
| **Process Communication** | Subprocess with shell=False | Prevents command injection | No shell features (acceptable) |

---

## Platforms (v1.0)

| Platform | Supported | Details | Notes |
|----------|-----------|---------|-------|
| **Windows** | ✅ Yes | 10/11/Server 2016-2022, x64 | Requires .NET runtime; Visual C++ runtime |
| **Ubuntu** | ✅ Yes (20.04, 22.04, 24.04) | x64 only | Requires .NET runtime |
| **macOS** | ✅ Yes | Intel/ARM via x64 emulation | Requires .NET runtime |
| **RHEL/CentOS** | ⏳ Planned | x64, RHEL 8-9 | After v1.0 validation |
| **Alpine/musl** | ❌ No | .NET Core issue with musl | Defer or use full .NET Framework |
| **ARM64** | ⏳ Maybe | Not tested; depends on MIP SDK support | Revisit after Stage 2 |

---

## Licensing and Distribution

| Decision | Choice | Rationale | Trade-offs |
|----------|--------|-----------|-----------|
| **MIP Wrapper License** | MIT (or Apache 2.0) | Permissive; open-source community friendly | Must be compatible with MIP SDK usage |
| **IPIA Requirement** | Required for public release | Microsoft policy for distributed apps | Not required for internal-only use |
| **IPIA Timeline** | ~72 hours to response | Microsoft's stated timeline | Must plan for before public release |
| **Public Distribution** | Deferred until IPIA signed | Legal compliance first | Can develop and test internally in meantime |
| **SDK Binary Bundling (v1)** | NOT in wheels (separate installation) | Resolves redistribution uncertainty | Requires clear installation docs |
| **Trusted Publishing** | GitHub Actions + PyPI OIDC | Best practice; removes credential storage | Setup required before release |
| **Release Signing** | TBD (planned for v1.5+) | Security best practice | Adds build complexity |

---

## Assumptions and Constraints

### Assumptions the Design Relies On

1. **Process Boundary is Trusted** - Python and .NET helper run in same process; threat model starts here
2. **Compute Environment is User-Controlled** - Not shared with untrusted processes (VMs, containers, CI jobs)
3. **MIP SDK is Updated Regularly** - Users keep MIP SDK current with security patches
4. **Certificate Storage is Secure** - User is responsible for storing certificates securely (not in repo, etc.)
5. **Delegated User UPN is Correct** - Configuration mistakes are caller's responsibility
6. **Azure Destination Security** - User owns RBAC and encryption on destination storage
7. **Temporary Filesystem is Secure** - System temp location has appropriate permissions
8. **Plaintext Leakage is Acceptable** - Python cannot guarantee memory erasure (documented)
9. **MIP SDK Token Caching Works** - MSAL handles tokens correctly (trust Microsoft library)
10. **Deletion = Erasure** - User accepts that deleted files may be recoverable (documented)

### Constraints the Design Works Within

1. **No Network Decryption Service** - Entire operation in one compute process; no remote MIP service
2. **No RMS Reimplementation** - Only use official Microsoft MIP SDK; no custom encryption
3. **No DRM Bypass** - Check usage rights; fail if insufficient (no workarounds)
4. **No Hardcoded Secrets** - All credentials via provider callbacks or configuration
5. **No Automatic Tenant Configuration** - User/admin must set up permissions outside package
6. **No Business Logic** - Package does decryption only; caller does processing
7. **No Unsupported Auth Flows** - No username/password, no client credentials as principal
8. **No Silent Failures** - Always fail explicitly; no hidden retries or fallbacks
9. **No Forensic Erasure** - Don't claim secure deletion; document limitations
10. **No Mixing Concerns** - Auth, authorization, and file operations are separate

---

## Future Decision Points (for Stages 2-5)

These are deferred decisions; Stage 1 makes assumptions but does not resolve them.

### Before Stage 2 Starts
- [ ] .NET helper skeleton: start from scratch or use Microsoft sample?
- [ ] MSAL version: latest stable or pinned version?
- [ ] Test tenant: create internal tenant or use shared tenant?
- [ ] Protected test file: created manually or generated during setup?

### Before Stage 3
- [ ] Logging framework: Python logging, structlog, or other?
- [ ] Timeout defaults: 30 seconds or configurable?
- [ ] Cancellation: CancellationToken or timeout-based?
- [ ] Secrets module: keyring, MSvault, or caller-provided?

### Before Stage 4 (Azure Destinations)
- [ ] DefaultAzureCredential or explicit auth methods?
- [ ] Upload retries: exponential backoff, max attempts?
- [ ] Partial upload cleanup: delete partial files or leave for manual cleanup?
- [ ] Destination path validation: strict or permissive?

### Before Stage 5 (Public Release)
- [ ] Binary wheels: after IPIA, should we bundle SDK binaries?
- [ ] Platform-specific wheels: separate wheels per OS/architecture?
- [ ] Release signing: GPG keys, sigstore, or other?
- [ ] SBOM format: SPDX JSON, CycloneDX, or other?

---

## Validation During Stage 2

These design decisions must be validated with actual implementation:

1. **MSAL Token Acquisition Works** - Confidential client with certificate, delegated user
2. **MIP SDK Inspection API** - Query protection metadata, usage rights
3. **Rights Checking Works** - Export right validation prevents unauthorized decryption
4. **Cleanup in Finally** - Exception in openpyxl still cleans temp files
5. **Protocol Versioning Works** - Helper version mismatch is rejected
6. **Timeout Enforcement** - Long-running decryption respects timeout
7. **Path Validation** - Traversal attempts are rejected
8. **Concurrent Operations** - Multiple clients in same process don't interfere

---

## Success Criteria by Category

### Architectural
- ✅ Process-bridge design is implemented
- ✅ Python and .NET have clean separation of concerns
- ✅ Trust boundary is respected (no network services)
- ⏳ Integration tests validate the design

### Security
- ✅ Threat model is comprehensive
- ✅ No secrets in logs, JSON, or argv
- ✅ Usage rights are checked before decryption
- ⏳ Security tests validate mitigations

### Functional
- ✅ Inspect returns accurate metadata
- ✅ Decrypt-to-file works for authorized users
- ✅ Decrypt-to-bytes respects size limits
- ✅ Unauthorized users get PermissionDeniedError
- ⏳ Integration tests validate all operations

### Operational
- ✅ Cleanup is automatic and reliable
- ✅ Errors are typed and descriptive
- ✅ Audit metadata is safe and useful
- ✅ Logging can be configured by caller

---

**Status:** ✅ All Stage 1 decisions documented  
**Next Review:** Before Stage 2 kickoff  
**Authority:** Subject to approval of Stage 1 deliverables
