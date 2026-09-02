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
    names = (
        (
            "LicenseTerms.rtf",
            "redist.txt",
            "ThirdPartyNotice.txt",
            "Microsoft.InformationProtection.File.nuspec",
        )
        if runtime_name == "win-x64"
        else (
            "MIP_Ubuntu2204_MIT_LICENSE.txt",
            "MIP_Ubuntu2204_Redistribution.txt",
            "Microsoft.InformationProtection.File.Ubuntu2204.nuspec",
        )
    )
    for name in names + ("DOTNET_LICENSE.txt", "DOTNET_ThirdPartyNotices.txt"):
        assert runtime.joinpath(name).is_file(), name

    if runtime_name == "ubuntu-22.04-x64":
        assert not runtime.joinpath("LicenseTerms.rtf").exists()
        assert not runtime.joinpath("redist.txt").exists()
        assert not runtime.joinpath("ThirdPartyNotice.txt").exists()
