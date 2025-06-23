#!/usr/bin/env python3
import os
import subprocess
import getpass
import shutil
import argparse
import sys

def run_command(cmd, check=True):
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
        print(f"\033[1;31mError output: {e.stderr}\033[0m")
        if check:
            raise
        return e

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='MainiX Installation Script')
    parser.add_argument('--resume-from', type=int, choices=range(1, 8), 
                      help='Resume installation from specific step (1-7)')
    parser.add_argument('--disk', help='Specify disk to use (e.g. sda)')
    parser.add_argument('--root-part', help='Specify root partition (e.g. sda1)')
    return parser.parse_args()

def step_partitioning(args):
    """Step 1: Disk partitioning"""
    print("\n\033[1;32m=== Step 1: Manual Disk Partitioning ===\033[0m")
    if args.disk:
        disk_dev = f"/dev/{args.disk}"
    else:
        disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
        print(f"Available disks: {', '.join(disks)}")
        disk = input("Select disk to install (e.g., sda): ").strip()
        disk_dev = f"/dev/{disk}"
    
    print(f"\nStarting cfdisk for {disk_dev}")
    print("Please create at least one root partition (/)")
    input("Press Enter to launch cfdisk...")
    run_command(f"cfdisk {disk_dev}")
    
    if args.root_part:
        root_part = f"/dev/{args.root_part}"
    else:
        partitions = subprocess.getoutput(f"lsblk -ln {disk_dev} | grep part | awk '{{print $1}}'").split()
        print(f"\nAvailable partitions: {partitions}")
        root_part = f"/dev/{input('Enter root partition (e.g., sda1): ').strip()}"
    
    print(f"\nFormatting {root_part} as ext4...")
    run_command(f"mkfs.ext4 -F {root_part}")
    run_command(f"mount {root_part} /mnt")
    
    return disk_dev, root_part

def step_base_install():
    """Step 2: Base system installation"""
    print("\n\033[1;32m=== Step 2: Base System Installation ===\033[0m")
    run_command("pacman -Sy debootstrap --noconfirm")
    run_command("debootstrap stable /mnt http://deb.debian.org/debian/")
    
    # Mount required for chroot
    run_command("mount --bind /dev /mnt/dev")
    run_command("mount --bind /proc /mnt/proc")
    run_command("mount --bind /sys /mnt/sys")

def step_essential_packages():
    """Step 3: Install essential packages"""
    print("\n\033[1;32m=== Step 3: Installing Essential Packages ===\033[0m")
    run_command("chroot /mnt apt-get update -y")
    run_command("chroot /mnt apt-get install -y sudo passwd login bash")

def step_user_config():
    print("\n\033[1;32m=== Step 4: User Configuration ===\033[0m")
    hostname = input("Enter hostname [mainix]: ").strip() or "mainix"
    username = input("Enter username [user]: ").strip() or "user"
    user_password = getpass.getpass("Enter user password: ")
    root_password = getpass.getpass("Enter root password: ")
    
    with open('/mnt/etc/hostname', 'w') as f:
        f.write(hostname)
    
    run_command(f"chroot /mnt bash -c 'mkdir -p /etc/skel'")
    run_command(f"chroot /mnt bash -c 'useradd --create-home --shell /bin/bash {username}'")
    run_command(f"chroot /mnt bash -c 'echo \"{username}:{user_password}\" | chpasswd'")
    run_command(f"chroot /mnt bash -c 'usermod -aG sudo {username}'")
    run_command(f"chroot /mnt bash -c 'echo \"root:{root_password}\" | chpasswd'")

def step_system_branding():
    print("\n\033[1;32m=== Step 5: System Branding ===\033[0m")
    os_release = """PRETTY_NAME="MainiX 2 (Oak)"
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
    with open('/mnt/etc/os-release', 'w') as f:
        f.write(os_release)

def step_desktop_install():
    """ШАГ 6, можно переключаться нормально, если читаешь иди нахуй"""
    print("\n\033[1;32m=== Step 6: Desktop Environment Installation ===\033[0m")
    run_command("chroot /mnt apt-get install -y budgie-desktop lightdm")

def step_grub_install(disk_dev):
    """Step 7: GRUB installation"""
    print("\n\033[1;32m=== Step 7: GRUB Installation ===\033[0m")
    run_command("chroot /mnt apt-get install -y grub-pc")
    run_command(f"chroot /mnt grub-install {disk_dev}")
    
    grub_custom = """GRUB_DISTRIBUTOR="MainiX"
GRUB_BACKGROUND="/boot/grub/grub.png"
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
"""
    with open('/mnt/etc/default/grub', 'a') as f:
        f.write(grub_custom)
    
    run_command("chroot /mnt update-grub")

def main():
    args = parse_arguments()
    steps = [
        step_partitioning,
        step_base_install,
        step_essential_packages,
        step_user_config,
        step_system_branding,
        step_desktop_install,
        step_grub_install
    ]
    
    start_step = args.resume_from or 1
    disk_dev = None
    
    try:
        for i, step in enumerate(steps[start_step-1:], start=start_step):
            print(f"\n\033[1;35m=== Starting installation from step {i} ===\033[0m")
            
            if i == 1:
                disk_dev, root_part = step(args)
            elif i == 7:
                if not disk_dev and args.disk:
                    disk_dev = f"/dev/{args.disk}"
                step(disk_dev)
            else:
                step()
                
    except Exception as e:
        print(f"\n\033[1;31mInstallation failed at step {i}: {e}\033[0m")
        sys.exit(1)
    
    print("\n\033[1;32m=== Installation Complete! ===\033[0m")
    print("System will reboot in 10 seconds...")
    run_command("sleep 10")
    run_command("reboot")

if __name__ == "__main__":
    main()
