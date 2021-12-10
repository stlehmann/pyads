pyads - Python package
======================

[![PyPI version](https://badge.fury.io/py/pyads.svg)](https://badge.fury.io/py/pyads)
[![CI](https://github.com/stlehmann/pyads/actions/workflows/ci.yml/badge.svg)](https://github.com/stlehmann/pyads/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/stlehmann/pyads/badge.svg?branch=master)](https://coveralls.io/github/stlehmann/pyads?branch=master)
[![Documentation Status](https://readthedocs.org/projects/pyads/badge/?version=latest)](http://pyads.readthedocs.io/en/latest/?badge=latest)
[![Downloads](https://pepy.tech/badge/pyads)](https://pepy.tech/project/pyads)
[![Downloads](https://pepy.tech/badge/pyads/week)](https://pepy.tech/project/pyads)

This is a python wrapper for TwinCATs ADS library. It provides python functions
for communicating with TwinCAT devices. *pyads* uses the C API provided by *TcAdsDll.dll* on Windows *adslib.so* on Linux. The documentation for the ADS API is available on [infosys.beckhoff.com](http://infosys.beckhoff.com/english.php?content=../content/1033/tcadsdll2/html/tcadsdll_api_overview.htm&id=20557).

Documentation: http://pyads.readthedocs.io/en/latest/index.html

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
git clone https://github.com/MrLeeh/pyads.git --recursive
cd pyads
python setup.py install
```

## Features

* connect to a remote TwinCAT device like a plc or a PC with TwinCAT
* create routes on Linux devices and on remote plcs
* supports TwinCAT 2 and TwinCAT 3
* read and write values by name or address
* read and write DUTs (structures) from the plc
* notification callbacks

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

[0]: https://infosys.beckhoff.de/english.php?content=../content/1033/TcSystemManager/Basics/TcSysMgr_AddRouteDialog.htm&id=

## Contributing guidelines

Contributions are very much welcome. pyads is under active development. However it is a side-project of mine so please have some
patience when creating issues or PRs. Here are some main guidelines which I ask you to follow along:

* Create PRs based on the [master](https://github.com/stlehmann/pyads) branch.
* Add an entry to the [Changelog](https://github.com/stlehmann/pyads/blob/master/CHANGELOG.md).
* Keep PRs small (if possible), this makes reviews easier and your PR can be merged faster.
* Address only one issue per PR. If you want to make additional fixes e.g. on import statements, style or documentation 
which are not directly related to your issue please create an additional PR that adresses these small fixes.
