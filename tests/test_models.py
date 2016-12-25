# -*- coding: utf-8 -*-

from .context import tafor

import unittest


class TestTafor(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.db = tafor.Session()

    def test_insert(self):
        pass

class TestSchedule(unittest.TestCase):

    def test_insert(self):
        pass
        


if __name__ == '__main__':
    unittest.main()