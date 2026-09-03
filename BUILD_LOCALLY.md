# Local Build

This repository contains a Python package and platform-specific .NET helpers. Published wheels include the helper and MIP runtime; local builds reproduce those wheels.

## Prerequisites

- Windows x64 or Ubuntu 22.04 x64
- Python 3.11 or newer
- .NET SDK compatible with `native/MipWrapper.Helper/MipWrapper.Helper.csproj`
- NuGet access to restore the Microsoft MIP SDK packages

## Build and test

```powershell
python -m pip install -e .
python -m pytest

# Windows x64 wheel
dotnet publish native/MipWrapper.Helper/MipWrapper.Helper.csproj -c Release -r win-x64 --self-contained true -o C:\tmp\mip-wrapper-runtime-win-x64
python tools/build_distribution.py --platform win-x64 --runtime-dir C:\tmp\mip-wrapper-runtime-win-x64 --output-dir dist

# Ubuntu 22.04 x64 wheel, run on Ubuntu 22.04
dotnet publish native/MipWrapper.Helper/MipWrapper.Helper.csproj -c Release -r linux-x64 --self-contained true -o /tmp/mip-wrapper-runtime-ubuntu2204-x64
chmod +x /tmp/mip-wrapper-runtime-ubuntu2204-x64/MipWrapper.Helper
python tools/build_distribution.py --platform ubuntu-22.04-x64 --runtime-dir /tmp/mip-wrapper-runtime-ubuntu2204-x64 --output-dir dist
```

The generated wheel is standalone for its target platform. Development-only helper overrides remain available through `MIP_WRAPPER_HELPER_PATH` or `helper_path`.

## Real integration test

The local `test_it.py` is intentionally ignored and requires a real Purview-protected file, a tenant ID, an application client ID and secret, a delegated user, the required MIP application permission with admin consent, the .NET helper, and network access to the MIP service. Keep credentials outside source control and do not print them.

The helper uses unattended `AcquireTokenForClient` authentication. `delegated_reader` uses the delegated user supplied in the request; `super_user` uses the application's Content.SuperUser permission. Unit tests cannot establish these tenant-side conditions.
