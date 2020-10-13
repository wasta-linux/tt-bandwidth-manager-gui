""" Main GUI module. """

import gi
import gzip
import logging
import os
import psutil
import re
import shutil
import subprocess
import time

from pathlib import Path
current_file_path = Path(__file__)

gi.require_version("Gtk", "3.0")
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from trafficcop import config
from trafficcop import handler
from trafficcop import utils


class TrafficCop(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id='org.wasta.apps.traffic-cop',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )

        # Add CLI options.
        self.add_main_option(
            'version', ord('V'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            'Print version number', None
        )

        # Get UI location based on current file location.
        self.ui_dir = '/usr/share/traffic-cop/ui'
        if str(current_file_path.parents[1]) != '/usr/lib/python3/dist-packages':
            self.ui_dir = str(current_file_path.parents[1] / 'data' / 'ui')

        # Define app-wide variables.
        self.tt_pid, self.tt_start = utils.get_tt_info()
        self.config_file = Path('/etc/tt-config.yaml')
        self.config_store = ''

    def do_startup(self):
        # Define builder and its widgets.
        Gtk.Application.do_startup(self)

        # Get widgets from glade file, which is defined in __init__.
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.ui_dir + '/mainwindow.glade')
        self.window = self.builder.get_object('mainwindow')
        self.toggle_active = self.builder.get_object('toggle_active')
        self.toggle_unit_state = self.builder.get_object('toggle_unit_state')
        self.button_restart = self.builder.get_object('button_restart')
        self.label_iface = self.builder.get_object('label_iface')
        self.button_log = self.builder.get_object('button_log')
        self.label_applied = self.builder.get_object('label_applied')
        self.button_applied = self.builder.get_object('button_applied')
        self.button_config = self.builder.get_object('button_config')
        self.button_reset = self.builder.get_object('button_reset')
        self.w_config = self.builder.get_object('w_config')
        self.vp_config = self.builder.get_object('vp_config')

    def do_activate(self):
        # Verify execution with elevated privileges.
        if os.geteuid() != 0:
            bin = '/usr/bin/traffic-cop'
            print("\ntraffic-cop needs elevated privileges; e.g.:\n\n$ pkexec", bin, "\n$ sudo", bin)
            exit(1)

        self.update_service_props()

        # Populate widget data.
        self.update_state_toggles()
        self.update_device_name()
        self.update_config_time()

        # Configure and show window.
        self.add_window(self.window)
        self.window.set_icon_name('traffic-cop')
        self.window.show()

        # Populate config viewport.
        self.treeview_config = self.update_treeview_config()
        self.treeview_config.show()
        self.vp_config.add(self.treeview_config)


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
            # Get version number from debian/changelog.
            if self.runmode == 'uninstalled':
                changelog = Path(__file__).parents[1] / 'debian' / 'changelog'
                with open(changelog) as f:
                    first_line = f.readline()
            else:
                changelog = Path('/usr/share/doc/tt-bandwidth-manager-gui/changelog.gz')
                with gzip.open(changelog) as f:
                    first_line = f.readline().strip().decode()
            # 2nd term in 1st line of changelog; also need to remove parentheses.
            version = first_line.split()[1][1:-1]
            print("\ntt-bandwidth-manager-gui", version)
            return 0

        # Verify execution with elevated privileges.
        if os.geteuid() != 0:
            bin = '/usr/bin/traffic-cop'
            print("\ntraffic-cop needs elevated privileges; e.g.:\n\n$ pkexec", bin, "\n$ sudo", bin)
            exit(1)

    def update_service_props(self):
        # Get true service start time.
        self.tt_pid, self.tt_start = utils.get_tt_info()

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
        tpat = '^ExecMainStartTimestamp=.*$'
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
                match = re.match(tpat, line)
                # The format for self.tt_start (Tue Oct 13 06:15:14 2020) isn't
                #   compatible with the log file viewer. (Tue 2020-10-13 05:59:00 WAT)
                self.svc_start_time = match.group().split('=')[1]
                continue
            except:
                pass

    def update_state_toggles(self):
        # Update toggle buttons according to current states.
        state = True if self.unit_file_state == 'enabled' else False
        self.toggle_unit_state.set_state(state)
        state = True if self.active_state == 'active' else False
        self.toggle_active.set_state(state)

    def update_device_name(self):
        # Get name of managed interface.
        self.label_iface.set_text("--")
        if psutil.pid_exists(self.tt_pid):
            proc = psutil.Process(self.tt_pid)
            iface = proc.cmdline()[2]
            self.label_iface.set_text(iface)

    def update_config_time(self):
        self.label_applied.set_text(self.tt_start)

    def update_treeview_config(self):
        '''
        This handles both initial config display and updating the display if the
        config file is edited externally.
        '''
        new_config_store = config.convert_yaml_to_store(self.config_file)
        if not self.config_store:
            # Check if modified time of config file is newer than last service restart.
            #   The config could have been externally modified. If so, those
            #   changes could be shown here in the app without them actually having
            #   been applied.
            config_mtime = utils.get_file_mtime(self.config_file)
            if config_mtime > self.tt_start:
                print("WARNING: The config file has been externally modified. Applying the changes now.")
                self.restart_service()
            # Define store.
            self.config_store = new_config_store
        else:
            # Update store from the config file.
            self.config_store = config.update_config_store(self.config_store, new_config_store)
        self.treeview_config = config.create_config_treeview(self.config_store)
        return self.treeview_config

    def update_info_widgets(self):
        self.update_service_props()
        self.update_state_toggles()
        self.update_device_name()
        self.update_config_time()
        self.update_treeview_config()

    def stop_service(self):
        cmd = ["systemctl", "stop", "tt-bandwidth-manager.service"]
        subprocess.run(cmd)
        self.update_info_widgets()

    def start_service(self):
        cmd = ["systemctl", "start", "tt-bandwidth-manager.service"]
        subprocess.run(cmd)
        self.tt_pid, self.tt_start = utils.wait_for_tt_start()
        self.update_info_widgets()

    def restart_service(self):
        cmd = ["systemctl", "restart", "tt-bandwidth-manager.service"]
        subprocess.run(cmd)
        self.tt_pid, self.tt_start = utils.wait_for_tt_start()
        # Check service status and update widgets.
        self.update_info_widgets()

    def get_user_confirmation(self):
        text = "The current configuration file will be backed up first."
        label = Gtk.Label(text)
        dialog = Gtk.Dialog(
            'Reset to default configuration?',
            self.window,
            None, #Gtk.Dialog.DESTROY_WITH_PARENT,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        )
        hmarg = 80
        vmarg = 20
        dialog.vbox.set_margin_top(vmarg)
        dialog.vbox.set_margin_bottom(vmarg)
        dialog.vbox.set_margin_start(hmarg)
        dialog.vbox.set_margin_end(hmarg)
        dialog.vbox.set_spacing(20)
        dialog.vbox.pack_start(label, True, True, 5)
        label.show()
        response = dialog.run()
        # CLOSE: -4, OK: -5, CANCEL: -6
        dialog.destroy()
        if response == -5:
            return True
        else:
            return False


app = TrafficCop()
