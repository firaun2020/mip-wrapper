# Local Development: Build and Test Instructions

This document explains how to build and test MIP Wrapper locally as a Python developer would use it.

MIP Wrapper is a Python library that requires a .NET helper component. For development, both components must be built and the helper must be discoverable.

## Prerequisites

- Python 3.11+
- .NET 6.0 SDK or later
- Git

## Quick Start

### 1. Create Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -e .
pip install pytest
```

### 3. Build .NET Helper

```bash
cd native/MipWrapper.Helper
dotnet publish -c Release -o ../../helper-bin
cd ../..
```

The compiled helper will be in `helper-bin/`.

### 4. Make Helper Discoverable

Copy or symlink the helper so Python can find it:

```bash
# Option A: Copy to current directory
cp helper-bin/MipWrapper.Helper .  # or .exe on Windows

# Option B: Add to PATH
export PATH="$PWD/helper-bin:$PATH"  # On Windows: set PATH=%cd%\helper-bin;%PATH%
```

## Running Unit Tests

All unit tests mock the .NET helper and do not require:
- Azure credentials
- Real certificates
- Real protected files

```bash
pytest tests/unit/ -v
```

Expected output:
```
tests/unit/test_auth.py::TestCertificateAuth::test_valid_configuration PASSED
tests/unit/test_auth.py::TestCertificateAuth::test_missing_tenant_id PASSED
tests/unit/test_auth.py::TestCertificateAuth::test_missing_certificate_file PASSED
tests/unit/test_auth.py::TestCertificateAuth::test_missing_password_file PASSED
tests/unit/test_auth.py::TestClientSecretAuth::test_valid_configuration PASSED
tests/unit/test_auth.py::TestClientSecretAuth::test_missing_tenant_id PASSED
tests/unit/test_protocol.py::TestProtocolRequest::test_inspect_request PASSED
tests/unit/test_protocol.py::TestProtocolRequest::test_decrypt_request PASSED
tests/unit/test_protocol.py::TestProtocolRequest::test_request_has_protocol_version PASSED
tests/unit/test_protocol.py::TestProtocolRequest::test_request_has_request_id PASSED
tests/unit/test_protocol.py::TestProtocolResponse::test_success_response PASSED
tests/unit/test_protocol.py::TestProtocolResponse::test_error_response PASSED
tests/unit/test_protocol.py::TestProtocolResponse::test_version_validation PASSED
tests/unit/test_protocol.py::TestProtocolResponse::test_ensure_success_raises_on_error PASSED
tests/unit/test_protocol.py::TestInspectResult::test_from_response PASSED
tests/unit/test_protocol.py::TestDecryptResult::test_from_response PASSED
tests/unit/test_client.py::TestMipClientInitialization::test_delegated_reader_requires_user PASSED
tests/unit/test_client.py::TestMipClientInitialization::test_valid_initialization PASSED
tests/unit/test_client.py::TestMipClientInitialization::test_invalid_authorization_mode PASSED
tests/unit/test_client.py::TestMipClientInspect::test_inspect_protected_file PASSED
tests/unit/test_client.py::TestMipClientInspect::test_inspect_unprotected_file PASSED
tests/unit/test_client.py::TestMipClientDecryptedFile::test_decrypted_file_cleanup PASSED
tests/unit/test_client.py::TestMipClientDecryptedFile::test_decrypted_file_cleanup_on_exception PASSED

========================= 24 passed in X.XXs =========================
```

## Building Docker Container

```bash
docker build -t mip-wrapper:v0.1 .
```

This builds a container with:
- .NET 6.0 runtime
- Python 3.11
- MIP Wrapper Python package
- Compiled MipWrapper.Helper
- All dependencies from NuGet

### Test Container Build

```bash
docker run --rm mip-wrapper:v0.1 python3 -c "import mip_wrapper; print(mip_wrapper.__version__)"
```

Expected output:
```
0.1.0
```

## Integration Testing (Requires Real Setup)

Integration tests require:
1. Azure AD tenant with MIP protection enabled
2. Registered application with certificate credentials
3. Protected test Excel file
4. Appropriate application permissions in Azure AD

See the main README for integration test requirements and setup.

## Troubleshooting

### Python package not found

Ensure you're in the virtual environment and have run `pip install -e .`.

### Helper executable not found

Ensure `MipWrapper.Helper` (or `.exe` on Windows) is:
1. Built: `dotnet publish -c Release -o ../../helper-bin`
2. In PATH or current directory
3. Has execute permissions: `chmod +x MipWrapper.Helper`

### Tests fail with "can't import mip_wrapper"

Reinstall the package: `pip install -e .`

### Docker build fails on .NET dependencies

Ensure you have internet connectivity for NuGet restore. The build uses official Microsoft sources.

## Local Development Workflow

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Install editable package
pip install -e .

# 3. Build .NET helper
cd native/MipWrapper.Helper && dotnet publish -c Release -o ../../helper-bin && cd ../..

# 4. Add helper to PATH
export PATH="$PWD/helper-bin:$PATH"

# 5. Run tests
pytest tests/unit/ -v

# 6. Make changes to src/mip_wrapper/ or native/MipWrapper.Helper/

# 7. Rebuild helper if needed
cd native/MipWrapper.Helper && dotnet publish -c Release -o ../../helper-bin && cd ../..

# 8. Re-run tests
pytest tests/unit/ -v
```

## Next Steps: Integration Testing

Once unit tests pass locally, see `docs/STAGE_2_DECISIONS.md` for tenant setup required before running integration tests.
