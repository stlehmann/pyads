from pathlib import Path
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.build import build
from wheel.bdist_wheel import bdist_wheel
import sys
import sysconfig
import os
import subprocess


adslib_relative = "adslib"
adslib_root = Path(__file__).parent.absolute() / adslib_relative


def platform_is_linux():
    return sys.platform.startswith("linux") or sys.platform.startswith("darwin")


def create_binaries():
    # Use `make` to build adslib
    # Build is done in-place, afterward e.g. `src/pyads/adslib/adslib.so` will exist
    subprocess.call(["make", "-C", adslib_relative])


def remove_binaries():
    """Remove all binary files in the adslib directory."""
    patterns = (
        "*.a",
        "**/*.o",
        "*.bin",
        "*.so",
    )
    for pattern in patterns:
        for file in adslib_root.glob(pattern):
            os.remove(file)


class CustomBuild(build):
    """Compile adslib (but only for Linux)."""
    def run(self):
        if platform_is_linux():
            remove_binaries()
            create_binaries()

        super().run()


class CustomInstall(install):
    """Install compiled adslib (but only for Linux)."""
    def run(self):
        if platform_is_linux():
            adslib_lib = adslib_root / "adslib.so"
            adslib_dest = Path(self.install_lib)
            if not adslib_dest.exists():
                adslib_dest.mkdir(parents=True)
            self.copy_file(
                str(adslib_lib),
                str(adslib_dest),
            )
        super().run()


class CustomBDistWheel(bdist_wheel):
    """Manually mark our wheel for a specific platform."""

    def get_tag(self):
        """

        See https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/
        """
        impl_tag = "py2.py3"  # Same wheel across Python versions
        abi_tag = "none"  # Same wheeel across ABI versions (not a C-extension)
        # But we need to differentiate on the platform for the compiled adslib:
        plat_tag = sysconfig.get_platform().replace("-", "_").replace(".", "_")

        if plat_tag.startswith("linux_"):
            # But the basic Linux prefix is deprecated, use new scheme instead:
            plat_tag = "manylinux_2_24" + plat_tag[5:]

        # MacOS platform tags area already okay

        # We also keep Windows tags in place, instead of using `any`, to prevent an
        # obscure Linux platform to getting a wheel without adslib source

        return impl_tag, abi_tag, plat_tag


# noinspection PyTypeChecker
setup(
    cmdclass={
        "build": CustomBuild,
        "install": CustomInstall,
        "bdist_wheel": CustomBDistWheel,
    },
)

# Also see `MANIFEST.in`
