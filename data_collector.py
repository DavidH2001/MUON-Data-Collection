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
import copy
from datetime import datetime, timezone

import numpy as np

from text_buff import TextBuff
from buff_queue import BuffQueue


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
               buff_queue: Buffer queue. Will create own if not defined.
               buff_threshold: Max event buffer trigger threshold.
               buff_time_ms: The time span of a single buffer in milliseconds.
               save_results: ??? do we need this ???
               use_arduino_time: Use Arduino timing if True else use PC clock. Defaults to False.
        """
        logging.basicConfig(encoding='utf-8', level=logging.INFO)

        self._com_port = com_port
        if not os.path.exists(save_dir):
            raise NotADirectoryError(f"The specified save directory {save_dir} does not exist.")
        self._save_dir: str = save_dir
        self._buff_threshold: int = kwargs.get('buff_threshold', 7)
        self._buff_time_ms: int = kwargs.get('buff_time_ms', 60000)
        self._trigger_string: bool = kwargs.get('trigger_string', '')
        self._save_results: bool = kwargs.get('save_results', True)
        self._use_arduino_time: bool = kwargs.get('use_arduino_time', False)
        self._start_time: (datetime, int) = None
        self._last_buff_saved_ms = None
        self._buff = TextBuff()
        self._buff_queue = kwargs.get("buff_queue", BuffQueue(save_dir=save_dir))
        self._event_file = None
        self._acquisition_ended = False
        self._buff_count = 0
        self._event_count = 0
        self._previous_arduino_time = 0
        self._last_buff_count_saved = 0
        self._event_freq_history = np.zeros(self._buff_queue.max_entries)
        self._median_frequency = None

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
        #if self._save_results:
        #    self._event_file.close()
        pass

    @property
    def acquisition_ended(self):
        return self._acquisition_ended

    def _wait_for_start(self, name: str):

        while True:
            line = self._com_port.readline()    # Wait and read data
            print(line, end='')
            self._com_port.write(b'got-it')
            if name in str(line):
                break

    def _process_middle_buffer(self):

        mid_buff = self._buff_queue.peek(index=self._buff_queue.mid_index)
        if mid_buff.num_entries > self._buff_threshold:
            logging.info(f'mid buff len={mid_buff.num_entries} exceeded threshold {self._buff_threshold}')

            # if self._ignore_buff_count > 0:
            #     logging.info('still within last saved buffer range so ignoring ')
            #     self._ignore_buff_count -= 1

            if self._save_results:
                last_buff_saved_ms = self._buff_queue.peek(-1).buff[-1].split()[-1]
                logging.info(f'last buff saved arduino time = {last_buff_saved_ms}')
                name = self._buff_queue.peek(0).buff[0].split()[0]
                name = f"{name}.txt"

                if self._buff_count - self._last_buff_count_saved >= self._buff_queue.num_entries:
                    index_from = 0
                else:
                    index_from = self._buff_queue.num_entries - (self._buff_count - self._last_buff_count_saved)
                logging.info(f'Saving file {name} index_from={index_from}')

                self._buff_queue.save(file_name=name, index_from=index_from)
                self._last_buff_count_saved = self._buff_count



    def _acquire_data(self) -> None:
        """
        Main data acquisition function used to sink the data from the serial port and hold it in a queue of buffers.
        Each buffer can hold a number of events that arrive within the specified time period. When the buffer queue is
        full the middle buffer is checked against the max number of events trigger threshold. This is then repeated for
        every subsequent buffer received. When a middle buffer exceeds the trigger threshold then the entire contents
        of the buffer queue are saved.
        """
        self._acquisition_ended = False
        while True:
            # Wait for and read event data.
            data = self._com_port.readline()
            if data == b'exit':
                logging.info("EXIT!!!")
                break
            data = codecs.decode(data, 'UTF-8')
            self._event_count += 1
            # Add date and time to event data.

            date_time_now = datetime.now(timezone.utc)
            data = date_time_now.strftime("%Y%m%d-%H%M%S.%f")[:-3] + " " + data
            logging.info(data)

            if self._start_time is None:
                # First time round so set start time.
                if self._use_arduino_time:
                    split_data = data.split()
                    arduino_time = int(split_data[2])
                    self._start_time = arduino_time
                else:
                    self._start_time = date_time_now
                logging.info(f'start_time = {self._start_time}')

            if self._use_arduino_time:
                elapsed_time_ms = arduino_time - self._start_time
            else:
                elapsed_time_ms = int((date_time_now - self._start_time).total_seconds() * 1000)
            logging.info(f'elapsed time (ms) = {elapsed_time_ms}')

            # Fill buffer with event data.
            if elapsed_time_ms < self._buff_time_ms:
                # Still within current buffer time period.
                self._buff.append(data)
            else:
                # Outside of buffer time period.
                #self._buff_count += 1
                logging.info(f'buff #{self._buff_count + 1} time {self._buff_time_ms} exceeded, added buff '
                             f'(len={self._buff.num_entries}) to queue at index {self._buff_queue.num_entries}')

                # Add current buffer to queue.
                self._buff_queue.append(copy.deepcopy(self._buff))
                # Add new data to new buffer.
                self._buff.append(data, reset=True)

                if self._use_arduino_time:
                    self._start_time = arduino_time
                else:
                    self._start_time = date_time_now

                logging.info(f'start_ms = {self._start_time}')

                # Update event frequency data.
                self._event_freq_history[self._buff_count % self._buff_queue.max_entries] = (
                        elapsed_time_ms / self._event_count)
                self._event_count = 1
                self._buff_count += 1

                # Check where we are in the buffer queue.
                if self._buff_queue.is_full():

                    # Update median frequency
                    self._median_frequency = np.median(self._event_freq_history)
                    print(self._event_freq_history)
                    print(self._median_frequency)

                    # And now process the queue
                    mid_buff = self._buff_queue.peek(index=self._buff_queue.mid_index)
                    logging.info(f'buff queue full with {self._buff_queue.max_entries} buffs, mid buff index='
                                 f'{self._buff_queue.mid_index} '
                                 f'with len={mid_buff.num_entries}')
                    self._process_middle_buffer()

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
    


    
