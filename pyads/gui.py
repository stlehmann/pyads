#-*-coding: utf-8-*-
"""
    pyads.gui
    ~~~~~~~~~

    Mapper class for binding GUI objects to the ADS API.

    :copyright: © 2013 by Stefan Lehmann
    :license: MIT, see LICENSE for details

"""
from constants import INDEXGROUP_MEMORYBIT, PLCTYPE_BOOL, INDEXGROUP_MEMORYBYTE
from pyads import adsSyncWriteReq, adsSyncReadReq


class ADSMapper():
    """
    Objects of this class represent a plc process value.
    The class accomblishes a connection between
    plc and the gui. For implementing the interaction between gui objects
    and plc values subclass and implement mapAdsToGui according to the
    given examples.
        
    **sample code:**        
    
    >>> class TextBoxMapper (ADSMapper):
    >>>     def mapAdsToGui(self, guiObject, value):
    >>>         guiObject.setText(str(value))
        
    >>> class ComboBoxMapper (ADSMapper):
    >>>     def mapAdsToGui(self, guiObject, value):
    >>>         index = guiObject.findData(QVariant(value))
    >>>         guiObject.setCurrentIndex(index)
        
    >>> class DSpinBoxMapper (ADSMapper):
    >>>     def mapAdsToGui(self, guiObject, value):
    >>>         guiObject.setValue(float(value))
        
    >>> class SpinBoxMapper (ADSMapper):
    >>>     def mapAdsToGui(self, guiObject, value):
    >>>         guiObject.setValue(int(value))
        
    >>> class BinaryMapper (ADSMapper):
    >>>     def mapAdsToGui(self, guiObject, value):
    >>>         guiObject.setText(__builtin__.bin(int(value)))

    """
    def __init__(self, plcAddress, plcDataType, guiObjects, hint=None):
        """
        :param int plcAddress: plc address
        :param int plcDataType: plc data type
        :param list guiObjects: list/tuple or single gui objects
            (for instance Qt objects)
        :param string hint: a hint for the user

        """
        self.hint = hint                #: hint for plc value
        self.plcAdr = plcAddress        #: plc address
        self.plcDataType = plcDataType  #: plc data type (PLCTYPE constant)
        self.currentValue = None        #: current value of parameter
        self.guiObjects = guiObjects    #: list/tuple or single gui objects (for instance Qt objects)
        
        if isinstance(guiObjects, (list, tuple)):
            for o in guiObjects:
                o.plcObject = self
        else:
            guiObjects.plcObject = self
                
    def write (self, adsAdr, value):
        """
        Write the value to the plc address.
        
        :param pyads.structs.AmsAdr adsAdr: address to the ADS device
        :param value: value to be written

        """
        self.currentValue = value
        indexgroup = INDEXGROUP_MEMORYBIT \
            if self.plcDataType == PLCTYPE_BOOL \
            else INDEXGROUP_MEMORYBYTE
        
        # Write value to plc
        err = adsSyncWriteReq(
            adsAdr, indexgroup,
            self.plcAdr,
            self.currentValue,
            self.plcDataType
        )

        if err == 0:
            return
         
        raise Exception(
            "error writing on address %i. error number %i"
            % (self.plcAdr, err)
        )
    
    def read(self, adsAdr):
        """
        Read from plc address and write in self.currentValue,
        call pyads.gui.mapAdsToGui() to show the value on
        the connected gui objects 

        :param pyads.structs.AmsAdr adsAdr: address to the ADS device
        :return: current value

        """
        indexgroup = INDEXGROUP_MEMORYBIT if self.plcDataType == PLCTYPE_BOOL else INDEXGROUP_MEMORYBYTE
            
        (err, value) = adsSyncReadReq(adsAdr, indexgroup, self.plcAdr, self.plcDataType)
        
        if err:
            raise Exception("error reading from address %i (%s). error number %i" % (self.plcAdr, self.name, err))
        
        #Wenn es sich um eine Liste oder ein Tuple handelt, dann einzelne Objekte schreiben*) 
        if isinstance(self.guiObjects, (list, tuple)):
            for o in self.guiObjects:
                self.mapAdsToGui(o, value)
        else:
            self.mapAdsToGui(self.guiObjects, value)
        
        self.currentValue = value
        return value
    
    def mapAdsToGui(self, guiObject, value):
        """
        Display the value on the connected gui object.
        Override, by default the value is printed on the console.

        :param guiObject: gui object for value output
        :param value: value to display in the gui object
        
        """
        print value