import os
import subprocess
import sys
import sysconfig
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.install import install
from wheel.bdist_wheel import bdist_wheel

src_folder = Path(__file__).parent.absolute() / "src"
# ^ This will be on PATH for editable install
adslib_folder = Path(__file__).parent.absolute() / "adslib"
adslib_file = src_folder / "adslib.so"


class CustomBuildPy(build_py):
    """Custom command for `build_py`.

    This command class is used because it is always run, also for an editable install.
    """

    @classmethod
    def compile_adslib(cls) -> bool:
        """Return `True` if adslib was actually compiled."""
        if cls.platform_is_unix():
            cls._clean_library()
            cls._compile_library()
            return True

        return False

    @staticmethod
    def _compile_library():
        """Use `make` to build adslib - build is done in-place."""
        # Produce `adslib.so`:
        subprocess.call(["make", "-C", "adslib"])

    @staticmethod
    def _clean_library():
        """Remove all compilation artifacts."""
        patterns = (
            "*.a",
            "**/*.o",
            "*.bin",
            "*.so",
        )
        for pattern in patterns:
            for file in adslib_folder.glob(pattern):
                os.remove(file)

        if adslib_file.is_file():
            os.remove(adslib_file)

    @staticmethod
    def platform_is_unix():
        return sys.platform.startswith("linux") or sys.platform.startswith("darwin")

    def run(self):
        if self.compile_adslib():
            # Move .so file from Git submodule into src/ to have it on PATH:
            self.move_file(
                str(adslib_folder / "adslib.so"),
                str(adslib_file),
            )

        super().run()


class CustomInstall(install):
    """Install compiled adslib (but only for Linux)."""

    def run(self):
        if CustomBuildPy.platform_is_unix():
            adslib_dest = Path(self.install_lib)
            if not adslib_dest.exists():
                adslib_dest.mkdir(parents=True)
            self.copy_file(
                str(adslib_file),
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
        "build_py": CustomBuildPy,
        "install": CustomInstall,
        "bdist_wheel": CustomBDistWheel,
    },
)
