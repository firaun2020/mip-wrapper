"""Validate metadata and layout of a platform-specific wheel."""

import argparse
import zipfile
from pathlib import Path


def verify_wheel(wheel_path: Path, expected_tag: str) -> None:
    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()
        wheel_files = [name for name in names if name.endswith(".dist-info/WHEEL")]
        if len(wheel_files) != 1:
            raise AssertionError("wheel must contain exactly one WHEEL metadata file")

        metadata = archive.read(wheel_files[0]).decode("utf-8")
        print(metadata, end="")
        fields = {
            line.split(": ", 1)[0]: line.split(": ", 1)[1]
            for line in metadata.splitlines()
            if ": " in line
        }
        if fields.get("Root-Is-Purelib") != "false":
            raise AssertionError("Root-Is-Purelib must be false")
        if fields.get("Tag") != expected_tag:
            raise AssertionError(
                f"expected Tag: {expected_tag}, got {fields.get('Tag')!r}"
            )
        if not any(name.startswith("mip_wrapper/") for name in names):
            raise AssertionError("wheel does not contain the mip_wrapper package")
        if any(".data/purelib/" in name for name in names):
            raise AssertionError("native package files must not be in purelib")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("expected_tag")
    args = parser.parse_args()
    verify_wheel(args.wheel, args.expected_tag)


if __name__ == "__main__":
    main()
