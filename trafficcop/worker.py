""" Functions that run in background threads. """
# All of these functions run inside of threads and use GLib to communicate back.

import gi
import subprocess
import time

#from pathlib import Path
from gi.repository import Gdk, GLib, Gtk
gi.require_version("Gtk", "3.0")
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
        #"&"
    ]
    cmd_txt = " ".join(cmd)
    subprocess.run(cmd_txt, shell=True)

def handle_button_config_clicked():
    cmd = [
        "gedit",
        "/etc/tt-config.yaml",
    ]
    subprocess.run(cmd)

    # set_sensitive doesn't disable user clicking on buttons in this case.
    #for b in app.app.buttons:
    #    GLib.idle_add(b.set_sensitive, False)
    # Neither subprocess.run nor os.system open the file as writeable.

    #os.system(" ".join(cmd))
    #filename = "/etc/tt-config.yaml"
    #with open(filename, "w") as file:
    #    data = file.read()
    #    print(data)

    #for b in app.app.buttons:
    #    GLib.idle_add(b.set_sensitive, True)

    return

def handle_config_changed():
    config_file = Path("/etc/tt-config.yaml")
    mod_time_epoch = config_file.stat().st_mtime
    #mod_time_obj = time.localtime(mod_time_epoch)
    #mod_time = time.strftime("%a %Y-%m-%d %H:%M:%S %Z", mod_time_obj)
    read_time = app.app.svc_start_time
    print("Service Start Time =", read_time)
    print("Config file mod. time =", mod_time_epoch)
    '''
    text = ''
    # Clear the label text if not empty.
    GLib.idle_add(label.set_text, text)
    if is_activated:
        #text = 'Checking the Snap Store...'
        #GLib.idle_add(wsmapp.app.label_button_source_online.set_text, text)
        GLib.idle_add(label.hide)
        GLib.idle_add(grid.attach, spinner, 2, 0, 1, 1)
        GLib.idle_add(spinner.show)
        GLib.idle_add(spinner.start)
        if util.snap_store_accessible():
            text = ''
            wsmapp.app.updatable_online_list = util.get_snap_refresh_list()
            wsmapp.app.updatable_online_dict = util.get_snap_refresh_dict()
            wsmapp.app.select_online_update_rows()
        else:
            text = 'No connection to the Snap Store.'
            wsmapp.app.button_source_online.set_active(False)
        GLib.idle_add(spinner.stop)
        GLib.idle_add(spinner.hide)
        GLib.idle_add(label.show)
    else:
        text = ''
        wsmapp.app.deselect_online_update_rows()

    GLib.idle_add(label.set_text, text)
    return
    '''
