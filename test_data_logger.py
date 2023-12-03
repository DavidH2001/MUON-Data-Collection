import unittest
from data_logger import DataLogger
from serial_com import SerialCom

class DataCollectorTest(unittest.TestCase):

    def test_add_data_channel(self):

        with DataLogger() as data_logger:
            buff = TextBuff(max_lines=7)
            bq = BuffQ(max_buffs=5)
            serial_com = SerialCom(bq)
            serial_com.connect(name="", )
            id = data_logger.add_data_channel()

            data_logger.channel[id].read(async=True)