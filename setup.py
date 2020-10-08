# https://docs.python.org/3/distutils/setupscript.html

import glob
from distutils.core import setup

setup(
    name='Traffic Cop',
    version='0.1.0',
    description="Manage bandwidth usage by app or process.",
    author="Nate Marti",
    author_email="nate_marti@sil.org",
    url="https://github.com/wasta-linux/tt-bandwidth-manager-gui",
    packages=['trafficcop'],
    package_data={'trafficcop': ['README.md']},
    scripts=['bin/traffic-cop'],
    data_files=[
        ('share/polkit-1/actions', glob.glob('data/actions/*')),
        ('share/icons/hicolor/scalable/apps', glob.glob('data/icons/*.svg')),
        ('share/traffic-cop/ui', glob.glob('data/ui/*.glade')),
        ('share/applications', glob.glob('data/*.desktop')),
    ]
)
