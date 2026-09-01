# Local Build

This repository contains a Python package and a Windows x64 .NET helper. The Python unit tests do not require a tenant, credentials, protected files, or a built helper.

## Prerequisites

- Windows x64
- Python 3.11 or newer
- .NET SDK compatible with `native/MipWrapper.Helper/MipWrapper.Helper.csproj`
- Microsoft MIP SDK runtime installed according to Microsoft's terms

## Build and test

```powershell
python -m pip install -e .
python -m pytest
dotnet restore native/MipWrapper.Helper/MipWrapper.Helper.csproj
dotnet build native/MipWrapper.Helper/MipWrapper.Helper.csproj -c Release
dotnet publish native/MipWrapper.Helper/MipWrapper.Helper.csproj -c Release -o helper-bin
$env:MIP_WRAPPER_HELPER_PATH = (Resolve-Path helper-bin/MipWrapper.Helper.exe)
```

The published helper is intentionally outside the Python wheel. Do not commit `helper-bin/`; it is ignored as a local build artifact.

## Real integration test

The local `test_it.py` is intentionally ignored and requires a real Purview-protected file, a tenant ID, an application client ID and secret, a delegated user, the required MIP application permission with admin consent, the .NET helper, and network access to the MIP service. Keep credentials outside source control and do not print them.

The helper uses unattended `AcquireTokenForClient` authentication and the delegated user supplied in the request. The user must have `Export` or `Owner` rights on the file. Unit tests cannot establish these tenant-side conditions.
