#import gi
import unittest

#gi.require_version("Gtk", "3.0")
#from gi.repository import Gtk

from pathlib import Path

from trafficcop import app
from trafficcop import config
from trafficcop import utils

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class All(unittest.TestCase):
    def setUp(self):
        self.tests_dir = Path(__file__).parents[1]
        self.pkg_dir = Path(__file__).parents[2]
        self.example_config = self.tests_dir / 'data' / 'tt-example.yaml'

    def test_IGNORE(self):
        # This is for testing new functions.
        pass

    def test_check_diff(self):
        example = self.example_config
        default = self.tests_dir / 'data' / 'tt-default-config.yaml'
        diff = utils.check_diff(example, default)
        self.assertNotEqual(diff, 0)

    def test_ensure_config_backup(self):
        # This only tests that tests/data/tt-config.yaml == tests/data/tt-config.yaml.bak.
        #   It doesn't test the creation of a properly-named new backup file.
        current = self.tests_dir / 'data' / 'tt-config.yaml'
        result = utils.mute(
            utils.ensure_config_backup,
            current
        )
        self.assertTrue(result)

    def tearDown(self):
        pass

class CompareTimestamps(unittest.TestCase):
    def setUp(self):
        self.convert = utils.convert_human_to_epoch

    def test_a_older(self):
        epochA = self.convert("Sat Oct 17 05:32:38 2020")
        epochB = self.convert("Sun Oct 18 05:32:38 2020")
        self.assertGreater(epochB, epochA)

    def test_b_older(self):
        epochA = self.convert("Sat Oct 17 05:32:38 2020")
        epochB = self.convert("Thu Sep 17 05:32:38 2020")
        self.assertGreater(epochA, epochB)

    def test_bad(self):
        epoch = utils.mute(self.convert, "Lun Sep 17 00:00:00 2020")
        self.assertEqual(epoch, "")

    def test_empty(self):
        epoch = self.convert("")
        self.assertEqual(epoch, "")

    def tearDown(self):
        pass
