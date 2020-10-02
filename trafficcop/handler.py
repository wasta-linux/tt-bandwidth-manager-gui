""" Signal handler module. """

import os
import re
import subprocess
#import threading

from trafficcop import app


class Handler():
    def gtk_widget_destroy(self, *args):
        app.app.quit()

    def on_toggle_unit_state_state_set(self, widget, state):
        state = str(state)
        print("Unit State toggled to", state + ".")

    def on_toggle_active_state_set(self, widget, state):
        state = str(state)
        print("Active State toggled to", state + ".")

    def on_button_restart_clicked(self, folder_obj):
        print("Restart button clicked.")

    def on_button_log_clicked(self, *args):
        # Get the time when the service was last started.
        cmd = [
            "journalctl",
            "--reverse",
            "--unit=tt-bandwidth-manager.service",
            "--since=-2days",
            "--output=short-full",
            ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout = result.stdout.decode()
        pat = '^.*: Started.*$'
        match = re.search(pat, stdout, re.MULTILINE)
        matched_line = match.group(0)
        start_time = " ".join(matched_line.split()[:4])

        # Follow the log since this time in a terminal window.
        cmd = "gnome-terminal --geometry=144x24+100+200 -- journalctl --unit=tt-bandwidth-manager.service --follow --output=cat --no-pager --since=\'" + start_time + "\'"
        os.system(cmd)

    def on_button_config_clicked(self, *args):
        print("Config button clicked.")

    def on_button_reset_clicked(self, button):
        print("Reset button clicked.")
