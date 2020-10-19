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
    cmd = ['nethogs', '-t', '-v2']
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, encoding='utf-8') as p:
        while main_window.is_visible() == True:
            try:
                line = p.stdout.readline()
                if line == '' and p.poll() is not None:
                    # Process completed. (Shouldn't happen.)
                    break
                elif line[0] == '/':
                    parts = line.split()
                    epoch = time.time()
                    parts.insert(0, epoch)
                    queue.put(parts)
            except KeyboardInterrupt:
                break

def print_queue_items(queue, main_window):
    while main_window.is_visible() == True:
        if not queue.empty():
            item = queue.get()
            print(item)
        else:
            time.sleep(1)
        time.sleep(2)

def list_ports_per_process(dict, main_window):
    # "scope" is "Global" or one of the "Names" given by the user.
    # "Shaping traffic for 'Name' on local ports [port], [port], ..."
    lines = '100'
    cmd = [
        'journalctl',
        '--lines=' + lines,
        '--unit=tt-bandwidth-manager.service',
        '--output=cat',
        '--no-pager',
    ]
    while main_window.is_visible() == True:
        output = subprocess.run(cmd, stdout=subprocess.PIPE, encoding='utf-8')
        lines = output.stdout.splitlines()
        # Example line:
        # 0          1            2 3        4 5                        6 7       8       9   10      11 12    13    14
        # 2020-10-19 16:10:15.116 | INFO     | traffictoll.cli:main:344 - Shaping traffic for 'Skype' on local ports 60362, 60364
        for line in lines:
            l = line.split()
            if len(l) < 11:
                continue
            name = l[10][1:-1] # remove quotes from item 10
            if l[7] == 'Removing':
                # l[14] is first port number.
                for i in l[14:]:
                    i = i.rstrip(',') # strip commas if multiple ports are listed
                    try:
                        dict[name].remove(i)
                    except (KeyError, ValueError):
                        # name not in dict or port not already in list.
                        pass
            elif l[7] == 'Shaping':
                to_add = []
                for i in l[14:]:
                    i = i.rstrip(',')
                    to_add.append(i)
                try:
                    dict[name].extend(to_add)
                    dict[name] = list(set(dict[name])) # set removes duplicates
                except KeyError:
                    # No known ports yet for name.
                    dict[name] = list(set(to_add))
        time.sleep(0.5)
