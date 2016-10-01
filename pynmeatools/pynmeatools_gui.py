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
import glob
import pynmeatools


# TODO
# Implement this here
# http://stackoverflow.com/questions/24469662/how-to-redirect-logger-output-into-pyqt-text-widget
#
#


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

logging.basicConfig(stream=sys.stderr)
logger = logging.getLogger('pynmeatools_gui')
logger.setLevel(logging.DEBUG)

pynmeatools.nmea0183logger.logger.setLevel(logging.DEBUG)


logger.info('HALLO')
logger.debug('HALLO')

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



class serialWidget(QWidget):
    """
    A widget for serial connections of 
    """
    def __init__(self,nmea0183logger):
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = pynmeatools.__version__
        self.nmea0183logger = nmea0183logger
        # Do the rest
        QWidget.__init__(self)

        layout = QGridLayout(self)
        # Serial baud rates
        baud = [300,600,1200,2400,4800,9600,19200,38400,57600,115200,576000,921600]
        self._combo_serial_devices = QComboBox(self)
        self._combo_serial_baud = QComboBox(self)
        for b in baud:
            self._combo_serial_baud.addItem(str(b))        
        self._button_serial_openclose = QPushButton('Open')
        self._button_serial_openclose.clicked.connect(self._openclose)
        self._test_serial_ports()

        layout.addWidget(self._combo_serial_devices,0,0)
        layout.addWidget(self._combo_serial_baud,0,1)
        layout.addWidget(self._button_serial_openclose,0,2)

        
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
        self._combo_serial_devices.clear()
        for port in ports_good:
            self._combo_serial_devices.addItem(str(port))

            
    def _openclose(self):
        """

        Opening or closing a serial device

        """
        funcname = self.__class__.__name__ + '._openclose()'
        print(funcname)
        logger.debug(funcname)
        port = str(self._combo_serial_devices.currentText())
        ind = self._combo_serial_devices.currentIndex()
        b = int(self._combo_serial_baud.currentText())
        if(self.sender().text() == 'Open'):
            logger.debug(funcname + ": Opening Serial port" + port)
            ret = self.nmea0183logger.add_serial_device(port)
            if(ret):
                self._combo_serial_devices.removeItem(ind)

                
        elif(self.sender().text() == 'Close'):
            pass

    



class deviceWidget(QWidget):
    """
    A widget for a NMEA device
    """
    def __init__(self,nmea0183loggerdevice=None):
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = pynmeatools.__version__
        # Do the rest
        QWidget.__init__(self)

        layout = QGridLayout(self)
        layout.addWidget(QLabel('Device'),0,0)



class QtPlainTextLoggingHandler(logging.Handler):

    def __init__(self,qtplaintextedit):
        logging.Handler.__init__(self)
        self.qtplaintextedit = qtplaintextedit

    def emit(self, record):
        record = self.format(record)
        #XStream.stdout().write("{}\n".format(record))
        self.qtplaintextedit.insertPlainText("{}\n".format(record))

#
#
# The main gui
#
#
class guiMain(QMainWindow):
    """

    Sensor response sledge

    """
    def __init__(self):
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = pynmeatools.__version__
        # Add a logger object
        print('q',pynmeatools.nmea0183logger)
        print('a',pynmeatools.nmea0183logger.nmea0183logger)
        self.nmea0183logger = pynmeatools.nmea0183logger.nmea0183logger(loglevel=logging.DEBUG)
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


        self._serial_widget = serialWidget(self.nmea0183logger)

        
        self._button_log = QPushButton('Show log')
        self._button_log.clicked.connect(self._log_widget)
        self._combo_loglevel = QComboBox()
        self._combo_loglevel.addItem('Debug')
        self._combo_loglevel.addItem('Info')
        self._combo_loglevel.addItem('Warning')

        # Layout
        mainlayout.addWidget(self._serial_widget,0,0)
        mainlayout.addWidget(QLabel('Status'),1,0)

        mainlayout.addWidget(self._button_log,0,1)
        mainlayout.addWidget(self._combo_loglevel,0,2)


        # Focus 
        mainwidget.setFocus()
        self.setCentralWidget(mainwidget)

    def _log_widget(self):
        """
        A widget 
        """

        self._log_text = QPlainTextEdit()
        self._log_widget = self._log_text        
        handler = QtPlainTextLoggingHandler(self._log_text)
        lformat='%(asctime)-15s:%(levelname)-8s:%(name)-20s:%(message)s'

        # Adding the gui logger
        handler.setFormatter(logging.Formatter(lformat))
        logger.addHandler(handler)
        # Adding the nmea0183 logger
        self.nmea0183logger.logger.addHandler(handler)

        self._log_text.show()
        print('hallo!')
        logger.info('hallo')
        


    def _quit(self):
        try:
            self._about_label.close()
        except:
            pass

        try:
            self._log_widget.close()
        except:
            pass        
        
        self.close()

        
    def _about(self):
        about_str = '\n pynmeatools_gui \n'        
        about_str += '\n This is pynmeatools_gui: ' + self.__version__
        about_str += '\n Written by Peter Holtermann \n'
        about_str += '\n peter.holtermann@io-warnemuende.de \n'
        about_str += '\n under the GPL v3 license \n'                
        self._about_label = QLabel(about_str)
        self._about_label.show()        


def main():
    app = QApplication(sys.argv)
    myapp = guiMain()
    myapp.show()
    sys.exit(app.exec_())    

if __name__ == "__main__":
    main()

