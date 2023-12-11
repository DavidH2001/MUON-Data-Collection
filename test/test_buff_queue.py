import os
import unittest
import tempfile
import pandas as pd
from text_buff import TextBuff
from buff_queue import BuffQueue


class TextBuffTest(unittest.TestCase):

    def test_buff_queue(self):
        """Test buffer queue functionality"""
        buff_queue = BuffQueue(max_entries=3)
        self.assertTrue(buff_queue.num_entries == 0)

        buff = TextBuff()
        buff.append("abc")
        buff.append("def")
        buff_queue.append(buff)
        self.assertTrue(buff_queue.num_entries == 1)

        buff = TextBuff()
        buff.append("123")
        buff.append("4567")
        buff.append("891011")
        buff_queue.append(buff)
        self.assertTrue(buff_queue.num_entries == 2)

        buff = TextBuff()
        buff.append("a")
        buff.append("bb")
        buff.append("ccc")
        buff.append("dddd")
        buff_queue.append(buff)
        self.assertTrue(buff_queue.num_entries == 3)
        self.assertTrue(buff_queue.mid_index == 1)
        self.assertEqual(buff_queue.peek(index=0).buff, ["abc", "def"])
        mid_buff = buff_queue.peek(index=buff_queue.mid_index)
        self.assertEqual(mid_buff.buff, ["123", "4567", "891011"])
        self.assertTrue(mid_buff.num_entries == 3)

        buff = TextBuff()
        buff.append("1 2 3 4")
        buff_queue.append(buff)
        self.assertTrue(buff_queue.num_entries == 3)
        mid_buff = buff_queue.peek(index=buff_queue.mid_index)
        self.assertEqual(mid_buff.buff, ["a", "bb", "ccc", "dddd"])
        self.assertTrue(mid_buff.num_entries == 4)

    def test_save(self):
        """Test buffer queue save."""
        temp_dir = "c:/users/dave/temp"
        #with tempfile.TemporaryDirectory() as temp_dir:
        if True:
            buff_queue = BuffQueue(max_entries=3, save_dir=temp_dir)
            buff = TextBuff()
            buff.append("111 abc")
            buff.append("222 def")
            buff_queue.append(buff)
            buff = TextBuff()
            buff.append("333 hij")
            buff.append("444 klm")
            buff.append("555 nop")
            buff_queue.append(buff)
            temp_file = 'q.txt'
            buff_queue.save(temp_file)
            self.assertTrue(os.path.isfile(os.path.join(temp_dir, temp_file)))
            df = pd.read_csv(os.path.join(temp_dir, temp_file), sep=' ', header=None)
            self.assertTrue(len(df) == 5)
            self.assertTrue(df.loc[0, 0] == 111)
            self.assertTrue(df.loc[0, 1] == 'abc')
            self.assertTrue(df.loc[4, 0] == 555)
            self.assertTrue(df.loc[4, 1] == 'nop')








