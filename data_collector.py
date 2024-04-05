#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
import os.path
import sys
import signal
import threading
import queue
import logging
import time
import codecs
import numpy as np
import pandas as pd
from ftplib import FTP
from datetime import datetime, timezone

date_time_format: str = "%Y-%m-%d %H:%M:%S.%f"


class DataCollector:
    """Data collector object class.

    This class is used to consume event data from a serial comm port and process it by looking for acquisition frequency
    (high/low) anomalies. When an anomaly is detected the event data buffer is saved to a file.

    The maximum events that can be held by the collector is defined by buffer size. The buffer is split into a
    number of sub buffers (windows) that are used to define the current event frequency i.e. time span of window
    divided by the number of events it holds. A frequency array is used to log the corresponding window frequencies for
    the whole buffer.

    When the buffer is full the logged frequencies are used to determine a baseline (median) frequency for the whole
    buffer. The buffer is the refilled starting from the beginning (oldest) entry again. The window frequency array is
    also updated as each new window of events is received. The median frequency is updated when the buffer is
    re-filled which allows for any drift in the detector system.

    Anomaly detection starts after the buffer has been initially filled with events using its central window. This
    enables events preceding and following an anomaly to be logged. Detection of an anomaly is achieved by comparing
    the window frequency against the current baseline frequency.

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
               save_dir: Optional string used to define a directory to save triggered events. If not defined then
                    events will not be saved.
               buff_size: The number of events to be held in the buffer. This should be set as an odd multiple of
                    window_size.
               window_size: The number of events used by the anomaly window.
               anomaly_threshold: Optional factor of base frequency used to trigger anomaly. Ignored if set to 0.0.
                    Defaults to 2.0.
               log_all_events: Set to True to log all events to file(s). Defaults to False.
               ignore_header_size: Number of initial data lines to be ignored that represent the header. Defaults to 6.
               start_string: String sent from detector that will initiate event capture. Defaults to "" i.e. not used.
               use_arduino_time: Use Arduino timing if True else use PC clock. Defaults to False.
               user_id: Unique user identity string.
               user_name:
               user_password:
               ip_address:
        """
        logging.basicConfig()
        self._com_port = com_port
        self._save_dir: str = kwargs.get('save_dir', None)
        self._saved_file_names: list = []
        self._ignore_header_size: int = kwargs.get("ignore_header_size", 8)
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
        self._anomaly_threshold = kwargs.get("anomaly_threshold", 2.0)
        self._log_all_events: bool = kwargs.get('log_all_events', '')
        self._start_string: bool = kwargs.get('start_string', '')
        self._user_id: str = kwargs['user_id']
        self._user_name = kwargs['user_name']
        self._user_password = kwargs['user_password']
        self._ip_address = kwargs['ip_address']
        if self._start_string != '':
            self._look_for_start = True
        else:
            self._look_for_start = False
        self._date_time_format: str = "%Y%m%d %H%M%S.%f"
        self._event_counter: int = 0
        self._buff_index: int = 0
        self._shut_down: bool = False
        self._acquisition_ended = False
        self._remote_access_ended = False
        self._queue_save_file_name = "queue.txt"
        self._file_queue = queue.Queue(maxsize=100)  # thread safe

        self._buff = pd.DataFrame({'comp_time': pd.Series(dtype='str'),
                                   'event': pd.Series(dtype='int'),
                                   'arduino_time': pd.Series(dtype='int'),
                                   'adc': pd.Series(dtype='int'),
                                   'sipm': pd.Series(dtype='int'),
                                   'dead_time': pd.Series(dtype='int'),
                                   'temp': pd.Series(dtype='float'),
                                   'win_f': pd.Series(dtype='float'),
                                   'median_f': pd.Series(dtype='float')})
        signal.signal(signal.SIGINT, self._signal_handler)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @property
    def processing_ended(self):
        if self._acquisition_ended and self._remote_access_ended:
            return True
        return False

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

    def _save_queue(self):
        """Save the file queue to file."""
        if os.path.exists(self._queue_save_file_name):
            os.remove(self._queue_save_file_name)
        logging.info(f"Saving file queue to {self._queue_save_file_name}")
        file_list = []
        while not self._file_queue.empty():
            file_list.append(self._file_queue.get() + '\n')
        if file_list:
            logging.info(f"Preserving {len(file_list)} file names")
            with open(self._queue_save_file_name, "w") as f:
                f.writelines(file_list)

    def _load_queue(self):
        """Load the file queue from file."""
        if os.path.exists(self._queue_save_file_name):
            logging.info(f"Loading unprocessed queue files from {self._queue_save_file_name}")
            with open(self._queue_save_file_name, "r") as f:
                self._file_queue.put(f.readline())
            os.remove(self._queue_save_file_name)

    def _copy_file_to_server(self, file_path: str) -> bool:
        """Copy file to remote server."""
        try:
            with FTP(self._ip_address, self._user_name, self._user_password) as ftp:
                ftp.cwd(self._user_id)
                with open(file_path, 'rb') as file:
                    # TODO ALL file_path is string containing all file names!!!
                    target_path = os.path.basename(file_path)
                    if not os.path.exists(file_path):
                        logging.info(f"{file_path} no longer exists and has been removed from queue")
                        return True
                    logging.info(f"Saving {target_path} to remote server")
                    ftp.storbinary(f'STOR {target_path}', file)
            return True
        except TimeoutError:
            logging.error("Timeout - unable to connect with remote FTP server")
            return False

    def _process_file_queue(self):
        """process the file queue."""
        logging.info("Remote access thread started")
        self._load_queue()
        while True:
            time.sleep(3)
            try:
                file_path = self._file_queue.get(block=False)
                if not self._copy_file_to_server(file_path):
                    # unable to copy file to server so place the path back into the queue
                    self._file_queue.put(file_path)
            except queue.Empty:
                pass
            if self._shut_down:
                logging.info("Remote access thread shutting down")
                if not self._file_queue.empty():
                    self._save_queue()
                self._remote_access_ended = True
                break

    def _save_buff(self, sub_dir=""):
        """Save current content of buffer."""
        self._saved_file_names.append(pd.to_datetime(self._buff['comp_time'][0]).strftime("%Y%m%d-%H%M%S.csv"))
        # save buffer locally
        file_dir = os.path.join(self._save_dir, sub_dir)
        if not os.path.isdir(file_dir):
            logging.info(f"Creating directory {file_dir}")
            os.mkdir(file_dir)
        file_path = os.path.join(file_dir, self._saved_file_names[-1])
        logging.info(f"Saving buffer to file {file_path}")
        self._buff.to_csv(file_path, index=False, date_format=date_time_format)
        if sub_dir == "anomaly":
            # save buffer file remotely
            # self._copy_file_to_server(file_path)
            self._file_queue.put(file_path)

    def _check_for_anomaly(self, frequency) -> None:
        """Check for event anomaly."""
        logging.debug(f"Checking mid buff[{self._mid_frequency_index}] window freq: "
                      f"{frequency} against median frequency {self._frequency_median}")
        if frequency > self._frequency_median * self._anomaly_threshold:
            logging.info("HIGH ANOMALY DETECTED!!!")
            return True
        if frequency < self._frequency_median / self._anomaly_threshold:
            logging.info("LOW ANOMALY DETECTED!!!")
            return True
        return False

    def _update_frequency_history(self, cur_buff_index: int) -> None:
        """With a new window set of data available update the window event frequency history and look for anomalies."""
        window_data = self._buff.copy().iloc[cur_buff_index - (self._window_size - 1): cur_buff_index + 1]

        window_data.loc[window_data.index[:], 'comp_time'] = (
            pd.to_datetime(window_data.loc[window_data.index[:], 'comp_time'], format=self._date_time_format))

        windows_time_diff = (window_data.loc[window_data.index[-1], 'comp_time'] -
                             window_data.loc[window_data.index[0], 'comp_time'])
        arduino_time_diff = (int(window_data.loc[window_data.index[-1], 'arduino_time']) -
                             int(window_data.loc[window_data.index[0], 'arduino_time'])) / 1000.0
        window_freq = len(window_data) / windows_time_diff.total_seconds()
        if self._frequency_array_full:
            # update buffer by removing the oldest window frequency and adding latest frequency
            self._frequency_array = np.roll(self._frequency_array, -1)
            self._frequency_array[-1] = window_freq
        else:
            # first time filling of frequency array
            self._frequency_array[self._frequency_index] = window_freq

        logging.info(f"window time (s) = {windows_time_diff.total_seconds()} arduino time (s) = {arduino_time_diff} "
                     f"window frequency[{self._frequency_index}] = {window_freq}")
        self._buff.loc[cur_buff_index, 'win_f'] = window_freq

        self._frequency_index += 1
        if self._frequency_index == len(self._frequency_array):
            # end of frequency array reached
            self._frequency_index = 0
            self._frequency_array_full = True
            # frequency array (and hence event buffer) is now full so start to capture current frequency median
            self._frequency_median = np.median(self._frequency_array)
            logging.info(f"buffer median frequency: {self._frequency_median}")
            self._buff.loc[cur_buff_index, 'median_f'] = self._frequency_median
            if self._log_all_events:
                # save buffer anyway if we are not looking for anomalies
                self._save_buff("all")

        if self._anomaly_threshold != 0.0 and self._frequency_array_full:
            if self._check_for_anomaly(self.frequency_array[self._mid_frequency_index]):
                if self._save_dir:
                    self._save_buff("anomaly")

    def _acquire_data(self) -> None:
        """
        Main data acquisition function used to sink the data from the serial port and hold it in a queue of buffers.
        Each buffer can hold a number of events that arrive within the specified time period. When the buffer queue is
        full the middle buffer is checked against the max number of events trigger threshold. This is then repeated for
        every subsequent buffer received. When a middle buffer exceeds the trigger threshold then the entire contents
        of the buffer queue are saved.
        """
        logging.info("Acquisition thread started")
        self._acquisition_ended = False
        header_line_count = 0
        while True:
            # Wait for and read event data.
            data = self._com_port.readline()
            if data == b'':
                continue
            if self._shut_down:
                break
            try:
                data = codecs.decode(data, 'UTF-8')
            except UnicodeDecodeError as e:
                print("--------------decode error-------------")
                print(e)
                print(data)
                print("---------------------------------------")
                sys.exit(0)
            #print(data)

            if data == 'exit':
                logging.info("EXIT!!!")
                break

            if self._look_for_start:
                if data.find(self._start_string) != -1:
                    self._look_for_start = False
                    logging.info(f"Start string '{self._start_string}' detected - beginning acquisition")
                continue
            elif self._ignore_header_size:
                # strip of the initial header data lines
                if header_line_count < self._ignore_header_size:
                    header_line_count += 1
                    continue
                else:
                    logging.info(f"Specified header size ({self._ignore_header_size}) consumed - "
                                 f"beginning acquisition")
                    self._ignore_header_size = 0

            data = data.split()[0:6]
            data.extend(['', ''])

            # if len(data) < 6:
            #     # ignore anything that does not consist of at least 6 fields
            #     continue
            # logging.debug(data)

            date_time_now = datetime.now(timezone.utc)
            data = [date_time_now.strftime(self._date_time_format)[:-3]] + data
            # logging.debug(self._buff_index)
            logging.debug(data)

            try:
                if len(self._buff) < self._buff_size:
                    # fill buffer for first time
                    self._buff.loc[len(self._buff)] = data
                else:
                    # Repeat filling of buffer. Note start from the beginning overwriting the oldest values.
                    self._buff.loc[self._buff_index] = data
            except ValueError as e:
                print("------------data buff error------------")
                print(e)
                print(data)
                print("---------------------------------------")
                sys.exit(0)

            if self._event_counter and not self._event_counter % self._window_size:
                # next window buffer full
                self._update_frequency_history(self._buff_index)

            self._buff_index = self._event_counter % self._buff_size
            self._event_counter += 1
        logging.info("Acquisition thread shutting down")
        self._acquisition_ended = True

    def acquire_data(self) -> None:
        t2 = threading.Thread(target=self._acquire_data)
        t2.start()

    def run_remote(self) -> None:
        t1 = threading.Thread(target=self._process_file_queue)
        t1.start()

    def _signal_handler(self, signal, frame):
        """
        Ctrl-c signal handler. Note this can result in an error being generated if
        we are currently blocking on com_port.readline()
        """
        logging.info('Ctrl-C detected - shutting down...')
        # if self._com_port is not None:
        #     self._com_port.close()
        #     logging.info("Com port closed")
        self._shut_down = True
