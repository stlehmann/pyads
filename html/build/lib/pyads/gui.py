#-*-coding: utf-8-*-
'''
Created on 19.09.2013
@author: lehmann
'''
from constants import INDEXGROUP_MEMORYBIT, PLCTYPE_BOOL, INDEXGROUP_MEMORYBYTE
from pyads import adsSyncWriteReq, adsSyncReadReq

class ADSMapper():
    '''
    @summary:  Objects of this class represent a plc process value. The class accomblishes a connection between
    plc and the gui. For implementing the interaction between gui objects and plc values subclass and implement
    mapAdsToGui according to the given examples.
        
    B{sample code:}        
    
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

    @version: 1.0.0
    
    '''
    def __init__(self, plcAddress, plcDataType, guiObjects, hint=None):
        '''
        @type plcAddress: int 
        @param plcAddress: plc address
        @type plcDataType: int
        @param plcDataType: plc data type
        @param guiObjects: list/tuple or single gui objects (for instance Qt objects)
        @type hint: string 
        '''
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
        '''
        writes the value to the plc address
        
        @type adsAdr: adsPy.AmsAdr
        @param adsAdr: address to the ADS device
        
        @param value: value to be written 
        '''
        self.currentValue = value
        indexgroup = INDEXGROUP_MEMORYBIT if self.plcDataType == PLCTYPE_BOOL else INDEXGROUP_MEMORYBYTE
        
        #Schreiben des Wertes in die SPS    
        err = adsSyncWriteReq(adsAdr, indexgroup, self.plcAdr, self.currentValue, self.plcDataType)

        if err == 0:
            return
         
        raise Exception("error writing on address %i. error number %i" % (self.plcAdr, err) )
    
    def read(self, adsAdr):
        '''
        reads from plc address and writes in self.currentValue, calls mapAdsToGui to show the value on
        the connected gui objects 
        
        @type adsAdr: adsPy.AmsAdr
        @param adsAdr: address to the ADS device
        
        @return: current value
        ''' 
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
        '''
        @summary: displays the value on the connected gui object, this function should be overriden, by default the value is printed on the console.
                
        @type guiObject: QObject
        @param guiObject: gui object for value output
        
        @param value: value to display in the gui object
        
        '''
        print value