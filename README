# MainiX Installer

## Description

MainiX Installer is a TUI (Text User Interface) installer that creates a custom Debian-based Linux distribution called MainiX. The installer provides:

- Choice between Debian Stable or Unstable (Sid) repositories
- Budgie Desktop environment installation
- Custom system branding (replacing Debian references with MainiX)
- Simple disk partitioning with cfdisk
- User account setup

## Features

- **Repository Selection**:
  - Regular Updates (Debian Stable)
  - Rolling Updates (Debian Unstable/Sid)

- **Desktop Environment**:
  - Budgie Desktop with LightDM
  - NetworkManager for network configuration

- **System Customization**:
  - Complete rebranding from Debian to MainiX
  - Custom GRUB bootloader configuration
  - Modified `/etc/os-release`

- **User Friendly**:
  - Interactive TUI interface
  - Progress tracking
  - Error handling with automatic restart

## Requirements

To run the installer from Arch Linux Live CD:

```bash
pacman -Sy python ncurses debootstrap
```

## Installation

1. Boot into Arch Linux Live CD environment
2. Clone or download the installer:
   ```bash
   git clone https://github.com/mainixlinux/installer.git
   cd installer
   ```
3. Make the installer executable:
   ```bash
   chmod +x installer.py
   ```
4. Run the installer:
   ```bash
   ./installer.py
   ```

## Usage

The installer will guide you through these steps:

1. Internet connection setup
2. Repository selection (Stable/Unstable)
3. Disk partitioning (using cfdisk)
4. User account creation
5. System installation
6. Bootloader installation


## Known Issues

- Requires running from Arch Linux Live CD environment
- Limited filesystem support (currently only ext4)
- No advanced partitioning options

## Contributing

Contributions are welcome! Please open an issue or pull request for any:
- Bug fixes
- Feature requests
- Documentation improvements

## License

This project is licensed under the (LICENSE).

---

*MainiX Installer - Creating your custom Debian-based system with ease*
