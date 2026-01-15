pyads - Python package
======================

[![PyPI version](https://badge.fury.io/py/pyads.svg)](https://badge.fury.io/py/pyads)
[![Anaconda-Server Badge](https://anaconda.org/conda-forge/pyads/badges/version.svg)](https://anaconda.org/conda-forge/pyads)
[![Anaconda-Server Badge](https://anaconda.org/conda-forge/pyads/badges/platforms.svg)](https://anaconda.org/conda-forge/pyads)

[![CI](https://github.com/stlehmann/pyads/actions/workflows/ci.yml/badge.svg)](https://github.com/stlehmann/pyads/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/stlehmann/pyads/badge.svg?branch=master)](https://coveralls.io/github/stlehmann/pyads?branch=master)
[![Documentation Status](https://readthedocs.org/projects/pyads/badge/?version=latest)](http://pyads.readthedocs.io/en/latest/?badge=latest)
[![Downloads](https://pepy.tech/badge/pyads)](https://pepy.tech/project/pyads)
[![Downloads](https://pepy.tech/badge/pyads/week)](https://pepy.tech/project/pyads)

This is a python wrapper for TwinCATs ADS library. It provides python functions
for communicating with TwinCAT devices. *pyads* uses the C API provided by *TcAdsDll.dll* on Windows *adslib.so* on Linux. The documentation for the ADS API is available on [infosys.beckhoff.com](https://infosys.beckhoff.com/content/1033/tc3_adsdll2/index.html?id=4279787267115190858).

Documentation: http://pyads.readthedocs.io/en/latest/index.html

Issues: In order to assist with issue management, please keep the issue tracker reserved for bugs. For any questions or feature requests, please use the [discussions](https://github.com/stlehmann/pyads/discussions) area. Alternatively, questions can be posted to [Stack Overflow](https://stackoverflow.com/) tagged with `twincat-ads` and state you are using the pyads library. Please search around before posting questions, particulary around route creation and ads error messages when reading or writing variables as these are common issues.

# Installation

From PyPi:

```bash
pip install pyads
```

From conda-forge:

```bash
conda install pyads
```

From source:

```bash
git clone https://github.com/stlehmann/pyads.git --recursive
cd pyads
pip install .
```

## Features

- connect to a remote TwinCAT device like a plc or a PC with TwinCAT
- create routes on Linux devices and on remote plcs
- supports TwinCAT 2 and TwinCAT 3
- read and write values by name or address
- read and write DUTs (structures) from the plc
- notification callbacks

## Basic usage

```python
import pyads

# connect to plc and open connection
plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_TC3PLC1)
plc.open()

# read int value by name
i = plc.read_by_name("GVL.int_val")

# write int value by name
plc.write_by_name("GVL.int_val", i)

# close connection
plc.close()
```

## Contributing guidelines

Contributions are very much welcome. pyads is under development. However it is a side-project so please have some patience when creating issues or PRs. Please also follow the [Contributing Guidelines](https://github.com/stlehmann/pyads/blob/master/CONTRIBUTING.md).
