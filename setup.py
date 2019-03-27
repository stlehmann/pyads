#! /usr/bin/env python
# -*-coding: utf-8 -*-
import io
import glob
import os
import re
import sys
import shutil
import subprocess
import functools
import operator
from setuptools import setup
from setuptools.command.test import test as TestCommand
from setuptools.command.install import install as _install
from distutils.command.build import build as _build
from distutils.command.clean import clean as _clean
from distutils.command.sdist import sdist as _sdist


def read(*names, **kwargs):
    try:
        with io.open(
            os.path.join(os.path.dirname(__file__), *names),
            encoding=kwargs.get("encoding", "utf8")
        ) as fp:
            return fp.read()
    except IOError:
        return ''


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


def platform_is_linux():
    return sys.platform.startswith('linux') or \
        sys.platform.startswith('darwin')


def get_files_rec(directory):
    res = []
    for (path, directory, filenames) in os.walk(directory):
        files = [os.path.join(path, fn) for fn in filenames]
        res.append((path, files))
    return res


data_files = get_files_rec('adslib')


def create_binaries():
    subprocess.call(['make', '-C', 'adslib'])


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
        shutil.copy('adslib/adslib.so', 'pyads/adslib.so')
    except OSError:
        pass


def remove_sharedlib():
    try:
        os.remove('pyads/adslib.so')
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


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ['--cov-report', 'html', '--cov-report', 'term',
                            '--cov=pyads']

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


cmdclass = {
    'test': PyTest,
    'build': build,
    'clean': clean,
    'sdist': sdist,
    'install': install,
}


long_description = read('README.md')


setup(
    name="pyads",
    version=find_version('pyads', '__init__.py'),
    description="Python wrapper for TwinCAT ADS library",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Stefan Lehmann",
    author_email="Stefan.St.Lehmann@gmail.com",
    packages=["pyads", "pyads.testserver_ex"],
    package_data={'pyads': ['adslib.so']},
    requires=[],
    install_requires=['typing'],
    provides=['pyads'],
    url='https://github.com/MrLeeh/pyads',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Microsoft :: Windows :: Windows 7',
        'Operating System :: POSIX :: Linux',
    ],
    cmdclass=cmdclass,
    data_files=data_files,
    tests_require=['pytest', 'pytest-cov'],
)
