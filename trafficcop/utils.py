import contextlib
import locale
import os
import psutil
import re
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

def convert_bytes_to_human(bytes_per_sec):
    # "human" means "3 significant digits, changing power as necessary."
    float = bytes_per_sec
    unit = 'B/s'
    if len(str(int(float))) > 3:
        # Switch to KB.
        float = float / 1000
        unit = 'KB/s'
        if len(str(int(float))) > 3:
            # Switch to MB.
            float = float / 1000
            unit = 'MB/s'
            if len(str(int(float))) > 3:
                # Switch to GB.
                float = float / 1000
                unit = 'GB/s'
    return [float, unit]

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

def update_scopes(scopes, queue, store):
    # Get time of current iteration.
    epoch = time.time()

    # Move current scopes dict's 'new' entries to 'last'.
    for scope in scopes.keys():
        scopes[scope]['last'] = scopes[scope]['now'].copy()

    # Update scopes dict 'new' entries.
    while not queue.empty():
        line = queue.get().split()
        cmdline = line[0]
        b_up = int(float(line[-2]))
        b_dn = int(float(line[-1]))
        scope = match_cmdline_to_scope(cmdline, store)
        if scope not in scopes.keys():
            # Initialize scopes[scope].
            scopes[scope] = {
                'last': {
                    'time': None,
                    'bytes_up': None,
                    'bytes_dn': None,
                },
                'now': {
                    'time': epoch,
                    'bytes_up': b_up,
                    'bytes_dn': b_dn,
                }
            }
            continue

        # Add epoch time to 'now'.
        scopes[scope]['now']['time'] = epoch
        # Update bytes for current scope.
        scopes[scope]['now']['bytes_up'] = b_up
        scopes[scope]['now']['bytes_dn'] = b_dn

    return scopes

def match_cmdline_to_scope(cmdline, store):
    # Strip pid and user from cmdline.
    cmdline_list = cmdline.split('/')
    cmdline_pid = cmdline_list[-2]
    exe = '/'.join(cmdline_list[:-2])

    # Get scope names, match-type, and match-str from store.
    scopes = {}
    for row in store:
        if row[0] == 'Global':
            continue
        scopes[row[0]] = row[11:]

    # Get cmdlines from proces_iter.
    match_cmdline_and_proc = {}
    proc_list = psutil.process_iter(attrs=['name', 'exe', 'cmdline'])
    for proc in proc_list:
        if not proc.cmdline():
            continue
        p_cmdline = ' '.join(proc.cmdline())
        p_exe = proc.exe()
        if p_exe == exe:
            match_cmdline_and_proc = proc.info
            break

    # Match cmdline with scope.
    scope = 'Global'
    if not match_cmdline_and_proc:
        return scope

    for k, v in scopes.items():
        # k = scope; v = [match-type, match-str]
        if v[0] == 'name':
            match = re.match(v[1], match_cmdline_and_proc['name'])
            if match:
                scope = k
                break
        elif v[0] == 'exe':
            # See if scope exe matches proc exe.
            match = re.match(v[1], match_cmdline_and_proc['exe'])
            if match:
                scope = k
                break
        elif v[0] == 'cmdline':
            # See if scope cmdline equals proc cmdline.
            if v[1] == match_cmdline_and_proc['cmdline']:
                scope = k
                break
        else:
            # Unhandled match-type.
            print('no match for', k, ':', v)
            continue
    return scope

def calculate_scope_data_usage(scope, data):
    elapsed = data['now']['time'] - data['last']['time']
    bytes_up = data['now']['bytes_up'] - data['last']['bytes_up']
    bytes_dn = data['now']['bytes_dn'] - data['last']['bytes_dn']
    rate_up = 0
    rate_dn = 0
    if elapsed > 0:
        rate_up = bytes_up / elapsed
        rate_dn = bytes_dn / elapsed
    return [rate_dn, rate_up]
