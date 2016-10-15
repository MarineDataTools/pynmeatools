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
import pynmea2
try:
    import pymqdatastream
except ImportError:
    print('Could not import pymqdatastream, this is not dramatic but some fuctionality is missing (network publishing)')
    pymqdatastream = None

logger = logging.getLogger('pynmeatool_nmea0183logger.py')
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


    


# TODO: This should be somewhere else
def parse(msg):
    """
    Function to parse a nmeadataset
    Input:
       msg: NMEA data str
    """
    ind = msg.find('$')
    #print(msg[ind:])
    # There is data before, lets test if its some sort of date/device string
    if(ind > 0):
        pass
    
    try:
        data = pynmea2.parse(msg[ind:])
        #
        return data


    except ValueError:
        print('Could not parse data: ' + str(msg))
        return None
    

class nmea0183logger(object):
    """
    """
    def __init__(self,loglevel=logging.INFO,print_raw_data=False):
        """
        """
        funcname =  '__init__()'
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(loglevel)
        self.loglevel = loglevel
        self.logger.debug(funcname)                    
        self.dequelen       = 10000
        self.serial         = []
        self.datafiles      = []        
        self.deques         = []
        self.pymqdatastream = None
        self.name           = 'nmea0183logger' # This is mainly used as a datastream identifier
        self.print_raw_data = print_raw_data

        
    def add_serial_device(self,port,baud=4800):
        """
        """
        funcname = 'add_serial_device()'
        try:
            self.logger.debug(funcname + ': Opening: ' + port)            
            serial_dict = {}
            serial_dict['sentences_read'] = 0
            serial_dict['bytes_read']     = 0
            serial_dict['device_name']    = port            
            serial_dict['port']           = port
            serial_dict['device']         = serial.Serial(port,baud)
            serial_dict['thread_queue']   = queue.Queue()
            serial_dict['data_queues']    = []
            serial_dict['data_signals']   = []
            serial_dict['streams']        = [] # pymqdatastream Streams
            serial_dict['thread']         = threading.Thread(target=self.read_nmea_sentences_serial,args = (serial_dict,))
            serial_dict['thread'].daemon = True
            serial_dict['thread'].start()
            self.serial.append(serial_dict)
            if(self.pymqdatastream != None):
                self.add_stream(serial_dict)
                
                
            return True
        except Exception as e:
            self.logger.debug(funcname + ': Exception: ' + str(e))            
            self.logger.debug(funcname + ': Could not open device at: ' + str(port))
            return False


    def rem_serial_device(self,ind):
        """

        Removes a serial item

        """
        pass

        
    def read_nmea_sentences_serial(self, serial_dict):
        """
        The polling thread
        input:
            serial_dict: 
            thread_queue: For stopping the thread
        """
        
        funcname = 'read_nmea_sentences()'
        serial_device = serial_dict['device']
        thread_queue = serial_dict['thread_queue']
        nmea_sentence = ''
        got_dollar = False                            
        while True:
            time.sleep(0.05)
            while(serial_device.inWaiting()):
                # TODO, this could be made much faster ... 
                try:
                    value = serial_device.read(1).decode('utf-8')
                    nmea_sentence += value
                    serial_dict['bytes_read'] += 1
                    if(value == '$'):
                        got_dollar = True
                        # Get the time
                        ti = time.time()

                    elif((value == '\n') and (got_dollar)):
                        got_dollar = False                    
                        nmea_data = {}
                        nmea_data['time'] = ti
                        nmea_data['device'] = serial_device.name
                        nmea_data['nmea'] = nmea_sentence
                        
                        if(self.print_raw_data):
                            write_str = ''
                            write_str += nmea_data['device'] + ' ' 
                            time_str = datetime.datetime.fromtimestamp(nmea_data['time']).strftime('%Y-%m-%d %H:%M:%S')
                            write_str +=  time_str + ' '
                            write_str += nmea_data['nmea']
                            print(write_str)
                            
                        for deque in self.deques:
                            deque.appendleft(nmea_data)

                        # Send into specialised data queues as e.g. for the gui
                        for deque in serial_dict['data_queues']:
                            deque.appendleft(nmea_data)

                        # Send into pymqdatastream streams
                        for stream in serial_dict['streams']:
                            stream.pub_data([[ti,nmea_sentence]])

                        # Call signal functions for new data
                        for s in serial_dict['data_signals']:
                            s()
                            
                        nmea_sentence = ''
                        serial_dict['sentences_read'] += 1

                except Exception as e:
                    self.logger.debug(funcname + ':Exception:' + str(e))

                    
            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                break
            except queue.Empty:
                pass
                    
        return True


    def add_tcp_stream(self,address,port):
        """
        """
        funcname = 'add_tcp_stream()'
        # Create a TCP/IP socket
        try:
            self.logger.debug(funcname + ': Opening TCP socket: ' + address + ' ' + str(port))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((address, port))
            sock.setblocking(0) # Nonblocking
            serial_dict = {}
            serial_dict['sentences_read'] = 0
            serial_dict['device']         = sock
            serial_dict['address']        = address
            serial_dict['port']           = port
            serial_dict['device_name']    = address + ':' + str(port)
            serial_dict['thread_queue']   = queue.Queue()
            serial_dict['thread']         = threading.Thread(target=self.read_nmea_sentences_tcp,args = (serial_dict,))
            serial_dict['thread'].daemon  = True
            serial_dict['thread'].start()
            print('1')            
            self.serial.append(serial_dict)            
        except Exception as e:
            self.logger.debug(funcname + ': Exception: ' + str(e))


    def read_nmea_sentences_tcp(self, serial_dict):
        """
        The tcp polling thread
        Args:
            serial_device: 

        """
        
        funcname = 'read_nmea_sentences_tcp()'
        serial_device = serial_dict['device']
        thread_queue = serial_dict['thread_queue']
        nmea_sentence = ''
        raw_data = ''
        got_dollar = False                   
        while True:
            time.sleep(0.05)
            try:
                data,address = serial_dict['device'].recvfrom(10000)
            except socket.error:
                pass
            else: 
                #print("recv:", data,"times",len(data), 'address',address)
                raw_data += raw_data + data.decode('utf-8')

                for i,value in enumerate(raw_data):
                    nmea_sentence += value
                    if(value == '$'):
                        got_dollar = True
                        # Get the time
                        ti = time.time()

                    elif((value == '\n') and (got_dollar)):
                        got_dollar = False                    
                        nmea_data = {}
                        nmea_data['time'] = ti
                        nmea_data['device'] = serial_dict['address'] + ':' + str(serial_dict['port'])
                        nmea_data['nmea'] = nmea_sentence
                        #self.logger.debug(funcname + ':Read sentence:' + nmea_sentence)
                        for deque in self.deques:
                            deque.appendleft(nmea_data)
                            
                        nmea_sentence = ''
                        serial_dict['sentences_read'] += 1
                        raw_data = raw_data[i+1:]

            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                break
            except queue.Empty:
                pass
                    
        return True



    def add_datastream(self,address=None):
        """
        Adds a nmea0183 logger datastream
        """
        funcname = 'add_datastream()'
        self.logger.debug(funcname)
        # Create a pymqdatastream if neccessary
        if(self.pymqdatastream == None):
            self.create_pymqdatastream()

        # Query remote datastreams
        self.logger.debug(funcname + ': querying')
        remote_datastreams = self.pymqdatastream.query_datastreams()
        self.logger.debug(funcname + ':' + str(remote_datastreams))
        for s in remote_datastreams:
            print(s.name)
            if(self.name in s.name): # Do we have a nmealogger?
                print('Found a logger!')
                print(s)
                for stream in s.Streams:
                    self.add_pymqdsStream(stream)                    


    def add_pymqdsStream(self,stream):
        funcname = 'add_pymqdsStream()'        
        if('nmea' in stream.name):
            if(stream.stream_type == 'pubstream'): # Do we have to subscribe?
                self.logger.debug(funcname + ': Found nmea stream, will subscribe')
                recvstream = self.pymqdatastream.subscribe_stream(stream,statistic=True)
            elif(stream.stream_type == 'substream'): # Already subscribed
                self.logger.debug(funcname + ': Found an already subscribed nmea stream')
                recvstream = stream
            else:
                self.logger.warning(funcname + ': Dont know what to do with stream:' + str(stream))
            serial_dict = {}
            serial_dict['sentences_read'] = 0
            serial_dict['bytes_read']     = 0
            serial_dict['device_name']    = recvstream.name
            serial_dict['address']        = recvstream.socket.address
            serial_dict['port']           = ''
            serial_dict['device']         = recvstream
            serial_dict['thread_queue']   = queue.Queue()
            serial_dict['data_queues']    = []
            serial_dict['data_signals']   = []
            serial_dict['streams']        = [] # pymqdatastream publication streams
            serial_dict['thread']         = threading.Thread(target=self.read_nmea_sentences_datastream,args = (serial_dict,))
            serial_dict['thread'].daemon  = True
            serial_dict['thread'].start()
            self.serial.append(serial_dict)
        else:
            self.logger.info(funcname + 'given stream is not a nmea stream')


    def read_nmea_sentences_datastream(self,serial_dict):
        """
        The datastream polling thread
        Args:
            serial_dict: 
        """
        thread_queue = serial_dict['thread_queue']
        recvstream = serial_dict['device']
        while True:
            time.sleep(0.02)
            ndata = len(recvstream.deque)
            if(ndata > 0):
                data = serial_dict['device'].pop_data(n=1)
                for d in data:
                    print('Data received',data)
                    #bytes_recv = 0
                    bytes_recv = serial_dict['device'].socket.statistic['bytes_received']
                    serial_dict['bytes_read'] = bytes_recv                    
                    nmea_data = {}
                    nmea_data['time'] = d['data'][0][0]
                    nmea_data['device'] = serial_dict['address'] + '/' + serial_dict['device_name']
                    nmea_data['nmea'] =  d['data'][0][1]

                    for deque in self.deques:
                        deque.appendleft(nmea_data)

                    # Send into specialised data queues as e.g. for the gui
                    for deque in serial_dict['data_queues']:
                        deque.appendleft(nmea_data)

                    # Send into pymqdatastream streams
                    for stream in serial_dict['streams']:
                        stream.pub_data([[ti,nmea_sentence]])

                    # Call signal functions for new data
                    for s in serial_dict['data_signals']:
                        s()

                    serial_dict['sentences_read'] += 1                      
                
                
            # Try to read from the queue, if something was read, quit
            # the thread
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                break
            except queue.Empty:
                pass                
            
            
    def add_file_to_save(self,filename, style = 'all'):
        """
        Adds a file to save the data to
        """
        
        funcname = 'add_file_to_save()'
        
        try:
            datafile_dict = {}
            datafile_dict['datafile'] = open(filename,'w')
            datafile_dict['thread_queue'] = queue.Queue()        
            self.deques.append(collections.deque(maxlen=self.dequelen))
            datafile_dict['file_thread'] = \
                        threading.Thread(target=self.save_nmea_sentences,\
                        args = (datafile_dict['datafile'],self.deques[-1],\
                                datafile_dict['thread_queue'],style))
            datafile_dict['file_thread'].daemon = True
            datafile_dict['file_thread'].start()
            self.datafiles.append(datafile_dict)
            self.logger.debug(funcname + ': opened file: ' + filename)
            return datafile_dict['datafile']
        except Exception as e:
            self.logger.warning(funcname + ': Exception: ' + str(e))
            return None

            
    def close_file_to_save(self,datafile):
        """
        Closes the thread and the file to save data to
        input: 
            datafile: can be either an integer or a file object 
        """
        funcname = 'close_file_to_save()'
        if(isinstance(datafile,int)):
            ind_datafile = datafile
            self.logger.debug(funcname + ': got ind, thats easy' )
            found_file = True
        else:
            self.logger.debug(funcname + ': File object, searching for the file' )
            found_file = False
            for ind_datafile,dfile in enumerate(self.datafiles):
                if(dfile['datafile'] == datafile):
                    self.logger.debug(funcname + ': Found file object at index:' + str(ind_datafile))
                    found_file = True
                    break

        if(found_file):
            # Closing thread by sending something to it
            self.datafiles[ind_datafile]['thread_queue'].put('stop')
            # Waiting for closing
            time.sleep(0.05)
        else:
            self.logger.warning(funcname + ': Could not close file: '+str(datafile) )
            print(self.datafiles)
            

    def save_nmea_sentences(self,datafile, deque, thread_queue, style):
        """
        Saves the nmea into a file
        """
        funcname = 'save_nmea_sentences()'
        ct = 0
        dt = 0.05
        while True:
            time.sleep(dt)
            ct += dt
            while(len(deque)):
                data = deque.pop()
                write_str = ''
                if(style == 'all'):
                    write_str += data['device'] + ' ' 
                    time_str = datetime.datetime.fromtimestamp(data['time']).strftime('%Y-%m-%d %H:%M:%S')
                    write_str +=  time_str + ' '
                    write_str += data['nmea']

                elif(style == 'raw'):
                    write_str += data['nmea']

                datafile.write(write_str)                    
            if(ct >= 10): # Sync the file every now and then and show some information
                ct = 0
                self.logger.debug(funcname + ': flushing')
                datafile.flush()                
                info_str = self.serial_info()
                self.logger.info(funcname + ':' + info_str)

            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                datafile.close()
                break
            except queue.Empty:
                pass
            
            
    def serial_info(self):
        """
        Creates an information string of the serial devices, the bytes and NMEA sentences read 
        Returns:
           info_str
        """
        info_str = ''
        for s in self.serial:
            info_str += s['port'] + ' ' + str(s['bytes_read']) + ' bytes '
            info_str += str(s['sentences_read']) + ' NMEA sentences' + '\n'

        return info_str
    
    
    def log_data_in_files(self, filename, time_interval):
        """
        Creates every time_interval a new file and logs the data to it
        input:
        filename: 
        time_interval: datetime.timedelta object, default: datetime.timedelta(hours=1)
        """
        funcname = 'log_data_in_files()'
        self.logger.debug(funcname)
        thread_queue = queue.Queue()
        # If time interval is larger than 10 seconds, create with time interval new files, otherwise only one file
        if(time_interval > datetime.timedelta(seconds=9.9999)):
            self.logger.debug(funcname + ': Starting thread to create every ' +str(time_interval) + ' a new file')
            self.time_thread = threading.Thread(target=self.time_interval_thread, args = (filename,time_interval,thread_queue))
            self.time_thread.daemon = True
            self.time_thread.start()
        else:
            self.logger.debug(funcname + ': Creating file and logging data to ' + filename)            
            datafile = self.add_file_to_save(filename)
            
            
    def time_interval_thread(self,filename,time_interval,thread_queue):
        """

        

        """
        funcname = 'time_interval_thread()'
        dt = .1
        self.logger.debug(funcname)
        now = datetime.datetime.now()
        filename_time = now.strftime(filename + '__%Y%m%d_%H%M%S.log')
        datafile = self.add_file_to_save(filename_time)
        tstart = now
        
        while True:
            time.sleep(dt)            
            now = datetime.datetime.now()
            if((now - tstart) > time_interval):
                self.logger.debug(funcname + ': Time interval thread:' + str(now) +' ' + str(tstart) + ' ' + str(time_interval))
                tstart = now
                self.logger.debug(funcname + ': Creating new file')
                self.close_file_to_save(datafile)
                time.sleep(0.01)
                filename_time = now.strftime(filename + '__%Y%m%d_%H%M%S.log')
                datafile = self.add_file_to_save(filename_time)
                time.sleep(0.01)                
                
            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                datafile.close()
                break
            except queue.Empty:
                pass
            
            
    def create_pymqdatastream(self,address=None):
        """Creates pymqdatastream to stream the read data and to comminucate
        with a remote logger object
        Input:
           address: The address of the datastream, default; pymqdatastream will take care
        """
        funcname = 'create_pymqdatastream()'
        # Import pymqdatastream here
        self.logger.debug(funcname + ': Creating DataStream')
        datastream = pymqdatastream.DataStream(name=self.name,logging_level=self.loglevel)
        self.pymqdatastream = datastream
            
            
    def add_stream(self,serial):
        """
        Adds a pymqdatastream Stream for a serial device.
        Input:
           serial: The serial device to be transmitted
        """
        funcname = 'add_stream()'
        self.logger.debug(funcname)
        datastream = self.pymqdatastream
        # Create variables
        timevar = pymqdatastream.StreamVariable(name = 'unix time',\
                                                unit = 'seconds',\
                                                datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'NMEA data',\
                                                datatype = 'str',\
                                                unit = 'NMEA')
        variables = [timevar,datavar]
        name = 'nmea;' + serial['device_name']
        # Adding publisher sockets and add variables
        pub_socket = datastream.add_pub_socket()
        
        sendstream =  datastream.add_pub_stream(
            socket = pub_socket,
            name   = name,variables = variables)
        
        serial['streams'].append(sendstream)
        print('Hallo',serial['streams'])
        
    def publish_devices(self):
        """
        Publishes all devices
        """
        funcname = 'publish_devices()'
        self.logger.debug(funcname)
        for s in self.serial:
            self.logger.debug(funcname + ': Adding stream for' + str(s))            
            self.add_stream(s)        
        
            
def main():
    """

    Main routine

    """
    usage_str = 'pynmeatools_nmea0183logger --serial_device /dev/ttyACM0 -f test_log -v -v -v'
    desc = 'A python NMEA logger. Example usage: ' + usage_str
    serial_help = 'Serial device to read data from in unixoid OSes e.g. /dev/ttyACM0'
    interval_help = 'Time interval at which new files are created (in seconds)'
    datastream_help = 'Connect to a nmea0183logger published with pymqdatastream'
    publish_datastream_help = 'Create a pymqdatastream Datastream to publish the data over a network'
    raw_data_datastream_help = 'Print raw NMEA data of all devices to the console'                                
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--log_stream', '-l')
    parser.add_argument('--filename', '-f')
    parser.add_argument('--serial_device', '-s', nargs='+', action='append', help=serial_help)
    parser.add_argument('--address', '-a')
    parser.add_argument('--port', '-p')
    parser.add_argument('--interval', '-i', default=0, type=int, help=interval_help)        
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--publish_datastream', '-pd', action='store_true', help=publish_datastream_help)
    parser.add_argument('--datastream', '-d', nargs = '?', default = False, help=datastream_help)
    parser.add_argument('--print_raw_data', '-r', action='store_true', help=raw_data_datastream_help)                                
    
    args = parser.parse_args()
    # Print help and exit when no arguments are given
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)
    
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG
        
    logger.setLevel(loglevel)
    
    time_interval = args.interval
    # Create a nmeaGrabber
    print('hallo Creating a logger')
    s = nmea0183logger(loglevel=logging.DEBUG,print_raw_data = args.print_raw_data)
    try:
        filename = args.filename
        print(filename)
        s.log_data_in_files(filename,datetime.timedelta(seconds=time_interval))
    except Exception as e:
        logger.debug('main(): ' + str(e))
    
    logger.debug('main(): ' + str(args.serial_device))
    #serial_device = args.serial_device
    if(args.serial_device != None):
        for serial_device in args.serial_device:
            logger.debug('Adding serial device ' + str(serial_device))
            serial_device = serial_device[0]
            if(serial_device != None):
                try:
                    s.add_serial_device(serial_device)
                except Exception as e:
                    logger.debug('main():',e)
                    
    
    if(args.address != None and args.port != None):
        addr = args.address
        port = int(args.port)
        s.add_tcp_stream(addr,port)



    
    print('Args publish_datastream:',args.publish_datastream)
    # Create datastream? 
    if(args.publish_datastream == True):
        logger.debug('Creating a pymqdatastream Datastream')
        s.create_pymqdatastream()
        # TODO: add all devices, should be done in nmealogger via registering ..
        s.publish_devices()


    # Connect to datastream?
    # False if not specified, None if no argument was given, otherwise address
    print('Args datastream:',args.datastream)
    if(args.datastream != False):    
        if(args.datastream == None):
            logger.debug('Connecting to  pymqdatastream Datastream logger')
            s.add_datastream()
        

        

    while(True):
        time.sleep(1.0)


if __name__ == "__main__":
    main()
    #pynmea0183logger --address 192.168.236.72 -p 10007 -f test_peter -v -v -v
    #pynmea0183logger --serial_device /dev/ttyACM0 -f test_peter -v -v -v

