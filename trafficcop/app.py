""" Main GUI module. """

import gi
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
        self.ui_dir = '/usr/share/traffic-cop/ui'
        if str(current_file_path.parents[1]) != '/usr/lib/python3/dist-packages':
            self.ui_dir = str(current_file_path.parents[1] / 'data' / 'ui')

        # Define app-wide variables.
        self.runmode = ''
        self.tt_pid = self.get_tt_pid()

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


        # Get the time when the service was last started.
        #self.update_service_props()

    def do_activate(self):
        # Verify execution with elevated privileges.
        #if os.geteuid() != 0:
        #    bin = '/usr/bin/wasta-bandwidth-manager'
        #    print("wasta-bandwidth-manager needs elevated privileges; e.g.:\n\n$ pkexec", bin, "\n$ sudo", bin)
        #    exit(1)
        self.update_service_props()

        # Populate widget data.
        self.update_state_toggles()
        self.update_device_name()
        self.update_config_time()

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
            proc = psutil.Process(pid)
            iface = proc.cmdline()[2]
            self.label_iface.set_text(iface)

    def update_config_time(self):
        self.label_applied.set_text(self.svc_start_time)

    def update_info_widgets(self):
        self.update_service_props()
        self.update_state_toggles()
        self.update_device_name()
        self.update_config_time()

    def get_tt_pid(self):
        exe = '/usr/bin/tt'
        procs = psutil.process_iter()
        for proc in procs:
            try:
                if exe in proc.cmdline():
                    return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return -1

    def wait_for_tt_start(self):
        # Wait for service status to start, otherwise update_service_props()
        #   may not get the correct info.
        ct = 0
        while ct < 100:
            self.tt_pid = self.get_tt_pid()
            if psutil.pid_exists(self.tt_pid):
                return
            time.sleep(0.1)
            ct += 1
        return

    def stop_service(self):
        cmd = ["systemctl", "stop", "tt-bandwidth-manager.service"]
        subprocess.run(cmd)
        self.update_info_widgets()

    def start_service(self):
        cmd = ["systemctl", "start", "tt-bandwidth-manager.service"]
        subprocess.run(cmd)
        self.wait_for_tt_start()
        self.update_info_widgets()

    def restart_service(self):
        cmd = ["systemctl", "restart", "tt-bandwidth-manager.service"]
        subprocess.run(cmd)
        self.wait_for_tt_start()
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

    def check_diff(self, file1, file2):
        result = subprocess.run(
            ["diff", file1, file2],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode

    def ensure_config_backup(self, current, default):
        # Make a backup of user config; add index to file name if other backup already exists.
        already = "Current config already backed up at"
        name = current.stem
        suffix = ".yaml.bak"
        backup = current.with_suffix(suffix)
        if not backup.exists():
            shutil.copyfile(current, backup)
            return
        diff = self.check_diff(current, backup)
        if diff == 0:
            print(already, backup)
            return
        # The backup file exists and is different from current config:
        #   need to choose new backup file name and check again.
        # Add index to name.
        i = 1
        # Set new backup file name.
        backup = current.with_name(name + '-' + str(i)).with_suffix(suffix)
        if not backup.exists():
            shutil.copyfile(current, backup)
            return
        diff = self.check_diff(current, backup)
        if diff == 0:
            print(already, backup)
            return
        while backup.exists():
            # Keep trying new indices until an available one is found.
            i += 1
            backup = current.with_name(name + '-' + str(i)).with_suffix(suffix)
            if not backup.exists():
                shutil.copyfile(current, backup)
                return
            diff = self.check_diff(current, backup)
            if diff == 0:
                print(already, backup)
                return


app = TrafficCop()
