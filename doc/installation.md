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
python setup.py install
```

Note: pyads only supports python 3.8 and above.

## Installation on Linux

For Linux *pyads* uses the ADS library *adslib.so* which needs to be compiled
from source if you use a source package. This should not be an issue, however
if you should encounter any problems with the *adslib.so* please contact me.

For the compilation to work you need to make sure `cmake` and `g++` are installed
on your system.

For Ubuntu-based systems or containers use the following commands for installing
the build-dependencies:

```bash
apt udpate
apt install -y cmake g++
```

For containers consider using a separate build stage to keep image size small.

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
```

If you get an *OSError* saying that the *adslib.so* could not be found there
probably went something wrong with the build process of the shared library. In
this case you can create the *adslib.so* manually by doing the following:

```bash
cd adslib
make
sudo make install
```

This compiles and places the *adslib.so* in your */usr/lib/* directory.
