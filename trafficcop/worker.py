""" Functions that run in background threads. """
# All of these functions run inside of threads and use GLib to communicate back.

#import gi
import subprocess

#from gi.repository import Gdk, GLib, Gtk
#gi.require_version("Gtk", "3.0")
from pathlib import Path

from trafficcop import app


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
