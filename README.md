# mip-wrapper

Unofficial Python wrapper for inspecting and decrypting files protected by Microsoft Purview Information Protection. The Python package starts a local JSON subprocess bridge to a separately built .NET helper, which calls the Microsoft Information Protection File SDK.

## Scope

- Windows x64 only
- Python 3.11 or newer
- `delegated_reader` is the only supported authorization mode
- Unattended client-secret authentication via MSAL
- Local file inspection and temporary decryption
- No DRM bypass: the delegated user must have the required document usage right

The package does not bundle the .NET helper or Microsoft MIP SDK binaries. Build and install the helper separately, and ensure its Microsoft SDK licensing and redistribution terms are satisfied for your environment.

## Installation

```powershell
python -m pip install mip-wrapper
dotnet publish native/MipWrapper.Helper/MipWrapper.Helper.csproj -c Release -o helper-bin
$env:MIP_WRAPPER_HELPER_PATH = (Resolve-Path helper-bin/MipWrapper.Helper.exe)
```

The helper requires the .NET runtime targeted by the project and the native Microsoft MIP SDK runtime available to it. `MIP_WRAPPER_HELPER_PATH` may point to the published helper executable. The source repository's `helper-bin/` directory is a local build output and is not part of the Python distribution.

## Usage

```python
import os
from mip_wrapper import MipClient
from mip_wrapper.auth import ClientSecretAuth

auth = ClientSecretAuth(
    tenant_id=os.environ["MIP_TENANT_ID"],
    client_id=os.environ["MIP_CLIENT_ID"],
    secret_provider=lambda: os.environ["MIP_CLIENT_SECRET"],
)

client = MipClient(
    auth=auth,
    authorization_mode="delegated_reader",
    delegated_user="reader@contoso.com",
)

info = client.inspect("protected.xlsx")
print(info.is_protected, info.usage_rights)

with client.decrypted_file("protected.xlsx") as file:
    process(file.path)
```

The context manager creates a temporary directory, returns the committed plaintext path, and removes the directory on normal exit and exceptions. A cleanup failure raises `CleanupError`. The original protected file is not used as the output path.

## Entra and document authorization

The app registration must be configured for the Microsoft Information Protection resource and granted the application permission required by the MIP SDK's delegated-reader flow, documented by Microsoft as `Content.DelegatedReader`, with tenant-admin consent. `delegated_reader` is package configuration terminology, not an Entra permission. The delegated user must independently have `Export` or `Owner` usage rights on the protected file; neither the package mode nor the app permission grants document access by itself.

The helper acquires app-only tokens with `AcquireTokenForClient`, using the tenant supplied by the request and the MIP SDK challenge resource as `{resource}/.default`. It does not perform an interactive delegated-user sign-in.

## Security and operational limits

- Do not put client secrets in source code, command-line arguments, logs, or protocol diagnostics. Supply them through a secret provider such as an environment-backed secret store.
- Protected file contents are written temporarily in plaintext while inside the context manager. Restrict host access and process only authorized content.
- The helper protocol is local and line-delimited JSON; it is not an authenticated network service.
- The package does not download, install, or update the helper or Microsoft SDK runtime.
- Real tenant credentials and protected files are required for integration testing. Unit tests use fake helper processes and do not prove tenant authorization or MIP service connectivity.

## Development

```powershell
python -m pip install -e .
python -m pytest
dotnet build native/MipWrapper.Helper/MipWrapper.Helper.csproj -c Release
```

See [`BUILD_LOCALLY.md`](BUILD_LOCALLY.md) for the local helper workflow. See [`docs/distribution-and-licensing.md`](docs/distribution-and-licensing.md) for the unresolved Microsoft SDK distribution and licensing questions. This project is not affiliated with or endorsed by Microsoft.

## License

The wrapper source is MIT licensed. The Microsoft Information Protection SDK and its native runtime are separately licensed by Microsoft; this repository does not grant rights to redistribute them.
