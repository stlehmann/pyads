from setuptools import setup
from setuptools.command.build import build

import sys
import subprocess


def platform_is_linux():
    return sys.platform.startswith("linux") or sys.platform.startswith("darwin")


class PyadsBuild(build):
    def run(self):
        if platform_is_linux():
            subprocess.call(["make", "-C", "adslib"])

        build.run(self)  # Avoid `super()` here for legacy


setup(
    cmdclass={
        "build": PyadsBuild,
    }
)
