# AdGuard VPN GUI for Linux

AdGuard team didn't properly port their VPN on Linux for some reason, so I did it myself. It's entirely vibecoded btw.

This application was only tested on Linux Mint 22.3 - Cinnamon 64-bit.

---

## How to install

Get the latest binary [here](https://github.com/LoyDizak/AdGuard-VPN-GUI-for-Linux/releases/latest)

Extract the archive and run the install script:

```bash
tar -xzf adGuardvpn-gui.tar.gz
bash install.sh
```

Note that you will need to log in to your AdGuard VPN account. You can do that in the installer script or by running the following command:

```bash
adguardvpn-cli login
```

To uninstall:
```bash
bash uninstall.sh
```

## How to build

### Dependencies

- `pyinstaller`
- `tkinter`



### Build

```bash
bash build.sh
```

The binary will appear in the `builds/` folder.

---