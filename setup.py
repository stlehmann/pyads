# -*-coding: utf-8 -*-
from distutils.core import setup

setup(
      name = "pyads",
      version = "1.0.4",
      description = "Python wrapper for TwinCAT ADS-DLL",
      author = "Karl-Heinz reichel",
      author_email = "kh.reichel@techdrivers.de",
      packages = ["pyads"],
      package_data = {'pyads': ['doc/*.*']},
      requires = ['ctypes'],
      provides=['pyads'],
      url = 'https://github.com/khReichel/pyads'
      )
