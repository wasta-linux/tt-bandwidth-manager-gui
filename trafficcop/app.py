""" Main GUI module. """

import gi
import json
import logging
import os
import re
import subprocess
import time

from pathlib import Path
current_file_path = Path(__file__)

gi.require_version("Gtk", "3.0")
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from trafficcop import handler


class TrafficCop(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id='org.wasta.apps.traffic-cop',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )

        # Add CLI options.
        self.add_main_option(
            'version', ord('V'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            'Print version number.', None
        )
        '''
        self.add_main_option(
            'snaps-dir', ord('s'), GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
            'Update snaps from offline folder.', '/path/to/wasta-offline'
        )
        self.add_main_option(
            'online', ord('i'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            'Update snaps from the online Snap Store.', None
        )
        '''
        # Get UI location based on current file location.
        self.ui_dir = '/usr/share/wasta-bandwidth-manager/ui'
        if str(current_file_path.parents[1]) != '/usr/share/wasta-bandwidth-manager':
            self.ui_dir = str(current_file_path.parents[1] / 'data' / 'ui')

        # Define app-wide variables.
        self.runmode = ''

    def do_startup(self):
        # Define builder and its widgets.
        Gtk.Application.do_startup(self)

        # Get widgets from glade file. (defined in __init__)
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.ui_dir + '/mainwindow.glade')
        self.toggle_active = self.builder.get_object('toggle_active')
        self.toggle_unit_state = self.builder.get_object('toggle_unit_state')
        self.button_restart = self.builder.get_object('button_restart')
        self.button_log = self.builder.get_object('button_log')
        self.button_reset = self.builder.get_object('button_reset')
        self.button_config = self.builder.get_object('button_config')

        # Get the time when the service was last started.
        self.update_service_props()

    def do_activate(self):
        # Verify execution with elevated privileges.
        #if os.geteuid() != 0:
        #    bin = '/usr/bin/wasta-bandwidth-manager'
        #    print("wasta-bandwidth-manager needs elevated privileges; e.g.:\n\n$ pkexec", bin, "\n$ sudo", bin)
        #    exit(1)
        self.update_state_toggles()

        # Get name of managed interface.
        self.update_device_name()

        '''
        cmd = [
            "systemctl",
            "status",
            "tt-bandwidth-manager.service",
            "--no-pager",
        ]
        status_output = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output_list = status_output.stdout.decode().splitlines()
        label_iface = self.builder.get_object('label_iface')
        for line in output_list:
            pat = '.*\s\/usr\/bin\/tt\s.*'
            try:
                match = re.match(pat, line)
                iface = match.group().split()[3]
                label_iface.set_text(iface)
                break
            except:
                pass
        '''
        # Define window and make runtime adjustments.
        self.window = self.builder.get_object('mainwindow')
        #self.window.set_icon_name('traffic-cop')
        self.add_window(self.window)
        self.window.show()

        # Connect GUI signals to Handler class.
        self.builder.connect_signals(handler.Handler())

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if not options:
            # No command line args passed: run GUI.
            self.activate()
            return 0

        if 'version' in options:
            # TODO: print version number from changelog instead of using apt-cache.
            proc = subprocess.run(['apt-cache', 'policy', 'tt-bandwidth-manager'])
            print(proc.stdout.decode())
            return 0

        # Verify execution with elevated privileges.
        #if os.geteuid() != 0:
        #    print("wasta-bandwidth-manager needs elevated privileges; e.g.:\n\n$ pkexec", __file__, "\n$ sudo", __file__)
        #    exit(1)

    def update_service_props(self):
        # Get state of systemd service.
        cmd = [
            "systemctl",
            "show",
            "tt-bandwidth-manager.service",
            "--no-pager",
        ]
        status_output = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output_list = status_output.stdout.decode().splitlines()

        # Parse output for unit state and active state.
        toggle_unit_state = self.builder.get_object('toggle_unit_state')
        toggle_active = self.builder.get_object('toggle_active')
        upat = '^UnitFileState=.*$'
        apat = '^ActiveState=.*$'
        #epat = '^ConditionTimestampMonotonic=.*$' # NOT epoch seconds!
        fpat = '^ExecMainStartTimestamp=.*$'
        for line in output_list:
            try:
                match = re.match(upat, line)
                self.unit_file_state = match.group().split('=')[1]
                continue
            except:
                pass
            try:
                match = re.match(apat, line)
                self.active_state = match.group().split('=')[1]
                continue
            except:
                pass
            try:
                match = re.match(fpat, line)
                self.svc_start_time = match.group().split('=')[1]
                continue
            except:
                pass

    def update_state_toggles(self):
        self.update_service_props()

        # Update toggle buttons according to current states.
        state = True if self.unit_file_state == 'enabled' else False
        self.toggle_unit_state.set_state(state)
        state = True if self.active_state == 'active' else False
        self.toggle_active.set_state(state)

    def update_device_name(self):
        # Get name of managed interface.
        cmd = [
            "systemctl",
            "status",
            "tt-bandwidth-manager.service",
            "--no-pager",
        ]
        status_output = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output_list = status_output.stdout.decode().splitlines()
        label_iface = self.builder.get_object('label_iface')
        for line in output_list:
            pat = '.*\s\/usr\/bin\/tt\s.*'
            try:
                match = re.match(pat, line)
                iface = match.group().split()[-2]
                label_iface.set_text(iface)
                return
            except:
                pass
        label_iface.set_text("--")

    def wait_for_tt_start(self):
        # Wait for a few seconds to give service status time to start.
        # TODO: Is there a better way to verify that tt has started?
        #   if [[ ping -c3 google.com ]]; then wait for tt; else return; fi
        time.sleep(3)


app = TrafficCop()
