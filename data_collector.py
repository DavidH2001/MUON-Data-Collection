#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 18 16:26:17 2022

@author: dave

Detetcor will automatically reset when this program connects with it.
"""
import os.path
import sys
import signal
import threading
import time
import logging
import codecs
import pandas as pd
from datetime import datetime, timezone


class DataCollector:
    """Data collector object class."""

    def __init__(self,
                 com_port: str,
                 save_dir: str = None,
                 **kwargs):
        """
        Constructor.
        :param com_port:
        :param save_dir:
        :param kwargs:
               buff_length: The number of events to be held in the buffer.
               save_results: ??? do we need this ???
               use_arduino_time: Use Arduino timing if True else use PC clock. Defaults to False.
        """
        logging.basicConfig(encoding='utf-8', level=logging.INFO)

        self._com_port = com_port
        if not os.path.exists(save_dir):
            raise NotADirectoryError(f"The specified save directory {save_dir} does not exist.")
        self._buff_length: int = kwargs.get('buff_length', 100)

        # self._save_dir: str = save_dir
        # self._buff_threshold: int = kwargs.get('buff_threshold', 7)
        # self._buff_time_ms: int = kwargs.get('buff_time_ms', 60000)
        self._trigger_string: bool = kwargs.get('trigger_string', '')
        # self._save_results: bool = kwargs.get('save_results', True)
        # self._use_arduino_time: bool = kwargs.get('use_arduino_time', False)
        # self._start_time: (datetime, int) = None
        # self._last_buff_saved_ms = None
        # self._buff = TextBuff()
        # self._buff_queue = kwargs.get("buff_queue", BuffQueue(save_dir=save_dir))
        # self._event_file = None
        self._acquisition_ended = False
        # self._buff_count = 0
        # self._event_count = 0
        # self._previous_arduino_time: int = 0
        # self._last_buff_count_saved: int = 0
        # self._event_freq_history: np.ndarray = np.zeros(self._buff_queue.max_entries)
        # self._median_frequency: float = None
        #self._df = pd.DataFrame(columns=['date_time', 'comp_time', 'event', 'adc', 'sipm', 'dead_time', 'temp', 'name'],
        #                        dtype=['str', 'int', 'int', 'int', 'float', 'float', 'int', 'float', 'str'])
        self._buff = pd.DataFrame({'comp_time': pd.Series(dtype='str'),
                                   'event': pd.Series(dtype='int'),
                                   'arduino_time': pd.Series(dtype='int'),
                                   'adc': pd.Series(dtype='int'),
                                   'sipm': pd.Series(dtype='int'),
                                   'dead_time': pd.Series(dtype='int'),
                                   'temp': pd.Series(dtype='float'),
                                   'name': pd.Series(dtype='str')})
        signal.signal(signal.SIGINT, self._signal_handler)

        print("\nTaking data ...")
        print("Press ctl+c to terminate process")
        time.sleep(1)
        if self._trigger_string != '':
            print("waiting for trigger string...")
            self._wait_for_start(self._trigger_string)
            print(f"Trigger string '{self._trigger_string}' detected, starting "
                  "acquisition")
        print("Starting acquisition")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # if self._save_results:
        #    self._event_file.close()
        pass

    @property
    def acquisition_ended(self):
        return self._acquisition_ended

    def _wait_for_start(self, name: str):

        while True:
            line = self._com_port.readline()  # Wait and read data
            print(line, end='')
            self._com_port.write(b'got-it')
            if name in str(line):
                break

    def _acquire_data(self) -> None:
        """
        Main data acquisition function used to sink the data from the serial port and hold it in a queue of buffers.
        Each buffer can hold a number of events that arrive within the specified time period. When the buffer queue is
        full the middle buffer is checked against the max number of events trigger threshold. This is then repeated for
        every subsequent buffer received. When a middle buffer exceeds the trigger threshold then the entire contents
        of the buffer queue are saved.
        """
        self._acquisition_ended = False
        cur_buff_index = 0
        while True:
            # Wait for and read event data.
            data = self._com_port.readline()
            if data == b'exit':
                logging.info("EXIT!!!")
                break

            data = codecs.decode(data, 'UTF-8')
            #self._event_count += 1
            date_time_now = datetime.now(timezone.utc)

            # if self._start_time is None:
            #     # First time round so set start time.
            #     if self._use_arduino_time:
            #         split_data = data.split()
            #         arduino_time = int(split_data[2])
            #         self._start_time = arduino_time
            #     else:
            #         self._start_time = date_time_now
            #     logging.info(f'start_time = {self._start_time}')
            #     continue

            data = data.split()
            data = [date_time_now.strftime("%Y%m%d %H%M%S.%f")[:-3]] + data

            if len(self._buff) < self._buff_length:
                self._buff.loc[len(self._buff)] = data
            else:
                self._buff.loc[cur_buff_index] = data
                cur_buff_index += 1
                if cur_buff_index == 10:
                    cur_buff_index = 0
                #cur_buff_index = cur_buff_index % self._buff_length # !?!?!?!
            logging.info(data)


        self._acquisition_ended = True

    def acquire_data(self) -> None:
        t1 = threading.Thread(target=self._acquire_data)
        t1.start()

    def _signal_handler(self, signal, frame):
        """
        Ctrl-c signal handler. Note this can result in an error being generated if
        we are currently blocking on com_port.readline()

        """
        logging.info('ctrl-c detected')

        if self._event_file is not None:
            self._event_file.close()
            logging.info("File closed")
        if self._com_port is not None:
            self._com_port.close()
            logging.info("Com port closed")
        sys.exit(1)




