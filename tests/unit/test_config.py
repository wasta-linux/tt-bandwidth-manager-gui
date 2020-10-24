#import gi
#import mock
import unittest

#gi.require_version("Gtk", "3.0")
#from gi.repository import Gtk
from pathlib import Path

from trafficcop import config
from trafficcop import utils

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase


class Yaml(unittest.TestCase):
    def setUp(self):
        tests_dir = Path(__file__).parents[1]
        self.data_dir = tests_dir / 'data'

    def test_convert_bad_syntax(self):
        yaml = self.data_dir / 'bad_syntax.yaml'
        store = config.convert_yaml_to_store(yaml)
        self.assertNotEqual(store, '')
        for row in store:
            # Ensure row has the correct number of columns.
            self.assertEqual(len(row[:]), 13)

    def test_convert_default(self):
        yaml = self.data_dir / 'tt-default-config.yaml'
        store = config.convert_yaml_to_store(yaml)
        # Ensure store is not empty.
        self.assertNotEqual(store, '')
        for row in store:
            # Ensure row has 7 columns.
            self.assertEqual(len(row[:]), 13)

    def test_convert_empty(self):
        yaml = self.data_dir / 'empty.yaml'
        store = utils.mute(config.convert_yaml_to_store, yaml)
        self.assertEqual(store, '')

    def tearDown(self):
        pass

class Bytes(unittest.TestCase):
    def setUp(self):
        pass

    def test_convert_config_rates_to_human(self):
        rates = [
            '4bit',
            '8bit',
            '16kbit',
            '23kbit',
            '8kbps',
            '16kbps',
            '3mbit',
            '3mibps',
            '7gibit',
        ]

        outputs = [
            ['0.50', 'B/s'],
            ['1.00', 'B/s'],
            ['2.00', 'KB/s'],
            ['2.88', 'KB/s'],
            ['8.00', 'KB/s'],
            ['16.00', 'KB/s'],
            ['375.00', 'KB/s'],
            ['2.93', 'MB/s'],
            ['854.49', 'MB/s'],
        ]
        for i in range(len(rates)):
            human = config.convert_config_rates_to_human(rates[i])
            self.assertEqual(outputs[i], human)

    def tearDown(self):
        pass
