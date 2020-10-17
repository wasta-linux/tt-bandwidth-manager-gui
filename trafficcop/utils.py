import contextlib
import locale
import os
import psutil
import shutil
import subprocess
import time


@contextlib.contextmanager
def setlocale(*args, **kw):
    saved = locale.setlocale(locale.LC_ALL)
    yield locale.setlocale(*args, **kw)
    locale.setlocale(locale.LC_ALL, saved)

def mute(func, *args, **kwargs):
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stdout(devnull):
            output = func(*args, **kwargs)
    return output

def convert_epoch_to_human(epoch):
    human = time.ctime(epoch)
    return human

def convert_human_to_epoch(human):
    if human:
        with setlocale(locale.LC_TIME, "C"):
            try:
                str = time.strptime(human, '%a %b %d %H:%M:%S %Y') # Tue Oct 13 05:59:00 2020
                # Convert object to epoch format.
                epoch = time.mktime(str) # Tue 2020-10-13 05:59:00 WAT
            except ValueError as v:
                print(repr(v))
                epoch = ''
            except Exception as e:
                print(repr(e))
                epoch = ''
    else:
        epoch = human
    return epoch

def convert_human_to_log(human):
    # Convert human to object.
    #   Doesn't work: prob b/c my locale is FR but human is reported in EN.
    with setlocale(locale.LC_TIME, "C"):
        str = time.strptime(human, '%a %b %d %H:%M:%S %Y') # Tue Oct 13 05:59:00 2020
        # Convert object to log format.
        log = time.strftime('%a %Y-%m-%d %H:%M%S %Z', str) # Tue 2020-10-13 05:59:00 WAT
        return log

def get_tt_info(exe='/usr/bin/tt'):
    procs = psutil.process_iter()
    for proc in procs:
        try:
            if exe in proc.cmdline():
                proc.start = convert_epoch_to_human(proc.create_time())
                return proc.pid, proc.start
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return -1, ""

def get_file_mtime(file):
    statinfo = os.stat(file)
    mtime = convert_epoch_to_human(statinfo.st_mtime)
    return mtime

def wait_for_tt_start(exe='/usr/bin/tt', max=100):
    # Wait for service status to start, otherwise update_service_props()
    #   may not get the correct info.
    ct = 0
    # Initially assume that tt is not running.
    tt_pid, tt_start = -1, ''
    while ct < max:
        tt_pid, tt_start = get_tt_info(exe)
        if psutil.pid_exists(tt_pid):
            return tt_pid, tt_start
        time.sleep(0.1)
        ct += 1
    return tt_pid, tt_start

def check_diff(file1, file2):
    result = subprocess.run(
        ["diff", file1, file2],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return result.returncode

def ensure_config_backup(current):
    # Make a backup of user config; add index to file name if other backup already exists.
    already = "Current config already backed up at"
    name = current.stem
    suffix = ".yaml.bak"
    backup = current.with_suffix(suffix)
    if not backup.exists():
        shutil.copyfile(current, backup)
        return True
    diff = check_diff(current, backup)
    if diff == 0:
        print(already, backup)
        return True
    # The backup file exists and is different from current config:
    #   need to choose new backup file name and check again.
    # Add index to name.
    i = 1
    # Set new backup file name.
    backup = current.with_name(name + '-' + str(i)).with_suffix(suffix)
    if not backup.exists():
        shutil.copyfile(current, backup)
        return True
    diff = check_diff(current, backup)
    if diff == 0:
        print(already, backup)
        return True
    while backup.exists():
        # Keep trying new indices until an available one is found.
        i += 1
        backup = current.with_name(name + '-' + str(i)).with_suffix(suffix)
        if not backup.exists():
            shutil.copyfile(current, backup)
            return True
        diff = check_diff(current, backup)
        if diff == 0:
            print(already, backup)
            return True
