""" Main GUI module. """

import gi
import gzip
import logging
import os
import psutil
import queue
import re
import shutil
import subprocess
import threading
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
from trafficcop import worker


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
        self.tt_pid, self.tt_start, self.tt_dev = utils.get_tt_info()
        self.config_file = Path('/etc/tt-config.yaml')
        self.default_config = Path("/usr/share/tt-bandwidth-manager/tt-default-config.yaml")
        self.config_store = ''
        self.net_hogs_q = queue.Queue()
        self.main_pid = os.getpid()
        self.managed_ports = {}
        self.scopes = {}

    def do_startup(self):
        '''
        do_startup is the setting up of the app, either for "activate" or for "open".
        It runs just after __init__.
        '''
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
        self.button_apply = self.builder.get_object('button_apply')
        self.button_config = self.builder.get_object('button_config')
        self.button_reset = self.builder.get_object('button_reset')
        self.w_config = self.builder.get_object('w_config')
        self.vp_config = self.builder.get_object('vp_config')

        # Main window.
        self.add_window(self.window)
        self.window.set_icon_name('traffic-cop')

        # Populate config viewport.
        self.treeview_config = self.update_treeview_config()
        self.treeview_config.show()
        self.vp_config.add(self.treeview_config)

        # Populate widget data.
        self.button_apply.set_sensitive(False)

        # Connect GUI signals to Handler class.
        self.builder.connect_signals(handler.Handler())

    def do_command_line(self, command_line):
        '''
        do_command_line runs after do_startup and before do_activate.
        '''
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
            print(f"Traffic Cop (app) / tt-bandwidth-manager-gui (package): {version}")
            exit(0)

    def do_activate(self):
        '''
        do_activate is the displaying of the window. It runs last after do_command_line.
        '''
        # Verify execution with elevated privileges.
        if os.geteuid() != 0:
            self.args.insert(0, 'pkexec')
            subprocess.run(self.args)
            exit()

        # Update widgets and show window.
        self.update_info_widgets()
        self.window.show()

        # Start tracking operations (self.window must be shown first).
        target = worker.parse_nethogs_to_queue
        args = self.net_hogs_q, self.window
        t_nethogs = threading.Thread(target=target, args=args, name='T-nh')
        t_nethogs.start()

        # Start bandwidth rate updater.
        t_bw_updater = threading.Thread(target=worker.bw_updater, name='T-bw')
        t_bw_updater.start()

        # Verify execution with elevated privileges.
        if os.geteuid() != 0:
            bin = '/usr/bin/traffic-cop'
            print("traffic-cop needs elevated privileges; e.g.:\n\n$ pkexec", bin, "\n$ sudo", bin)
            exit(1)

    def update_service_props(self):
        # Get true service start time.
        self.tt_pid, self.tt_start, self.tt_dev = utils.get_tt_info()

        # Get state of systemd service.
        cmd = [
            "systemctl",
            "show",
            "tt-bandwidth-manager.service",
            "--no-pager",
        ]
        status_output = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        utils.print_result(cmd, status_output)
        if status_output.returncode != 0:
            # Status output error. Probably due to kernel incompatibility after update.
            #   Fall back to trying "systemctl status" command instead.
            self.unit_file_state = 'unknown'
            self.active_state = 'unknown'
            self.svc_start_time = 'unknown'
            cmd.pop(1)
            cmd.insert(1, "status")
            status_output = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            utils.print_result(cmd, status_output)
            output_list = status_output.stdout.decode().splitlines()
            #print(output_list)
            upat = '\s+Loaded: loaded \(/etc/systemd/system/tt-bandwidth-manager.service; (.*);.*'
            apat = '\s+Active: (.*) since .*'
            for line in output_list:
                try:
                    match = re.match(upat, line)
                    self.unit_file_state = match.group(1)
                except:
                    pass
                try:
                    match = re.match(apat, line)
                    self.active_state = match.group(1).split()[0]
                except:
                    pass

        # Continue with processing of "systemctl show" command output.
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
        pid, time, dev = utils.get_tt_info()
        if pid > 0:
            self.label_iface.set_text(dev)
        else:
            self.label_iface.set_text("--")

    def update_config_time(self):
        self.label_applied.set_text(self.tt_start)

    def update_button_states(self):
        # TODO: I need a way to "watch" the config file if setting the "Apply"
        #   button to "sensitive" is ever going to work.
        # Update "Apply" button to be insensitive.
        #self.button_apply.set_sensitive(False)
        # Update "Reset..." button to be insensitive.
        self.button_reset.set_sensitive(False)

        # Set "Apply" button to proper state.
        #config_mtime = utils.get_file_mtime(self.config_file)
        #if self.tt_start and config_mtime > self.tt_start:
            # Update "Apply" button to be sensitive.
            #self.button_apply.set_sensitive(True)

        # Set "Reset..." button to proper state.
        diff_configs = utils.check_diff(self.config_file, self.default_config)
        if not diff_configs == 0:
            # Update "Reset..." button to be sensitive.
            self.button_reset.set_sensitive(True)

    def update_treeview_config(self):
        '''
        This handles both initial config display and updating the display if the
        config file is edited externally.
        '''
        if not self.config_store:
            # App is just starting up; create the store.
            self.config_store = config.convert_yaml_to_store(self.config_file)

        if self.tt_start:
            # Service is running.
            # Check if modified time of config file is newer than last service restart.
            #   The config could have been externally modified. If so, those
            #   changes could be shown here in the app without them actually having
            #   been applied.
            config_mtime = utils.get_file_mtime(self.config_file)
            config_epoch = utils.convert_human_to_epoch(config_mtime)
            tt_epoch = utils.convert_human_to_epoch(self.tt_start)
            if config_epoch > tt_epoch:
                print("WARNING: The config file has been modified since the service started.\nApplying the changes now.")
                self.restart_service()
            else:
                new_config_store = config.convert_yaml_to_store(self.config_file)
                self.config_store = config.update_config_store(self.config_store, new_config_store)

        treeview_config = config.create_config_treeview(self.config_store)
        return treeview_config

    def update_info_widgets(self):
        self.update_service_props()
        self.update_state_toggles()
        self.update_device_name()
        self.update_config_time()
        self.update_button_states()

    def stop_service(self):
        cmd = ["systemctl", "stop", "tt-bandwidth-manager.service"]
        result = subprocess.run(cmd)
        utils.print_result(cmd, result)
        self.update_info_widgets()

    def start_service(self):
        cmd = ["systemctl", "start", "tt-bandwidth-manager.service"]
        result = subprocess.run(cmd)
        utils.print_result(cmd, result)
        self.tt_pid, self.tt_start, self.tt_dev = utils.wait_for_tt_start()
        self.update_info_widgets()
        self.treeview_config = self.update_treeview_config()

    def restart_service(self):
        cmd = ["systemctl", "restart", "tt-bandwidth-manager.service"]
        result = subprocess.run(cmd)
        utils.print_result(cmd, result)
        self.tt_pid, self.tt_start, self.tt_dev = utils.wait_for_tt_start()
        # Check service status and update widgets.
        self.update_info_widgets()
        self.treeview_config = self.update_treeview_config()

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
