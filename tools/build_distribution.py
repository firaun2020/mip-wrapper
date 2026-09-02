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

DOTNET_NOTICE_NAMES = {
    "LICENSE.txt": "DOTNET_LICENSE.txt",
    "ThirdPartyNotices.txt": "DOTNET_ThirdPartyNotices.txt",
}


def _mip_package_license_dirs(platform_name: str) -> list[Path]:
    package_names = [
        "microsoft.informationprotection.file"
        if platform_name == "win-x64"
        else "microsoft.informationprotection.file.ubuntu2204",
        "microsoft.informationprotection.file",
    ]
    return [
        Path.home() / ".nuget" / "packages" / package_name / "1.18.124" / "lib"
        for package_name in package_names
    ]


def _copy_runtime(runtime_dir: Path, destination: Path, platform_name: str) -> None:
    def ignore(path: str, names: list[str]) -> set[str]:
        if platform_name == "win-x64":
            return {name for name in names if name in {"x86", "arm64"}}
        return set()

    shutil.copytree(runtime_dir, destination, ignore=ignore)


def _copy_mip_notices(platform_name: str, destination: Path) -> None:
    license_dir = next(
        (
            candidate
            for candidate in _mip_package_license_dirs(platform_name)
            if all((candidate / name).is_file() for name in NOTICE_NAMES)
        ),
        None,
    )
    missing = sorted(
        name for name in NOTICE_NAMES
        if license_dir is None or not (license_dir / name).is_file()
    )
    if missing:
        raise SystemExit(
            "MIP NuGet license files are missing from "
            f"the restored packages: {', '.join(missing)}"
        )
    for name in NOTICE_NAMES:
        shutil.copy2(license_dir / name, destination / name)


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
