#! /usr/bin/env python2
# -*-coding: utf-8 -*-
from setuptools import setup

import versioneer

setup(
      name = "pyads",
      version = versioneer.get_version(),
      cmdclass = versioneer.get_cmdclass(),
      description = "Python wrapper for TwinCAT ADS library",
      author = "Stefan Lehmann",
      author_email = "Stefan.St.Lehmann@gmail.com",
      packages = ["pyads"],
      package_data = {'pyads': ['doc/*.*']},
      requires = ['ctypes'],
      provides=['pyads'],
      license='MIT',
      url = 'https://github.com/MrLeeh/pyads'
)
