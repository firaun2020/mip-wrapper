# Stage 2 Approved Decisions

**Date:** September 2, 2026  
**Status:** Ready for Stage 2 Implementation  

These decisions were approved and lock in the v0.1 implementation approach.

---

## Runtime Distribution (APPROVED)

**Decision:** Private container image for internal v0.1 only.

**Container Contents:**
- Base: .NET 6.0+ runtime
- Python 3.11+
- `mip_wrapper` Python package
- `MipWrapper.Helper` (.NET executable)
- MIP SDK dependencies (via NuGet restore)

**Target:** Azure Container Apps Job

**Constraint:** Internal private use only. Do not publish publicly. Do not assume this is the final public distribution model.

**Future Public Distribution:** Deferred until Microsoft clarifies IPIA and binary-redistribution requirements.

---

## Certificate Handling (APPROVED)

**Decision:** File-based certificate and password at runtime.

**Approach:**
- Certificate file: Supplied at runtime (mounted volume)
- Password file: Separate file, supplied at runtime (mounted volume)
- Both files: Read-only, restrictive permissions (0o600)
- Helper reads the password file directly
- Password never passed via command-line arguments or JSON protocol

**Constraints:**
- Files NOT built into container image
- Files NOT deleted by the package
- Files NOT retained after certificate loads
- Filesystem permissions enforced by OS
- Deployment platform responsible for secret provisioning

**Future Enhancements:** Azure Key Vault, OS cert stores (v1.5+)

---

## Licensing and IPIA (IN PROGRESS)

**Action:** Contact Microsoft immediately.

**Contact:** IPIA@microsoft.com

**Questions:**
- Is IPIA required for an open-source community wrapper?
- Can MIP SDK binaries be redistributed in PyPI wheels?
- Are there special terms for unpaid open-source projects?
- What is the current process and timeline?

**Status:** Do not block v0.1. Document responses for v1.0 decision.

**Timing:** Contact before Stage 2 starts; get response before public release.

---

## Stage 2 Scope (APPROVED)

### INCLUDED in v0.1
- Certificate-based authentication (file-based)
- Delegated-reader authorization only
- Local file input
- File inspection (metadata)
- Export/Owner usage-right validation
- Temporary file decryption (context manager)
- Automatic cleanup (finally block)
- Typed exceptions
- Sanitized logging (no secrets)
- One authorized integration test
- One unauthorized integration test
- Verification: `openpyxl` compatibility

### NOT IN v0.1
- Super-user mode (→ v1.1+)
- ADLS/Blob adapters (→ v0.3)
- SharePoint downloading (→ v2.0+)
- Managed Identity for MIP (→ v1.5+)
- Interactive authentication (→ v1.5+)
- `decrypt_bytes` (→ v0.3+)
- Public PyPI publication (→ v1.0 after IPIA)
- Public container publication (→ v1.0 after IPIA)

---

## What This Means for Implementation

### v0.1 Objectives
1. Prove delegated-reader decryption works with real protected files
2. Validate architecture (separate processes, protocol)
3. Test rights enforcement (Export or Owner required)
4. Confirm cleanup works in all scenarios
5. Demonstrate `openpyxl` compatibility

### No Guessing on These
- Certificate and password are provided as files
- Helper reads password directly; Python doesn't pass it
- Container is private; not for public use
- No "if IPIA is required" logic; keep implementation clean
- No speculative features (super-user, destinations, etc.)

### Clear Exit Criteria
- Real protected Excel file decrypts ✅
- Unauthorized user gets `PermissionDeniedError` ✅
- Temp files clean up correctly ✅
- `openpyxl` can read decrypted file ✅
- No tokens/passwords in logs ✅
- Integration tests pass ✅

---

## Timeline

- **Week 1-2:** Setup (git, Docker build, test tenant, protected file)
- **Week 2-4:** Core implementation (auth, decryption, protocol)
- **Week 4-5:** Testing and fixes
- **Week 5-6:** Documentation and final validation

---

## Next Steps

1. **Immediately:** Contact Microsoft (IPIA@microsoft.com)
2. **This week:** Assign Stage 2 team (C# developer, Python developer, QA)
3. **This week:** Provision test tenant and create protected file
4. **This week:** Set up git, Docker build environment
5. **Next week:** Begin implementation
6. **Week 6:** Checkpoint – v0.1 complete

---

**Status:** All blocking decisions resolved. Ready to begin Stage 2 implementation.
