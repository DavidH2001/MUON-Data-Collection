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
import numpy as np
import pandas as pd
from buff_queue import BuffQueue
from data_collector import DataCollector
from unittest.mock import Mock


class DataCollectorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def test_data_collector(self):
        """This test """
        # Create test data to be returned by mocked com port. Data consists of text lines containing:
        #    <event number>, <arduino time>
        # Note, the last entry in each of these buffers will cause the buffer to be full and thus is written to the
        # next buffer. Each buffer will contain the number events defined by its range(). For example range(1, 8) will
        # contain 7 events made up from the last event in the preceding buffer through to the penultimate event in the
        # current buffer. The first buffer is different as it will contain one less event.
        # For example, here we generate 10 entries, 1 to 9 are added to buff#1 which start at (and increment by)
        # 60000 (max buff time) / 9.
        # buff#1 len=9
        data = [f'{x} {int(float(60000 * x / 9))}\n'.encode() for x in range(1, 11)]
        # buff#2 = len=8 10->10+8-1 = 17
        data += [f'{len(data)+x} {int(float(data[-1].split()[1]) + 60000 * x/8)}\n'.encode() for x in range(1, 9)]
        # buff#3 (middle) len=7 18->18+7-1 = 24
        data += [f'{len(data)+x} {int(float(data[-1].split()[1]) + 60000 * x/7)}\n'.encode() for x in range(1, 8)]
        # buff#3 len= 13  25->25+13-1 = 37
        data += [f'{len(data)+x} {int(float(data[-1].split()[1]) + 60000 * x/13)}\n'.encode() for x in range(1, 14)]
        # buff#4 len=10 38->38+10-1 -> 47
        data += [f'{len(data)+x} {int(float(data[-1].split()[1]) + 60000 * x/10)}\n'.encode() for x in range(1, 11)]
        # buff#5 = force exit
        data += [b'exit']

        # Mock the data collector com_port returned by serial package. The above data will be returned
        # when reading lines.
        # create new mock object
        mock_com_port = Mock()
        mock_com_port.readline.side_effect = data
        DataCollector.com_port = mock_com_port

        # mock the data collector serial package and attached mocked com port
        mock_serial = Mock()
        DataCollector.serial = mock_serial
        mock_serial.Serial.return_value = mock_com_port

        data_file = 'c:/Users/dave/Temp/test.txt'
        if os.path.isfile(data_file):
            os.remove(data_file)
        if True: #with tempfile.TemporaryFile() as data_file:
            with DataCollector(mock_com_port, data_file, trigger_string='', save_results=True) as data_collector:
                # Middle data buffer only contained 7 events so file should be empty.
                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)
                self.assertTrue(os.stat(data_file).st_size == 0)

                # Add another data buffer using the time of the last data item making sure we miss the 'exit' entry.
                data = [f'{len(data)+x} {int(float(data[-2].split()[1]) + 60000 * x/8)}\n'.encode()
                        for x in range(1, 9)]
                data += [b'exit']
                # Restart acquisition. Buffer queue will bump along one more buffer resulting in middle buffer now
                # containing 13 events.
                mock_com_port.readline.side_effect = data
                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)
                # The data file should now contain the current buffer queue i.e. last NUM_BUFFS buffer writes.
                self.assertTrue(os.stat(data_file).st_size > 0)
                #saved_data = pd.read_csv(data_file, sep=' ', header=None)
                a=1

    def test_data_collector_csv(self):

        # Get and prepare test data from CSV file.
        data = pd.read_csv("./data/event_test_set.csv", dtype={0: str, 1: str}, header=None).iloc[:, 0:2]
        data = [f"{row[0]} {row[1]}".encode() for _, row in data.iterrows()]
        data.append(b'exit')

        # Mock the data collector com_port returned by serial package. The above data will be returned
        # when reading lines.
        # create new mock object
        mock_com_port = Mock()
        mock_com_port.readline.side_effect = data
        DataCollector.com_port = mock_com_port

        # mock the data collector serial package and attached mocked com port
        mock_serial = Mock()
        DataCollector.serial = mock_serial
        mock_serial.Serial.return_value = mock_com_port

        data_file = 'c:/Users/dave/Temp/test.txt'
        if os.path.isfile(data_file):
            os.remove(data_file)

        buff_queue = BuffQueue(max_entries=6)

        if True:  # with tempfile.TemporaryFile() as data_file:
            with DataCollector(mock_com_port, data_file, buff_time_ms=100000, save_results=True) as data_collector:
                # Middle data buffer only contained 7 events so file should be empty.
                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)
                self.assertTrue(os.stat(data_file).st_size == 0)


