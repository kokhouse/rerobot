# coding=utf-8
"""
PyTests for Rero
"""
import unittest
from unittest import mock
import sys
sys.modules['Rero.mongo_manager'] = mock.MagicMock()
sys.modules['Rero.redis_manager'] = mock.MagicMock()
from Rero.Modules import ranking


# TODO finish tests
class TestRero(unittest.TestCase):
    """
    Test suite for Rero.
    """
    def setUp(self):
        with open("./test/textForXp.txt") as file:
            self.xp_text = file.read()
        file.close()

    def testLevelToXp(self):
        x = ranking.level_to_xp(0)
        self.assertEquals(x, 0)

        x = ranking.level_to_xp(1)
        self.assertEquals(x, 165)

    def testXpToLevel(self):
        x = ranking.xp_to_level(300)
        self.assertEquals(x, 2)

    def testLengthToXp(self):
        """

        :return:
        """
        text_1 = self.xp_text[:10]
        x = ranking.xp_calculation(len(text_1))
        self.assertEquals(x, 0.1)

        text_1 = self.xp_text[:200]
        x = ranking.xp_calculation(len(text_1))
        self.assertEquals(x, 3)

        text_2 = self.xp_text[:700]
        x = ranking.xp_calculation(len(text_2))
        self.assertEquals(x, 1.5)

        text_3 = self.xp_text[:900]
        x = ranking.xp_calculation(len(text_3))
        self.assertEquals(x, 1)

        text_4 = self.xp_text[:1500]
        x = ranking.xp_calculation(len(text_4))
        self.assertEquals(x, 0)
