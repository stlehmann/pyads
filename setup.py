#! /usr/bin/env python2
# -*-coding: utf-8 -*-
from setuptools import setup

setup(
      name = "pyads",
      version = "1.1.0",
      description = "Python wrapper for TwinCAT ADS library",
      author = "Stefan Lehmann",
      author_email = "Stefan.St.Lehmann@gmail.com",
      packages = ["pyads"],
      package_data = {'pyads': ['doc/*.*']},
      requires = ['ctypes'],
      provides=['pyads'],
      url = 'https://github.com/MrLeeh/pyads'
)
