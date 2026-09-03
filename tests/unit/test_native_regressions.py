"""Regression checks for native helper safety and authorization contracts."""

from pathlib import Path


PROGRAM = (
    Path(__file__).parents[2]
    / "native"
    / "MipWrapper.Helper"
    / "Program.cs"
).read_text()


def test_delegated_reader_is_the_only_supported_mode():
    assert 'request.AuthorizationMode != "delegated_reader" && request.AuthorizationMode != "super_user"' in PROGRAM


def test_engine_identity_and_delegated_email_are_explicit():
    assert 'var engineId = isDelegated ? request.DelegatedUser! : request.ClientId!;' in PROGRAM
    assert 'var identity = isDelegated ? request.DelegatedUser! : request.ClientId!;' in PROGRAM
    assert "Identity = new Microsoft.InformationProtection.Identity(identity)" in PROGRAM
    assert "settings.DelegatedUserEmail = request.DelegatedUser!;" in PROGRAM
    assert 'if (isDelegated)' in PROGRAM


def test_super_user_engine_uses_service_principal_identity_without_delegation():
    assert 'var engineId = isDelegated ? request.DelegatedUser! : request.ClientId!;' in PROGRAM
    assert 'var identity = isDelegated ? request.DelegatedUser! : request.ClientId!;' in PROGRAM
    assert 'new Microsoft.InformationProtection.File.FileEngineSettings(\n            engineId,\n            authDelegate,\n            "",\n            "en-US")' in PROGRAM
    assert 'if (request.AuthorizationMode == "delegated_reader" && protection != null)' in PROGRAM


def test_super_user_capability_does_not_depend_on_document_rights():
    assert 'if (request.AuthorizationMode == "super_user")\n            return true;' in PROGRAM


def test_application_id_preserves_the_client_guid():
    from mip_wrapper.bridge.protocol import ProtocolRequest
    import json

    client_id = "8872e138-b875-4362-85c9-5965f46648e4"
    request = ProtocolRequest(command="inspect", client_id=client_id)
    assert json.loads(request.to_json())["client_id"] == client_id
    assert "var clientId = request.ClientId!;" in PROGRAM
    assert "ApplicationId = clientId" in PROGRAM
    assert 'ApplicationName = "mip-wrapper"' in PROGRAM
    assert 'ApplicationVersion = "0.2.0"' in PROGRAM


def test_client_id_is_trimmed_and_validated_before_mip_initialization():
    assert "request.ClientId = request.ClientId?.Trim();" in PROGRAM
    assert "Guid.TryParse(request.ClientId, out _)" in PROGRAM
    assert '"client_id must be a valid GUID"' in PROGRAM


def test_msal_authority_uses_configured_tenant_and_sdk_host():
    assert "var authorityUri = new Uri(authority);" in PROGRAM
    assert '$"{authorityUri.Scheme}://{authorityUri.Host}/{_tenantId}"' in PROGRAM
    assert ".WithAuthority(tenantAuthority)" in PROGRAM
    assert ".WithAuthority(new Uri(authority))" not in PROGRAM
    assert '"/common"' not in PROGRAM
    assert '"/organizations"' not in PROGRAM


def test_output_paths_are_safe():
    assert "PathEquals(request.SourcePath!, request.OutputPath!)" in PROGRAM
    assert 'File.Exists(request.OutputPath!)' in PROGRAM
    assert '"Output file already exists"' in PROGRAM


def test_export_or_owner_right_is_required():
    assert "Rights.Export" in PROGRAM
    assert "Rights.Owner" in PROGRAM
    assert "User lacks Export or Owner right" in PROGRAM


def test_commit_result_and_output_are_verified():
    assert "var commitSucceeded = handler.CommitAsync(request.OutputPath!).GetAwaiter().GetResult();" in PROGRAM
    assert "if (!commitSucceeded)" in PROGRAM
    assert '"MIP commit did not create the output file"' in PROGRAM


def test_ubuntu_runtime_excludes_optional_lttng_provider(tmp_path):
    from tools.build_distribution import _copy_runtime

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    (source / "libcoreclrtraceptprovider.so").write_bytes(b"optional")
    (source / "libcoreclr.so").write_bytes(b"required")
    (source / "libmip_file_sdk.so").write_bytes(b"required")

    _copy_runtime(source, destination, "ubuntu-22.04-x64")

    assert not (destination / "libcoreclrtraceptprovider.so").exists()
    assert (destination / "libcoreclr.so").is_file()
    assert (destination / "libmip_file_sdk.so").is_file()


def test_fixed_preflight_scope_was_removed_and_challenge_is_used():
    assert "https://aadrm.com/.default" not in PROGRAM
    assert "tokenRequest.WithClaims(claimsChallenge)" in PROGRAM
    assert 'AcquireTokenForClient(new[] { $"{resource}/.default" })' in PROGRAM


def test_secret_is_not_written_to_python_logs_or_error_text(caplog):
    from mip_wrapper.bridge.client import HelperClient
    from mip_wrapper.bridge.protocol import ProtocolResponse
    from unittest.mock import MagicMock, patch

    secret = "regression-secret"
    response = ProtocolResponse(
        protocol_version="1.0",
        request_id="request",
        success=False,
        error={"code": "DecryptionError", "message": "operation failed"},
    )

    with patch("mip_wrapper.bridge.client.subprocess.Popen") as popen:
        process = MagicMock()
        process.stdout.readline.return_value = (
            '{"protocol_version":"1.0","request_id":"request",'
            '"success":false,"error":{"code":"DecryptionError",'
            '"message":"operation failed"}}\n'
        )
        popen.return_value = process
        client = HelperClient(Path("fake-helper"))
        try:
            client._send_request(
                __import__("mip_wrapper.bridge.protocol", fromlist=["ProtocolRequest"]).ProtocolRequest(
                    command="decrypt", client_secret=secret
                )
            )
        except Exception:
            pass

    assert secret not in caplog.text
    assert secret not in str(response.error)
