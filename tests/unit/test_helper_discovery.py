"""Tests for helper executable discovery."""

import pytest

from mip_wrapper import MipClient, MissingRuntimeError
from mip_wrapper.exceptions import InvalidConfigurationError


class TestHelperDiscovery:
    """Test helper executable discovery mechanisms."""

    def test_explicit_helper_path(self, test_auth, mock_helper_path):
        """Test explicit helper_path parameter works."""
        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
            helper_path=str(mock_helper_path),
        )
        assert client.helper_path == mock_helper_path

    def test_environment_variable_helper_path(self, test_auth, tmp_path, monkeypatch):
        """Test MIP_WRAPPER_HELPER_PATH environment variable works."""
        mock_helper_path = tmp_path / "fake-helper"
        mock_helper_path.write_text("fake helper")
        monkeypatch.setenv("MIP_WRAPPER_HELPER_PATH", str(mock_helper_path))

        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
        )
        assert client.helper_path == mock_helper_path

    def test_missing_helper_raises_clear_error(self, test_auth, monkeypatch, tmp_path):
        """Test missing helper discovery raises MissingRuntimeError with clear instructions."""
        # Isolate both cwd and package-relative discovery locations.
        monkeypatch.delenv("MIP_WRAPPER_HELPER_PATH", raising=False)
        monkeypatch.chdir(str(tmp_path))
        isolated_client = tmp_path / "package" / "mip_wrapper" / "client.py"
        monkeypatch.setattr("mip_wrapper.client.__file__", str(isolated_client))

        with pytest.raises(MissingRuntimeError) as exc_info:
            MipClient(
                auth=test_auth,
                authorization_mode="delegated_reader",
                delegated_user="user@example.com",
            )

        error = exc_info.value
        assert "MipWrapper.Helper" in error.message
        assert "dotnet publish" in error.message
        assert "BUILD_LOCALLY.md" in error.message
        assert error.error_code == "HelperNotFound"

    def test_environment_variable_nonexistent_file(self, test_auth, monkeypatch, caplog, tmp_path):
        """Test warning when environment variable points to nonexistent file."""
        monkeypatch.chdir(str(tmp_path))
        isolated_client = tmp_path / "package" / "mip_wrapper" / "client.py"
        monkeypatch.setattr("mip_wrapper.client.__file__", str(isolated_client))
        monkeypatch.setenv("MIP_WRAPPER_HELPER_PATH", str(tmp_path / "missing-helper"))

        with pytest.raises(MissingRuntimeError):
            MipClient(
                auth=test_auth,
                authorization_mode="delegated_reader",
                delegated_user="user@example.com",
            )

        # Should have warning about env var pointing to nonexistent file
        assert any("MIP_WRAPPER_HELPER_PATH" in record.message for record in caplog.records)

    def test_packaged_windows_helper_is_discovered_from_isolated_runtime(
        self, test_auth, monkeypatch, tmp_path
    ):
        """Packaged discovery must use its own runtime, not repository helper-bin."""
        runtime = tmp_path / "_runtime" / "win-x64"
        (runtime / "x64").mkdir(parents=True)
        (runtime / "MipWrapper.Helper.exe").write_bytes(b"fake executable")
        (runtime / "x64" / "mip_file_sdk.dll").write_bytes(b"fake native")
        (runtime / "Microsoft.InformationProtection.dll").write_bytes(b"fake managed")

        monkeypatch.delenv("MIP_WRAPPER_HELPER_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("mip_wrapper.client.platform.system", lambda: "Windows")
        monkeypatch.setattr(
            "mip_wrapper.client.resources.files", lambda package: tmp_path
        )

        client = MipClient(
            auth=test_auth,
            authorization_mode="delegated_reader",
            delegated_user="user@example.com",
        )

        assert client.helper_path == runtime / "MipWrapper.Helper.exe"

    def test_packaged_linux_helper_requires_ubuntu_2204_x64(
        self, test_auth, monkeypatch, tmp_path
    ):
        monkeypatch.delenv("MIP_WRAPPER_HELPER_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("mip_wrapper.client.platform.system", lambda: "Linux")
        monkeypatch.setattr("mip_wrapper.client.platform.machine", lambda: "x86_64")
        monkeypatch.setattr(
            "mip_wrapper.client.Path.read_text",
            lambda path, encoding="utf-8": 'ID=ubuntu\nVERSION_ID="22.04"\n',
        )

        with pytest.raises(MissingRuntimeError, match="Ubuntu 22.04"):
            MipClient(
                auth=test_auth,
                authorization_mode="delegated_reader",
                delegated_user="user@example.com",
            )
