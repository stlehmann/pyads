#! /usr/bin/env python
# -*-coding: utf-8 -*-
import os
import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand
import versioneer

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
cmdclass.update({'test': PyTest})

setup(
      name = "pyads",
      version = versioneer.get_version(),
      description = "Python wrapper for TwinCAT ADS library",
      author = "Stefan Lehmann",
      author_email = "Stefan.St.Lehmann@gmail.com",
      packages = ["pyads"],
      package_data = {'pyads': ['doc/*.*']},
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
      cmdclass=cmdclass
)
