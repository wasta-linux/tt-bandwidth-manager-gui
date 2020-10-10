import psutil
import shutil
import subprocess
import time

def get_tt_pid():
    exe = '/usr/bin/tt'
    procs = psutil.process_iter()
    for proc in procs:
        try:
            if exe in proc.cmdline():
                return proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return -1

def wait_for_tt_start():
    # Wait for service status to start, otherwise update_service_props()
    #   may not get the correct info.
    ct = 0
    while ct < 100:
        tt_pid = get_tt_pid()
        if psutil.pid_exists(tt_pid):
            return tt_pid
        time.sleep(0.1)
        ct += 1
    return tt_pid

def check_diff(file1, file2):
    result = subprocess.run(
        ["diff", file1, file2],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return result.returncode

def ensure_config_backup(current, default):
    # Make a backup of user config; add index to file name if other backup already exists.
    already = "Current config already backed up at"
    name = current.stem
    suffix = ".yaml.bak"
    backup = current.with_suffix(suffix)
    if not backup.exists():
        shutil.copyfile(current, backup)
        return
    diff = check_diff(current, backup)
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
    diff = check_diff(current, backup)
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
        diff = check_diff(current, backup)
        if diff == 0:
            print(already, backup)
            return
