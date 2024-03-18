#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 29 14:01:33 2022

@author: dave
"""
import os
import unittest
from time import sleep
import tempfile
import json
import numpy as np
import pandas as pd
import codecs
import logging
from data_collector import DataCollector
from muon_run import _check_config
from unittest.mock import Mock


def set_logging():
    """Set logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        handlers=[
            logging.FileHandler('C:/Users/dave/Temp/muon_log.txt'),
            logging.StreamHandler()
        ]
    )


class DataCollectorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        set_logging()

    def setUp(self):
        """The test setup is responsible for setting up a mocked serial comm port that will be passed to the
           DataCollector instance constructor. The mocked comm port uses _data_func() to feed the test event
           data (held in a CSV file) to the collector one line at a time."""

        def _data_func():
            """Embedded function used to handle the serving up of the serial data."""
            if self.max_events_to_be_processed and self.data_index == self.max_events_to_be_processed:
                result = b'exit'
            else:
                result = self.data[self.data_index]
                if self.use_arduino_time:
                    sleep(0.1)
                else:
                    # Sleep off the difference between previous and current arduino times so as PC clock will
                    # approximate the time difference.
                    result_split = result.split()
                    if result_split[0] != b'exit' and len(result_split) > 1:
                        arduino_time = int(result_split[1])
                        arduino_elapsed_time = arduino_time - self.previous_arduino_time
                        sleep(arduino_elapsed_time / 1000)
                        self.previous_arduino_time = arduino_time

                self.data_index += 1
            return result

        self.data_index = 0
        self.use_arduino_time = False
        self.previous_arduino_time = 0
        self.max_events_to_be_processed = None

        # Get and prepare test data from CSV file.
        self.df = pd.read_csv("./data/event_test_set2.csv", dtype={0: str, 1: str}).iloc[:, 0:7]
        self.data = [f"{row[0]} {row[1]} {row[2]} {row[3]} {row[4]} {row[5]} {row[6]}".encode() for _, row in
                     self.df.iterrows()]
        self.data.append(b'exit')
        self._data_func = _data_func

        # Mock the data collector com_port returned by serial package. The above data will be returned
        # when reading lines.
        # create new mock object
        self.mock_com_port = Mock()
        # note, could have passed the data directly to side_effect instead of calling function
        self.mock_com_port.readline.side_effect = self._data_func
        DataCollector.com_port = self.mock_com_port
        # mock the data collector serial package and attached mocked com port
        mock_serial = Mock()
        DataCollector.serial = mock_serial
        mock_serial.Serial.return_value = self.mock_com_port

    def test_config(self):
        """Test configuration file access."""
        with open("../config.json") as json_data_file:
            config = json.load(json_data_file)

        self.assertTrue("event_files" in config)
        self.assertTrue("root_dir" in config["event_files"])
        self.assertTrue("user" in config)
        self.assertTrue("latitude" in config["user"])
        self.assertTrue("longitude" in config["user"])
        config['event_files']['root_dir'] = ""
        config['user']['latitude'] = 0.0
        config['user']['longitude'] = 0.0

        with self.assertRaises(ValueError) as context:
            _check_config(config)
        self.assertTrue("Please edit config.json to define the required root directly for logging event files."
                        in str(context.exception))

        config['event_files']['root_dir'] = "a:/b/c"
        with self.assertRaises(ValueError) as context:
            _check_config(config)
        self.assertTrue(f"The root_dir '{config['event_files']['root_dir']}' defined in config.json does not exist."
                        in str(context.exception))

        config['event_files']['root_dir'] = "c:/"
        with self.assertRaises(ValueError) as context:
            _check_config(config)
        self.assertTrue("Please edit config.json to define the user latitude and longitude decimal values."
                        in str(context.exception))

        config['user']['latitude'] = 50.815
        config['user']['longitude'] = -1.224
        _check_config(config)

    def test_data_collector_params(self):
        """Test data collector argument parameters"""
        mock_com_port = Mock()
        with self.assertRaises(NotADirectoryError) as context:
            dir_name = "* not a directory *"
            _ = DataCollector(mock_com_port,
                              save_dir=dir_name,
                              buff_size=10,
                              window_size=2)
        self.assertTrue(f"The specified save directory {dir_name} does not exist." in str(context.exception))
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                _ = DataCollector(mock_com_port,
                                  save_dir=temp_dir,
                                  buff_size=10,
                                  window_size=3)
            self.assertTrue("Require buff size is an odd multiple of window size." in str(context.exception))

    def test_data_collector_event_consumption(self):
        """This test consumes event data from the mocked serial comm port which is defined in the above setup()
        function. Using the test class member variable max_events_to_be_processed, the event data is consumed in a
        number of consecutive batches testing the collector status as we go. This test defines a buffer of 12 events
        using a window size of 4 events which results in a frequency array of size 3.
        """
        window_size = 4
        with DataCollector(self.mock_com_port,
                           buff_size=12,
                           window_size=window_size,
                           save_results=True,
                           ignore_header_size=0,
                           use_arduino_time=self.use_arduino_time) as data_collector:

            # Collect 1 window length of events so frequency array should contain 1 value.
            self.max_events_to_be_processed = window_size + 1
            # Middle data buffer only contained 7 events so file should be empty.
            data_collector.acquire_data()
            while not data_collector.acquisition_ended:
                sleep(0.01)
            self.assertEqual(data_collector.event_counter, self.max_events_to_be_processed)
            f = data_collector.frequency_array.copy()
            self.assertTrue(f[1] == f[2] == 0.0)
            self.assertTrue(int(f[0]) > 9.0 and f[0] < 14.0)

            # Collect another window length of events so frequency array should contain 2 values.
            self.max_events_to_be_processed = 2 * window_size + 1
            data_collector.acquire_data()
            while not data_collector.acquisition_ended:
                sleep(0.01)
            self.assertEqual(data_collector.event_counter, self.max_events_to_be_processed)
            f2 = data_collector.frequency_array.copy()
            self.assertTrue(f[0] == f2[0])
            self.assertTrue(int(f2[1]) > 9.0 and f2[1] < 14.0)
            self.assertTrue(f2[2] == 0.0)

            # Collect another window length of events so frequency array should now be full of 3 values.
            self.max_events_to_be_processed = 3 * window_size + 1
            # Middle data buffer only contained 7 events so file should be empty.
            data_collector.acquire_data()
            while not data_collector.acquisition_ended:
                sleep(0.01)
            self.assertEqual(data_collector.event_counter, self.max_events_to_be_processed)
            f3 = data_collector.frequency_array.copy()
            self.assertTrue(f3[0] == f2[0])
            self.assertTrue(f3[1] == f2[1])
            self.assertTrue(f3[2] != f2[2])

            # Collect another window length of events so frequency array should remain full and first (original)
            # value overwritten.
            self.max_events_to_be_processed = 4 * window_size + 1
            # Middle data buffer only contained 7 events so file should be empty.
            data_collector.acquire_data()
            while not data_collector.acquisition_ended:
                sleep(0.01)
            self.assertEqual(data_collector.event_counter, self.max_events_to_be_processed)
            f4 = data_collector.frequency_array.copy()
            self.assertTrue(f4[0] == f3[1])
            self.assertTrue(f4[1] == f3[2])
            self.assertTrue(f4[2] != f3[2])

    def test_data_collector_event_anomalies(self):
        """Test logging of event anomalies to file. test data contains a single high and low event anomaly."""
        #temp_dir = 'c:/Users/dave/Temp'
        # if os.path.isfile(data_file):
        #     os.remove(data_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            window_size = 5
            buff_size = 25
            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               buff_size=buff_size,
                               window_size=window_size,
                               save_results=True,
                               ignore_header_size=0,
                               use_arduino_time=self.use_arduino_time) as data_collector:

                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)

                self.assertEqual(len(data_collector.saved_file_names), 2)
                file_path = os.path.join(temp_dir, "anomaly", data_collector.saved_file_names[0])
                self.assertTrue(os.path.isfile(file_path))
                df = pd.read_csv(file_path)
                self.assertEqual(df.shape, (buff_size, 9))
                df = df.sort_values(by=['event'], ignore_index=True)
                # check high anomaly is in center of saved event buffer
                self.assertEqual(df['event'][df.shape[0] // 2], 69)

                file_path = os.path.join(temp_dir, "anomaly", data_collector.saved_file_names[1])
                self.assertTrue(os.path.isfile(file_path))
                df = pd.read_csv(file_path)
                self.assertEqual(df.shape, (buff_size, 9))
                df = df.sort_values(by=['event'], ignore_index=True)
                # check low anomaly is in center of saved event buffer
                self.assertEqual(df['event'][df.shape[0] // 2], 104)

    def test_data_collector_log_all_events(self):
        """Test logging of all events to file."""
        temp_dir = 'c:/Users/dave/Temp'
        # if os.path.isfile(data_file):
        #     os.remove(data_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            window_size = 10
            buff_size = 30
            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               buff_size=buff_size,
                               window_size=window_size,
                               log_all_events=True,
                               save_results=True,
                               ignore_header_size=0,
                               use_arduino_time=self.use_arduino_time) as data_collector:

                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)

                # We should have 4 log all buffers + 1 low anomaly buffer. High anomaly is spread out over larger
                # window size and is thus not seen.
                self.assertEqual(len(data_collector.saved_file_names), 5)
                file_path = os.path.join(temp_dir, "all", data_collector.saved_file_names[0])
                df = pd.read_csv(file_path)
                self.assertTrue(os.path.isfile(file_path))
                # confirm we have 3 window frequencies at required positions
                states = df['win_f'].notna()
                self.assertTrue(np.array_equal(np.where(states)[0], np.array([9, 19, 29])))
                win_f_array = df[df['win_f'].notna()]['win_f'].values
                self.assertEqual(win_f_array.size, 3)
                # confirm we have 1 median frequency at required position and check correct against window frequencies
                states = df['median_f'].notna()
                self.assertTrue(np.array_equal(np.where(states)[0], np.array([29])))
                median_f_array = df[df['median_f'].notna()]['median_f'].values
                self.assertEqual(median_f_array.size, 1)
                self.assertEqual(np.median(win_f_array), median_f_array[0])

    def test_data_collector_start_string(self):
        """Test start acquisition trigger string."""
        start_string = b"Kaz"
        event_index = 6
        self.data[event_index] = start_string
        with tempfile.TemporaryDirectory() as temp_dir:
            window_size = 10
            buff_size = 30
            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               buff_size=buff_size,
                               window_size=window_size,
                               log_all_events=True,
                               save_results=True,
                               ignore_header_size=0,
                               start_string=codecs.decode(start_string, 'UTF-8'),
                               use_arduino_time=self.use_arduino_time) as data_collector:

                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)

                file_path = os.path.join(temp_dir, "all", data_collector.saved_file_names[0])
                self.assertTrue(os.path.isfile(file_path))
                df = pd.read_csv(file_path, dtype={0: str, 1: str}).iloc[:, 0:7]
                self.assertEqual(df['event'][0], str(event_index+2))

    def test_data_collector_start_string_fail(self):
        """Test start acquisition trigger string fails."""
        start_string = "Kaz"
        with tempfile.TemporaryDirectory() as temp_dir:
            window_size = 10
            buff_size = 30
            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               buff_size=buff_size,
                               window_size=window_size,
                               log_all_events=True,
                               save_results=True,
                               ignore_header_size=0,
                               start_string=start_string,
                               use_arduino_time=self.use_arduino_time) as data_collector:
                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)
                self.assertTrue(data_collector.saved_file_names == [])



