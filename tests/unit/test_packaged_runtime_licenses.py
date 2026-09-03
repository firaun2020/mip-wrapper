"""Checks licensing files in an installed platform wheel."""

import platform
from importlib import resources

def test_bundled_runtime_license_file_names_are_platform_specific(tmp_path, monkeypatch):
    runtime_name = "win-x64" if platform.system() == "Windows" else "ubuntu-22.04-x64"
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
    runtime = tmp_path / "_runtime" / runtime_name
    runtime.mkdir(parents=True)
    for name in names + ("DOTNET_LICENSE.txt", "DOTNET_ThirdPartyNotices.txt"):
        runtime.joinpath(name).touch()
    monkeypatch.setattr(
        "mip_wrapper.client.resources.files", lambda package: tmp_path
    )
    packaged = resources.files("mip_wrapper").joinpath("_runtime", runtime_name)
    for name in names + ("DOTNET_LICENSE.txt", "DOTNET_ThirdPartyNotices.txt"):
        assert packaged.joinpath(name).is_file(), name

    if runtime_name == "ubuntu-22.04-x64":
        assert not packaged.joinpath("LicenseTerms.rtf").exists()
        assert not packaged.joinpath("redist.txt").exists()
        assert not packaged.joinpath("ThirdPartyNotice.txt").exists()
