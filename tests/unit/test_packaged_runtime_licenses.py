"""Checks licensing files in an installed platform wheel."""

import os
import platform
from importlib import resources

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("MIP_WRAPPER_EXPECT_PACKAGED_RUNTIME") != "1",
    reason="requires an installed platform wheel",
)


def test_bundled_runtime_license_files_exist():
    runtime_name = "win-x64" if platform.system() == "Windows" else "ubuntu-22.04-x64"
    runtime = resources.files("mip_wrapper").joinpath("_runtime", runtime_name)
    for name in (
        "LicenseTerms.rtf",
        "redist.txt",
        "ThirdPartyNotice.txt",
        "DOTNET_LICENSE.txt",
        "DOTNET_ThirdPartyNotices.txt",
    ):
        assert runtime.joinpath(name).is_file(), name
