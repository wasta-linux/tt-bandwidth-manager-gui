- update screenshot
- prepare email text

### Planned features
- [x] Show current config in app window.
- [x] Show bandwidth used by currently configured processes.
- [ ] Consider showing more precision on higher bandwidth prefixes (e.g. M, G, T)
- [ ] Enable tweaking existing config in app window.
- [ ] Enable adding new config in app window.

### Updated row layout
|     | Process               | Maximum        | Minimum       | Priority   | Current        |
| --- | --------------------- | -------------- | ------------- | ---------- | -------------- |  
| [ ] | Firefox | [16] KB/s [up] | [0] KB/s [up] | [1] [up] | [0] KB/s [up] |
|     | exe: /usr/lib/firefox | [96] KB/s [dn] | [0] KB/s [dn] | [1] [dn] | [90] KB/s [dn] |

[ ] = checkbox

[up] = 'menu-sort-up' icon

[dn] = 'menu-sort-down' icon

### Feature wishlist
- Develop a decent integration test suite.
- Set config in app window instead of text file.
- Have a tray status indicator.
- Show current download/upload rates in panel.
