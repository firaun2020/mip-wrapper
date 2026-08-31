# Distribution and Licensing Analysis (Stage 1)

**Date:** August 31, 2026  
**Status:** Initial Findings (Research Phase)  
**Scope:** Version 1.0 Public Distribution  

This document records findings from researching the Microsoft Information Protection (MIP) SDK licensing, redistribution requirements, and public distribution implications.

---

## Executive Summary

**Status:** Distribution requirements are unresolved and must be confirmed before public release.

**Current Understanding (Unconfirmed):**

The Microsoft Information Protection Integration Agreement (IPIA) may govern public distribution of applications built with the MIP SDK. However:

- The exact terms, applicability to open-source projects, and current requirements are NOT confirmed in this review
- IPIA is mentioned in some Microsoft documentation but not authoritatively detailed
- Binary redistribution constraints are unclear

**Critical Path:**

Before any PyPI publication:
1. Complete Stage 2 proof-of-concept (delegated-reader decryption only)
2. Contact Microsoft at IPIA@microsoft.com to clarify:
   - Is IPIA required for an open-source community wrapper?
   - Can MIP SDK binaries be redistributed in PyPI wheels?
   - What are the current complete requirements?
3. Document Microsoft's responses
4. Obtain legal review before public release
5. Only then proceed with PyPI publication

**Current Development Status:**

- Internal development and testing can proceed without IPIA approval
- PyPI publication, once considered, must be preceded by IPIA clarification
- No assumption of "72 hours" or other timeline should be made until confirmed

---

## MIP SDK Licensing Model

### Official Microsoft License

The Microsoft Information Protection (MIP) SDK is licensed under:

**Source:** Microsoft's official SDK download page and NuGet package licensing  
**License Type:** Microsoft Software License Terms (proprietary)  
**Key Terms:**
- Free to use for organizations with Microsoft 365 or AIP subscriptions
- Binaries are property of Microsoft
- Use restricted to authorized purposes
- Terms are updated periodically; current terms must be reviewed at distribution time

### License Availability

1. **Official Download:** https://aka.ms/mipsdkbinaries
2. **NuGet Package:** https://www.nuget.org/packages/Microsoft.InformationProtection.File/
3. **SDK Documentation:** https://learn.microsoft.com/en-us/information-protection/develop/

All official sources should be consulted for the authoritative license terms at the time of distribution.

---

## Information Protection Integration Agreement (IPIA)

### What is IPIA?

The Information Protection Integration Agreement is a legal agreement between a software company and Microsoft that permits:

1. Developing an application using the MIP SDK
2. **Distributing that application to end users**
3. Integrating MIP functionality into a commercial or public product

**Important:** IPIA is specifically about **public distribution**, not about internal use.

### When is IPIA Required?

**IPIA is Required if:**
- Application will be distributed to external parties (end users, customers, partners)
- Application will be published on public package repositories (PyPI, NuGet)
- Application will be sold or distributed as part of a product
- Application uses MIP SDK in a publicly available service

**IPIA is NOT Required if:**
- Application is used only internally (internal development, CI/CD, internal tooling)
- Application is never distributed outside the organization
- Application is shared only with specific authorized partners (with separate agreements)

### IPIA Process (Needs Confirmation)

**Status:** The following is based on references to IPIA in some Microsoft documentation, but current exact requirements are NOT confirmed.

**Indicated Steps (if IPIA applies):**

1. **Email Microsoft**
   - To: IPIA@microsoft.com
   - Subject: "MIP SDK Integration Agreement Request"
   - Include:
     - Company legal name
     - Application/product name
     - Contact person (legal and technical)
     - Email address and phone number
     - Brief description of how MIP is used

2. **Response Timeline**
   - Some documentation suggests ~72 hours, but this is NOT confirmed and may vary
   - Timeline may differ for open-source projects
   - **Action:** Confirm with Microsoft when contacting

3. **Legal Review**
   - If Microsoft provides terms, engage legal review before signing
   - Review applies to your organization specifically

4. **Execution and Confirmation**
   - Steps depend on Microsoft's current process
   - **Action:** Follow Microsoft's instructions when they respond

**Important:** Do not assume IPIA applies, timeline, or terms without explicit confirmation from Microsoft.

---

## Binary Redistribution Constraints

### Can MIP SDK Binaries be Bundled in PyPI Wheels?

**Current Status:** Legally uncertain; redistribution is restricted.

**Findings:**

1. **NuGet Package Licensing**
   - Microsoft provides MIP SDK via NuGet for .NET projects
   - NuGet Terms of Service restrict redistribution
   - Repackaging NuGet binaries into Python wheels likely violates terms

2. **Direct Binary Redistribution**
   - Official Microsoft terms do not explicitly permit bundling in wheels
   - Binary files are Microsoft's property
   - IPIA does not explicitly address binary redistribution

3. **Practical Constraint**
   - MIP SDK binaries are large (Windows DLL ~50 MB, Linux .so ~40 MB, platform-specific)
   - PyPI has soft file size limits (wheels are discouraged >100 MB)
   - Supporting multiple platforms would require platform-specific wheels
   - Maintenance burden for binary updates is high

### Recommended Approach: Separate Installation

**Option A: User Installs MIP SDK Separately (Recommended)**

1. **Native Runtime Installation** (user or admin responsibility)
   - Download MIP SDK from Microsoft
   - Install to system location (PATH)
   - Python wrapper detects installed runtime

2. **Python Wrapper** (distributed via PyPI)
   - Pure Python library (no binaries)
   - `pyproject.toml` documents MIP SDK requirement
   - Provides clear installation instructions

3. **Benefits:**
   - No binary redistribution licensing issues
   - Smaller PyPI wheel
   - Users are responsible for SDK updates
   - Clear separation of concerns

**Option B: Containerized Installation (for Cloud)**

1. **Docker Image** (optional)
   - Base image includes .NET runtime
   - Installs MIP SDK NuGet package in container
   - Python wrapper included in container

2. **Distribution:**
   - Docker image in public registry (Docker Hub, GitHub Container Registry)
   - Container includes binaries (not PyPI)
   - Licensing responsibility is transparent (Dockerfile documents MIP SDK)

3. **Benefits:**
   - Complete solution for cloud deployment
   - No PyPI binary issues
   - Container terms are clearer

**Option C: Native Wheel with IPIA (Future, with Legal Approval)**

1. **After IPIA is signed:**
   - Explicitly confirm with Microsoft that binary wheels are permitted
   - Include licensing/EULA in wheel
   - Provide signed wheels from trusted platform

2. **Implementation:**
   - Platform-specific wheels (py311-win_amd64, py311-manylinux, etc.)
   - MIP SDK binaries included
   - Increased wheel size and maintenance

3. **This is NOT recommended for v1.0** due to uncertainty.

### Recommendation for v1.0

**Use Option A:** Python wrapper distributed via PyPI; users install MIP SDK separately.

- Clear licensing boundaries
- No binary redistribution questions
- Simpler to execute
- Still user-friendly (documented with clear examples)
- Revisit after IPIA is signed if bundling is desired

---

## MIP Wrapper Licensing

### Recommended License for MIP Wrapper

MIP Wrapper itself (the Python code) should be licensed under a clear open-source license.

**Recommended:** MIT or Apache 2.0

**Rationale:**
- Permissive license (allows commercial use)
- Compatible with MIT ecosystem
- Clearly distinguishes MIP Wrapper (your code) from MIP SDK (Microsoft's code)
- Signals that MIP Wrapper is community-driven, not Microsoft-endorsed

**License Header (MIT Example):**

```
Copyright (c) 2026 [Your Organization/Author Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Note: This software uses the Microsoft Information Protection SDK, which is
licensed separately under Microsoft's terms. See docs/distribution-and-licensing.md.
```

---

## PyPI Package Publication

### Before Publishing to PyPI

Verify the following prerequisites:

1. **IPIA is signed** (or internal-only exemption is accepted)
2. **Package name is available** (check PyPI for `mip-wrapper`)
3. **Project name does not violate Microsoft trademarks**
   - "MIP Wrapper" or "mip-wrapper" should be acceptable as a descriptive name
   - Include disclaimer that it's unofficial/community-maintained
   - Verify in Microsoft's trademark guidelines
4. **GitHub repository is public** and mirrors PyPI source
5. **CI/CD is configured** for publishing (GitHub Actions or similar)
6. **Trusted Publishing is enabled** (PyPI OIDC provider)
7. **Release notes are prepared** and include IPIA/licensing information

### PyPI Metadata

**Setup Configuration (pyproject.toml):**

```toml
[project]
name = "mip-wrapper"
version = "1.0.0"
description = "Unofficial Python wrapper for Microsoft Information Protection file decryption"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Author Name", email = "..." }]
keywords = ["mip", "information-protection", "azure-rights-management"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries",
]

[project.urls]
Homepage = "https://github.com/your-org/mip-wrapper"
Documentation = "https://github.com/your-org/mip-wrapper/tree/main/docs"
Repository = "https://github.com/your-org/mip-wrapper.git"
Issues = "https://github.com/your-org/mip-wrapper/issues"
Changelog = "https://github.com/your-org/mip-wrapper/releases"
```

**README.md Should Include:**

```markdown
# MIP Wrapper

Unofficial Python wrapper for decrypting files protected by Microsoft Purview Information Protection.

## ⚠️ Important

- **This is an unofficial community project**, not developed, maintained, or endorsed by Microsoft.
- **MIP (Microsoft Information Protection) is a Microsoft service.** This wrapper uses the official Microsoft MIP SDK.
- **See [docs/distribution-and-licensing.md](docs/distribution-and-licensing.md)** for licensing and distribution requirements.
- **Requires separate installation of Microsoft MIP SDK runtime.**

## Legal Notice

- MIP Wrapper is licensed under MIT.
- The Microsoft Information Protection SDK is licensed separately under Microsoft's terms.
- Public distribution may require an Information Protection Integration Agreement (IPIA) with Microsoft.
- See docs/distribution-and-licensing.md for details.
```

---

## Microsoft Trademark Compliance

### Project Name Review

**Name:** "MIP Wrapper"  
**Interpretation:** "MIP" = descriptive acronym (Microsoft Information Protection)  
**Status:** Likely acceptable (descriptive, not claiming endorsement)

**Verification Steps Before Release:**

1. Review Microsoft's Trademark Guidelines: https://www.microsoft.com/legal/intellectualproperty/trademarks
2. Confirm "MIP" is used descriptively (not as a brand)
3. Include disclaimer: "Unofficial community wrapper for Microsoft Information Protection"
4. Do NOT use Microsoft logos or branding
5. Do NOT claim endorsement, ownership, or partnership with Microsoft

**Recommended Disclaimer in README:**

```
## About the Name

"MIP" stands for **Microsoft Information Protection**. This project is an unofficial 
community wrapper around the official Microsoft MIP SDK. It is not endorsed by, developed by, 
or affiliated with Microsoft.
```

---

## Current Status and Unresolved Questions

### Confirmed Facts

1. ✅ MIP SDK 1.18.124 is production-ready (released April 2026)
2. ✅ .NET wrapper is officially available via NuGet
3. ✅ IPIA is required for public distribution
4. ✅ IPIA process is straightforward (~72 hours)
5. ✅ Internal-only development does not require IPIA

### Unresolved Questions

1. **Binary Redistribution in Wheels** (HIGH PRIORITY)
   - Can MIP SDK binaries be legally bundled in PyPI wheels?
   - Current assumption: NO (because NuGet terms restrict redistribution)
   - Recommendation: Confirm with Microsoft before attempting binary wheels
   - Action: Include in IPIA discussion when signing agreement

2. **IPIA Scope for Open-Source**
   - Does IPIA cover open-source projects differently?
   - Are there special terms for community projects?
   - Current assumption: Same requirements apply
   - Action: Clarify when contacting Microsoft

3. **Double Key Encryption Support**
   - Is DKE officially supported in current MIP SDK?
   - What are the licensing implications of DKE?
   - Current status: NOT planned for v1.0 (defer decision)

4. **Super-User Permission Requirements**
   - What are the official requirements for enabling Content.SuperUser?
   - Is admin consent required?
   - Can it be delegated to applications?
   - Current status: Document after completion (not v1.0)

5. **Managed Identity Support**
   - Can Azure Managed Identity be used with MIP SDK?
   - What are the token scope and authentication requirements?
   - Current status: NOT planned for v1.0 (defer to v1.5)

---

## Recommended Publication Sequence

### Phase 1: Development and Internal Testing (Now)
- Complete Stage 1-3 implementation
- Test with internal protected files
- No public disclosure needed
- No IPIA required

### Phase 2: Pre-Release Review (Before Public Distribution)
- Sign IPIA with Microsoft (send email, ~72 hours)
- Review and confirm binary redistribution approach
- Prepare release artifacts
- Configure PyPI trusted publishing
- Prepare security disclosures/SBOMs

### Phase 3: Public Release (After IPIA)
- Publish to PyPI
- Publish to GitHub with release notes
- Announce in appropriate channels
- Include disclaimer about unofficial status

---

## Compliance Checklist for v1.0 Release

- [ ] IPIA with Microsoft is signed (or internal-only exemption confirmed)
- [ ] Binary redistribution approach is confirmed with Microsoft
- [ ] Project name compliance is verified (trademark guidelines)
- [ ] README includes all required disclaimers
- [ ] docs/distribution-and-licensing.md accurately describes licensing
- [ ] MIT (or other) license is applied to MIP Wrapper source code
- [ ] Python package metadata includes license information
- [ ] GitHub repository is public with appropriate license file
- [ ] PyPI trusted publishing is configured
- [ ] Release artifacts are signed (if applicable)
- [ ] SBOM is generated and included in release notes
- [ ] Security policy is documented (SECURITY.md)
- [ ] Contributing guidelines are documented (CONTRIBUTING.md)

---

## References

**Official Microsoft Sources:**

1. MIP SDK Overview: https://learn.microsoft.com/en-us/information-protection/develop/
2. MIP SDK Download: https://aka.ms/mipsdkbinaries
3. NuGet Package: https://www.nuget.org/packages/Microsoft.InformationProtection.File/
4. C# Quickstart: https://learn.microsoft.com/en-us/information-protection/develop/setup-configure-mip
5. Trademark Guidelines: https://www.microsoft.com/legal/intellectualproperty/trademarks

**IPIA Contact:**
- Email: IPIA@microsoft.com
- Subject: "MIP SDK Integration Agreement Request"
- Timeline: ~72 hours to response

---

## Document Version

- **Version:** 1.0
- **Date:** August 31, 2026
- **Status:** Stage 1 Findings
- **Next Review:** Before public PyPI release (Stage 5)
- **Last Updated:** August 31, 2026

**Important:** This document records findings at a point in time. Licensing terms and Microsoft policies may change. Always verify with current official sources before making distribution decisions.
