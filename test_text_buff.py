import unittest
from text_buff import TextBuff


class TextBuffTest(unittest.TestCase):

    def test_text_buff(self):
        """Test text buff functionality"""
        buff = TextBuff()
        self.assertTrue(buff.num_entries == 0)
        buff.append("abc")
        self.assertTrue(buff.num_entries == 1)
        buff.append("def")
        self.assertTrue(buff.num_entries == 2)
        buff.append("ghi", reset=True)
        self.assertTrue(buff.num_entries == 1)


