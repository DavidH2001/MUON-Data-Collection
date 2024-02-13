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
import numpy as np
import pandas as pd
from datetime import datetime, timezone


class DataCollector:
    """Data collector object class.

    This class is used to consume event data from a serial comm port and process it by looking for acquisition frequency
    (high/low) anomalies. When an anomaly is detected the event data buffer is saved to a file.

    The maximum events that can be held by the collector is defined by buffer size. The buffer is split into a
    number of sub buffers (windows) that are used to define the event frequency at their time of acquisition. When the
    buffer is full the corresponding logged window frequencies are used to determine a baseline (median) frequency.
    Each frequency is stored in array that has the same size as the number of windows spanning the buffer.
    This baseline frequency is continuously updated to allow for any drift in the detector system.The window frequency
    is also used to detect anomalies by comparing it against the current baseline.

    Anomaly detection starts after the buffer has been initially filled with events using its central window. This
    enables events preceding and following an anomaly to be logged.

    The Saved buffer CSV files are not ordered chronologically. When loading a CSV file (into a pandas data frame for
    example) you will need to reorder the rows e.g., using event number."""
    def __init__(self,
                 com_port: str,
                 **kwargs):
        """
        Constructor.
        :param com_port:
        :param save_dir:
        :param kwargs:
               save_dir: Optional string used to define a directory to save triggered events.
               buff_size: The number of events to be held in the buffer. This should be set as an odd multiple of
                    window_size.
               window_size: The number of events used by the anomaly window.
               anomaly_detect_fraction: Optional fraction of base frequency used to trigger anomaly. Defaults to 0.2.
               save_results: ??? do we need this ???
               log_all_events: Set to True to log all events to file(s). Defaults to False.
               use_arduino_time: Use Arduino timing if True else use PC clock. Defaults to False.
        """
        logging.basicConfig(encoding='utf-8', level=logging.INFO)

        self._com_port = com_port
        self._save_dir: str = kwargs.get('save_dir', None)
        self._saved_file_names: list = []
        if self._save_dir and not os.path.exists(self._save_dir):
            raise NotADirectoryError(f"The specified save directory {self._save_dir} does not exist.")
        self._buff_size: int = kwargs.get('buff_size', 90)
        self._window_size: int = kwargs.get('window_size', 10)
        if self._buff_size % self._window_size != 0:
            raise ValueError("Require buff size is an odd multiple of window size.")
        self._frequency_array: np.array = np.zeros(self._buff_size // self._window_size)
        self._mid_frequency_index = self.frequency_array.size // 2
        self._frequency_median: float = 0.0
        self._frequency_index: int = 0
        self._frequency_array_full: bool = False
        self._anomaly_detect_fraction = kwargs.get("anomaly_detect_fraction", 0.2)
        self._log_all_events: bool = kwargs.get('log_all_events', '')
        self._date_time_format: str = "%Y%m%d %H%M%S.%f"
        self._event_counter: int = 0
        self._buff_index: int = 0
        self._trigger_string: bool = kwargs.get('trigger_string', '')
        self._acquisition_ended = False
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

    @property
    def frequency_array(self):
        return self._frequency_array

    @property
    def event_counter(self):
        return self._event_counter

    @property
    def saved_file_names(self):
        return self._saved_file_names

    def _wait_for_start(self, name: str):

        while True:
            line = self._com_port.readline()  # Wait and read data
            print(line, end='')
            self._com_port.write(b'got-it')
            if name in str(line):
                break

    def _save_buff(self):
        """Save current content of buffer."""
        self._saved_file_names.append(self._buff['comp_time'][0].strftime("%Y%m%d-%H%M%S.csv"))
        file_path = os.path.join(self._save_dir, self._saved_file_names[-1])
        logging.info(f"Saving buffer to file {file_path}")
        self._buff.to_csv(file_path, index=False)

    def _check_for_anomaly(self, frequency) -> None:
        """Check for event anomaly."""
        if frequency > (1 + self._anomaly_detect_fraction) * self._frequency_median:
            logging.info("HIGH ANOMALY DETECTED!!!")
            return True
        if frequency < (1 - self._anomaly_detect_fraction) * self._frequency_median:
            logging.info("LOW ANOMALY DETECTED!!!")
            return True
        return False

    def _update_frequency_history(self, cur_buff_index: int) -> None:
        """With a new window set of data available update the window event frequency history and look for anomalies."""
        window_data = self._buff.iloc[cur_buff_index - (self._window_size - 1): cur_buff_index + 1]
        window_data.iloc[:, 0] = pd.to_datetime(window_data.iloc[:, 0], format=self._date_time_format)
        diff = window_data.iloc[-1, 0] - window_data.iloc[0, 0]
        window_freq = len(window_data) / diff.total_seconds()
        if self._frequency_array_full:
            # update buffer by removing the oldest window frequency and adding latest frequency
            self._frequency_array = np.roll(self._frequency_array, -1)
            self._frequency_array[-1] = window_freq
        else:
            # first time filling of frequency array
            self._frequency_array[self._frequency_index] = window_freq

        logging.debug(f"time diff (s) = {diff.total_seconds()} _frequency_array[{self._frequency_index}] = "
                      f"{window_freq}")

        self._frequency_index += 1
        if self._frequency_index == len(self._frequency_array):
            # end of frequency array reached
            if self._log_all_events:
                # save buffer anyway if we are not looking for anomalies
                self._save_buff()
            self._frequency_index = 0
            self._frequency_array_full = True
            # frequency array (and hence event buffer) is now full so start to capture current frequency median
            self._frequency_median = np.median(self._frequency_array)
            logging.info(f"Frequency Median = {self._frequency_median}")

        if not self._log_all_events and self._frequency_array_full:
            logging.debug(f"CHECKING mid freq: {self.frequency_array[self._mid_frequency_index]}")
            if self._check_for_anomaly(self.frequency_array[self._mid_frequency_index]):
                self._save_buff()

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
            date_time_now = datetime.now(timezone.utc)
            data = data.split()
            data = [date_time_now.strftime(self._date_time_format)[:-3]] + data

            if len(self._buff) < self._buff_size:
                # fill buffer for first time
                self._buff.loc[len(self._buff)] = data
            else:
                # Repeat filling of buffer. Note start from the beginning overwriting the oldest values.
                self._buff.loc[self._buff_index] = data

            if self._event_counter and not self._event_counter % self._window_size:
                # next window buffer full
                self._update_frequency_history(self._buff_index)

            self._buff_index = self._event_counter % self._buff_size
            self._event_counter += 1
            logging.debug(data)

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




