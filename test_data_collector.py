#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 29 14:01:33 2022

@author: dave
"""

import os
import unittest
import tempfile
import numpy as np
import pandas as pd
from data_collector import DataCollector
from unittest.mock import Mock


class DataCollectorTest(unittest.TestCase):

    def test_com_port(self):
        """This test mocks the DataCollector com_port returned by the serial module. The above data will be returned
            when reading lines."""

        # Create test data to be returned by mocked com port. Data consists of text lines containing:
        #    <event number>, <arduino time>
        data = [b'1 100\n', b'2 200\n', b'3 300\n', b'4 400\n', b'4 400\n',
                b'5 2000\n', b'6 2010\n', b'7 2020\n', b'8 2040\n', b'9 2050\n', b'10 2060\n',
                b'11 3000\n', b'12 3010\n', b'13 3020\n', b'14 3050\n',
                b'15 5000\n', b'16 5010\n', b'17 5020\n', b'18 5040\n', b'19 5050\n', b'20 5060\n',
                b'21 60000\n',
                b'exit']

        # Create new mock object.
        mock_com_port = Mock()
        mock_com_port.readline.side_effect = data
        DataCollector.com_port = mock_com_port

        # Mock the DataCollector serial module and attached mocked com port.
        mock_serial = Mock()
        DataCollector.serial = mock_serial
        mock_serial.Serial.return_value = mock_com_port

        data_file = 'c:/Users/dave/Temp/test.txt'
        if os.path.isfile(data_file):
            os.remove(data_file)
        if True: #with tempfile.TemporaryFile() as data_file:
            with DataCollector(mock_com_port, data_file, trigger_string='', save_results=True) as data_collector:
                # Middle buffer only contains 7 events so file should be empty.
                data_collector.acquire_data(save_results=True)
                self.assertTrue(os.stat(data_file).st_size == 0)


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
        data = [f'{x} {int(float(60000 * x / 9))}\n'.encode() for x in range(1, 11)]
        # buff#2 = 10 -> 10+8-1 = 17
        data += [f'{len(data)+x} {int(float(data[-1].split()[1]) + 60000 * x/8)}\n'.encode() for x in range(1, 9)]
        # buff#3 = 18 -> 18+7-1 = 24
        data += [f'{len(data)+x} {int(float(data[-1].split()[1]) + 60000 * x/7)}\n'.encode() for x in range(1, 8)]
        # buff#3 = 25 -> 25+13-1 = 37
        data += [f'{len(data)+x} {int(float(data[-1].split()[1]) + 60000 * x/13)}\n'.encode() for x in range(1, 14)]
        # buff#4 = 38 -> 38+10-1 -> 47
        data += [f'{len(data)+x} {int(float(data[-1].split()[1]) + 60000 * x/10)}\n'.encode() for x in range(1, 11)]
        # buff#5 = 48 (single event)
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
                # Middle buffer only contains 7 events so file should be empty.
                data_collector.acquire_data(save_results=True)
                self.assertTrue(os.stat(data_file).st_size == 0)


                # Add more data using the time of the last data item making sure we miss the 'exit' entry.
                data = [f'{len(data)+x} {int(float(data[-2].split()[1]) + 60000 * x/8)}\n'.encode() for x in range(1, 9)]
                data += [b'exit']
                # Now buffer queue will bump along one buffer making the middle buffer now containing 13 events.
                mock_com_port.readline.side_effect = data
                data_collector.acquire_data(save_results=True)
                # The data file should now contain the current buffer queue i.e. last NUM_BUFFS buffer writes.
                self.assertTrue(os.stat(data_file).st_size > 0)
                saved_data = pd.read_csv(data_file, sep=' ', header=None)
                #self.assertTrue(np.equal(saved_data[2].values, range(10, )

        a=1