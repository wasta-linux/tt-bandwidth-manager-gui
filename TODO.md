### Planned features
- [x] Show current config in app window.
- [ ] Develop a decent test suite.
- [ ] Show bandwidth used by currently configured processes.
  - run nethogs -t, outputting to a tempfile
  - match process name from nethogs with process being managed by tt
  - ALSO:
    - netstat can tie ports to pids and process names:
    - sudo netstat -tnp | grep skype | tr -s ' ' | cut -d' ' -f4,7 | awk -F':' '{print $2}' | sort -u
    - 33165 5259/skypeforlinux
    - 33843 5259/skypeforlinux
    - 34030 5238/skypeforlinux
    - some info here: https://stackoverflow.com/questions/838317/how-to-tie-a-network-connection-to-a-pid-without-using-lsof-or-netstat
    - stats by pid: cat /proc/$pid/net/netstat | grep IpExt | awk '{print $8" "$9"}'

- [ ] Enable tweaking existing config in app window.
- [ ] Enable adding new config in app window.

### Feature wishlist
- Set config in app window instead of text file.
- Have a tray status indicator.
- Show current download/upload rates in panel.
