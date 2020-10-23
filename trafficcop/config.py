import gi
import yaml

gi.require_version("Gtk", "3.0")
#from gi.repository import Gio
#from gi.repository import GLib
from gi.repository import Gtk

from trafficcop import app


def create_config_treeview(store):
    tree = Gtk.TreeView(model=store)
    r_name = Gtk.CellRendererText()
    r_name.set_alignment(0.0, 0.0)
    rend_str = Gtk.CellRendererText()
    rend_str.set_alignment(0.5, 0.0)
    r_int = Gtk.CellRendererText()
    r_int.set_alignment(0.5, 0.0)
    r_float = Gtk.CellRendererText()
    r_float.set_alignment(1.0, 0.0)
    c_name = Gtk.TreeViewColumn("Process", r_name, text=0)
    c_dn_max = Gtk.TreeViewColumn("Max Down", rend_str, text=1)
    c_up_max = Gtk.TreeViewColumn("Max Up", rend_str, text=2)
    c_dn_min = Gtk.TreeViewColumn("Min Down", rend_str, text=3)
    c_up_min = Gtk.TreeViewColumn("Min Up", rend_str, text=4)
    c_dn_pri = Gtk.TreeViewColumn("Pri. Down", r_int, text=5)
    c_up_pri = Gtk.TreeViewColumn("Pri. Up", r_int, text=6)
    c_dn_rt = Gtk.TreeViewColumn("Rate Down", r_float, text=7)
    c_dn_u = Gtk.TreeViewColumn("", r_name, text=8)
    c_dn_u.set_fixed_width(40)
    c_up_rt = Gtk.TreeViewColumn("Rate Up", r_float, text=9)
    c_up_u = Gtk.TreeViewColumn("", r_name, text=10)
    c_up_u.set_fixed_width(40)
    tree.append_column(c_name)
    c_list = [c_dn_max, c_up_max, c_dn_min, c_up_min, c_dn_pri, c_up_pri]
    for c in c_list:
        c.set_alignment(0.5)
        c.set_expand(True)
        tree.append_column(c)
    tree.append_column(c_dn_rt)
    tree.append_column(c_dn_u)
    tree.append_column(c_up_rt)
    tree.append_column(c_up_u)
    return tree

def update_config_store(store, new_store):
    # Delete all existing rows.
    for row in store:
        store.remove(row.iter)
    # Add new rows.
    for row in new_store:
        store.append(row[:])
    return store

def update_store_rates(store, dict):
    for row in store:
        for scope, values in dict.items():
            if row[0] == scope:
                if scope == 'Global':
                    row[7] = ' '*4
                    row[8] = ' '*4
                    row[9] = ' '*4
                    row[10] = ' '*4
                if values[0] <= 0:
                    row[7] = ' '*4
                    row[8] = ' '*4
                else:
                    row[7] = '{:.2f}'.format(values[0])
                    row[8] = values[1]
                if values[2] <= 0:
                    row[9] = ' '*4
                    row[10] = ' '*4
                else:
                    row[9] = '{:.2f}'.format(values[2])
                    row[10] = values[3]
                break

def convert_dict_to_list(k, v_dict):
    if not type(v_dict) == dict:
        # Scope (Global or Process) not given valid config.
        v_dict = {}
    name = k
    try:
        dn_max = v_dict['download']
    except KeyError:
        dn_max = ''
    try:
        up_max = v_dict['upload']
    except KeyError:
        up_max = ''
    try:
        dn_min = v_dict['download-minimum']
    except KeyError:
        dn_min = ''
    try:
        up_min = v_dict['upload-minimum']
    except KeyError:
        up_min = ''
    try:
        dn_pri = v_dict['download-priority']
    except KeyError:
        dn_pri = 9
    try:
        up_pri = v_dict['upload-priority']
    except KeyError:
        up_pri = 9
    # The match section can theoretically be any of the attributes that
    #   psutil.process exposes. This could get really complicated. Just going to
    #   support 'name', 'exe', and 'cmdline'. Others seem less useful.
    # List of possible attributes:
    #   https://psutil.readthedocs.io/en/latest/index.html#psutil.Process.as_dict
    dn_rate = ' '*4 #'{:.2f}'.format(0)
    dn_unit = ' '*4 #'B/s'
    up_rate = ' '*4 #'{:.2f}'.format(0)
    up_unit = ' '*4 #'B/s'
    try:
        m_type = 'name'
        m_str = v_dict['match'][0][m_type]
    except KeyError:
        try:
            m_type = 'exe'
            m_str = v_dict['match'][0][m_type]
        except KeyError:
            try:
                m_type = 'cmdline'
                m_str = m_str = v_dict['match'][0][m_type]
            except:
                m_str = ''
                m_type = ''

    list = [
        name,
        dn_max, up_max,
        dn_min, up_min,
        int(dn_pri), int(up_pri),
        dn_rate, dn_unit,
        up_rate, up_unit,
        m_type, m_str
    ]
    return list

def convert_yaml_to_store(file):
    # Get dict from yaml file.
    with open(file, 'r') as stream:
        try:
            content = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print(e)
            return ''

    if not content:
        # Yaml file has no viable content.
        print("ERROR: {} has no usable content.".format(file))
        return ''

    # Create a new "flat" dict to hold the config.
    config_dict = {}
    # Move global config keys down into their own dict under a 'Global' key.
    g_name = 'Global'
    g_config = convert_dict_to_list(g_name, content)
    config_dict[g_name] = {
        'download': g_config[1],
        'upload': g_config[2],
        'download-minimum': g_config[3],
        'upload-minimum': g_config[4],
        'download-priority': g_config[5],
        'upload-priority': g_config[6],
        'match-type': g_config[7],
        'match-str': g_config[8],
    }

    # Move process config keys up to the main dict.
    for p_name, p in content['processes'].items():
        config_dict[p_name] = p

    # Convert dict to a list store.
    store = Gtk.ListStore(str, str, str, str, str, int, int, str, str, str, str, str, str)
    for k, v in config_dict.items():
        l = convert_dict_to_list(k, v)
        l_iter = store.append(l)
    return store
