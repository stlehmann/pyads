# -*-coding: utf-8 -*-
from distutils.core import setup

setup(
      name = "adsPy",
      version = "1.0.2",
      description = "Python wrapper for Beckhoff ADS-DLL",
      author = "Stefan Lehmann",
      author_email = "mrleeh@gmx.de",
      packages = ["adsPy"],
      package_data = {'adsPy': ['doc/*.*']},
      requires = ['ctypes'],
      provides=['adsPy'],
      url = 'http://mrleeh.square7.ch/'
      )