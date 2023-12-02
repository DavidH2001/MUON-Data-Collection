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


class DataCollector:
    """Data collector object class."""
    def __init__(self,
                 com_port: str,
                 event_file_name: str = None,
                 trigger_string: str = '',
                 save_results: bool = True):

        """
        Constructor.
        :param com_port:
        :param event_file_name:
        :param trigger_string:
        :param save_results:
        """
        self._com_port = com_port
        self._event_file_name: str = event_file_name
        self._event_file = None
        self._save_results: bool = save_results

        if self._save_results:
            self._event_file = open(self._event_file_name, "w")

        self._save_results: bool = save_results
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

        ###buff = []
        ###buff_queue = collections.deque(maxlen=NUM_BUFFS)
        ###start_ms = None
        ###last_buff_saved_ms = None
        print("exit acquisition detected")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._save_results:
            self._event_file.close()

    def _wait_for_start(self, name: str):

        while True:
            line = self._com_port.readline()    # Wait and read data
            print(line, end='')
            self._com_port.write(b'got-it')
            if name in str(line):
                break

    def acquire_data(self,
                     num_buffs: int = 5,
                     buff_threshold: int = 7,
                     buff_time_ms: int = 60000,
                     save_results: bool = True) -> None:
        """
        Main data acquisition function used to sink the data from the serial port and hold it in a queue of buffers.
        When the buffer queue is full the middle buffer is checked against the trigger threshold. This is then
        repeated for every subsequent buffer received.

        :param num_buffs: The maximum number of buffers to be held by the queue.
        :param buff_threshold: Max event buffer trigger threshold.
        :param buff_time_ms: The time span of a single buffer in milliseconds.
        :param save_results: ??? do we need this ???
        """
        _buff: list = []
        _num_buffs: int = num_buffs
        _buff_threshold: int = buff_threshold
        _buff_time_ms: int = buff_time_ms
        _start_time_ms: int = None
        _last_buff_saved_ms = None
        buff_queue: collections.deque = collections.deque(maxlen=_num_buffs)
        mid_buff: int = int(num_buffs / 2)

        while True:
            # Wait for and read event data.
            data = self._com_port.readline()
            if data == b'exit':
                break
            data = codecs.decode(data, 'UTF-8')
            data = str(datetime.now()) + " " + data
            print(data, end='')
            parts = data.split()
            if _start_time_ms is None:
                # First time round so set start time to arduino ms time.
                _start_time_ms = int(parts[3])
                print(f'start_time_ms = {_start_time_ms}')

            print(f'ellapsed time = {int(parts[3]) - _start_time_ms}')

            # Fill buffer with event data.
            if int(parts[3]) - _start_time_ms < _buff_time_ms:
                # Still within current buffer time period.
                _buff.append(data)
            else:
                # Outside of buffer time period.
                buff_queue.append(_buff)
                print(f'buff time {_buff_time_ms} exceeded, added the buff (len={len(_buff)}) to buff queue at index'
                      f' {len(buff_queue) - 1}')
                # Start new buffer with the latest event.
                _buff = [data]
                _start_time_ms = int(parts[3])
                print(f'start_ms = {_start_time_ms}')

                # Check where we are in the buffer queue.
                if len(buff_queue) == num_buffs:
                    print(f'buff queue now full with {num_buffs} buffs, mid buff index = {mid_buff}, '
                          f'rate={len(buff_queue[mid_buff])}')
                    # Check content of middle buffer.
                    if len(buff_queue[mid_buff]) > buff_threshold:
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
                            self._event_file.writelines(lines)
                            self._event_file.flush()

    def _signal_handler(self, signal, frame):
        """
        Ctrl-c signal handler. Note this can result in an error being generated if
        we are currently blocking on com_port.readline()

        """
        print('ctrl-c detected')

        if self._event_file is not None:
            self._event_file.close()
            print("File closed")
        if self._com_port is not None:
            self._com_port.close()
            print("Com port closed")
        sys.exit(1)
    


    
