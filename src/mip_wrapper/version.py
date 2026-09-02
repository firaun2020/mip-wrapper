"""Version information and compatibility checking."""

from packaging import version as pkg_version

# Package version
PACKAGE_VERSION = "0.2.0"

# Supported protocol version
PROTOCOL_VERSION = "1.0"

# Minimum helper version
MIN_HELPER_VERSION = "1.0.0"

# MIP SDK version we expect
MIP_SDK_VERSION = "1.18.124"


def check_helper_version(helper_version: str) -> None:
    """
    Check helper version compatibility.

    Args:
        helper_version: Version string from helper

    Raises:
        ValueError: If helper version is incompatible
    """
    try:
        helper_v = pkg_version.parse(helper_version)
        min_v = pkg_version.parse(MIN_HELPER_VERSION)

        if helper_v < min_v:
            raise ValueError(
                f"Helper version {helper_version} is older than minimum "
                f"required {MIN_HELPER_VERSION}. Please rebuild the helper."
            )
    except (ValueError, pkg_version.InvalidVersion) as e:
        raise ValueError(f"Cannot parse helper version '{helper_version}': {e}") from e


def check_protocol_version(protocol_version: str) -> None:
    """
    Check protocol version compatibility.

    Args:
        protocol_version: Version string from protocol

    Raises:
        ValueError: If protocol version is incompatible
    """
    if protocol_version != PROTOCOL_VERSION:
        raise ValueError(
            f"Protocol version mismatch: helper uses {protocol_version}, "
            f"package expects {PROTOCOL_VERSION}"
        )
