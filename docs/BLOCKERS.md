# Stage 1 Blockers and Critical Path Items

**Status:** These items must be resolved before proceeding to Stage 2 implementation or public release.

---

## Blockers Resolved in Stage 1

- [x] Architecture: Trust boundary and component separation
- [x] Security: Threat model with mitigations
- [x] API: Python interface specification
- [x] Protocol: Versioned JSON communication design

## Remaining Blockers

### Critical for Stage 2 Implementation

**1. Certificate and Secret Handling (Architecture)**
- [ ] Confirm the MVP design for certificate password delivery
- [ ] Options: protected file, Key Vault direct access, OS cert store, or other
- [ ] Must be defined BEFORE implementation starts
- [ ] Impact: Core authentication flow

**2. Helper Runtime and Distribution (Architecture)**
- [ ] How is the .NET helper built? (automated build, manual compilation, cloud build)
- [ ] Where does it come from? (bundled in Python package, separate installation, container)
- [ ] How is it versioned? (SemVer, tied to Python package version, independent)
- [ ] How does Python discover/spawn it? (PATH search, fixed location, helper package query)
- [ ] How are .NET and native MIP dependencies managed?
- [ ] Impact: Installation experience, dependency management, update strategy

**3. Super-User Mode (Design)**
- [ ] Defer implementation to v1.1 or later
- [ ] First milestone (v0.1-v0.2) supports delegated-reader only
- [ ] Impact: Scope, testing strategy, authorization design

### Critical for Public Release

**4. IPIA and Distribution Rights (Legal)**
- [ ] Contact Microsoft to clarify IPIA requirements for community projects
- [ ] Confirm whether MIP SDK binaries can be redistributed in PyPI wheels
- [ ] Confirm timeline and current process with IPIA team
- [ ] Obtain legal review before PyPI publication
- [ ] Impact: Version 1.0 release date, distribution model, packaging approach

**5. Trademark and Project Name Compliance (Legal)**
- [ ] Verify "MIP Wrapper" project name complies with Microsoft trademark guidelines
- [ ] Confirm "unofficial community wrapper" disclaimer is sufficient
- [ ] Impact: Public announcement, documentation, PyPI metadata

---

## Items Deferred to Later Versions

### v0.3 (Destinations)
- ADLS Gen2 and Blob Storage adapters
- Pipeline API for processor callbacks
- Requires core (v0.1-v0.2) to be stable first

### v1.1 (Super-User and Compliance)
- Application super-user authorization mode
- Requires delegated-reader to be fully tested

### v1.5 (Advanced Auth)
- Managed Identity support
- Interactive authentication (for development)
- Certificate rotation automation
- Azure Key Vault integration

### v2.0+ (Future)
- C++ pybind11 extension (replace .NET bridge if needed)
- In-memory decryption API (decrypt_bytes)
- SharePoint source adapter
- Token provider authentication (after threat modeling)

---

## Decision Points Before Each Stage

### Before Stage 2 (Implementation)
- [ ] Certificate/secret handling approach is decided
- [ ] Helper runtime model is decided
- [ ] Team is assigned and has .NET + Python skills
- [ ] Test tenant is provisioned (for integration tests)
- [ ] Build environment is set up (dotnet CLI, Python, git)

### Before Stage 3 (Hardening)
- [ ] Stage 2 proof-of-concept works with real protected file
- [ ] All v0.1 integration tests pass
- [ ] No critical security issues found
- [ ] Architecture and threat model are validated

### Before Stage 4 (Destinations)
- [ ] Stage 3 core package is stable and reviewed
- [ ] Azure credentials/authentication approach is decided
- [ ] Upload retry and failure handling are specified

### Before Stage 5 (Public Release)
- [ ] IPIA requirements are confirmed with Microsoft
- [ ] Legal review is complete
- [ ] Security audit is complete (internal or third-party)
- [ ] All tests pass on all supported platforms
- [ ] Documentation is complete and reviewed

---

## External Dependencies Requiring Confirmation

### From Microsoft
1. IPIA requirements and process (contact IPIA@microsoft.com)
2. Binary redistribution permissions
3. Current MIP SDK support matrix (platform versions, .NET versions)
4. Trademark guidelines for "MIP" usage

### From Organization
1. Legal review of proposed licensing
2. Budget and timeline for Stages 2-5
3. Test tenant setup for integration testing
4. Decision on internal vs. public distribution

---

## Risk: These Claims Need Validation

- "IPIA is required for public distribution" – Not confirmed
- "IPIA response takes ~72 hours" – Not confirmed
- "MIP SDK binaries cannot be redistributed in wheels" – Not confirmed
- "Internal development is exempt from IPIA" – Likely true but not confirmed
- "Separate processes with 0o700 temp files are secure" – Designed but unvalidated

**Action:** Do not publish or release claims about these items until they are confirmed or tested.

---

## Next Review: Before Stage 2 Kickoff

Ensure all critical-path blockers are resolved before beginning implementation work.
