#!/usr/bin/env python3
import os
import subprocess
import argparse
import time

def run_command(cmd, check=True):
    print(f"\n\033[1;34mExecuting: {cmd}\033[0m")
    try:
        result = subprocess.run(cmd, shell=True, check=check,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)
        if result.stdout: print(result.stdout)
        if result.stderr: print(f"\033[1;33m{result.stderr}\033[0m")
        return result
    except subprocess.CalledProcessError as e:
        print(f"\033[1;31mCommand failed: {e}\033[0m")
        if check: raise
        return e

def prepare_chroot(mount_point):
    required_mounts = [
        ('/dev', f"{mount_point}/dev"),
        ('/dev/pts', f"{mount_point}/dev/pts"),
        ('/proc', f"{mount_point}/proc"),
        ('/sys', f"{mount_point}/sys"),
        ('/run', f"{mount_point}/run")
    ]
    
    for src, dest in required_mounts:
        if not os.path.exists(dest):
            os.makedirs(dest, exist_ok=True)
        if not os.path.ismount(dest):
            run_command(f"mount --bind {src} {dest}")

def setup_os_identity(mount_point):
    os_release_content = """PRETTY_NAME="MainiX 2 (Oak)"
NAME="MainiX"
VERSION_ID="2"
VERSION="2 (Oak)"
VERSION_CODENAME=oak
ID=mainix
ID_LIKE=debian
HOME_URL="https://mainix.org/"
SUPPORT_URL="https://mainix.org/support/"
BUG_REPORT_URL="https://mainix.org/bugs/"
"""
    with open(f"{mount_point}/etc/os-release", "w") as f:
        f.write(os_release_content)
    
    with open(f"{mount_point}/etc/issue", "w") as f:
        f.write("MainiX 2 (Oak) \\n \\l\n")

def install_grub(mount_point, disk_dev):
    run_command(f"chroot {mount_point} apt-get update -y")
    run_command(f"chroot {mount_point} apt-get install -y grub-pc os-prober")
    
    run_command(f"chroot {mount_point} grub-install {disk_dev}")

    grub_config = """GRUB_DISTRIBUTOR="MainiX"
GRUB_CMDLINE_LINUX_DEFAULT="quiet"
"""
    with open(f"{mount_point}/etc/default/grub", "a") as f:
        f.write(grub_config)
    
    run_command(f"chroot {mount_point} update-grub")

def main():
    parser = argparse.ArgumentParser(description='MainiX Installer')
    parser.add_argument('--mount-point', default='/mnt', help='Mount point')
    args = parser.parse_args()

    try:
        disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
        print(f"Available disks: {', '.join(disks)}")
        disk_dev = f"/dev/{input('Select disk (e.g., sda): ').strip()}"
        
        root_part = f"/dev/{input('Enter root partition (e.g., sda1): ').strip()}"
        run_command(f"mkfs.ext4 -F {root_part}")
        run_command(f"mount {root_part} {args.mount_point}")
        
        run_command("pacman -Sy debootstrap --noconfirm")
        run_command(f"debootstrap stable {args.mount_point} http://deb.debian.org/debian/")
        
        prepare_chroot(args.mount_point)
        
        setup_os_identity(args.mount_point)
        
        install_grub(args.mount_point, disk_dev)
        
        print("\n\033[1;32mMainiX 2 (Oak) installation complete! Rebooting...\033[0m")
        run_command("sleep 5")
        run_command("reboot")

    except Exception as e:
        print(f"\n\033[1;31mInstallation failed: {str(e)}\033[0m")
        exit(1)

if __name__ == "__main__":
    main()
