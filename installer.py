#!/usr/bin/env python3
import os
import subprocess
import argparse
import time

def run_command(cmd, check=True):
    """Execute shell command with error handling"""
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

def manual_partitioning(disk_dev):
    print("\n\033[1;32m=== Disk Partitioning ===\033[0m")
    print("Instructions:")
    print("1. Create at least one root partition (/)")
    print("2. Set bootable flag (toggle with [Space])")
    print("3. Select 'Write' to save changes")
    print("4. Confirm with 'yes'")
    print("5. Select 'Quit' to exit\n")
    os.system("clear && stty sane && tput reset")
    time.sleep(1)
    print(f"\033[1;36mLaunching cfdisk for {disk_dev}...\033[0m")
    cfdisk_exit = os.system(f"cfdisk {disk_dev}")
    if cfdisk_exit != 0:
        raise Exception("cfdisk exited abnormally. Partitioning failed.")
    partitions = subprocess.getoutput(
        f"lsblk -ln {disk_dev} | grep part | awk '{{print $1}}'").split()
    if not partitions:
        raise Exception("No partitions created! Please create at least one partition.")
    
    print(f"\nCreated partitions: {partitions}")
    return f"/dev/{input('Enter root partition (e.g., sda1): ').strip()}"

def prepare_chroot(mount_point):
    required_mounts = {
        '/dev': f"{mount_point}/dev",
        '/dev/pts': f"{mount_point}/dev/pts", 
        '/proc': f"{mount_point}/proc",
        '/sys': f"{mount_point}/sys",
        '/run': f"{mount_point}/run"
    }
    
    for src, dest in required_mounts.items():
        os.makedirs(dest, exist_ok=True)
        if not os.path.ismount(dest):
            run_command(f"mount --bind {src} {dest}")

def setup_mainix_identity(mount_point):
    """Configure MainiX 2 (Oak) identity"""
    with open(f"{mount_point}/etc/os-release", "w") as f:
        f.write("""PRETTY_NAME="MainiX 2 (Oak)"
NAME="MainiX"
VERSION_ID="2"
VERSION="2 (Oak)"
VERSION_CODENAME=oak
ID=mainix
ID_LIKE=debian
HOME_URL="https://mainix.org/"
SUPPORT_URL="https://mainix.org/support/"
BUG_REPORT_URL="https://mainix.org/bugs/"
""")
    with open(f"{mount_point}/etc/issue", "w") as f:
        f.write("MainiX 2 (Oak) \\n \\l\n")

def install_grub(mount_point, disk_dev):
    run_command(f"chroot {mount_point} apt-get update -y")
    run_command(f"chroot {mount_point} apt-get install -y grub-pc os-prober")
    
    with open(f"{mount_point}/etc/default/grub", "w") as f:
        f.write('GRUB_DISTRIBUTOR="MainiX"\n')
        f.write('GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n')
    
    run_command(f"chroot {mount_point} grub-install {disk_dev}")
    run_command(f"chroot {mount_point} update-grub")

def main():
    parser = argparse.ArgumentParser(description='MainiX Installer')
    parser.add_argument('--mount-point', default='/mnt', help='Mount point')
    args = parser.parse_args()

    try:
        print("\033[1;32m=== MainiX 2 (Oak) Installation ===\033[0m")
        disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
        print(f"Available disks: {', '.join(disks)}")
        disk_dev = f"/dev/{input('Select disk (e.g., sda): ').strip()}"
        root_part = manual_partitioning(disk_dev)
        run_command(f"mkfs.ext4 -F {root_part}")
        run_command(f"mount {root_part} {args.mount_point}")
        run_command("pacman -Sy debootstrap --noconfirm")
        run_command(f"debootstrap stable {args.mount_point} http://deb.debian.org/debian/")
        prepare_chroot(args.mount_point)
        setup_mainix_identity(args.mount_point)
        install_grub(args.mount_point, disk_dev)
        
        print("\n\033[1;32mInstallation complete! Rebooting in 5 seconds...\033[0m")
        time.sleep(5)
        os.system("reboot")

    except Exception as e:
        print(f"\n\033[1;31mError: {str(e)}\033[0m")
        print("You may need to manually unmount partitions and try again.")
        exit(1)

if __name__ == "__main__":
    main()
