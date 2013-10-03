#-*- coding:utf-8-*-
'''
Created on 25.03.2013
@author: lehmann
'''
from pyads import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys

class MainForm(QDialog):

    def _initADS(self):
        self.adsPort = adsPortOpen()
        self.adsAdr = adsGetLocalAddress()
        self.adsAdr.setPort(PORT_SPS1)

    def __init__(self, parent=None):
        super(MainForm, self).__init__(parent)
        
        #ADS initialisieren       
        self._initADS()
        
        #Elemente
        bit1CheckBox = QCheckBox("Bit1")
        (errCode, bit1) = adsSyncReadReq(self.adsAdr, INDEXGROUP_MEMORYBIT, 100*8+0, PLCTYPE_BOOL)
        if errCode == 0: bit1CheckBox.setChecked(bit1)
        
        bit2CheckBox = QCheckBox("Bit2")
        (errCode, bit2) = adsSyncReadReq(self.adsAdr, INDEXGROUP_MEMORYBIT, 100*8+1, PLCTYPE_BOOL)
        if errCode == 0: bit2CheckBox.setChecked(bit2)
        
        bit3CheckBox = QCheckBox("Bit3")
        (errCode, bit3) = adsSyncReadReq(self.adsAdr, INDEXGROUP_MEMORYBIT, 100*8+2, PLCTYPE_BOOL)
        if errCode == 0: bit3CheckBox.setChecked(bit3)
        
        bit4CheckBox = QCheckBox("Bit4")
        (errCode, bit4) = adsSyncReadReq(self.adsAdr, INDEXGROUP_MEMORYBIT, 100*8+3, PLCTYPE_BOOL)
        if errCode == 0: bit4CheckBox.setChecked(bit4)
        
        #Layout
        layout = QVBoxLayout()
        layout.addWidget(bit1CheckBox)
        layout.addWidget(bit2CheckBox)
        layout.addWidget(bit3CheckBox)
        layout.addWidget(bit4CheckBox)
        self.setLayout(layout)
        
        #Signale
        self.connect(bit1CheckBox, SIGNAL("stateChanged(int)"), self.bit1CheckBox_stateChanged)
        self.connect(bit2CheckBox, SIGNAL("stateChanged(int)"), self.bit2CheckBox_stateChanged)
        self.connect(bit3CheckBox, SIGNAL("stateChanged(int)"), self.bit3CheckBox_stateChanged)
        self.connect(bit4CheckBox, SIGNAL("stateChanged(int)"), self.bit4CheckBox_stateChanged)
                 
    def __del__(self):
        adsPortClose()
        
    def bit1CheckBox_stateChanged(self, state):
        adsSyncWriteReq(self.adsAdr, INDEXGROUP_MEMORYBIT, 100*8+0, state, PLCTYPE_BOOL)
    
    def bit2CheckBox_stateChanged(self, state):
        adsSyncWriteReq(self.adsAdr, INDEXGROUP_MEMORYBIT, 100*8+1, state, PLCTYPE_BOOL)
    
    def bit3CheckBox_stateChanged(self, state):
        adsSyncWriteReq(self.adsAdr, INDEXGROUP_MEMORYBIT, 100*8+2, state, PLCTYPE_BOOL)
    
    def bit4CheckBox_stateChanged(self, state):
        adsSyncWriteReq(self.adsAdr, INDEXGROUP_MEMORYBIT, 100*8+3, state, PLCTYPE_BOOL)
        
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    frm = MainForm()
    frm.show()
    app.exec_() 
