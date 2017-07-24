# Installation

From PyPi:

```bash
$ pip install pyads
```

From Github:

```bash
$ git clone https://github.com/MrLeeh/pyads.git --recursive
$ cd pyads
$ python setup.py install
```

## Installation on Linux

For Linux *pyads* uses the ADS library *adslib.so* which needs to be compiled
from source if you use a source package. This should not be an issue, however
if you should encounter any problems with the *adslib.so* please contact me.

## Installation on Windows

On Windows *pyads* uses the *TcADSDll.dll* which is provided when you install
Beckhoffs TwinCAT on your machine. Make sure that it is accessible and 
installed in your PATH.

## Testing your installation

You can test your installation by simply popping up a python console and
importing the pyads module. If no errors occur everything is fine and you can
carry on.

```python

>>> import pyads
>>>
```

If you get an *OSError* saying that the *adslib.so* could not be found there
probably went something wrong with the build process of the shared library. In
this case you can create the *adslib.so* manually by doing the following:

```bash
$ cd src
$ make
$ sudo make install
```

This compiles and places the *adslib.so* in your */usr/lib/* directory.
