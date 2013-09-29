# -*-coding: utf-8 -*-
from distutils.core import setup

setup(
      name = "adsPy",
      version = "1.0.2",
      description = "Python wrapper for TwinCAT ADS-DLL",
      author = "Stefan Lehmann",
      author_email = "mrleeh@gmx.de",
      packages = ["adsPy"],
      package_data = {'adsPy': ['doc/*.*']},
      requires = ['ctypes'],
      provides=['adsPy'],
      url = 'https://github.com/MrLeeh/adsPy'
      )