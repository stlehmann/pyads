# ADS
Fork of the Beckhoff/ADS repo: https://github.com/Beckhoff/ADS

Modified for use with the pyads python wrapper: https://github.com/MrLeeh/pyads

## Usage
```bash
git clone https://github.com/dabrowne/ADS.git

# Change into root of the cloned repository
cd ADS

# Build the library and install to /usr/lib/
sudo make install
```

## Modifications from original repo

 - Adjusted the build process to output Linux shared object (.so)
 - Wrapped API in extern "C" to avoid name mangling