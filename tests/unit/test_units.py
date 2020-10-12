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

    def test_check_diff(self):
        example = self.tests_dir / 'data' / 'tt-example.yaml'
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

    def test_IGNORE(self):
        # This is for testing new functions.
        pass

    def test_INCOMPLETE_restart_service(self):
        pass
        #app.app.do_startup()
        # Get widget state.
        #timestamp_pre = app.app.label_applied.get_text()
        #app.app.restart_service()
        #timestamp_post = app.app.label_applied.get_text()
        #self.assertNotEqual(timestamp_pre, timestamp_post)

    def tearDown(self):
        pass
