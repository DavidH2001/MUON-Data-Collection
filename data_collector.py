#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUON data collection project.
DataCollector class definition.
Original development by Dave Hardwick
"""
from enum import Enum
import os.path
import sys
import math
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

DATE_TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"
VERSION: str = "0.3.4"


class Status(Enum):
    NORMAL = 1
    MEDIAN_FREQUENCY_EXCEEDED = 2


class DataCollector:
    """Data collector object class.
    This class is used to consume event data from a serial comm port and process it by looking for acquisition frequency
    (high/low) anomalies. When an anomaly is detected the event data buffer is saved to a file. Anomaly detection starts
    after the buffer has been initially filled with events using its central window. This enables events preceding and
    following an anomaly to be logged. Detection of an anomaly is achieved by comparing a shifting window frequency
    against the current baseline frequency.
    Note, the Saved buffer CSV files are not ordered chronologically. When loading a CSV file (into a pandas data frame
    for example) you will need to reorder the rows e.g., using event number."""
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
               log_all_events: Set to True to log all events to file(s). Defaults to True.
               ignore_header_size: Number of initial data lines to be ignored that represent the header. Defaults to 6.
               start_string: String sent from detector that will initiate event capture. Defaults to "" i.e. not used.
               use_arduino_time: Use Arduino timing if True else use PC clock. Defaults to False.
               user_id: Unique user identity string.
               user_name:
               user_password:
               ip_address:
               queue_save_path:
        """
        logging.basicConfig()
        self._com_port = com_port
        self._saved_file_names: list = []
        self._ignore_header_size: int = kwargs.get("ignore_header_size", 0)
        self._save_dir: str = kwargs.get('save_dir', None)
        if self._save_dir and not os.path.exists(self._save_dir):
            raise NotADirectoryError(f"The specified save directory {self._save_dir} does not exist.")
        self._buff_size: int = kwargs.get('buff_size', 90)
        self._window_size: int = kwargs.get('window_size', 10)
        self._window_index = 0
        self._window_buff_indices = [0] * self._window_size
        self._ignore_event_count = 0
        # if self._buff_size % self._window_size != 0:
        #     raise ValueError("Require buff size is an odd multiple of window size.")
        self._frequency_array: np.array = np.zeros(self._buff_size)
        self._mid_frequency_index = self.frequency_array.size // 2
        self._frequency_median: float = 0.0
        self._max_median_frequency: float = kwargs.get("max_median_frequency", 1.0)

        self._frequency_index: int = 0
        self._frequency_array_full: bool = False
        # total number of events received since start
        self._event_counter: int = 0
        # buffer index points to latest event entry - cycles between 0 and _buff_size -1
        self._buff_index: int = 0
        self._look_for_start = True

        self._anomaly_threshold = kwargs.get("anomaly_threshold", 2.0)
        self._log_all_events: bool = kwargs.get('log_all_events', True)
        self._start_string: bool = kwargs.get('start_string', '')
        if self._start_string != '':
            self._look_for_start_string = True
        else:
            self._look_for_start_string = False
        self._user_id: str = kwargs.get('user_id', "")
        self._user_name = kwargs.get('user_name', "")
        self._user_password = kwargs.get('user_password', "")
        self._ip_address = kwargs.get('ip_address', "")
        self._date_time_format: str = "%Y%m%d %H%M%S.%f"

        self._shut_down: bool = False
        self._acquisition_ended = True
        self._remote_access_ended = True
        self._queue_save_path = kwargs.get("queue_save_path", "queue.txt")
        self._file_queue = queue.Queue(maxsize=100)  # thread safe
        self._suppress_timeout_message = False
        self._status: Enum = Status.NORMAL
        self._buff = pd.DataFrame({'comp_time': pd.Series(dtype='str'),
                                   'event': pd.Series(dtype='int'),
                                   'arduino_time': pd.Series(dtype='int'),
                                   'adc': pd.Series(dtype='int'),
                                   'sipm': pd.Series(dtype='float'),
                                   'dead_time': pd.Series(dtype='int'),
                                   'temp': pd.Series(dtype='float'),
                                   'win_f': pd.Series(dtype='float'),
                                   'median_f': pd.Series(dtype='float')})
        self._buff_date_time_start = ""
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
        if os.path.exists(self._queue_save_path):
            os.remove(self._queue_save_path)
        logging.info(f"Saving file queue to {self._queue_save_path}...")
        file_list = []
        while not self._file_queue.empty():
            file_list.append(self._file_queue.get() + '\n')
        if file_list:
            logging.info(f"{len(file_list)} file names have been preserved")
            with open(self._queue_save_path, "w") as f:
                f.writelines(file_list)

    def _load_queue(self):
        """Load the file queue from file."""
        if os.path.exists(self._queue_save_path):
            logging.info(f"Loading unprocessed files from {self._queue_save_path}...")
            with open(self._queue_save_path, "r") as f:
                i = 0
                for file_path in f:
                    file_path = file_path.rstrip("\n")
                    if not os.path.exists(file_path):
                        logging.info(f"Throwing away {file_path} as it no longer exists")
                        continue
                    self._file_queue.put(file_path)
            logging.info(f"{i} files loaded")
            os.remove(self._queue_save_path)

    def _copy_file_to_server(self, file_path: str) -> bool:
        """Copy file to remote server."""
        try:
            with FTP(self._ip_address, self._user_name, self._user_password) as ftp:
                if self._user_id not in ftp.nlst():
                    logging.info(f"Creating remote user directory {self._user_id}")
                    ftp.mkd(self._user_id)
                ftp.cwd(self._user_id)
                with open(file_path, 'rb') as file:
                    target_path = os.path.basename(file_path)
                    if not os.path.exists(file_path):
                        logging.info(f"{file_path} no longer exists and has been removed from queue")
                        return True
                    logging.info(f"Saving {target_path} to remote server")
                    ftp.storbinary(f'STOR {target_path}', file)
                    self._suppress_timeout_message = False
            return True
        except TimeoutError:
            if not self._suppress_timeout_message:
                logging.error("Timeout - unable to connect with remote FTP server")
            self._suppress_timeout_message = True
            return False

    def _process_file_queue(self):
        """Process the file queue running on separate thread."""
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
                logging.info("Remote access thread shutting down...")
                if not self._file_queue.empty():
                    self._save_queue()
                self._remote_access_ended = True
                break

    def _write_csv(self, file_path):
        """Write event data as CSV file."""
        if os.path.isfile(file_path):
            logging.info(f"File {file_path} already exists so aborting save!")
            return False
        self._saved_file_names.append(file_path)
        with open(file_path, 'a') as f:
            # write metadata first
            f.write(f"{VERSION},{self._user_id},{self._buff_size},{self._window_size},"
                    f"{self._anomaly_threshold},{self._buff_start_event},{self._buff_date_time_start}\n")
            self._buff.to_csv(f, index=False, date_format=DATE_TIME_FORMAT, lineterminator='\n')
        return True

    def _save_buff(self, sub_dir=""):
        """Save current content of buffer."""
        # file name is UTC of first event
        middle_event_number = self._buff.loc[self._buff.index[int(self._buff_size / 2)], 'event']
        file_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{str(middle_event_number)}.csv"
        file_dir = os.path.join(self._save_dir, sub_dir)
        if not os.path.isdir(file_dir):
            logging.info(f"Creating directory {file_dir}")
            os.makedirs(file_dir)
        file_path = os.path.join(file_dir, file_name)
        logging.info(f"Saving buffer to file {file_path}")
        if self._write_csv(file_path) and sub_dir == "anomaly":
            # queue buffer file name to be saved remotely on separate thread
            self._file_queue.put(file_path)

    def _check_for_anomaly(self, mid_frequency) -> bool:
        """Check for event anomaly."""
        logging.debug(f"Checking mid buff[{self._mid_frequency_index}] window freq: "
                      f"{mid_frequency:.3f} against median frequency {self._frequency_median:.3f} "
                      f"ignore_event_count: {self._ignore_event_count }")
        if mid_frequency > self._frequency_median * self._anomaly_threshold:
            logging.info(f"HIGH ANOMALY DETECTED at frequency {mid_frequency:.3f}")
            return True
        if mid_frequency < self._frequency_median / self._anomaly_threshold:
            logging.info(f"LOW ANOMALY DETECTED at frequency {mid_frequency:.3f}")
            return True
        return False

    def _update_frequency_history(self, cur_buff_index: int) -> bool:
        """With a new window set of data available update the window event frequency history and look for anomalies."""
        window_data = self._buff.iloc[self._window_buff_indices]
        window_data = window_data.sort_values(by='arduino_time', ignore_index=True)
        windows_time_start = (window_data.loc[window_data.index[0], 'arduino_time'] -
                              window_data.loc[window_data.index[0], 'dead_time'])
        windows_time_end = (window_data.loc[window_data.index[-1], 'arduino_time'] -
                            window_data.loc[window_data.index[-1], 'dead_time'])
        windows_time_diff = (windows_time_end - windows_time_start) / 1000.0
        window_freq = len(window_data) / windows_time_diff

        if self._frequency_array_full:
            # update buffer by removing the oldest window frequency and adding latest frequency
            self._frequency_array = np.roll(self._frequency_array, -1)
            self._frequency_array[-1] = window_freq
        else:
            # first time filling of frequency array
            self._frequency_array[self._frequency_index] = window_freq
        # logging.debug(f"window time (s) = {windows_time_diff.total_seconds()} arduino time (s) = {arduino_time_diff} "
        #              f"window frequency[{self._frequency_index}] = {window_freq}")
        self._buff.loc[cur_buff_index, 'win_f'] = window_freq
        self._frequency_index += 1
        if self._frequency_index == len(self._frequency_array):
            # end of frequency array reached
            self._frequency_index = 0
            self._frequency_array_full = True

        return True

    def _update_median_frequency(self):
        """Add median frequency entry to buff."""
        self._frequency_median = np.median(self._frequency_array)
        if self._frequency_median > self._max_median_frequency:
            logging.info(f"Median frequency {self._frequency_median:.3f} exceeded maximum "
                         f"{self._max_median_frequency:.3f}")
            logging.info("Check that you running in coincidence mode and connected to the S-detector")
            self._status = Status.MEDIAN_FREQUENCY_EXCEEDED
            return False
        logging.info(f"buffer median frequency: {self._frequency_median:.3f}")
        self._buff.loc[self._buff_size - 1, 'median_f'] = self._frequency_median

    def _reset(self):
        """Reset parameters required for re-start."""
        self._frequency_index: int = 0
        self._frequency_array_full: bool = False
        self._event_counter: int = 0
        self._buff_index: int = 0
        self._look_for_start = True
        self._buff = self._buff[0:0]

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
            # print(data)
            if data == b'':
                continue
            if self._shut_down:
                break
            try:
                data = codecs.decode(data, 'UTF-8', errors='replace')
            except UnicodeDecodeError as e:
                print("--------------Decode Error-------------")
                print(e)
                print(data)
                print("---------------------------------------")
                sys.exit(0)

            if data == 'exit':
                logging.info("EXIT!!!")
                break

            if self._look_for_start:
                if self._look_for_start_string:
                    if data.find(self._start_string) != -1:
                        self._look_for_start = False
                        logging.info(f"Start string '{self._start_string}' detected - beginning acquisition...")
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
                else:
                    # auto search for start i.e., ignore header comments and look for event string
                    if "###" in data:
                        continue
                    if len(data.split()) < 6:
                        continue
                    logging.info("Event line detected - beginning acquisition")
                    logging.info("Note, only first 10 events will be displayed if logging at INFO level...")
                    self._look_for_start = False

            if "###" in data:
                # assume detector is re-booting
                logging.info("Looks like detector has re-started - resetting for new acquisition...")
                self._reset()
                continue

            data_list = data.split()
            if len(data_list) < 6:
                logging.info(f"Bad event line detected '{data}'")
                continue
            data_list = data_list[0:6]
            data_list[0] = int(data_list[0])    # event
            data_list[1] = int(data_list[1])    # arduino time
            data_list[2] = int(data_list[2])    # ADC
            data_list[3] = float(data_list[3])  # SIPM
            data_list[4] = int(data_list[4])    # dead time
            data_list[5] = float(data_list[5])  # temp
            data_list.extend([pd.NA, pd.NA])

            date_time_now = datetime.now(timezone.utc)
            if self._buff_index == 0:
                self._buff_date_time_start = date_time_now
                self._buff_start_event = data_list[0]

            data_list = [date_time_now.strftime(self._date_time_format)[:-3]] + data_list
            if self._event_counter < 10:
                # always log first few events
                logging.info(data_list)
            else:
                logging.debug(data_list)

            try:
                if len(self._buff) < self._buff_size:
                    # fill buffer for first time
                    self._buff.loc[len(self._buff)] = data_list
                else:
                    # repeat filling of buffer. Note start from the beginning overwriting the oldest values
                    self._buff.loc[self._buff_index] = data_list
                # preserve the buff indices that reflect the latest window
                self._window_buff_indices[self._window_index] = self._buff_index
                self._window_index = self._window_index + 1 if self._window_index < (self._window_size - 1) else 0
                if self._window_index == 0:
                    self._new_anomaly_window = True
                if self._ignore_event_count:
                    self._ignore_event_count -= 1
                self._event_counter += 1
            except ValueError as e:
                print("------------Data Buff Error------------")
                print(e)
                print(data_list)
                print("---------------------------------------")
                sys.exit(0)

            if self._event_counter >= self._window_size:
                if not self._update_frequency_history(self._buff_index):
                    break

            # anomaly check
            if not math.isclose(self._anomaly_threshold, 0.0) and self._frequency_array_full:
                if self._check_for_anomaly(self.frequency_array[self._mid_frequency_index]):
                    if self._save_dir and self._ignore_event_count == 0:
                        self._ignore_event_count = 1 * self._window_size
                        self._save_buff("anomaly")

            # end of buffer check
            self._buff_index = self._event_counter % self._buff_size
            if self._buff_index == 0:
                self._update_median_frequency()
                if self._save_dir and self._log_all_events:
                    self._save_buff("all")

        logging.info("Acquisition thread shutting down...")
        self._acquisition_ended = True

    def acquire_data(self) -> None:
        t2 = threading.Thread(target=self._acquire_data)
        self._acquisition_ended = False
        t2.start()

    def run_remote(self) -> None:
        t1 = threading.Thread(target=self._process_file_queue)
        self._remote_access_ended = False
        t1.start()

    def _signal_handler(self, signal, frame):
        """Ctrl-C (and Z?) signal handler. Note this can result in an error being generated if we are currently
           blocking on com_port.readline().
        """
        logging.info('Ctrl-C detected - shutting down...')
        self._shut_down = True
