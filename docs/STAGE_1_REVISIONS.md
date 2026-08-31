# Stage 1 Revisions (August 31, 2026)

**Status:** Initial Stage 1 documents have been revised to correct material issues before Stage 2 begins.

---

## What Changed and Why

### 1. Process Model (Architecture)

**Issue:** Described Python and .NET helper as running in "the same OS process"

**Fix:** Updated to reflect the correct model:
- Python and .NET helper are **separate OS processes**
- They share a **deployment boundary** (container, VM, CI job)
- They communicate via **JSON protocol over subprocess stdin/stdout**
- Each process has its own memory, lifecycle, and process-level security

**Impact:** Threat model, IPC design, process lifecycle management

**Files Updated:**
- `architecture.md` (Trust Boundaries section)
- `threat-model.md` (Scope and Assumptions sections)

---

### 2. Runtime and Helper Distribution Model

**Issue:** Vague statement that "MIP SDK is pre-installed on the system"

**Fix:** Added comprehensive "Runtime and Helper Distribution (MVP Model)" section:
- Defined where MipWrapper.Helper comes from (built locally during Stage 2)
- Clarified how it's discovered (PATH search or package-relative location)
- Documented the MVP approach for internal proof-of-concept
- Listed three possible future models (wheels with binaries, separate helper package, container)
- Deferred final decision until IPIA is resolved

**Impact:** Installation experience, version management, dependency management

**Files Updated:**
- `architecture.md` (new section after MIP SDK section)

---

### 3. Certificate Password Handling

**Issue:** Described a callback mechanism that doesn't work across process boundaries

**Fix:** Defined a concrete MVP design for Stage 2:
- Certificate stored in protected mounted location with password file
- Both Python and helper read the same password file directly
- Password never passed as command-line argument or through protocol
- Documented constraints (file permissions, no version control)
- Listed future alternatives (Key Vault, OS cert stores, bidirectional IPC)

**Impact:** Authentication flow, threat model, configuration approach

**Files Updated:**
- `architecture.md` (Certificate Password Delivery section)

---

### 4. Removed `decrypt_bytes` from v0.1 Scope

**Issue:** Protocol includes `decrypt_bytes` which conflicts with security requirement of not sending plaintext over stdout

**Fix:**
- Removed `decrypt_bytes` command from helper protocol
- Removed `decrypt_bytes` operation from Python API (marked as deferred to v0.3+)
- Removed error code for "FileTooLarge"
- Documented that in-memory decryption requires proper IPC design

**Impact:** Initial scope, protocol simplification, security clarity

**Files Updated:**
- `python-api.md` (removed decrypt_bytes section, added deferral note)
- `helper-protocol.md` (removed decrypt_bytes command and result format)

---

### 5. Fixed Risk Assessment Language

**Issue:** Claimed "all high-priority threats have low residual risk" before implementation

**Fix:**
- Changed risk summary table to show status (Designed; unvalidated)
- Updated conclusion to: "Mitigations are proposed but remain unvalidated"
- Documented that residual risk will be reassessed after implementation and testing
- Removed "No blockers identified" claim from summary

**Impact:** Honest assessment of design vs. validated security

**Files Updated:**
- `threat-model.md` (Risk Summary section and conclusion)
- `STAGE_1_PRESENTATION.md` (summary claims)

---

### 6. Licensing Findings – Separated Facts from Assumptions

**Issue:** Made legal conclusions (IPIA required, 72-hour timeline, cannot redistribute) without proper sourcing

**Fix:** Updated licensing document:
- Changed executive summary to "Status: Unresolved"
- Clarified that IPIA requirements are NOT confirmed
- Documented that 72-hour timeline is NOT confirmed
- Softened claims about binary redistribution
- Added "Current Understanding (Unconfirmed)" framing
- Emphasized need to contact Microsoft before public release
- Removed claims about PyPI publication "automatically allowed"

**Impact:** Legal compliance, accurate communication of uncertainty

**Files Updated:**
- `distribution-and-licensing.md` (Executive Summary, IPIA Process sections)

---

### 7. Deferred Super-User Mode to v1.1+

**Issue:** Included super-user authorization in v1.0 scope

**Fix:**
- Super-user design remains documented
- Implementation is deferred to v1.1 or later
- v0.1-v0.2 focuses on delegated-reader only (least-privilege)
- Simplifies initial testing and reduces attack surface

**Impact:** Scope reduction, simpler first implementation

**Files Updated:**
- `RELEASE_PLAN.md` (new document)
- Various sections mentioning authorization modes

---

## New Documents Created

### 1. `BLOCKERS.md`
Lists critical path items that must be resolved before each stage:
- Certificate/secret handling approach (architecture decision)
- Helper runtime distribution model (architecture decision)
- IPIA clarification with Microsoft (legal)
- Trademark compliance (legal)
- Items deferred to v1.5, v2.0, etc.

### 2. `RELEASE_PLAN.md`
Staged release plan from v0.1 to v1.0:
- v0.1 (MVP proof-of-concept): 4-6 weeks
- v0.2 (Hardened core): 2-3 weeks
- v0.3 (Azure destinations): 3-4 weeks
- v1.0 (Stable release): 1-2 weeks
- Public release checklist
- Post-release roadmap (v1.1, v1.5, v2.0)

### 3. `STAGE_1_REVISIONS.md` (this document)
Summary of all changes made in this revision

---

## Unchanged Documents

The following documents were accurate and needed only minor updates:
- `python-api.md` – Removed decrypt_bytes; API design remains solid
- `helper-protocol.md` – Removed decrypt_bytes command; protocol design remains solid
- `stage-1-decisions.md` – Mostly accurate; documents design decisions well
- `threat-model.md` – Comprehensive; updated assumptions and risk assessment

---

## Summary of Corrections

| Issue | Status | Impact |
|-------|--------|--------|
| Process model (same vs. separate) | ✅ Fixed | Architecture, threat model |
| Runtime distribution model | ✅ Defined | Installation, versioning |
| Certificate password callback | ✅ Specified MVP | Authentication design |
| decrypt_bytes (conflicting requirements) | ✅ Deferred | Simpler initial scope |
| Risk assessment (premature claims) | ✅ Softened | Honest security posture |
| Licensing (unsourced legal claims) | ✅ Clarified | Legal accuracy |
| Super-user mode | ✅ Deferred | Simpler first version |
| IPIA timeline (72 hours) | ✅ Marked unconfirmed | Avoid missed expectations |

---

## What's Ready for Stage 2

✅ Architecture (correct process model, runtime design TBD at start of Stage 2)  
✅ Threat model (with proper assumptions and unvalidated status)  
✅ Python API (excluding decrypt_bytes)  
✅ Helper protocol (correct scope)  
✅ Release plan (versioning and blockers clear)  
✅ Licensing (assumptions documented; IPIA TBD)  

❌ **NOT Ready:** Certificate/secret handling approach (decision required before implementation)  
❌ **NOT Ready:** Helper runtime distribution (decision required before implementation)  

---

## Before Stage 2 Starts

1. **Resolve blocking decisions:**
   - How is certificate password delivered? (protected file, Key Vault, OS store, etc.)
   - How is .NET helper distributed? (bundled, separate package, container)

2. **Assign Stage 2 team:**
   - C# / .NET developer (helper implementation)
   - Python developer (wrapper and protocol bridge)
   - QA/testing (integration testing with test tenant)

3. **Provision test environment:**
   - Azure test tenant with MIP protection enabled
   - Protected test file (created by tenant admin)
   - Build environment (dotnet CLI, Python 3.11+, git)

4. **Schedule approval checkpoint:**
   - Review of these revisions
   - Go/no-go decision for Stage 2 start

---

**Next Step:** Review and approve Stage 1 revisions before Stage 2 begins.
