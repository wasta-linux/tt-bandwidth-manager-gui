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
            # Ensure row has 7 columns.
            self.assertEqual(len(row[:]), 7)

    def test_convert_default(self):
        yaml = self.data_dir / 'tt-default-config.yaml'
        store = config.convert_yaml_to_store(yaml)
        # Ensure store is not empty.
        self.assertNotEqual(store, '')
        for row in store:
            # Ensure row has 7 columns.
            self.assertEqual(len(row[:]), 7)

    def test_convert_empty(self):
        yaml = self.data_dir / 'empty.yaml'
        store = utils.mute(config.convert_yaml_to_store, yaml)
        self.assertEqual(store, '')

    def tearDown(self):
        pass
