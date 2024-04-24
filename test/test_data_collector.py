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
from data_collector import DataCollector, Status
from muon_run import _check_config
from unittest.mock import Mock


def set_logging():
    """Set logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        handlers=[
            logging.FileHandler('muon_log.txt'),
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
        with open("../config.template.json") as json_data_file:
            config = json.load(json_data_file)

        self.assertIn("event_files", config)
        self.assertIn("root_dir", config["event_files"])
        self.assertIn("user", config)
        self.assertIn("system", config)
        self.assertIn("remote", config)

        self.assertIn("name", config["user"])
        self.assertIn("password", config["user"])
        self.assertIn("latitude", config["user"])
        self.assertIn("longitude", config["user"])
        self.assertIn("ip_address", config["remote"])

        config['event_files']['root_dir'] = ""
        with self.assertRaises(ValueError) as context:
            _check_config(config)
        self.assertIn(f"Please edit config.json to define the required root directory for logging event files.",
                      str(context.exception))

        config['event_files']['root_dir'] = "a:/b/c"
        with self.assertRaises(ValueError) as context:
            _check_config(config)
        self.assertIn(f"The root_dir '{config['event_files']['root_dir']}' defined in config.json does not exist.",
                      str(context.exception))

        config['event_files']['root_dir'] = "."
        config['user']['latitude'] = 0.0
        config['user']['longitude'] = 0.0
        with self.assertRaises(ValueError) as context:
            _check_config(config)
        self.assertIn("Please edit config.json to define the user latitude and longitude decimal values.",
                      str(context.exception))

        config['event_files']['root_dir'] = "."
        config["remote"]["ip_address"] = "1.2.3.4"
        with self.assertRaises(ValueError) as context:
            _check_config(config)
        self.assertIn("Please edit config.json to define the user latitude and longitude decimal values.",
                      str(context.exception))

        config["user"]["longitude"] = 10.0
        config["user"]["latitude"] = 10.0
        with self.assertRaises(ValueError) as context:
            _check_config(config)
        self.assertIn("Please set a user name and password when defining a remote IP address.",
                      str(context.exception))

        config["user"]["name"] = 10.0
        config["user"]["password"] = 10.0

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

    # def test_data_collector_event_consumption(self):
    #     """This test consumes event data from the mocked serial comm port which is defined in the above setup()
    #     function. Using the test class member variable max_events_to_be_processed, the event data is consumed in a
    #     number of consecutive batches testing the collector status as we go. This test defines a buffer of 12 events
    #     using a window size of 4 events which results in a frequency array of size 3.
    #     """
    #     window_size = 4
    #     with DataCollector(self.mock_com_port,
    #                        buff_size=12,
    #                        window_size=window_size,
    #                        save_results=True,
    #                        ignore_header_size=0,
    #                        use_arduino_time=self.use_arduino_time,
    #                        max_median_frequency=15.0) as data_collector:
    #
    #         # Collect 1 window length of events so frequency array should contain 1 value.
    #         self.max_events_to_be_processed = window_size + 1
    #         # Middle data buffer only contained 7 events so file should be empty.
    #         data_collector.acquire_data()
    #         while not data_collector.processing_ended:
    #             sleep(0.01)
    #         self.assertEqual(data_collector.event_counter, self.max_events_to_be_processed)
    #         f = data_collector.frequency_array.copy()
    #         self.assertTrue(f[1] == f[2] == 0.0)
    #         self.assertTrue(int(f[0]) > 9.0 and f[0] < 14.0)
    #
    #         # Collect another window length of events so frequency array should contain 2 values.
    #         self.max_events_to_be_processed = 2 * window_size + 1
    #         data_collector.acquire_data()
    #         while not data_collector.processing_ended:
    #             sleep(0.01)
    #         self.assertEqual(data_collector.event_counter, self.max_events_to_be_processed)
    #         f2 = data_collector.frequency_array.copy()
    #         self.assertTrue(f[0] == f2[0])
    #         self.assertTrue(int(f2[1]) > 9.0 and f2[1] < 14.0)
    #         self.assertTrue(f2[2] == 0.0)
    #
    #         # Collect another window length of events so frequency array should now be full of 3 values.
    #         self.max_events_to_be_processed = 3 * window_size + 1
    #         # Middle data buffer only contained 7 events so file should be empty.
    #         data_collector.acquire_data()
    #         while not data_collector.processing_ended:
    #             sleep(0.01)
    #         self.assertEqual(data_collector.event_counter, self.max_events_to_be_processed)
    #         f3 = data_collector.frequency_array.copy()
    #         self.assertTrue(f3[0] == f2[0])
    #         self.assertTrue(f3[1] == f2[1])
    #         self.assertTrue(f3[2] != f2[2])
    #
    #         # Collect another window length of events so frequency array should remain full and first (original)
    #         # value overwritten.
    #         self.max_events_to_be_processed = 4 * window_size + 1
    #         # Middle data buffer only contained 7 events so file should be empty.
    #         data_collector.acquire_data()
    #         while not data_collector.processing_ended:
    #             sleep(0.01)
    #         self.assertEqual(data_collector.event_counter, self.max_events_to_be_processed)
    #         f4 = data_collector.frequency_array.copy()
    #         self.assertTrue(f4[0] == f3[1])
    #         self.assertTrue(f4[1] == f3[2])
    #         self.assertTrue(f4[2] != f3[2])

    def test_data_collector_frequency_array_population(self):
        """This test consumes event data from the mocked serial comm port which is defined in the above setup()
        function. Using the test class member variable max_events_to_be_processed, the event data is consumed in a
        number of consecutive batches testing the collector status as we go. This test defines a buffer of 12 events
        using a window size of 4 events which results in a frequency array of size 3.
        """
        window_size = 4
        buff_size = 12
        with DataCollector(self.mock_com_port,
                           buff_size=buff_size,
                           window_size=window_size,
                           save_results=True,
                           ignore_header_size=0,
                           use_arduino_time=self.use_arduino_time,
                           max_median_frequency=15.0) as dc:
            # Collect 1 window length of events so frequency array should contain 1 value.
            self.max_events_to_be_processed = window_size
            # Middle data buffer only contained 7 events so file should be empty.
            dc.acquire_data()
            while not dc.processing_ended:
                sleep(0.01)
            self.assertEqual(dc.event_counter, self.max_events_to_be_processed)
            self.assertEqual(dc._buff_index, window_size)
            self.assertTrue(np.allclose(dc._frequency_array[1:], np.zeros(buff_size - 1)))
            self.assertGreater(dc._frequency_array[0], 1.0)
            self.assertEqual(dc._buff.loc[3, 'win_f'], dc._frequency_array[0])
            f1 = dc.frequency_array.copy()

            # Collect another window length of events so frequency array should now contain an additional value for
            # each subsequent event.
            self.max_events_to_be_processed = 2 * window_size
            # Middle data buffer only contained 7 events so file should be empty.
            dc.acquire_data()
            while not dc.processing_ended:
                sleep(0.01)
            self.assertEqual(dc.event_counter, self.max_events_to_be_processed)
            self.assertEqual(dc._buff_index, 2 * window_size)
            self.assertTrue(np.allclose(dc._frequency_array[5:], np.zeros(buff_size - 5)))
            self.assertEqual(f1[0], dc._frequency_array[0])
            self.assertGreater(dc._frequency_array[1], 1.0)
            self.assertGreater(dc._frequency_array[2], 1.0)
            self.assertGreater(dc._frequency_array[3], 1.0)
            self.assertGreater(dc._frequency_array[4], 1.0)
            self.assertEqual(dc._buff.loc[4, 'win_f'], dc._frequency_array[1])
            self.assertEqual(dc._buff.loc[5, 'win_f'], dc._frequency_array[2])
            self.assertEqual(dc._buff.loc[6, 'win_f'], dc._frequency_array[3])
            self.assertEqual(dc._buff.loc[7, 'win_f'], dc._frequency_array[4])
            f2 = dc.frequency_array.copy()

            # Collect another 1 window lengths (now 3 in total) which means we should have reached end of buffer.
            self.max_events_to_be_processed = 3 * window_size
            dc.acquire_data()
            while not dc.processing_ended:
                sleep(0.01)
            self.assertEqual(dc.event_counter, self.max_events_to_be_processed)
            self.assertEqual(dc._buff_index, 0)
            self.assertGreater(dc._frequency_array[0], 1.0)
            self.assertEqual(f2[0], dc._frequency_array[0])
            self.assertEqual(f2[1], dc._frequency_array[1])
            self.assertEqual(f2[2], dc._frequency_array[2])
            self.assertEqual(f2[3], dc._frequency_array[3])
            self.assertEqual(f2[4], dc._frequency_array[4])
            self.assertGreater(dc._frequency_array[5], 1.0)
            self.assertGreater(dc._frequency_array[6], 1.0)
            self.assertGreater(dc._frequency_array[7], 1.0)
            self.assertGreater(dc._frequency_array[8], 1.0)
            self.assertEqual(dc._frequency_array[9], 0.0)
            self.assertEqual(dc._frequency_array[10], 0.0)
            self.assertEqual(dc._frequency_array[11], 0.0)
            self.assertEqual(dc._buff.loc[8, 'win_f'], dc._frequency_array[5])
            self.assertEqual(dc._buff.loc[9, 'win_f'], dc._frequency_array[6])
            self.assertEqual(dc._buff.loc[10, 'win_f'], dc._frequency_array[7])
            self.assertEqual(dc._buff.loc[11, 'win_f'], dc._frequency_array[8])
            f3 = dc.frequency_array.copy()

            # Collect another 1 window lengths (now 4 in total) which means we should have wrapped round.
            self.max_events_to_be_processed = 4 * window_size
            dc.acquire_data()
            while not dc.processing_ended:
                sleep(0.01)
            self.assertEqual(dc.event_counter, self.max_events_to_be_processed)
            self.assertEqual(dc._buff_index, 4)
            # remember that the frequency array shifts to the left
            self.assertEqual(dc._frequency_array[0], f3[1])
            self.assertEqual(dc._frequency_array[1], f3[2])
            self.assertEqual(dc._frequency_array[2], f3[3])
            self.assertEqual(dc._frequency_array[3], f3[4])
            self.assertEqual(dc._frequency_array[4], f3[5])
            self.assertEqual(dc._frequency_array[5], f3[6])
            self.assertEqual(dc._frequency_array[6], f3[7])
            self.assertEqual(dc._frequency_array[7], f3[8])
            self.assertGreater(dc._frequency_array[8], 1.0)
            self.assertGreater(dc._frequency_array[9], 1.0)
            self.assertGreater(dc._frequency_array[10], 1.0)
            self.assertGreater(dc._frequency_array[11], 1.0)
            self.assertEqual(dc._buff.loc[0, 'win_f'], dc._frequency_array[8])
            self.assertEqual(dc._buff.loc[1, 'win_f'], dc._frequency_array[9])
            self.assertEqual(dc._buff.loc[2, 'win_f'], dc._frequency_array[10])
            self.assertEqual(dc._buff.loc[3, 'win_f'], dc._frequency_array[11])
            f4 = dc.frequency_array.copy()

            # Collect another 2 events.
            self.max_events_to_be_processed = 4 * window_size + 2
            dc.acquire_data()
            while not dc.processing_ended:
                sleep(0.01)
            self.assertEqual(dc.event_counter, self.max_events_to_be_processed)
            self.assertEqual(dc._buff_index, 6)
            # remember that the frequency array shifts to the left
            self.assertEqual(dc._frequency_array[0], f4[2])
            self.assertEqual(dc._frequency_array[1], f4[3])
            self.assertEqual(dc._frequency_array[2], f4[4])
            self.assertEqual(dc._frequency_array[3], f4[5])
            self.assertEqual(dc._frequency_array[4], f4[6])
            self.assertEqual(dc._frequency_array[5], f4[7])
            self.assertEqual(dc._frequency_array[6], f4[8])
            self.assertEqual(dc._frequency_array[7], f4[9])
            self.assertEqual(dc._frequency_array[8], f4[10])
            self.assertEqual(dc._frequency_array[9], f4[11])
            self.assertEqual(dc._buff.loc[0, 'win_f'], dc._frequency_array[6])
            self.assertEqual(dc._buff.loc[1, 'win_f'], dc._frequency_array[7])
            self.assertEqual(dc._buff.loc[2, 'win_f'], dc._frequency_array[8])
            self.assertEqual(dc._buff.loc[3, 'win_f'], dc._frequency_array[9])
            self.assertEqual(dc._buff.loc[4, 'win_f'], dc._frequency_array[10])
            self.assertEqual(dc._buff.loc[5, 'win_f'], dc._frequency_array[11])
            self.assertEqual(dc._buff.loc[6, 'win_f'], dc._frequency_array[0])
            self.assertEqual(dc._buff.loc[7, 'win_f'], dc._frequency_array[1])
            self.assertEqual(dc._buff.loc[8, 'win_f'], dc._frequency_array[2])
            self.assertEqual(dc._buff.loc[9, 'win_f'], dc._frequency_array[3])
            self.assertEqual(dc._buff.loc[10, 'win_f'], dc._frequency_array[4])
            self.assertEqual(dc._buff.loc[11, 'win_f'], dc._frequency_array[5])

    def test_median_frequency(self):
        """Test the calculation of median on filling the frequency array."""
        window_size = 4
        buff_size = 12
        with DataCollector(self.mock_com_port,
                           buff_size=buff_size,
                           window_size=window_size,
                           save_results=True,
                           ignore_header_size=0,
                           use_arduino_time=self.use_arduino_time,
                           max_median_frequency=15.0) as dc:
            # Collect a buffer
            self.max_events_to_be_processed = buff_size - 1
            dc.acquire_data()
            while not dc.processing_ended:
                sleep(0.01)
            # Note the frequency array is not yet full as wait for the first window of events to be received before
            # start filling it.
            self.assertEqual(dc._frequency_median, 0.0)
            # now collect required remaining event to fill the frequency array.
            self.max_events_to_be_processed = buff_size
            dc.acquire_data()
            while not dc.processing_ended:
                sleep(0.01)
            expected_median = np.median(dc.frequency_array)
            self.assertEqual(dc._frequency_median, expected_median)

    def test_data_collector_exceed_max_median_frequency(self):
        """Test data collector exits due to high median frequency detected."""
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
                while not data_collector.processing_ended:
                    sleep(0.01)

                self.assertEqual(data_collector._status, Status.MEDIAN_FREQUENCY_EXCEEDED)

    def test_data_collector_event_anomalies(self):
        """Test logging of event anomalies to file. test data contains a single high and low event anomaly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            window_size = 5
            buff_size = 25
            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               buff_size=buff_size,
                               window_size=window_size,
                               save_results=True,
                               ignore_header_size=0,
                               use_arduino_time=self.use_arduino_time,
                               max_median_frequency=15.0) as data_collector:

                data_collector.acquire_data()
                while not data_collector.processing_ended:
                    sleep(0.01)

                self.assertIn(len(data_collector.saved_file_names), [2])
                file_path = os.path.join(temp_dir, "anomaly", data_collector.saved_file_names[0])
                self.assertTrue(os.path.isfile(file_path))
                df = pd.read_csv(file_path, skiprows=1)
                self.assertEqual(df.shape, (buff_size, 9))
                df = df.sort_values(by=['event'], ignore_index=True)
                # check high anomaly is in center of saved event buffer
                self.assertEqual(df['event'][df.shape[0] // 2], 69)

                file_path = os.path.join(temp_dir, "anomaly", data_collector.saved_file_names[1])
                self.assertTrue(os.path.isfile(file_path))
                df = pd.read_csv(file_path, skiprows=1)
                self.assertEqual(df.shape, (buff_size, 9))
                df = df.sort_values(by=['event'], ignore_index=True)
                # check low anomaly is in center of saved event buffer
                self.assertIn(df['event'][df.shape[0] // 2], [104, 105])

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
                               use_arduino_time=self.use_arduino_time,
                               max_median_frequency=15.0) as data_collector:

                data_collector.acquire_data()
                while not data_collector.processing_ended:
                    sleep(0.01)

                # We should have 4 log all buffers + 1 low anomaly buffer. High anomaly is spread out over larger
                # window size and is thus not seen.
                self.assertEqual(len(data_collector.saved_file_names), 5)
                file_path = os.path.join(temp_dir, "all", data_collector.saved_file_names[0])
                df = pd.read_csv(file_path, skiprows=1)
                self.assertTrue(os.path.isfile(file_path))
                # confirm we have window frequencies at required positions
                states = df['win_f'].notna()
                self.assertTrue(np.array_equal(np.where(states)[0], np.arange(window_size - 1, buff_size)))
                win_f_array = df['win_f']
                # replace missing frequencies in first buffer with 0.0 so as we match collectors calculation for median
                win_f_array = win_f_array.fillna(0.0).values
                # confirm we have 1 median frequency at required position and check correct against window frequencies
                states = df['median_f'].notna()
                self.assertTrue(np.array_equal(np.where(states)[0], np.array([29])))
                median_f_array = df[df['median_f'].notna()]['median_f'].values
                self.assertEqual(median_f_array.size, 1)
                self.assertAlmostEqual(np.median(win_f_array), median_f_array[0])

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
                               use_arduino_time=self.use_arduino_time,
                               max_median_frequency=15.0) as data_collector:

                data_collector.acquire_data()
                while not data_collector.processing_ended:
                    sleep(0.01)

                file_path = os.path.join(temp_dir, "all", data_collector.saved_file_names[0])
                self.assertTrue(os.path.isfile(file_path))
                df = pd.read_csv(file_path, dtype={0: str, 1: str}, skiprows=1).iloc[:, 0:7]
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
                               use_arduino_time=self.use_arduino_time,
                               max_median_frequency=15.0) as data_collector:
                data_collector.acquire_data()
                while not data_collector.processing_ended:
                    sleep(0.01)
                self.assertTrue(data_collector.saved_file_names == [])

    def test_save_load_queue(self):
        """Test save and load queue functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            f1_path = os.path.join(temp_dir, "file_1.csv")
            f1 = open(f1_path, 'w')
            f1.writelines(["a", "b"])
            f1.close()
            f2_path = os.path.join(temp_dir, "file_2.csv")
            f2 = open(f2_path, 'w')
            f2.writelines(["a", "b"])
            f2.close()
            queue_save_path = os.path.join(temp_dir, "queue.txt")
            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               log_all_events=True,
                               save_results=True,
                               ignore_header_size=0,
                               start_string="",
                               queue_save_path=os.path.join(queue_save_path),
                               use_arduino_time=self.use_arduino_time,
                               max_median_frequency=15.0) as dc:
                dc._file_queue.put(f1_path)
                dc._file_queue.put(f2_path)
                self.assertFalse(os.path.exists(queue_save_path))
                dc._save_queue()
                self.assertTrue(os.path.exists(queue_save_path))

            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               log_all_events=True,
                               save_results=True,
                               ignore_header_size=0,
                               start_string="",
                               queue_save_path=os.path.join(queue_save_path),
                               use_arduino_time=self.use_arduino_time,
                               max_median_frequency=15.0) as dc:
                self.assertTrue(os.path.exists(queue_save_path))
                dc._load_queue()
                self.assertFalse(os.path.exists(queue_save_path))
                self.assertEqual(dc._file_queue.get(), f1_path)
                self.assertEqual(dc._file_queue.get(), f2_path)

    def test_data_collector_file_queue(self):
        """Test preservation of event anomaly file names to queue/file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_save_path = os.path.join(temp_dir, "queue.txt")
            with DataCollector(self.mock_com_port,
                               save_dir=temp_dir,
                               save_results=True,
                               ignore_header_size=0,
                               ip_address="1.2.3.4",  # defining ip will cause DC to use queue/file
                               queue_save_path=os.path.join(queue_save_path),
                               use_arduino_time=self.use_arduino_time,
                               max_median_frequency=15.0) as dc:

                dc.acquire_data()
                dc.run_remote()
                while not dc._acquisition_ended:
                    sleep(0.01)

                # Tell remaining thread (remote process) to shut down. Note remote thread will probably still be
                # blocked trying to FTP a file extracted from the queue at this point. Eventually this will time
                # out and be reinstated to the queue before saving its content.
                dc._shut_down = True
                sleep(20)
                self.assertTrue(queue_save_path)
