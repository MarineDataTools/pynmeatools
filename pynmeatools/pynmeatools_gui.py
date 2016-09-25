#!/usr/bin/env python3
import sys
import os
import logging
try:
    import queue as queue # python 3
except:
    import Queue as queue # python 2.7
import threading
import serial
import socket
import datetime
import collections
import time
import argparse
import pynmeatools
import glob


# Import qt
try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    print('Using pyqt5')
except:
    try:
        from PyQt4.QtGui import * 
        from PyQt4.QtCore import *
        print('Using pyqt4')
    except:
        raise Exception('Could not import qt, exting')


print(pynmeatools)

logger = logging.getLogger('pynmeatools_gui')
logging.basicConfig(stream=sys.stderr, level=logging.INFO)



def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system

        found here: http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    """
    
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            #print("Opening serial port", port)
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result



class guiMain(QMainWindow):
    """

    Sensor response sledge

    """
    def __init__(self):
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = pynmeatools.__version__
        # Do the rest
        QWidget.__init__(self)
        # Create the menu
        self.file_menu = QMenu('&File',self)

        #self.file_menu.addAction('&Settings',self.fileSettings,Qt.CTRL + Qt.Key_S)
        self.file_menu.addAction('&Quit',self._quit,Qt.CTRL + Qt.Key_Q)
        self.about_menu = QMenu('&About',self)
        self.about_menu.addAction('&About',self._about)        
        self.menuBar().addMenu(self.file_menu)
        self.menuBar().addMenu(self.about_menu)        
        mainwidget = QWidget(self)
        mainlayout = QGridLayout(mainwidget)


        self._combo_serial = QComboBox(self)

        mainlayout.addWidget(self._combo_serial,0,0)


        self._test_serial_ports()
        # Focus 
        mainwidget.setFocus()
        self.setCentralWidget(mainwidget)

    def _test_serial_ports(self):
        """
        
        Look for serial ports

        """
        funcname = self.__class__.__name__ + '._test_serial_ports()'        
        ports = serial_ports()
        # This could be used to pretest devices
        #ports_good = self.test_device_at_serial_ports(ports)
        ports_good = ports
        logger.debug(funcname + ': ports:' + str(ports_good))
        self._combo_serial.clear()
        for port in ports_good:
            self._combo_serial.addItem(str(port))        

    def _quit(self):
        try:
            self._about_label.close()
        except:
            pass
        
        self.close()

        
    def _about(self):
        about_str = '\n pynmeatools_gui \n'        
        about_str += '\n This is pynmeatools_gui: ' + self.__version__
        about_str += '\n Copyright Peter Holtermann \n'
        about_str += '\n peter.holtermann@io-warnemuende.de \n'        
        self._about_label = QLabel(about_str)
        self._about_label.show()        


def main():
    app = QApplication(sys.argv)
    myapp = guiMain()
    myapp.show()
    sys.exit(app.exec_())    

if __name__ == "__main__":
    main()

