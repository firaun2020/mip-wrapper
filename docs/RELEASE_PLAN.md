# Release Plan: v0.1 to v1.0

**Current Status:** Stage 1 (Design)  
**Next Stage:** Stage 2 (Proof of Concept: v0.1)  

---

## Version 0.1 (MVP Proof of Concept)

**Timeline:** 4-6 weeks (Stage 2)  
**Status:** Internal/Private. Not for public distribution or publication.  
**Runtime:** Private container image (internal use only, not published)

### Deliverables
- C# .NET helper (MSAL + MIP SDK integration)
- Python wrapper with context manager for temporary decryption
- Certificate-based authentication (file-based certificate and password)
- Delegated-reader authorization
- Usage-right checking (Export or Owner)
- Temporary file cleanup (context manager)
- File inspection (metadata)
- Typed exceptions and error handling
- Sanitized logging (no secrets)
- One integration test (authorized delegated user)
- One integration test (unauthorized user)
- Verification: `openpyxl` can open decrypted files
- Private container image for Azure Container Apps Jobs

### Runtime: Container Image
- Base: .NET 6.0+ runtime image
- Includes: Python 3.11+, MIP Wrapper package, MipWrapper.Helper
- MIP SDK: Obtained via NuGet during build
- Certificate/Password: Mounted at runtime (not in image)
- Target: Azure Container Apps Job (internal subscription)
- Scope: Internal proof-of-concept only

### Success Criteria
- [ ] Real protected Excel file decrypts successfully
- [ ] Delegated-reader authorization enforces usage rights
- [ ] Unauthorized user receives PermissionDeniedError
- [ ] Temp files cleaned after success and failure
- [ ] No tokens/secrets/passwords in logs
- [ ] Integration tests pass (test tenant)
- [ ] Decrypted file opens with `openpyxl`
- [ ] Container image builds and runs
- [ ] Code is documented

### Known Limitations
- **Internal/Private Only** – No public distribution
- **Delegated-Reader Only** – Super-user deferred to v1.1+
- **Local File Input Only** – No SharePoint, ADLS, Blob yet
- **No Azure Destinations** – ADLS/Blob adapters in v0.3+
- **No In-Memory Decryption** – `decrypt_bytes` deferred to v0.3+
- **No HYOK or DKE** – Azure RMS only
- **No Managed Identity** – Certificate-only for v0.1

### Not Included
- PyPI publication (blocked: IPIA pending)
- Public container publication (blocked: IPIA pending)
- Public GitHub repository (stays private)
- Documentation for end-users
- Platform beyond container

---

## Version 0.2 (Hardened Core)

**Timeline:** 2-3 weeks (Stage 3)  
**Scope:** Security hardening, error handling, logging

### Deliverables
- Input validation (paths, parameters)
- Comprehensive error handling
- Redacted logging (no secrets)
- Timeout management
- Cancellation support
- Security review and fixes
- Extended test coverage
- Documentation (setup, API, examples)
- Packaging (pyproject.toml, dependencies)

### Additional Success Criteria
- [ ] Code review completed (internal)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No high-severity security issues
- [ ] Documentation is complete and clear

### Still Deferred
- Super-user mode
- Azure destinations
- Managed Identity
- Interactive auth
- decrypt_bytes

---

## Version 0.3 (Azure Destinations)

**Timeline:** 3-4 weeks (Stage 4)  
**Scope:** Upload to Azure storage, processing pipeline

### Deliverables
- ADLS Gen2 destination adapter
- Blob Storage destination adapter
- Processing pipeline (processor callback)
- DefaultAzureCredential integration
- Upload error handling and retry
- Cleanup after upload
- Destination tests

### New Success Criteria
- [ ] Upload to ADLS works
- [ ] Upload to Blob works
- [ ] Uploads cleaned up on failure
- [ ] Destination path validation works
- [ ] Tests pass with test storage accounts

### Licensing Consideration
- If public release is planned, IPIA and binary redistribution must be resolved first
- v0.3 is still pre-release (0.x versioning)

### Still Deferred
- Super-user mode
- Public PyPI release
- Managed Identity
- Interactive auth

---

## Version 1.0 (Stable, Supported Release)

**Timeline:** 1-2 weeks (Stage 5)  
**Scope:** Release preparation, legal/licensing, publication

### Prerequisites (Must be Completed First)
- [ ] IPIA requirements clarified with Microsoft
- [ ] Binary redistribution permissions confirmed (or deferred)
- [ ] Trademark compliance verified
- [ ] Security audit completed
- [ ] All tests pass on all platforms
- [ ] Documentation reviewed and finalized
- [ ] Legal review completed

### Deliverables
- Stable v0.3 codebase
- Security audit report (if applicable)
- SBOM (Software Bill of Materials)
- Release notes
- PyPI publication
- GitHub release with artifacts
- Official announcement

### Version 1.0 Stability Promises
- Semantic versioning going forward
- Breaking changes only in major versions
- Security updates for at least 12 months
- Public issue tracking and support

### Included in v1.0
- Certificate authentication
- Delegated-reader authorization
- Local file input
- Temporary decryption (context manager)
- Explicit decryption (persistent output)
- File inspection (metadata)
- ADLS Gen2 destinations
- Blob Storage destinations
- Processing pipeline
- Comprehensive documentation
- Full test suite
- TypeHints throughout

### Still Not Included in v1.0
- Super-user mode (planned for v1.1)
- Managed Identity (planned for v1.5)
- Interactive authentication (planned for v1.5)
- decrypt_bytes (planned for v1.5+)
- SharePoint source adapter (planned for v2.0)
- C++ pybind11 extension (planned for v2.0+)

---

## Post-Release (v1.1+)

### v1.1 - Super-User Support
- Application super-user mode
- Compliance and audit scenarios
- Admin role support

### v1.5 - Advanced Authentication
- Managed Identity (Azure)
- Interactive authentication (dev-only)
- Certificate rotation
- Azure Key Vault integration

### v2.0 - Evolution
- C++ pybind11 extension (optional)
- SharePoint source adapter
- In-memory decryption (decrypt_bytes)
- Token provider authentication
- Other advanced features

---

## Public Release Readiness Checklist

Before publishing v1.0 to PyPI:

### Legal and Licensing
- [ ] IPIA requirements are documented and confirmed
- [ ] Binary redistribution approach is documented and confirmed
- [ ] Project name and trademarks are compliant
- [ ] License headers are in all source files
- [ ] LICENSE file is in the repository
- [ ] CONTRIBUTING.md describes contribution process
- [ ] Legal review is complete

### Security
- [ ] Security audit is complete (internal or third-party)
- [ ] All critical/high-severity issues are resolved
- [ ] SECURITY.md documents security policy
- [ ] Vulnerability reporting process is defined

### Testing and Quality
- [ ] All unit tests pass on all platforms
- [ ] All integration tests pass
- [ ] Code coverage is documented
- [ ] CI/CD pipeline is green
- [ ] No TODOs or FIXMEs in code

### Documentation
- [ ] README.md is comprehensive and clear
- [ ] API documentation is complete
- [ ] Setup instructions are tested
- [ ] Architecture documentation is current
- [ ] Threat model is documented
- [ ] Examples are working and tested
- [ ] FAQ addresses common questions

### Packaging
- [ ] pyproject.toml is correct and complete
- [ ] Dependencies are pinned and minimal
- [ ] py.typed marker is present
- [ ] Package metadata is accurate
- [ ] SBOM is generated

### Infrastructure
- [ ] PyPI account is configured
- [ ] Trusted publishing is enabled (GitHub Actions)
- [ ] Release process is automated
- [ ] Release artifacts are signed (if applicable)
- [ ] GitHub releases are configured

### Announcement
- [ ] Release notes are written
- [ ] Announcement is reviewed
- [ ] Community channels are identified
- [ ] Blog post or article is prepared

---

## Current Status

**Stage 1:** ✅ Design and Feasibility (Complete)  
**Stage 2:** ⏳ Proof of Concept (v0.1) – Awaiting approval and team assignment  
**Stage 3:** ⏳ Hardening (v0.2) – Depends on Stage 2  
**Stage 4:** ⏳ Destinations (v0.3) – Depends on Stage 3  
**Stage 5:** ⏳ Release Prep (v1.0) – Depends on Stage 4 + IPIA clarification  

---

## Key Decisions to Make

1. **Before Stage 2:** Certificate/secret handling approach
2. **Before Stage 2:** Helper runtime distribution model
3. **Before Stage 4:** Azure authentication (DefaultAzureCredential vs. explicit)
4. **Before Stage 5:** IPIA response from Microsoft
5. **Before Stage 5:** Binary redistribution decision (bundled or separate)

---

## Timeline Estimate

- **Stage 2 (v0.1):** 4-6 weeks
- **Stage 3 (v0.2):** 2-3 weeks
- **Stage 4 (v0.3):** 3-4 weeks
- **Stage 5 (v1.0):** 1-2 weeks (depends on legal)

**Total: ~11-16 weeks from Stage 2 start to v1.0 release** (excluding IPIA delays)

---

## Go/No-Go Decisions

### After Stage 2
- Does the proof-of-concept work?
- Are security concerns addressed?
- **Decision:** Proceed to Stage 3 or iterate on Stage 2?

### After Stage 3
- Is the core stable and well-tested?
- **Decision:** Proceed to Stage 4 (destinations) or maintain v0.2 as-is?

### After Stage 4
- Do destinations work correctly?
- Is the complete feature set stable?
- **Decision:** Proceed to Stage 5 (release prep) or maintain v0.3 as internal tool?

### After Stage 5
- Has IPIA been resolved?
- Is the security audit complete?
- Are all blockers resolved?
- **Decision:** Publish v1.0 to PyPI or defer?

---

**Next Review:** After Stage 2 completion
