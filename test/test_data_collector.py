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
import pandas as pd
from data_collector import DataCollector
from unittest.mock import Mock


class DataCollectorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def test_data_collector_csv(self):

        data_index = 0

        # Get and prepare test data from CSV file.
        data = pd.read_csv("./data/event_test_set.csv", dtype={0: str, 1: str}, header=None).iloc[:, 0:2]
        data = [f"{row[0]} {row[1]}".encode() for _, row in data.iterrows()]
        data.append(b'exit')

        def _data_func():
            """Function used to emulate a delay and pass serial data"""
            nonlocal data_index
            result = data[data_index]
            sleep(0.1)
            data_index += 1
            return result

        # Mock the data collector com_port returned by serial package. The above data will be returned
        # when reading lines.
        # create new mock object
        mock_com_port = Mock()
        # note, could have passed the data directly to side_effect instead of calling function
        mock_com_port.readline.side_effect = _data_func
        DataCollector.com_port = mock_com_port

        # mock the data collector serial package and attached mocked com port
        mock_serial = Mock()
        #mock_serial.side_effect = foo
        DataCollector.serial = mock_serial
        mock_serial.Serial.return_value = mock_com_port

        temp_dir = 'c:/Users/dave/Temp'
        # if os.path.isfile(data_file):
        #     os.remove(data_file)

        if True:  # with tempfile.TemporaryDir() as temp_dir:
            with DataCollector(mock_com_port,
                               save_dir=temp_dir,
                               buff_time_ms=100000,
                               save_results=True) as data_collector:
                # Middle data buffer only contained 7 events so file should be empty.
                data_collector.acquire_data()
                while not data_collector.acquisition_ended:
                    sleep(0.01)

                a=1
                files = [f for f in os.listdir(temp_dir)] # if os.path.isfile(os.path.join(temp_dir, f))]

                self.assertTrue(len(files) == 3)
                df = pd.read_csv(os.path.join(temp_dir, files[0]), sep=' ', header=None)
                self.assertTrue(df.iloc[0, 1] == 10)
                self.assertTrue(df.iloc[-1, 1] == 34)
                df = pd.read_csv(os.path.join(temp_dir, files[1]), sep=' ', header=None)
                self.assertTrue(df.iloc[0, 1] == 29)
                self.assertTrue(df.iloc[-1, 1] == 56)
                df = pd.read_csv(os.path.join(temp_dir, files[2]), sep=' ', header=None)
                self.assertTrue(df.iloc[0, 1] == 30)
                self.assertTrue(df.iloc[-1, 1] == 60)
                a=1

                #self.assertTrue(os.stat(data_file).st_size == 0)
                # self assert have 3 files

