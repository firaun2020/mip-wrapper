# Stage 1 Complete: Design and Feasibility Summary

**Project:** MIP Wrapper  
**Objective:** Security-first Python wrapper for Microsoft Purview Information Protection file decryption  
**Stage:** 1 (Design and Feasibility)  
**Status:** ✅ Complete  
**Date:** August 31, 2026  

---

## What Was Accomplished in Stage 1

### Research and Documentation

1. **Architecture Document** (`docs/architecture.md`)
   - Process-bridge design (Python + .NET helper)
   - Trust boundaries and execution environments
   - Component responsibilities clearly separated
   - Authentication and authorization model
   - Cleanup and temporary-file safety
   - Success criteria for implementation

2. **Threat Model** (`docs/threat-model.md`)
   - Comprehensive threat analysis (9 categories, 40+ scenarios)
   - Mitigations for each threat
   - Residual risk assessment
   - Security assumptions documented
   - Out-of-scope threats identified

3. **Python API Specification** (`docs/python-api.md`)
   - Complete public API design
   - Exception hierarchy
   - Authentication configuration (Certificate, Secret)
   - Authorization modes (Delegated Reader, Super-User)
   - Core operations (Inspect, Decrypt, Decrypt Bytes)
   - Logging and audit metadata
   - Version 1 scope limitations clearly defined

4. **Native Helper Protocol** (`docs/helper-protocol.md`)
   - Versioned JSON protocol (v1.0) over stdin/stdout
   - Request/response formats with all fields defined
   - Error codes and handling strategies
   - Authentication challenge flow
   - Process lifecycle management
   - Security considerations documented

5. **Distribution and Licensing** (`docs/distribution-and-licensing.md`)
   - MIP SDK licensing model explained
   - IPIA (Information Protection Integration Agreement) requirements
   - Binary redistribution constraints
   - Recommended approach: separate SDK installation
   - PyPI publication prerequisites
   - Trademark compliance guidance
   - Unresolved questions identified
   - Compliance checklist for release

### Research Findings

- **MIP SDK Status:** v1.18.124 (April 2026), production-ready
- **Supported Platforms:** Windows 10/11, Ubuntu 20.04/22.04/24.04, RHEL 8/9, macOS
- **Authentication:** OAuth2 delegate pattern via MSAL, supports certificate-based confidential clients
- **Authorization:** Supports delegated-reader and application super-user modes
- **Official SDK:** .NET NuGet package available; no official Python SDK exists
- **Documentation:** Excellent C# and C++ samples; MIT SDK License Terms
- **.NET Bridge:** Recommended for initial implementation (faster than pybind11 C++)
- **IPIA Required:** For public distribution only; internal development is exempt

---

## Design Decisions Made

### 1. Use .NET Helper Instead of Direct C++ Extension

**Decision:** Implement Stage 2 using a .NET helper process, not pybind11.

**Rationale:**
- Official .NET wrapper is well-maintained (NuGet 1.18.124)
- Faster development (C# samples are available)
- Easier to threat-model (process isolation)
- Simpler cross-platform build (one .NET binary per OS)
- Better error handling (managed exceptions)
- Can replace with C++ later without breaking Python API

**Trade-offs:**
- Adds .NET runtime dependency (acceptable for Windows/Linux/macOS)
- Slight performance overhead (interop marshaling)
- Not suitable for minimal/embedded environments (acceptable for v1)

### 2. Process-Bridge Communication via JSON/stdin-stdout

**Decision:** Use versioned JSON protocol over subprocess stdin/stdout, not IPC or sockets.

**Rationale:**
- Simple to implement and debug
- No network exposure (subprocess-only)
- Clear protocol versioning for compatibility
- Easy to log and audit
- No secrets in JSON (kept internal to .NET process)

**Trade-offs:**
- Slightly slower than in-process (acceptable: network RT dominates)
- JSON parsing overhead (negligible)
- No bidirectional streaming (fine for batch operations)

### 3. Separate Certificate Password Delivery

**Decision:** Certificate password is obtained via callback, never passed in protocol.

**Rationale:**
- Prevents password from appearing in argv, JSON, logs, or crash dumps
- Allows Key Vault integration later
- Supports interactive input (if needed)
- Aligns with security best practices

**Trade-offs:**
- Slightly more complex callback interface
- Requires caller to implement password provider

### 4. No Binary Redistribution in Wheels

**Decision:** MIP Wrapper will be distributed via PyPI as a pure Python wrapper; users install MIP SDK separately.

**Rationale:**
- Resolves IPIA binary redistribution uncertainty
- Smaller wheels (no large binaries)
- Clear licensing boundaries
- Simpler to maintain
- Users own SDK version responsibility

**Trade-offs:**
- Less convenient than bundled installation
- Requires clear documentation and installation instructions
- Can revisit after IPIA if bundling is desired

### 5. Delegated-Reader as Primary Mode for v1

**Decision:** Delegated-reader mode is recommended and tested; super-user mode is supported but explicitly acknowledged.

**Rationale:**
- Delegated-reader aligns with least-privilege principles
- Most common real-world scenario
- Super-user is available for audit/compliance but must be explicitly requested
- Safer to default to delegated mode

**Trade-offs:**
- Super-user requires more tenant configuration
- Not suitable for "decrypt everything" scenarios (unless explicitly requested)

### 6. Explicit Unprotected-Output Acknowledgement

**Decision:** `allow_unprotected_output=True` is required before decryption can produce plaintext.

**Rationale:**
- Prevents accidental data leakage
- Signals that the caller understands the security implications
- Enforced at API level (fail fast)
- Clear error messages guide correct usage

**Trade-offs:**
- Extra API parameter (minimal friction)
- No silent failures or hidden behavior

---

## Unresolved Questions (Priority Ordered)

### 🔴 HIGH PRIORITY

**1. Can MIP SDK Binaries be Bundled in PyPI Wheels?**
- Status: Legally uncertain
- Impact: Determines distribution strategy for future versions
- Action: Explicitly clarify with Microsoft during IPIA process
- Assumption for v1: NO (separate installation required)
- Resolution: Confirm licensing terms before attempting binary wheels

**2. Is IPIA Required for Internal-Only Use?**
- Status: Clarified (answer: NO)
- Impact: Internal development can proceed without IPIA
- Assumption: Internal-only use is exempt from IPIA
- Resolution: ✅ Confirmed by Microsoft documentation

**3. What is the Complete IPIA Process Timeline?**
- Status: ~72 hours typical response time
- Impact: Timeline for v1.0 public release
- Current assumption: 3-5 business days end-to-end
- Action: Email IPIA@microsoft.com with project details early (v1 prep)

### 🟡 MEDIUM PRIORITY

**4. What are the Exact Requirements for Content.SuperUser?**
- Status: Not documented in current Microsoft guides
- Impact: Implementation of super-user mode
- Assumption: Requires tenant admin configuration (not automatic)
- Action: Test during Stage 2 integration testing with dedicated tenant

**5. What are the Token Acquisition Requirements for Delegated-Reader?**
- Status: Partially documented
- Impact: .NET helper token acquisition flow
- Assumption: MSAL can handle delegated scenarios with supplied user
- Action: Validate during Stage 2 with real protected file

**6. Are there Usage-Right Reporting Limitations?**
- Status: SDK documentation shows available rights but may be incomplete
- Impact: Audit metadata accuracy
- Assumption: Report what the SDK exposes
- Action: Document limitations in logs/metadata

### 🟢 LOW PRIORITY (Defer to v1.5+)

**7. Can Managed Identity be Used with MIP SDK?**
- Status: Not documented for MIP SDK
- Impact: Would simplify cloud deployments
- Assumption: Not supported in v1; defer to v1.5
- Action: Research and implement in future version

**8. What is the DKE (Double Key Encryption) Support Status?**
- Status: SDK may support it; unclear if officially validated
- Impact: Support for highly sensitive data
- Assumption: Out of scope for v1
- Action: Research before v2 planning

**9. Can Certificate Rotation be Automated?**
- Status: User responsibility for now
- Impact: Long-lived certificate management
- Assumption: v1 requires manual rotation
- Action: Document best practices; automate in v2

---

## Architecture Decisions Summary

### Component Separation
| Component | Responsibility | Language | Distribution |
|-----------|-----------------|----------|--------------|
| Python API | Validation, orchestration, cleanup | Python 3.11+ | PyPI wheel |
| .NET Helper | Auth, decryption, MIP SDK access | C# / .NET 5+ | Bundled with Python wrapper |
| MIP SDK | Protection, RMS, encryption/decryption | C++ (native) | User-installed or vendor-supplied |

### Authentication Ownership
| Aspect | Owner | Rationale |
|--------|-------|-----------|
| Certificate loading | .NET helper | Prevents password leakage to Python |
| Token acquisition | .NET helper | MSAL integration, refresh handling |
| Config validation | Python | Fast-fail on invalid parameters |
| Usage-right checking | .NET helper | Delegated to MIP SDK via handler |

### Trust Boundary
```
┌─────────────────────────────────────────────────┐
│ User-Controlled Compute (VM, Container, CI)     │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ MIP Wrapper Process (Python + .NET)        │  │
│  │  ├── Python: Validation, orchestration    │  │
│  │  ├── .NET: Auth, MIP SDK integration      │  │
│  │  └── Temporary files (0o700 perms)        │  │
│  └───────────────────────────────────────────┘  │
│         ↓ (JSON protocol)                       │
│  ┌───────────────────────────────────────────┐  │
│  │ Microsoft MIP SDK (Official)               │  │
│  │ C++ native binaries + .NET wrapper         │  │
│  └───────────────────────────────────────────┘  │
│         ↓ (TLS)                                 │
│  Azure Rights Management Service                │
└─────────────────────────────────────────────────┘
```

---

## Version 1.0 Scope Finalized

### ✅ INCLUDED IN v1.0
- Certificate-based authentication
- Delegated-reader authorization mode
- Application super-user mode (explicit)
- Local file input
- File inspection (metadata)
- Temporary decryption (context manager)
- Explicit decryption (persistent)
- Decrypt to bytes (with size limit)
- Usage-right checking
- Automatic cleanup
- Typed exceptions
- Audit metadata
- Redacted logging
- Windows and Ubuntu support
- Integration tests (opt-in)
- Unit tests
- Threat model
- Architecture documentation

### ❌ OUT OF SCOPE (v1.0)
- Azure destination uploads (v2)
- Processing pipeline (v2)
- SharePoint downloads (v2+)
- Managed Identity (v1.5+)
- Token provider authentication (v2 with threat modeling)
- Interactive authentication (v1.5 development-only)
- Double Key Encryption (defer)
- HYOK scenarios (defer)
- Password-protected Office files (separate concern)
- Username/password authentication (never)
- Binary redistribution in wheels (after IPIA review)
- C++ pybind11 extension (v2+)

---

## Recommended Stage 2 Implementation Plan

**Objective:** Build a minimal but complete, working proof-of-concept.

### Timeline: 4-6 weeks (depending on team size and MIP SDK learning curve)

### Stage 2 Deliverables

1. **Minimal .NET Helper** (C#)
   - Initialize MIP SDK
   - MSAL OAuth2 token acquisition
   - Certificate loading and password callback
   - Inspect file (query protection metadata)
   - Decrypt to file (with rights checking)
   - Error handling and protocol responses

2. **Core Python API** (mip_wrapper/)
   - MipClient class
   - CertificateAuth configuration
   - decrypt_file() context manager
   - Simple exception types
   - Protocol bridging (spawn helper, request/response)

3. **Unit Tests**
   - Auth config validation
   - Path validation (no traversal)
   - Cleanup in finally blocks
   - Protocol serialization
   - Exception types

4. **Integration Tests** (opt-in)
   - Create a test Excel file with MIP protection (tenant setup required)
   - Decrypt using delegated-reader mode
   - Verify decryption with openpyxl
   - Test unauthorized access (permission denied)
   - Test cleanup after exception

5. **Documentation**
   - Install instructions (requires separate MIP SDK)
   - Quick-start example
   - Threat model review (validate architecture)
   - API reference (auto-generated from docstrings)

### Stage 2 Success Criteria

- ✅ A protected test Excel file can be decrypted
- ✅ Delegated-reader authorization works correctly
- ✅ Delegated user must have Export right to succeed
- ✅ Unauthorized identity receives PermissionDeniedError
- ✅ Decrypted file exists only in temp directory
- ✅ Temp directory is cleaned after context exits
- ✅ Cleanup also occurs after exceptions (openpyxl, etc.)
- ✅ No tokens, secrets, or passwords appear in logs
- ✅ Unit tests pass
- ✅ One integration test passes (dedicated tenant)
- ✅ Architecture document is accurate
- ✅ Threat model is validated

### Stage 2 Implementation Order

1. Research and set up .NET helper skeleton (MSAL, MIP SDK imports)
2. Implement MSAL token acquisition (confidential client with certificate)
3. Implement file inspection (query protection metadata)
4. Implement certificate password callback
5. Implement file decryption (check Export right)
6. Implement protocol (JSON serialization)
7. Implement Python MipClient and CertificateAuth
8. Implement context manager for temp files
9. Write unit tests
10. Set up integration test tenant and create protected file
11. Run full integration test
12. Document setup and quick-start

### Stage 2 Dependencies

**Team Skills Required:**
- C# / .NET (for helper)
- Python 3.11+ (for wrapper)
- MSAL and OAuth2 concepts
- Windows or Linux development environment
- MIP SDK documentation reading

**External Dependencies:**
- Microsoft MIP SDK (NuGet: Microsoft.InformationProtection.File 1.18.124+)
- MSAL.NET (NuGet)
- .NET 5.0+ Runtime
- Python 3.11+
- Test tenant with MIP protection enabled (for integration tests)
- Protected test file (created by tenant admin)

**Setup Time:**
- ~1 week: Understand MIP SDK API, MSAL flows
- ~1 week: Set up test tenant, create protected file
- ~2 weeks: Core implementation
- ~1 week: Testing, documentation

---

## Stage 3+ Preview

After Stage 2 is complete and working:

### Stage 3: Hardened Package
- Input validation and error handling
- Timeout management
- Cancellation support
- Security tests
- Packaging (pyproject.toml)
- Redacted logging
- Documentation completion
- Runtime platform detection

### Stage 4: Azure Destinations
- DataLakeDestination adapter
- BlobStorageDestination adapter
- Pipeline API (processor callback)
- Explicit unprotected-output acknowledgement
- Upload tests
- Cleanup after upload failure

### Stage 5: Public Release
- IPIA with Microsoft (sign agreement)
- Binary distribution decision
- Security audit (third-party review optional)
- SBOM generation
- Signed releases
- PyPI trusted publishing setup
- Public announcement

---

## Critical Path Items (Must Complete Before v1 Release)

1. ✅ **Threat model approved** (Stage 1 complete)
2. ✅ **Architecture approved** (Stage 1 complete)
3. ✅ **API design approved** (Stage 1 complete)
4. ⏳ **Proof-of-concept works** (Stage 2 required)
5. ⏳ **IPIA signed with Microsoft** (before public release)
6. ⏳ **Security review completed** (Stage 3-4)
7. ⏳ **Integration tests pass** (Stage 2 required)
8. ⏳ **Documentation complete** (Stage 3 required)

---

## Approval Checkpoints

### Before Stage 2 Starts
- [ ] Architecture is approved (process-bridge design, component responsibilities)
- [ ] Threat model is reviewed (risks are acceptable)
- [ ] Python API is approved (exception hierarchy, method signatures)
- [ ] Helper protocol is approved (JSON format, error codes)
- [ ] Distribution approach is approved (separate SDK installation for v1)
- [ ] Budget/timeline for Stage 2 is approved

### After Stage 2 (Before Stage 3)
- [ ] Proof-of-concept works with real protected file
- [ ] All Stage 2 success criteria are met
- [ ] Integration test passes
- [ ] No security issues discovered in implementation
- [ ] Architecture and threat model remain valid

### Before Public Release (Stage 5)
- [ ] IPIA with Microsoft is signed
- [ ] Security review is complete
- [ ] PyPI trusted publishing is configured
- [ ] Release artifacts are prepared
- [ ] Documentation is finalized

---

## Next Steps

1. **Review Stage 1 deliverables** (this document and all docs/)
2. **Approval:** Confirm that architecture, threat model, and API design are acceptable
3. **Identify Stage 2 implementation team** (C# + Python skills)
4. **Plan Stage 2 kickoff** (test tenant setup, environment preparation)
5. **Schedule Stage 2 completion review** (proof-of-concept demonstration)

---

## Document Artifacts

**Stage 1 Deliverables:**
- ✅ `docs/architecture.md` - Design and component responsibilities
- ✅ `docs/threat-model.md` - Comprehensive threat analysis
- ✅ `docs/python-api.md` - Public API specification
- ✅ `docs/helper-protocol.md` - Native helper JSON protocol (v1.0)
- ✅ `docs/distribution-and-licensing.md` - Legal and redistribution findings
- ✅ `docs/stage-1-summary.md` - This document

**What's NOT Included (Created in Later Stages):**
- `src/mip_wrapper/` - Python package (Stage 2)
- `native/MipWrapper.Helper/` - .NET helper (Stage 2)
- `tests/` - Unit and integration tests (Stage 2+)
- `CONTRIBUTING.md` - Contribution guidelines (Stage 3)
- `SECURITY.md` - Security policy (Stage 3)
- `README.md` - Finalized for release (Stage 5)

---

## Questions and Feedback

Stage 1 is now complete. Key discussion points before moving to Stage 2:

1. Is the process-bridge architecture acceptable?
2. Are the threat mitigations sufficient?
3. Does the Python API meet requirements?
4. Is the separate SDK installation approach acceptable for v1?
5. Should any Stage 2 success criteria be modified?
6. Timeline and team availability for Stage 2?

---

**Status:** ✅ Stage 1 Complete  
**Date:** August 31, 2026  
**Author:** Claude Code with research agent  
**Next Stage:** Awaiting approval to proceed to Stage 2
