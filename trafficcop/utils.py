import contextlib
import locale
import netifaces
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

def get_net_device():
    '''
    Return the gateway internet device.
    If there are multiple gateways found, then the highest priority device is returned:
        1. Bluetooth (AF_BLUETOOTH)
        2. Cellular (AF_PPPOX)
        3. IPv6 (AF_INET6)
        4. IPv4 (AF_INET)
    '''
    gws = netifaces.gateways()
    families = [
        netifaces.AF_BLUETOOTH,
        netifaces.AF_PPPOX,
        netifaces.AF_INET6,
        netifaces.AF_INET,
    ]
    for family in families:
        try:
            device = gws['default'][family][1]
            break
        except KeyError:
            continue
    return device

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
    '''
    Wait for service status to start, otherwise update_service_props()
    '''
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
    '''
    Make a backup of user config; add index to file name if other backup already exists.
    '''
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

def update_global_scope():
    '''
    Update system bandwidth usage for the Global scope.
    '''
    net_io = psutil.net_io_counters(pernic=True)
    dev = get_net_device()
    bytes_up = net_io[dev].bytes_sent
    bytes_dn = net_io[dev].bytes_recv
    return [bytes_up, bytes_dn]

def update_scopes(scopes, queue, store):
    '''
    Retrieve items from nethogs queue and show updated download and upload rates.
    '''
    # Get time of current iteration.
    epoch = time.time()

    # Move current scopes dict's 'new' entries to 'last'.
    for scope in scopes.keys():
        scopes[scope]['last'] = scopes[scope]['now'].copy()

    # Update scopes dict 'new' entries.
    while not queue.empty():
        line = queue.get().split()
        exe_pid_usr = line[0]
        b_up = int(float(line[-2]))
        b_dn = int(float(line[-1]))
        scope = match_cmdline_to_scope(exe_pid_usr, store)
        if not scope:
            # Not matched; will be counted in 'Global'.
            continue
        if scope not in scopes.keys():
            # Initialize scopes[scope].
            scopes[scope] = {
                'last': {
                    'time': None,
                    'bytes_up': None,
                    'bytes_dn': None,
                },
                'now': {}
            }

        # Add epoch time to 'now'.
        scopes[scope]['now']['time'] = epoch
        # Update bytes for current scope.
        scopes[scope]['now']['bytes_up'] = b_up
        scopes[scope]['now']['bytes_dn'] = b_dn

    # Update Global scope.
    b_up = update_global_scope()[0]
    b_dn = update_global_scope()[1]
    if 'Global' not in scopes.keys():
        scopes['Global'] = {
                'last': {
                    'time': None,
                    'bytes_up': None,
                    'bytes_dn': None,
                },
                'now': {}
        }
    scopes['Global']['now']['time'] = epoch
    scopes['Global']['now']['bytes_up'] = b_up
    scopes['Global']['now']['bytes_dn'] = b_dn

    return scopes

def match_cmdline_to_scope(exe_pid_usr, store):
    # Strip pid and user from cmdline.
    cmdline_list = exe_pid_usr.split('/')
    pid = cmdline_list[-2]
    exe = '/'.join(cmdline_list[:-2])

    # Get scope names, match-type, and match-str from store.
    scopes = {}
    for row in store:
        if row[0] == 'Global':
            continue
        scopes[row[0]] = row[11:]

    # Get cmdlines from proces_iter.
    match_exe_pid_usr_and_proc = {}
    proc_list = psutil.process_iter(attrs=['pid', 'name', 'exe', 'cmdline'])
    for proc in proc_list:
        if not proc.cmdline():
            continue
        p_pid = str(proc.pid)
        if p_pid == pid:
            match_exe_pid_usr_and_proc = proc.info
            break

    # Match cmdline with scope.
    scope = None
    if not match_exe_pid_usr_and_proc:
        return None

    for k, v in scopes.items():
        # k = scope; v = [match-type, match-str]
        if v[0] == 'name':
            match = re.match(v[1], match_exe_pid_usr_and_proc['name'])
            if match:
                scope = k
                break
        elif v[0] == 'exe':
            # See if scope exe matches proc exe.
            match = re.match(v[1], match_exe_pid_usr_and_proc['exe'])
            if match:
                scope = k
                break
        elif v[0] == 'cmdline':
            # See if scope cmdline equals proc cmdline.
            if v[1] == match_exe_pid_usr_and_proc['cmdline']:
                scope = k
                break
        else:
            # Unhandled match-type.
            print('no match for', k, ':', v)
            continue
    return scope

def calculate_data_rates(data):
    elapsed = data['now']['time'] - data['last']['time']
    bytes_up = data['now']['bytes_up'] - data['last']['bytes_up']
    bytes_dn = data['now']['bytes_dn'] - data['last']['bytes_dn']
    rate_up = 0
    rate_dn = 0
    if elapsed > 0:
        rate_up = bytes_up / elapsed
        rate_dn = bytes_dn / elapsed
    return [rate_dn, rate_up]
