#! /usr/bin/env python
# -*-coding: utf-8 -*-
import os
import sys
import shutil
import subprocess
from setuptools import setup
from setuptools.command.test import test as TestCommand
from setuptools.command.install import install as _install
from distutils.command.build import build as _build
from distutils.command.clean import clean as _clean
from distutils.command.sdist import sdist as _sdist
import versioneer


def get_files_rec(directory):
    res = []
    for (path, directory, filenames) in os.walk(directory):
        files = [os.path.join(path, fn) for fn in filenames]
        res.append((path, files))
    return res

data_files = get_files_rec('src')


def create_binaries():
    subprocess.call(['make', '-C', 'src'])


def remove_binaries():
    subprocess.call(['make', 'clean', '-C', 'src'])


def copy_sharedlib():
    shutil.copy('src/adslib.so', 'pyads/adslib.so')


def remove_sharedlib():
    try:
        os.remove('pyads/adslib.so')
    except OSError:
        pass


class build(_build):
    def run(self):
        remove_binaries()
        create_binaries()
        copy_sharedlib()
        remove_binaries()
        _build.run(self)


class clean(_clean):
    def run(self):
        remove_binaries()
        remove_sharedlib()
        _clean.run(self)


class sdist(_sdist):
    def run(self):
        remove_binaries()
        remove_sharedlib()
        _sdist.run(self)


class install(_install):
    def run(self):
        create_binaries()
        copy_sharedlib()
        _install.run(self)


# class install(_install):
#     def run(self):
#         try:
#             subprocess.call(['make', 'clean', '-C', 'src'])
#             subprocess.call(['make', '-C', 'src'])
#             subprocess.call(['cp', 'src/adslib.so', 'pyads/adslib.so'])
#         except Exception as e:
#             print(e)
#             print(
#                 '------------------------------------\n'
#                 'Error compiling the adslib library. '
#                 'Please install manually from https://github.com/dabrowne/ADS or '
#                 'visit https://github.com/MrLeeh/pyads for details.\n'
#                 '------------------------------------'
#             )
#         _install.run(self)


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args=[]

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


cmdclass = versioneer.get_cmdclass()
cmdclass.update({
    'test': PyTest,
    'build': build,
    'clean': clean,
    'sdist': sdist,
    'install': install,
})


setup(
      name = "pyads",
      version = versioneer.get_version(),
      description = "Python wrapper for TwinCAT ADS library",
      author = "Stefan Lehmann",
      author_email = "Stefan.St.Lehmann@gmail.com",
      packages = ["pyads"],
      package_data={'pyads': ['adslib.so']},
      requires = [],
      provides=['pyads'],
      url = 'https://github.com/MrLeeh/pyads',
      classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Microsoft :: Windows :: Windows 7'
      ],
      cmdclass=cmdclass,
      data_files=data_files
)
