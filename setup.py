import os

from setuptools import setup
from wheel.bdist_wheel import bdist_wheel


class PlatformWheel(bdist_wheel):
    """Mark runtime wheels as platform-specific rather than pure Python."""

    def finalize_options(self):
        super().finalize_options()
        target = os.environ.get("MIP_WRAPPER_WHEEL_PLATFORM")
        if target in {"win-x64", "ubuntu-22.04-x64"}:
            self.root_is_pure = False

    def get_tag(self):
        target = os.environ.get("MIP_WRAPPER_WHEEL_PLATFORM")
        if target == "win-x64":
            return "py3", "none", "win_amd64"
        if target == "ubuntu-22.04-x64":
            return "py3", "none", "manylinux_2_35_x86_64"
        return super().get_tag()


setup(cmdclass={"bdist_wheel": PlatformWheel})
