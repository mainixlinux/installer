#!/usr/bin/env python3
import os
import subprocess
import getpass
import argparse

def run_command(cmd, check=True):
    """Execute shell command with better error handling"""
    print(f"\n\033[1;34mExecuting: {cmd}\033[0m")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"\033[1;33m{result.stderr}\033[0m")
        return result
    except subprocess.CalledProcessError as e:
        print(f"\033[1;31mCommand failed: {e}\033[0m")
        if check:
            raise
        return e

def manual_partitioning(disk_dev):
    print("\n\033[1;32m=== Disk Partitioning ===\033[0m")
    print("Please create at least one root partition (/)")
    print("Set the bootable flag for your root partition")
    
    # Reset terminal for cfdisk
    run_command("stty sane")
    run_command("reset")
    
    # Run cfdisk with clean terminal
    run_command(f"cfdisk {disk_dev}")
    
    partitions = subprocess.getoutput(f"lsblk -ln {disk_dev} | grep part | awk '{{print $1}}'").split()
    print(f"\nAvailable partitions: {partitions}")
    return f"/dev/{input('Enter root partition (e.g., sda1): ').strip()}"

def main():
    parser = argparse.ArgumentParser(description='MainiX Installer')
    parser.add_argument('--mount-point', default='/mnt', help='Mount point')
    args = parser.parse_args()

    try:
        disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
        print(f"Available disks: {', '.join(disks)}")
        disk_dev = f"/dev/{input('Select disk (e.g., sda): ').strip()}"
        
        root_part = manual_partitioning(disk_dev)
        
        run_command(f"mkfs.ext4 -F {root_part}")
        run_command(f"mount {root_part} {args.mount_point}")
        
        run_command("pacman -Sy debootstrap --noconfirm")
        run_command(f"debootstrap stable {args.mount_point} http://deb.debian.org/debian/")
        
        run_command(f"mount --bind /dev {args.mount_point}/dev")
        run_command(f"mount --bind /proc {args.mount_point}/proc")
        run_command(f"mount --bind /sys {args.mount_point}/sys")
        
        run_command(f"chroot {args.mount_point} apt-get update -y")
        run_command(f"chroot {args.mount_point} apt-get install -y sudo adduser")
        
        username = input("Enter admin username [user]: ").strip() or "user"
        run_command(f"chroot {args.mount_point} adduser --disabled-password --gecos '' {username}")
        run_command(f"chroot {args.mount_point} usermod -aG sudo {username}")
        run_command(f"chroot {args.mount_point} passwd {username}")
        run_command("chroot {args.mount_point} passwd root")
        
        run_command(f"chroot {args.mount_point} apt-get install -y grub-pc")
        run_command(f"chroot {args.mount_point} grub-install {disk_dev}")
        
        with open(f"{args.mount_point}/etc/profile.d/oobe.sh", "w") as f:
            f.write("""#!/bin/sh
if [ ! -f /etc/oobe_completed ]; then
    curl -o /tmp/oobe.py https://example.com/oobe.py
    python3 /tmp/oobe.py
    touch /etc/oobe_completed
fi
""")
        run_command(f"chmod +x {args.mount_point}/etc/profile.d/oobe.sh")
        
        print("\n\033[1;32mInstallation complete! Rebooting...\033[0m")
        run_command("sleep 5")
        run_command("reboot")

    except Exception as e:
        print(f"\n\033[1;31mInstallation failed: {e}\033[0m")
        exit(1)

if __name__ == "__main__":
    main()
