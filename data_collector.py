#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 18 16:26:17 2022

@author: dave

Detetcor will automatically reset when this program connects with it.  
"""

import sys
import signal
import time
import collections
import codecs
from datetime import datetime

# Create a queue of NUM_BUFF buffers each having a life span of BUFF_TIME_MS. When NUM_BUFF buffers have been queued
# the middle buffer is checked for its quantity/capture rate. This is then repeated for every subsequent buffer
# received.

class DataCollector:

    def __init__(self,
                 com_port: str,
                 file_name: str,
                 trigger_string: str = '',
                 save_results: bool = True):

        """

        :param port_name:
        :param file_name:
        :param trigger_string:
        :param save_results:
        """
        self._com_port = com_port
        self._data_file = None
        signal.signal(signal.SIGINT, self._signal_handler)

        print("\nTaking data ...")
        print("Press ctl+c to terminate process")
        #com_port = serial.Serial(port_name)
        #com_port.baudrate = 9600
        #com_port.bytesize = 8
        #com_port.parity = 'N'
        #com_port.stopbits = 1
        time.sleep(1)
        if trigger_string != '':
            print("waiting for trigger string...")
            self._wait_for_start(trigger_string)
            print(f"Trigger string '{trigger_string}' detected, starting "
                  "acquisition")
        print("Starting acquisition")
        if save_results:
            self._data_file = open(file_name, "w")
        ###buff = []
        ###buff_queue = collections.deque(maxlen=NUM_BUFFS)
        ###start_ms = None
        ###last_buff_saved_ms = None
        print("exit acquisition detected")

    def _wait_for_start(self, name: str):

        while True:
            line = self._com_port.readline()    # Wait and read data
            print(line, end='')
            self._com_port.write(b'got-it')
            if name in str(line):
                break

    def acquire_data(self,
                     num_buffs: int = 5,
                     max_buff_rate: int = 7,
                     buff_time_ms: int = 60000,
                     save_results: bool = True):

        _buff = []
        _num_buffs = num_buffs
        _max_buff_rate = max_buff_rate
        _buff_time_ms = buff_time_ms
        _start_time_ms = None
        _last_buff_saved_ms = None

        buff_queue = collections.deque(maxlen=_num_buffs)
        mid_buff = int(num_buffs / 2)

        while True:
            data = self._com_port.readline()  # Wait and read data
            if data == b'exit':
                break
            data = codecs.decode(data, 'UTF-8')
            data = str(datetime.now()) + " " + data
            print(data, end='')
            parts = data.split()
            if _start_time_ms is None:
                # set start time to arduino ms time
                _start_ms = int(parts[3])
                print(f'start_ms = {_start_time_ms}')

            print(f'ellapsed time = {int(parts[3]) - _start_time_ms}')
            if int(parts[3]) - _start_time_ms < _buff_time_ms:
                _buff.append(data)
            else:
                buff_queue.append(buff)
                print(f'!!! got buff len = {len(buff)}, added to buff queue at index {len(buff_queue) - 1}')
                # start new buffer with latest event
                buff = [data]
                _start_ms = int(parts[3])
                print(f'start_ms = {_start_ms}')
                if len(buff_queue) == num_buffs:
                    print(f'buff queue full, mid buff index = {mid_buff}, rate={len(buff_queue[mid_buff])}')
                    if len(buff_queue[mid_buff]) > max_buff_rate:
                        print('mid buff rate exceeded')
                        if save_results:
                            last_buff_saved_ms = buff_queue[-1][3]
                            n = 0
                            for i in range(num_buffs):
                                if buff_queue[i][3] <= last_buff_saved_ms:
                                    break
                                else:
                                    n += 1
                            print(f"overlap = {n}")
                            # lines = [x for y in buff_queue for x in y]
                            lines = []
                            for i in range(n, num_buffs):
                                lines += buff_queue[i]
                            self._data_file.writelines(lines)
                            self._data_file.flush()

    def _signal_handler(self, signal, frame):
        """
        Ctrl-c signal handler. Note this can result in an error being generated if
        we are currently blocking on com_port.readline()

        """
        print('ctrl-c detected')

        if self._data_file is not None:
            self._data_file.close()
            print("File closed")
        if self._com_port is not None:
            self._com_port.close()
            print("Com port closed")
        sys.exit(1)
    


    
