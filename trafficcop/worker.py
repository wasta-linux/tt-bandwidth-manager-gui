""" Functions that run in background threads. """
# All of these functions run inside of threads and use GLib to communicate back.

#import gi
import psutil
import subprocess
import sys
import time

#from gi.repository import Gdk, GLib, Gtk
#gi.require_version("Gtk", "3.0")
from pathlib import Path

from trafficcop import app
from trafficcop import config
from trafficcop import utils


def handle_button_log_clicked():
    # Follow the log since service start time in a terminal window.
    cmd = [
        "gnome-terminal",
        "--geometry=144x24+100+200",
        "--",
        "journalctl",
        "--unit=tt-bandwidth-manager.service",
        "--follow",
        "--output=cat",
        "--no-pager",
        "--since=\'" + app.app.svc_start_time + "\'",
        #"--since=\'" + app.app.tt_start + "\'", # this doesn't work
    ]
    cmd_txt = " ".join(cmd)
    subprocess.run(cmd_txt, shell=True)
    return

def handle_button_config_clicked():
    cmd = [
        "gedit",
        "/etc/tt-config.yaml",
    ]
    subprocess.run(cmd)
    return

def handle_config_changed():
    pass
    #app.app.update_service_props()
    #read_time = app.app.tt_start
    #print("Service Start Time =", read_time)

def parse_nethogs_to_queue(queue, main_window):
    delay = 1
    cmd = ['nethogs', '-t', '-v2', '-d' + str(delay)]
    stdout = subprocess.PIPE
    stderr = subprocess.STDOUT
    with subprocess.Popen(cmd, stdout=stdout, stderr=stderr, encoding='utf-8') as p:
        while main_window.is_visible():
            # There is a long wait for each line: sometimes nearly 2 seconds!
            line = p.stdout.readline()
            if line[0] == '/':
                queue.put(line)
            elif line == '' and p.poll() is not None:
                # Process completed. (Shouldn't happen.)
                break

def bw_updater():
    while app.app.window.is_visible():
        time.sleep(1.5)
        # Get all applicable cmdlines & bytes transferred for each scope in config.
        # Sum the total sent for each scope, as well as the total received and give it a timestamp.
        app.app.scopes = utils.update_scopes(app.app.scopes, app.app.net_hogs_q, app.app.config_store)

        # Get the upload and download rates (B/s).
        rates_dict = {}
        for scope, data in app.app.scopes.items():
            #if scope == 'Global':
            #    continue
            if not data['last']['time']:
                continue
            rates = utils.calculate_scope_data_usage(scope, data)

            # Adjust the number to only show 3 sig. digits; change units as necessary (KB/s, MB/s, GB/s).
            human_up = utils.convert_bytes_to_human(rates[0])
            human_dn = utils.convert_bytes_to_human(rates[1])
            rates_dict[scope] = [*human_up, *human_dn]

        # Update the values shown in the treeview.
        config.update_store_rates(app.app.config_store, rates_dict)
