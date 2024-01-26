#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 29 14:01:33 2022

@author: dave
"""
import copy
import os
import unittest
from time import sleep
import tempfile
import pandas as pd
from data_collector import DataCollector
from unittest.mock import Mock


class DataCollectorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        self.data_index = 0
        self.use_arduino_time = False
        self.previous_arduino_time = 0
        self.max_events_to_be_processed = None

        # Get and prepare test data from CSV file.
        self.df = pd.read_csv("./data/event_test_set2.csv", dtype={0: str, 1: str}).iloc[:, 0:7]
        self.data = [f"{row[0]} {row[1]} {row[2]} {row[3]} {row[4]} {row[5]} {row[6]}".encode() for _, row in
                     self.df.iterrows()]
        self.data.append(b'exit')

        def _data_func():
            """Function used to handle the serving up of the serial data."""
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
                    if result_split[0] != b'exit':
                        arduino_time = int(result_split[1])
                        arduino_elapsed_time = arduino_time - self.previous_arduino_time
                        sleep(arduino_elapsed_time / 1000)
                        self.previous_arduino_time = arduino_time

                self.data_index += 1
            return result

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
            self.assertTrue("buff size is not a multiple of window size." in str(context.exception))

    def test_data_collector_csv(self):

        # Define a buffer of 12 events with a window size of 4 events. This will result in a frequency array of
        # size 3.
        window_size = 4
        with DataCollector(self.mock_com_port,
                           buff_size=12,
                           window_size=window_size,
                           save_results=True,
                           use_arduino_time=self.use_arduino_time) as data_collector:

            # Collect 1 window length of events so frequency array should contain 1 value.
            self.max_events_to_be_processed = window_size + 1
            # Middle data buffer only contained 7 events so file should be empty.
            data_collector.acquire_data()
            while not data_collector.acquisition_ended:
                sleep(0.01)
            self.assertEquals(data_collector.event_counter, self.max_events_to_be_processed)
            f = data_collector.frequency_array.copy()
            self.assertTrue(f[1] == f[2] == 0.0)
            self.assertTrue(int(f[0]) > 9.0 and f[0] < 14.0)

            # Collect another window length of events so frequency array should contain 2 values.
            self.max_events_to_be_processed = 2 * window_size + 1
            data_collector.acquire_data()
            while not data_collector.acquisition_ended:
                sleep(0.01)
            self.assertEquals(data_collector.event_counter, self.max_events_to_be_processed)
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
            self.assertEquals(data_collector.event_counter, self.max_events_to_be_processed)
            f3 = data_collector.frequency_array.copy()
            self.assertTrue(f3[0] == f2[0])
            self.assertTrue(f3[1] == f2[1])
            self.assertTrue(f3[2] != f2[2])

            # Collect another window length of events so frequency array should remain full with first (original)
            # value overwritten.
            self.max_events_to_be_processed = 4 * window_size + 1
            # Middle data buffer only contained 7 events so file should be empty.
            data_collector.acquire_data()
            while not data_collector.acquisition_ended:
                sleep(0.01)
            self.assertEquals(data_collector.event_counter, self.max_events_to_be_processed)
            f4 = data_collector.frequency_array.copy()
            self.assertTrue(f4[0] != f3[0])
            self.assertTrue(f4[2] == f3[2])
            self.assertTrue(f4[2] == f3[2])


    def test_data_collector_trigger(self):

        temp_dir = 'c:/Users/dave/Temp'
        # if os.path.isfile(data_file):
        #     os.remove(data_file)

        if True:  # with tempfile.TemporaryDir() as temp_dir:
            window_size = 5
            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               buff_size=20,
                               window_size=window_size,
                               save_results=True,
                               use_arduino_time=self.use_arduino_time) as data_collector:

                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)

