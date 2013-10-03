# -*-coding: utf-8 -*-
from distutils.core import setup

setup(
      name = "pyads",
      version = "1.0.2",
      description = "Python wrapper for TwinCAT ADS-DLL",
      author = "Stefan Lehmann",
      author_email = "mrleeh@gmx.de",
      packages = ["pyads"],
      package_data = {'pyads': ['doc/*.*']},
      requires = ['ctypes'],
      provides=['pyads'],
      url = 'https://github.com/MrLeeh/pyads'
      )
