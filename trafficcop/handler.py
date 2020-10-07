""" Signal handler module. """

import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from trafficcop import app
from trafficcop import worker


class Handler():
    #def __init__(self):
        #self.window = app.app.window

    def gtk_widget_destroy(self, *args):
        app.app.quit()

    def on_toggle_unit_state_state_set(self, widget, state):
        sstate = str(state)
        print("Unit State toggled to", sstate + ".")
        # Apply new state to the service.
        if state == True:
            cmd = ["systemctl", "enable", "tt-bandwidth-manager.service"]
        elif state == False:
            cmd = ["systemctl", "disable", "tt-bandwidth-manager.service"]
        subprocess.run(cmd)
        # Ensure that toggle button matches true state.
        app.app.update_state_toggles()

    def on_toggle_active_state_set(self, widget, state):
        # Apply new state to the service.
        if state == True:
            cmd = ["systemctl", "start", "tt-bandwidth-manager.service"]
            subprocess.run(cmd)
            app.app.wait_for_tt_start()
        elif state == False:
            cmd = ["systemctl", "stop", "tt-bandwidth-manager.service"]
            subprocess.run(cmd)

        # Ensure that toggle button matches true state.
        app.app.update_state_toggles()
        # Update managed device name.
        app.app.update_device_name()

    def on_button_restart_clicked(self, folder_obj):
        # Restart the service
        cmd = ["systemctl", "restart", "tt-bandwidth-manager.service"]
        subprocess.run(cmd)
        # Check service status and update toggles.
        app.app.update_state_toggles()
        time.sleep(3)
        app.app.update_device_name()

    def on_button_log_clicked(self, *args):
        target = worker.handle_button_log_clicked
        t_log = threading.Thread(target=target)
        t_log.start()

    def on_button_config_clicked(self, *args):
        target = worker.handle_button_config_clicked
        t_config = threading.Thread(target=target)
        t_config.start()

        target = worker.handle_config_changed
        t_restart = threading.Thread(target=target)
        t_restart.start()

    def on_button_reset_clicked(self, button):
        current = Path("/etc/tt-config.yaml")
        # Make a backup of existing config, add index if backup already exists.
        name = current.stem
        suffix = ".yaml.bak"
        backup = current.with_suffix(suffix)
        if backup.exists():
            # Add index to name.
            i = 1
            backup = current.with_name(name + '-' + str(i)).with_suffix(suffix)
            print(backup)
            while backup.exists():
                # Keep trying new indices until an available one is found.
                i += 1
                backup = current.with_name(name + '-' + str(i)).with_suffix(suffix)
        # Make backup copy.
        shutil.copyfile(current, backup)
        # Copy /usr/share/tt-bandwidth-manager/tt-default-config.yaml to /etc/tt-config.yaml;
        #   overwrite existing file.
        default = Path("/usr/share/tt-bandwidth-manager/tt-default-config.yaml")
        print("copying", default, "to", current)
        shutil.copyfile(default, current)
        cmd = ["systemctl", "restart", "tt-bandwidth-manager.service"]
        restart = subprocess.run(cmd)
        # Ensure that toggle buttons match true state.
        app.app.update_state_toggles()
