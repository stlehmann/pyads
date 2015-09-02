pyads - Python package
======================

[![Code Issues](http://www.quantifiedcode.com/api/v1/project/3e884877fac4408ea0d33ec4a788a212/badge.svg)](http://www.quantifiedcode.com/app/project/3e884877fac4408ea0d33ec4a788a212)

This is a python wrapper for TwinCATs ADS library. It provides python functions
for communicating with TwinCAT devices. *pyads* uses the C API *AdsDLL.dll*. The
documentation for the ADS API is available on [infosys.beckhoff.com](http://infosys.beckhoff.com/english.php?content=../content/1033/tcadsdll2/html/tcadsdll_api_overview.htm&id=20557).
### Some Samples

**open port, set port number to 801**
```python
>>> port = adsPortOpen()
>>> adr = adsGetLocalAddress()
>>> adr.setPort(PORT_SPS1)
```

**set ADS-state and machine-state**
```python
>>> adsSyncWriteControlReq(adr, ADSSTATE_STOP, 0, 0)
```

**read bit %MX100.0, toggle it and write back to plc**
```python
>>> data = adsSyncReadReq(adr, INDEXGROUP_MEMORYBIT, 100*8 + 0, PLCTYPE_BOOL)
>>> adsSyncWriteReq(adr, INDEXGROUP_MEMORYBIT, 100*8 + 0, not data)
```

**write an UDINT value to MW0 and read it from plc**
```python
>>> adsSyncWriteReq(adr, INDEXGROUP_MEMORYBYTE, 0, 65536, PLCTYPE_UDINT)
>>> adsSyncReadReq(adr, INDEXGROUP_MEMORYBYTE, 0, PLCTYPE_UDINT)
```

**write a string value in MW0 and read it from plc**
```python
>>> adsSyncWriteReq(adr, INDEXGROUP_MEMORYBYTE, 0, "Hallo, wie geht es?", PLCTYPE_STRING)
>>> adsSyncReadReq(adr, INDEXGROUP_MEMORY_BYTE, 0, PLCTYPE_STRING)
```

**read a value of type real from global variable foo**
```python
>>> adsSyncReadByName(adr, ".foo", PLCTYPE_REAL)
```

**write a value of type real to global variable bar**
```python
>>> adsSyncWriteByName(adr, ".bar", 1.234, PLCTYPE_REAL)
```

**close port**
```python
>>> adsPortClose()
```