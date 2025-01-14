## Installation

- Checkout to /opt/libvirt-memballoon
- Symlink `vm-balloon.service` to `/etc/systemd/system` and `journald@libvirt-balloon.conf` to `/etc/systemd`.
- systemctl daemon-reload
- systemctl enable vm-balloon
