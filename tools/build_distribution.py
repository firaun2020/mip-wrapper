"""Build a platform-specific wheel with a previously published helper."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


TARGETS = {
    "win-x64": "win-x64",
    "ubuntu-22.04-x64": "ubuntu-22.04-x64",
}

NOTICE_NAMES = {
    "LICENSE.txt",
    "LicenseTerms.rtf",
    "redist.txt",
    "ThirdPartyNotice.txt",
}

MIT_LICENSE = """MIT License

Copyright (c) Microsoft Corporation. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the Software), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

DOTNET_NOTICE_NAMES = {
    "LICENSE.txt": "DOTNET_LICENSE.txt",
    "ThirdPartyNotices.txt": "DOTNET_ThirdPartyNotices.txt",
}


def _mip_package_root(package_name: str) -> Path:
    root = Path.home() / ".nuget" / "packages" / package_name / "1.18.124"
    if not root.is_dir():
        raise SystemExit(f"MIP NuGet package is missing: {root}")
    return root


def _copy_runtime(runtime_dir: Path, destination: Path, platform_name: str) -> None:
    def ignore(path: str, names: list[str]) -> set[str]:
        if platform_name == "win-x64":
            return {name for name in names if name in {"x86", "arm64"}}
        return set()

    shutil.copytree(runtime_dir, destination, ignore=ignore)


def _copy_mip_notices(platform_name: str, destination: Path) -> None:
    if platform_name == "win-x64":
        package_root = _mip_package_root("microsoft.informationprotection.file")
        license_dir = package_root / "lib"
        missing = sorted(name for name in NOTICE_NAMES if not (license_dir / name).is_file())
        if missing:
            raise SystemExit(
                "Windows MIP NuGet license files are missing: "
                f"{', '.join(missing)}"
            )
        for name in NOTICE_NAMES:
            shutil.copy2(license_dir / name, destination / name)
        shutil.copy2(
            next(package_root.glob("*.nuspec")),
            destination / "Microsoft.InformationProtection.File.nuspec",
        )
        return

    package_root = _mip_package_root(
        "microsoft.informationprotection.file.ubuntu2204"
    )
    nuspec = next(package_root.glob("*.nuspec"), None)
    if nuspec is None:
        raise SystemExit("Ubuntu MIP NuGet .nuspec is missing")
    nuspec_text = nuspec.read_text(encoding="utf-8-sig")
    if '<license type="expression">MIT</license>' not in nuspec_text:
        raise SystemExit(
            "Ubuntu MIP NuGet package does not provide verifiable MIT license metadata"
        )
    if not any(package_root.rglob("libmip_file_sdk.so")):
        raise SystemExit(
            "Ubuntu MIP NuGet package does not contain libmip_file_sdk.so"
        )

    shutil.copy2(nuspec, destination / nuspec.name)
    (destination / "MIP_Ubuntu2204_MIT_LICENSE.txt").write_text(
        "Official license metadata for Microsoft.InformationProtection.File.Ubuntu2204 1.18.124\n"
        "Package source: https://www.nuget.org/packages/Microsoft.InformationProtection.File.Ubuntu2204/1.18.124\n"
        "License metadata source: https://licenses.nuget.org/MIT\n"
        "The package .nuspec declares: <license type=\"expression\">MIT</license>\n\n"
        + MIT_LICENSE,
        encoding="utf-8",
    )
    (destination / "MIP_Ubuntu2204_Redistribution.txt").write_text(
        "Redistribution basis for the bundled Ubuntu MIP native libraries:\n"
        "The official Microsoft.InformationProtection.File.Ubuntu2204 1.18.124 .nuspec\n"
        "declares the package license as MIT. The package contains libmip_file_sdk.so\n"
        "and the related MIP native libraries. This file is an attribution summary;\n"
        "the original .nuspec and MIT license text are included alongside it.\n"
        "Source: https://www.nuget.org/packages/Microsoft.InformationProtection.File.Ubuntu2204/1.18.124\n",
        encoding="utf-8",
    )

    for notice in package_root.rglob("*"):
        if (
            notice.is_file()
            and notice != nuspec
            and any(term in notice.name.lower() for term in ("thirdparty", "notice"))
        ):
            shutil.copy2(notice, destination / f"MIP_Ubuntu2204_{notice.name}")


def _find_dotnet_root() -> Path:
    candidates = []
    if os.environ.get("DOTNET_ROOT"):
        candidates.append(Path(os.environ["DOTNET_ROOT"]))
    dotnet = shutil.which("dotnet")
    if dotnet:
        candidates.append(Path(dotnet).resolve().parent)
    candidates.extend((Path("/usr/share/dotnet"), Path(r"C:\Program Files\dotnet")))
    for candidate in candidates:
        if all((candidate / name).is_file() for name in DOTNET_NOTICE_NAMES):
            return candidate
    raise SystemExit(".NET runtime license files were not found")


def _copy_dotnet_notices(destination: Path) -> None:
    dotnet_root = _find_dotnet_root()
    for source_name, destination_name in DOTNET_NOTICE_NAMES.items():
        shutil.copy2(dotnet_root / source_name, destination / destination_name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=TARGETS, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    runtime_dir = args.runtime_dir.resolve()
    if not runtime_dir.is_dir():
        raise SystemExit(f"Runtime directory does not exist: {runtime_dir}")

    with tempfile.TemporaryDirectory(prefix="mip-wrapper-build-") as directory:
        staging = Path(directory)
        for name in ("pyproject.toml", "setup.py", "README.md", "LICENSE"):
            shutil.copy2(project_root / name, staging / name)
        shutil.copytree(project_root / "src", staging / "src")
        packaged_runtime = staging / "src" / "mip_wrapper" / "_runtime" / TARGETS[args.platform]
        _copy_runtime(runtime_dir, packaged_runtime, args.platform)
        _copy_mip_notices(args.platform, packaged_runtime)
        _copy_dotnet_notices(packaged_runtime)

        environment = os.environ.copy()
        environment["MIP_WRAPPER_WHEEL_PLATFORM"] = args.platform
        args.output_dir.resolve().mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(args.output_dir.resolve()),
            ],
            cwd=staging,
            env=environment,
            check=True,
        )


if __name__ == "__main__":
    main()
