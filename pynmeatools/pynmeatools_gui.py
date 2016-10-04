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



class positionWidget(QWidget):
    """
    A widget for NMEA position datasets (GGA, GGL)
    """
    def __init__(self):
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = pynmeatools.__version__
        QWidget.__init__(self)
        layout = QGridLayout(self)
        layout.addWidget(QLabel('Hallo!'),0,0)


#
#
# NMEA device
#
# Connect NMEA sentences and widgets which can plot them
plotwidgets = []
plotwidgets.append(['GGA',positionWidget])        

#class deviceWidget(QWidget):
class deviceWidget(QFrame):
    """
    A widget for a single NMEA device in a nmea0183logger
    """
    update_ident_widgets = pyqtSignal()    
    def __init__(self, ind_device=0, parent_gui = None,dequelen = 100000):
        # Do the rest
        #QWidget.__init__(self)
        super(deviceWidget, self).__init__()
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = pynmeatools.__version__
        # Do the rest
        self.dequelen = dequelen
        QWidget.__init__(self)
        self.nmea0183logger = parent_gui.nmea0183logger
        self.serial = self.nmea0183logger.serial[ind_device]
        self.data_deque = collections.deque(maxlen=self.dequelen) # Get the data from nmealogger
        self.identifiers = []
        self.num_identifiers = []        
        self.serial['data_queues'].append(self.data_deque)
        self._info_str = self.serial['port']
        self._qlabel_info     = QLabel(self._info_str)
        self._qlabel_bin      = QLabel('')
        self._qlabel_sentence = QLabel('')
        self._qlabels_identifiers = []
        self._update_info()
        
        self._flag_show_raw_data = False
        self._button_raw_data = QPushButton('Raw data')
        self._button_raw_data.clicked.connect(self._show_raw_data)
        self.layout = QGridLayout(self)
        self.layout.addWidget(self._qlabel_info,0,0)
        self.layout.addWidget(self._qlabel_bin,1,0)
        self.layout.addWidget(self._qlabel_sentence,2,0)        
        self.layout.addWidget(self._button_raw_data,3,0)
        
        
    def _new_data(self):
        """Function called as a signal when new data arrives, this is a dummy
        function which emits a signal (update_ident_widgets.) and is
        otherwise doing not much

        """
        funcname = self.__class__.__name__ + '._new_data()'
        # We do it with signals to make it thread-safe
        self.update_ident_widgets.emit()
        print('Hallo new data!')

    def _update_info(self):
        #print('Update')        
        if( self.nmea0183logger != None ):
            self._bin_str = 'Bytes read ' + str(self.serial['bytes_read'])
            self._sentence_str = 'NMEA sets read ' + str(self.serial['sentences_read'])
            self._qlabel_bin.setText(self._bin_str)
            self._qlabel_sentence.setText(self._sentence_str)

            for ind,lab in enumerate(self._qlabels_identifiers):
                txt = self.identifiers[ind][:-1] + ' ' + str(self.num_identifiers[ind])
                lab.setText(txt)
                

    def _update_identifier_widgets(self):
        """
        """
        while(len(self.data_deque) > 0):
            raw_data = self.data_deque.pop()
            #print('Got: ' + str(raw_data))
            data = pynmeatools.parse(raw_data['nmea'])
            # Show raw data
            if(self._flag_show_raw_data):
                self._plaintext_data.insertPlainText(str(raw_data['nmea']))

            # Check for new identifiers
            if(data != None):
                ident = data.identifier()
                print('Ident:' + ident)
                try:
                    ind = self.identifiers.index(ident)
                    self.num_identifiers[ind] += 1
                except:
                    print('Adding identifier:' + str(ident))                    
                    self.identifiers.append(ident)
                    self.num_identifiers.append(0)
                    lab = QLabel(ident[:-1] + ' 1')
                    #lab = QLabel(ident,self)
                    self._qlabels_identifiers.append(lab)
                    self.layout.addWidget(lab,3 + len(self.identifiers),0)   
                    # Test if we have a widget for plotting this dataset
                    for ide in plotwidgets:
                        if(isinstance(ide[0], str)):
                            ind = ident.find(ide[0])
                            if(ind >= 0):
                                print('Found a widget for ' + str(ident) + ':' + str(ide[1]))
                self._update_info()
                #if not ident in self.identifiers:

                print(self.identifiers)
                print(self.num_identifiers)
                


    def _show_raw_data(self):
        """
        Plots the raw data in a plaintextwidget
        """
        self._flag_show_raw_data = True
        self._plaintext_data = QPlainTextEdit()
        self._plaintext_data.setAttribute(Qt.WA_DeleteOnClose)
        self._plaintext_data.destroyed.connect(self._raw_data_close)        
        self._plaintext_data.show()


    def _raw_data_close(self):
        print('Destroyed!')
        self._flag_show_raw_data = False        


class serialWidget(QWidget):
    """
    A widget for serial connections of 
    """
    def __init__(self,parent_gui):
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = pynmeatools.__version__
        self.parent_gui = parent_gui
        self.nmea0183logger = parent_gui.nmea0183logger
        self.emit_signals = []
        # Do the rest
        QWidget.__init__(self)
        
        layout = QGridLayout(self)
        # Serial baud rates
        baud = [300,600,1200,2400,4800,9600,19200,38400,57600,115200,576000,921600]
        self._combo_serial_devices = QComboBox(self)
        self._combo_serial_baud = QComboBox(self)
        for b in baud:
            self._combo_serial_baud.addItem(str(b))

        self._combo_serial_baud.setCurrentIndex(4)
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
                # Create a new device widget
                ind_serial = len(self.nmea0183logger.serial) - 1
                dV = deviceWidget(ind_device = ind_serial,parent_gui = self.parent_gui)
                dV.setStyleSheet(""" deviceWidget { border: 2px solid black; border-radius: 2px; background-color: rgb(255, 255, 255); } """)
                # The signal seems to be connected here, otherwise it does not work ...
                dV.update_ident_widgets.connect(dV._update_identifier_widgets)
                self.parent_gui._add_device(dV)
                self.nmea0183logger.serial[-1]['data_signals'].append(dV._new_data)

                
        elif(self.sender().text() == 'Close'):
            pass


        # Call all the functions in self.emit_signals
        for s in self.emit_signals:
            s()






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
        self.nmea0183logger = pynmeatools.nmea0183logger.nmea0183logger(loglevel=logging.DEBUG)
        # Do the rest
        QWidget.__init__(self)
        # Create the menu
        self.file_menu = QMenu('&File',self)
        self.device_widgets = []
        #self.file_menu.addAction('&Settings',self.fileSettings,Qt.CTRL + Qt.Key_S)
        self.file_menu.addAction('&Quit',self._quit,Qt.CTRL + Qt.Key_Q)
        self.about_menu = QMenu('&About',self)
        self.about_menu.addAction('&About',self._about)
        self.menuBar().addMenu(self.file_menu)
        self.menuBar().addMenu(self.about_menu)
        mainwidget = QWidget(self)
        mainlayout = QGridLayout(mainwidget)
        
        
        self._serial_widget = serialWidget(self)
        
        
        self._button_log = QPushButton('Show log')
        self._button_log.clicked.connect(self._log_widget)
        self._combo_loglevel = QComboBox()
        self._combo_loglevel.addItem('Debug')
        self._combo_loglevel.addItem('Info')
        self._combo_loglevel.addItem('Warning')
        
        
        # A table to add all the serial devices
        self._widget_devices = QWidget(self)
        self._layout_devices = QHBoxLayout(self._widget_devices)
        self._layout_devices.addStretch(1)
        
        # Layout
        mainlayout.addWidget(self._serial_widget,0,0)
        mainlayout.addWidget(self._button_log,0,1)
        mainlayout.addWidget(self._combo_loglevel,0,2)

        mainlayout.addWidget(self._widget_devices,1,0,2,3)

        # Focus 
        mainwidget.setFocus()
        self.setCentralWidget(mainwidget)


    def _add_device(self,device):
        """
        
        Adds a new deviceWidget
        
        """
                
        device.setMaximumWidth(300)
        ind = len(self.device_widgets)
        self.device_widgets.append(device)
        self._layout_devices.insertWidget(ind,device)        
        
        
    def _log_widget(self):
        """
        A widget of log data
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


    def _something_changed(self):
        """
        """
        funcname = self.__class__.__name__ + '._something_changed()'        
        self.logger.debug(funcname)

        
    
        


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

