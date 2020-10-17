import unittest
#from pathlib import Path

from trafficcop import config

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase


class New(unittest.TestCase):
    def setUp(self):
        pass

    def test_new(self):
        result = True
        self.assertTrue(result)

    def tearDown(self):
        pass
