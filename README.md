# mip-wrapper

Unofficial Python wrapper for inspecting and decrypting files protected by Microsoft Purview Information Protection. The Python package starts a local JSON subprocess bridge to a bundled .NET helper, which calls the Microsoft Information Protection File SDK.

## Scope

- Windows x64 and Ubuntu 22.04 x64 wheels
- Python 3.11 or newer
- `delegated_reader` and `super_user` authorization modes
- Unattended client-secret authentication via MSAL
- Local file inspection and temporary decryption
- No DRM bypass: the delegated user must have the required document usage right

The published platform wheel bundles a self-contained helper and the target platform's Microsoft MIP SDK runtime. Ubuntu support is specifically Ubuntu 22.04 x64; other Linux distributions and architectures are rejected by runtime discovery.

## Installation

```powershell
python -m pip install mip-wrapper
```

No separate .NET installation, helper download, or `MIP_WRAPPER_HELPER_PATH` setting is required for a supported published wheel. `MIP_WRAPPER_HELPER_PATH` and `helper_path` remain available as development overrides.

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

For service-principal access to all tenant-protected content, use `authorization_mode="super_user"` and omit `delegated_user`:

```python
client = MipClient(auth=auth, authorization_mode="super_user")
```

The context manager creates a temporary directory, returns the committed plaintext path, and removes the directory on normal exit and exceptions. A cleanup failure raises `CleanupError`. The original protected file is not used as the output path.

## Entra and document authorization

The app registration must be configured for the Microsoft Information Protection resource and granted the application permission required by the selected MIP flow, with tenant-admin consent. `delegated_reader` is package configuration terminology, not an Entra permission. Delegated mode requires the `Content.DelegatedReader` application permission and a delegated user with `Export` or `Owner` usage rights on the file. Super-user mode requires the Azure Rights Management Service `Content.SuperUser` application permission; it is intended for service-principal access to tenant-protected content and does not use a delegated user's document rights.

The helper acquires app-only tokens with `AcquireTokenForClient`, using the tenant supplied by the request and the MIP SDK challenge resource as `{resource}/.default`. It does not perform an interactive delegated-user sign-in.

## Security and operational limits

- Do not put client secrets in source code, command-line arguments, logs, or protocol diagnostics. Supply them through a secret provider such as an environment-backed secret store.
- Protected file contents are written temporarily in plaintext while inside the context manager. Restrict host access and process only authorized content.
- The helper protocol is local and line-delimited JSON; it is not an authenticated network service.
- The package does not download, install, or update runtime files after installation; they are selected at wheel build time.
- Real tenant credentials and protected files are required for integration testing. Unit tests use fake helper processes and do not prove tenant authorization or MIP service connectivity.

## Development

```powershell
python -m pip install -e .
python -m pytest
dotnet build native/MipWrapper.Helper/MipWrapper.Helper.csproj -c Release
```

See [`BUILD_LOCALLY.md`](BUILD_LOCALLY.md) for the platform wheel build workflow. This project is not affiliated with or endorsed by Microsoft.

## License

The wrapper source is MIT licensed. The Microsoft Information Protection SDK and its native runtime are separately licensed by Microsoft; this repository does not grant rights to redistribute them.
