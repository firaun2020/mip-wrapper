"""Tests for version compatibility checking."""

import pytest

from mip_wrapper.version import (
    check_helper_version,
    check_protocol_version,
    MIN_HELPER_VERSION,
    PROTOCOL_VERSION,
)


class TestVersionChecking:
    """Test version compatibility checks."""

    def test_compatible_helper_version(self):
        """Test compatible helper version passes."""
        check_helper_version("1.0.0")  # Should not raise

    def test_compatible_newer_helper_version(self):
        """Test newer helper version passes."""
        check_helper_version("1.1.0")  # Should not raise

    def test_incompatible_older_helper_version(self):
        """Test older helper version fails."""
        with pytest.raises(ValueError, match="older than minimum"):
            check_helper_version("0.9.0")

    def test_invalid_helper_version_format(self):
        """Test invalid version format fails."""
        with pytest.raises(ValueError, match="Cannot parse helper version"):
            check_helper_version("invalid-version")

    def test_compatible_protocol_version(self):
        """Test compatible protocol version passes."""
        check_protocol_version(PROTOCOL_VERSION)

    def test_incompatible_protocol_version(self):
        """Test incompatible protocol version fails."""
        with pytest.raises(ValueError, match="Protocol version mismatch"):
            check_protocol_version("2.0")
