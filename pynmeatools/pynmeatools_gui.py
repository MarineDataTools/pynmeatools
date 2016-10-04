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
    def __init__(self,port='XXX'):
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = pynmeatools.__version__
        QWidget.__init__(self)
        self.port = port
        Font = QFont('SansSerif', 15)
        self.titles = {}
        self.titles['lat']  = QLabel('Latitude')
        self.titles['lon']  = QLabel('Longitude')
        self.titles['time'] = QLabel('Time (UTC)')
        self.titles['sat'] = QLabel('# Sat.')
        self.titles['dil'] = QLabel('Accur.')                

        self.labels = {}
        self.labels['lat']  = QLabel('XX')
        self.labels['lon']  = QLabel('XX')
        self.labels['time'] = QLabel('XX')
        self.labels['sat']  = QLabel('XX')
        self.labels['dil']  = QLabel('XX')                
        for lab in self.titles.items():
            lab[1].setFont(Font)

        for lab in self.labels.items():
            lab[1].setFont(Font)            

        mainlayout = QVBoxLayout(self)

        layout = QGridLayout(self)
        layout.addWidget(self.titles['time'],0,0)
        layout.addWidget(self.labels['time'],1,0)                        
        layout.addWidget(self.titles['lat'],0,1)
        layout.addWidget(self.labels['lat'],1,1)
        layout.addWidget(self.titles['lon'],0,2)
        layout.addWidget(self.labels['lon'],1,2)
        layout.addWidget(self.titles['sat'],2,0)
        layout.addWidget(self.titles['dil'],2,1)                                
        layout.addWidget(self.labels['sat'],3,0)
        layout.addWidget(self.labels['dil'],3,1)

        lab = QLabel(self.port)
        lab.setFont(Font)            
        mainlayout.addWidget(lab)
        mainlayout.addLayout(layout)


    def new_data(self,new_data):
        """
        The function to feed the widget with new data
        """
        try:
            data = pynmeatools.parse(new_data['nmea'])
        except Exception as e:
            print(str(e))
            return

        if('GGA' in data.identifier()):
            print('DATA',data)            
            if(not(data.timestamp == None)):
                tstr = data.timestamp.strftime('%H:%M:%S')
                self.labels['time'].setText(tstr)
            if(len(data.lat) > 0):
                #latstr = str(data.latitude)
                latstr = '{:03.6f} '.format(data.latitude)
                latstr += data.lat_dir
                self.labels['lat'].setText(latstr)
            if(len(data.lon) > 0):
                #lonstr = str(data.longitude)                
                lonstr = '{:03.6f} '.format(data.longitude)
                lonstr += data.lon_dir
                self.labels['lon'].setText(lonstr)
            if(len(data.num_sats) > 0):
                self.labels['sat'].setText(data.num_sats)
            if(len(data.horizontal_dil) > 0):
                self.labels['dil'].setText(data.horizontal_dil)                
            


#
#
# NMEA device
#
# Connect NMEA sentences and widgets which can plot them
plotwidgets = []
plotwidgets.append(['GGA',positionWidget,'Position'])        

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

        # A list of widgets to plot the NMEA data
        self.plot_widgets = []        
        
        self._flag_show_raw_data = False
        self._button_raw_data = QPushButton('Raw data')
        self._button_raw_data.clicked.connect(self._show_raw_data)
        self.layout = QGridLayout(self)
        self.layout_idents = QVBoxLayout(self)
        self.layout_plot_idents = QVBoxLayout(self)        
        self.layout.addWidget(self._qlabel_info,0,0)
        self.layout.addWidget(self._qlabel_bin,1,0)
        self.layout.addWidget(self._qlabel_sentence,2,0)
        self.layout.addLayout(self.layout_idents,3,0)
        self.layout.addLayout(self.layout_plot_idents,4,0)
        self.layout_plot_idents.addWidget(self._button_raw_data)
        
        
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
            self._bin_str = 'Bytes read \t' + str(self.serial['bytes_read'])
            self._sentence_str = 'NMEA sets read \t' + str(self.serial['sentences_read'])
            self._qlabel_bin.setText(self._bin_str)
            self._qlabel_sentence.setText(self._sentence_str)

            for ind,lab in enumerate(self._qlabels_identifiers):
                txt = self.identifiers[ind][:-1] + ' \t' + str(self.num_identifiers[ind])
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

            # Send data to widgets
            # TODO: This could be done thread safe using queues
            
            for w in self.plot_widgets:
                w.new_data(raw_data)

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
                    self._qlabels_identifiers.append(lab)
                    self.layout_idents.addWidget(lab)   
                    # Test if we have a widget for plotting this dataset
                    for ide in plotwidgets:
                        if(isinstance(ide[0], str)):
                            ind = ident.find(ide[0])
                            if(ind >= 0):
                                print('Found a widget for ' + str(ident) + ':' + str(ide[1]))
                                but = QPushButton(ide[2])
                                but.clicked.connect(self._open_widgets)
                                self.layout_plot_idents.addWidget(but)
                                
                self._update_info()
                #print(self.identifiers)
                #print(self.num_identifiers)
                
                
    def _open_widgets(self):
        """
        Opens widgets for plotting data
        """
        sender = self.sender()
        sender_txt =str(sender.text())
        print('Hallo: ' + str(sender.text()))
        # Check which widget we have
        for ide in plotwidgets:
            print(ide)
            if(sender_txt == ide[2]):
                w = ide[1]
                self.plot_widgets.append(w(port=self.serial['port']))
                self.plot_widgets[-1].show()

                
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


    def closeEvent(self, event):
        print("Closing all plot widgets")
        try:
            self._plaintext_data.close()
        except:
            pass
        for w in self.plot_widgets:
            w.close()


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
    """
    A handler to display logging text into a qt text widget
    """
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


        # Closing all device widgets
        for w in self.device_widgets:
            w.close()
        
        
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

