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
        # Isolate every discovery source, including packaged resources.
        monkeypatch.delenv("MIP_WRAPPER_HELPER_PATH", raising=False)
        monkeypatch.chdir(str(tmp_path))
        isolated_client = tmp_path / "package" / "mip_wrapper" / "client.py"
        monkeypatch.setattr("mip_wrapper.client.__file__", str(isolated_client))
        monkeypatch.setattr(MipClient, "_find_packaged_helper", lambda self: None)

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

    def test_environment_variable_nonexistent_file_is_authoritative(self, test_auth, monkeypatch, tmp_path):
        """An invalid explicit override must not fall back to another helper."""
        monkeypatch.chdir(str(tmp_path))
        isolated_client = tmp_path / "package" / "mip_wrapper" / "client.py"
        monkeypatch.setattr("mip_wrapper.client.__file__", str(isolated_client))
        monkeypatch.setenv("MIP_WRAPPER_HELPER_PATH", str(tmp_path / "missing-helper"))

        with pytest.raises(MissingRuntimeError) as exc_info:
            MipClient(
                auth=test_auth,
                authorization_mode="delegated_reader",
                delegated_user="user@example.com",
            )

        assert exc_info.value.error_code == "HelperNotFound"

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

        client = object.__new__(MipClient)
        assert client._find_helper() == runtime / "MipWrapper.Helper.exe"

    def test_packaged_linux_helper_is_discovered_on_ubuntu_2204_x64(
        self, test_auth, monkeypatch, tmp_path
    ):
        runtime = tmp_path / "_runtime" / "ubuntu-22.04-x64"
        runtime.mkdir(parents=True)
        helper = runtime / "MipWrapper.Helper"
        helper.write_bytes(b"fake executable")
        helper.chmod(0o700)
        (runtime / "libmip_file_sdk.so").write_bytes(b"fake native")
        (runtime / "Microsoft.InformationProtection.dll").write_bytes(b"fake managed")

        monkeypatch.delenv("MIP_WRAPPER_HELPER_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("mip_wrapper.client.platform.system", lambda: "Linux")
        monkeypatch.setattr("mip_wrapper.client.platform.machine", lambda: "x86_64")
        monkeypatch.setattr(
            "mip_wrapper.client.resources.files", lambda package: tmp_path
        )
        monkeypatch.setattr(
            "mip_wrapper.client._read_os_release",
            lambda: {"ID": "ubuntu", "VERSION_ID": "22.04"},
        )
        monkeypatch.setattr("mip_wrapper.client._is_executable", lambda path: True)

        client = object.__new__(MipClient)
        assert client._find_helper() == helper

    def test_missing_packaged_helper_on_ubuntu_2204_is_rejected(
        self, test_auth, monkeypatch, tmp_path
    ):
        monkeypatch.delenv("MIP_WRAPPER_HELPER_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        isolated_client = tmp_path / "package" / "mip_wrapper" / "client.py"
        monkeypatch.setattr("mip_wrapper.client.__file__", str(isolated_client))
        monkeypatch.setattr("mip_wrapper.client.platform.system", lambda: "Linux")
        monkeypatch.setattr("mip_wrapper.client.platform.machine", lambda: "x86_64")
        monkeypatch.setattr(MipClient, "_find_packaged_helper", lambda self: None)

        with pytest.raises(MissingRuntimeError, match="MipWrapper.Helper"):
            object.__new__(MipClient)._find_helper()

    def test_unsupported_linux_distribution_is_rejected(
        self, test_auth, monkeypatch, tmp_path
    ):
        monkeypatch.delenv("MIP_WRAPPER_HELPER_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("mip_wrapper.client.platform.system", lambda: "Linux")
        monkeypatch.setattr("mip_wrapper.client.platform.machine", lambda: "x86_64")
        monkeypatch.setattr(
            "mip_wrapper.client._read_os_release",
            lambda: {"ID": "mariner", "VERSION_ID": "2.0"},
        )

        with pytest.raises(MissingRuntimeError, match="Ubuntu 22.04") as exc_info:
            object.__new__(MipClient)._find_packaged_helper()
        assert exc_info.value.error_code == "UnsupportedPlatform"
