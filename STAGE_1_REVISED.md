# Stage 1 Revised and Corrected

**Status:** Material issues have been fixed. Ready for review and approval before Stage 2.

---

## What Was Fixed

### Critical Issues Corrected

1. **Process Model** ✅
   - Corrected: Python and .NET helper run in **separate OS processes** (not same process)
   - Implication: Shared deployment boundary, but distinct memory and lifecycle
   - Files: `architecture.md`, `threat-model.md`

2. **Runtime Distribution** ✅  
   - Added concrete MVP model for Stage 2
   - Identified three possible future models
   - Deferred final decision until IPIA clarified
   - Files: `architecture.md` (new "Runtime and Helper Distribution" section)

3. **Certificate Password Handling** ✅
   - Specified concrete MVP approach (protected file + password file)
   - Documented constraints and future alternatives
   - No callback across process boundaries in v0.1
   - Files: `architecture.md` (revised "Certificate Password Delivery" section)

4. **Removed decrypt_bytes** ✅
   - Conflicted with security requirement (no plaintext over stdout)
   - Deferred to v0.3+ with proper IPC design
   - Files: `python-api.md`, `helper-protocol.md`

5. **Risk Assessment** ✅
   - Changed from "low residual risk" to "designed but unvalidated"
   - Honest about validation needed after implementation
   - Files: `threat-model.md`

6. **Licensing Findings** ✅
   - Separated assumptions from confirmed facts
   - Removed unsupported claims about IPIA timeline
   - Documented need to contact Microsoft
   - Noted "internal development is exempt" as likely but unconfirmed
   - Files: `distribution-and-licensing.md`

7. **Super-User Mode** ✅
   - Deferred from v1.0 to v1.1+
   - First implementation focuses on delegated-reader (least-privilege)
   - Documented in release plan

---

## New Documents Created

1. **`BLOCKERS.md`** – Critical path items that must be resolved
2. **`RELEASE_PLAN.md`** – Staged v0.1 → v1.0 with timelines and go/no-go decisions
3. **`STAGE_1_REVISIONS.md`** – Detailed change log of all fixes

---

## What Remains Unresolved (Blocking Stage 2 Start)

These decisions must be made BEFORE implementation begins:

### 1. Certificate/Secret Handling
**Decision Required:** How does the helper obtain the certificate password?
- Option A: Shared password file in protected location (current MVP)
- Option B: Helper reads from Azure Key Vault directly (MSI)
- Option C: OS certificate store (Windows DPAPI, Linux keyring)
- Option D: Bidirectional IPC callback (requires threat modeling)
- Option E: Other approach

**Impact:** Architecture decision, affects authentication flow

### 2. Helper Runtime Distribution
**Decision Required:** How is MipWrapper.Helper delivered to users?
- Option A: Bundled in Python wheel (after IPIA approval)
- Option B: Separate versioned helper package
- Option C: Precompiled binaries in releases (with instructions)
- Option D: Container image (ACI, AKS, Cloud Run)
- Option E: Built locally by users (requires .NET SDK)

**Impact:** Installation experience, versioning strategy, dependency management

### 3. IPIA and Licensing
**Decision Required:** Contact Microsoft to clarify:
- Is IPIA required for open-source community projects?
- Can MIP SDK binaries be redistributed in PyPI wheels?
- What is the current process and timeline?
- Are there special terms for unpaid open-source projects?

**Impact:** Public release timeline, distribution model, legal compliance

---

## What's Ready for Stage 2

✅ **Architecture** – Process model, components, trust boundaries clearly defined  
✅ **Security** – Threat model comprehensive with unvalidated status noted  
✅ **Python API** – Specification complete (minus decrypt_bytes)  
✅ **Helper Protocol** – Versioned JSON protocol v1.0 defined  
✅ **Release Plan** – v0.1 → v1.0 with clear milestones  
✅ **Blockers List** – Critical path items identified  

❌ **NOT Ready for Code:** Blocking decisions above must be made first

---

## Recommended Next Steps

### 1. Review (This Week)
- Read revised documents, especially:
  - `STAGE_1_REVISIONS.md` (summary of changes)
  - `BLOCKERS.md` (what must be decided)
  - `RELEASE_PLAN.md` (timeline and versions)

### 2. Make Blocking Decisions (Next Week)
- Decide: Certificate/password handling approach for Stage 2
- Decide: Helper runtime distribution model for Stage 2
- Assign: Stage 2 implementation team

### 3. Clarify with Microsoft (Before Stage 2)
- Email IPIA@microsoft.com with project details
- Ask about binary redistribution permissions
- Ask about open-source project terms
- Document Microsoft's responses

### 4. Prepare Stage 2 (Before Code Starts)
- Provision test tenant and protected test file
- Set up build environment
- Create git repository and CI/CD pipeline
- Define Stage 2 success criteria in detail

### 5. Go/No-Go Decision (Before Implementation)
- Architecture and decisions are approved
- Team is assigned and ready
- Environment is provisioned
- Proceed to Stage 2 implementation

---

## Document Status

| Document | Status | Notes |
|----------|--------|-------|
| architecture.md | ✅ Revised | Process model fixed, runtime model added |
| threat-model.md | ✅ Revised | Assumptions corrected, risk assessment updated |
| python-api.md | ✅ Revised | decrypt_bytes deferred |
| helper-protocol.md | ✅ Revised | decrypt_bytes command removed |
| distribution-and-licensing.md | ✅ Revised | Legal claims softened, IPIA marked unresolved |
| stage-1-decisions.md | ✅ Current | No major changes needed |
| BLOCKERS.md | ✨ New | Critical path items |
| RELEASE_PLAN.md | ✨ New | v0.1 → v1.0 with timelines |
| STAGE_1_REVISIONS.md | ✨ New | Change log and summary |

---

## Key Changes at a Glance

```
BEFORE (Issues)          →  AFTER (Corrected)
──────────────────────────────────────────────
Same-process            →  Separate processes, shared deployment
"MIP SDK pre-installed" →  Concrete MVP distribution model
Callback across IPC     →  Protected file for cert password
decrypt_bytes included  →  Deferred to v0.3+
"Low residual risk"     →  "Designed but unvalidated"
"72-hour IPIA response" →  "Timeline unconfirmed – ask Microsoft"
v1.0 with super-user    →  v0.1-0.2 delegated-reader only; super-user v1.1+
"No blockers"           →  Clear blocking decisions listed
```

---

## Approval Checklist

Before proceeding to Stage 2:

- [ ] All revisions have been reviewed
- [ ] Process model (separate processes) is acceptable
- [ ] Runtime distribution decisions are made
- [ ] Certificate/password handling approach is decided
- [ ] IPIA clarification request is being sent to Microsoft
- [ ] Test tenant and environment are provisioned
- [ ] Stage 2 team is assigned
- [ ] Go/no-go decision is made

---

**Status:** Stage 1 revisions complete. Awaiting review and approval before Stage 2 begins.

**Next:** Review the new `BLOCKERS.md` and `RELEASE_PLAN.md` documents, then make the three blocking decisions.
