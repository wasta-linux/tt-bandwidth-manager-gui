import gi
import os
import re
import shutil
import subprocess
import time
import unittest

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from pathlib import Path

from trafficcop import app

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class All(unittest.TestCase):
    def setUp(self):
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
