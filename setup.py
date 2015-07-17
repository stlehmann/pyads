#! /usr/bin/env python2
# -*-coding: utf-8 -*-
from setuptools import setup
import versioneer

setup(
      name = "pyads",
      version = versioneer.get_version(),
      description = "Python wrapper for TwinCAT ADS library",
      author = "Stefan Lehmann",
      author_email = "Stefan.St.Lehmann@gmail.com",
      packages = ["pyads"],
      package_data = {'pyads': ['doc/*.*']},
      requires = ['ctypes'],
      provides=['pyads'],
      url = 'https://github.com/MrLeeh/pyads',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries'
      ],
      cmdclass=versioneer.get_cmdclass()
)
