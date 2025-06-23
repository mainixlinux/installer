#!/usr/bin/env python3
import os
import subprocess
import getpass
import shutil

def run_command(cmd, check=True):
    """Execute shell command"""
    print(f"Executing: {cmd}")
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
            print(result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if check:
            raise
        return e

def get_input(prompt, default=None):
    """Get user input"""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response or default
    return input(f"{prompt}: ").strip()

def manual_partitioning(disk_dev):
    """Manual disk partitioning using cfdisk"""
    print(f"\nStarting manual partitioning for {disk_dev}")
    print("Please create at least one root partition (/) and optionally swap")
    print("Set the bootable flag for your root partition")
    input("Press Enter to launch cfdisk...")
    run_command(f"cfdisk {disk_dev}")
    
    partitions = subprocess.getoutput(f"lsblk -ln {disk_dev} | grep part | awk '{{print $1}}'").split()
    print(f"\nAvailable partitions: {partitions}")
    root_part = get_input("Enter root partition (e.g., sda1)")
    return f"/dev/{root_part}"

def main():
    print("=== MainiX Installation ===")
    
    print("\n=== Manual Disk Partitioning ===")
    disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
    print(f"Available disks: {', '.join(disks)}")
    disk = get_input("Select disk to install (e.g., sda)")
    disk_dev = f"/dev/{disk}"
    
    root_part = manual_partitioning(disk_dev)
    
    print(f"\nFormatting {root_part} as ext4...")
    run_command(f"mkfs.ext4 -F {root_part}")
    
    run_command(f"mount {root_part} /mnt")
    
    print("\n=== User Configuration ===")
    hostname = get_input("Hostname", "mainix")
    username = get_input("Username", "user")
    user_password = getpass.getpass("User password: ")
    root_password = getpass.getpass("Root password: ")
    
    print("\n=== Installing Base System ===")
    run_command("pacman -Sy debootstrap --noconfirm")
    run_command("debootstrap stable /mnt http://deb.debian.org/debian/")
    
    with open('/mnt/etc/hostname', 'w') as f:
        f.write(hostname)
    
    run_command(f"chroot /mnt useradd -m -G sudo -s /bin/bash {username}")
    run_command(f"chroot /mnt sh -c 'echo \"{username}:{user_password}\" | chpasswd'")
    run_command(f"chroot /mnt sh -c 'echo \"root:{root_password}\" | chpasswd'")
    
    os_release = """PRETTY_NAME="MainiX 2 (Oak)"
NAME="MainiX"
VERSION_ID="2"
VERSION="2 (Oak)"
VERSION_CODENAME=oak
ID=mainix
ID_LIKE=debian
HOME_URL="https://mainix.c9t.ru/"
SUPPORT_URL="https://mainix.c9t.ru/tg/"
BUG_REPORT_URL="https://mainix.c9t.ru/bugtracker/"
"""
    with open('/mnt/etc/os-release', 'w') as f:
        f.write(os_release)
    
    print("\n=== Installing Budgie Desktop ===")
    run_command("chroot /mnt apt-get update -y")
    run_command("chroot /mnt apt-get install -y budgie-desktop lightdm")
    
    print("\n=== Installing and Configuring GRUB ===")
    run_command("chroot /mnt apt-get install -y grub-pc")
    
    run_command("mount --bind /dev /mnt/dev")
    run_command("mount --bind /proc /mnt/proc")
    run_command("mount --bind /sys /mnt/sys")
    
    run_command(f"chroot /mnt grub-install {disk_dev}")
    
    grub_custom = """GRUB_DISTRIBUTOR="MainiX"
GRUB_BACKGROUND="/boot/grub/grub.png"
GRUB_CMDLINE_LINUX_DEFAULT="quiet"
"""
    with open('/mnt/etc/default/grub', 'a') as f:
        f.write(grub_custom)
    
    run_command("chroot /mnt update-grub")
    
    print("\n=== Installation Complete! ===")
    print("System will reboot in 10 seconds...")
    run_command("sleep 10")
    run_command("reboot")

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print("Installation aborted due to error.")
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user.")
