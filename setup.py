import glob
import os
import sys
import shutil
import subprocess
import functools
import operator
from setuptools import setup
from setuptools.command.install import install as _install
from distutils.command.build import build as _build
from distutils.command.clean import clean as _clean
from distutils.command.sdist import sdist as _sdist


def platform_is_linux():
    return sys.platform.startswith("linux") or sys.platform.startswith("darwin")


def get_files_rec(directory):
    res = []
    for path, directory, filenames in os.walk(directory):
        files = [os.path.join(path, fn) for fn in filenames]
        res.append((path, files))
    return res


def create_binaries():
    subprocess.call(["make", "-C", "adslib"])


def remove_binaries():
    """Remove all binary files in the adslib directory."""
    patterns = (
        "adslib/*.a",
        "adslib/*.o",
        "adslib/obj/*.o",
        "adslib/*.bin",
        "adslib/*.so",
    )

    for f in functools.reduce(operator.iconcat, [glob.glob(p) for p in patterns]):
        os.remove(f)


def copy_sharedlib():
    try:
        shutil.copy("adslib/adslib.so", "src/pyads/adslib.so")
    except OSError:
        pass


def remove_sharedlib():
    try:
        os.remove("adslib.so")
    except OSError:
        pass


class build(_build):
    def run(self):
        if platform_is_linux():
            remove_binaries()
            create_binaries()
            copy_sharedlib()
            remove_binaries()
        _build.run(self)


class clean(_clean):
    def run(self):
        if platform_is_linux():
            remove_binaries()
            remove_sharedlib()
        _clean.run(self)


class sdist(_sdist):
    def run(self):
        if platform_is_linux():
            remove_binaries()
        _sdist.run(self)


class install(_install):
    def run(self):
        if platform_is_linux():
            create_binaries()
            copy_sharedlib()
        _install.run(self)


# noinspection PyTypeChecker
setup(
    cmdclass={
        "build": build,
        "clean": clean,
        # "sdist": sdist,
        "install": install,
    },
    data_files=get_files_rec("adslib"),  # Maybe necessary?
)
