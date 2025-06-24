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

def manual_partitioning(disk_dev):
    """Interactive partitioning with cfdisk"""
    print("\n\033[1;32m=== Disk Partitioning ===\033[0m")
    print("Instructions:")
    print("1. Create root partition (/) with at least 20GB")
    print("2. Set bootable flag (toggle with Space)")
    print("3. Select 'Write' then 'Quit'\n")
    
    os.system("clear && stty sane && tput reset")
    time.sleep(1)
    
    print(f"\033[1;36mLaunching cfdisk for {disk_dev}...\033[0m")
    if os.system(f"cfdisk {disk_dev}") != 0:
        raise Exception("Partitioning failed. Please try again.")
    
    partitions = subprocess.getoutput(
        f"lsblk -ln {disk_dev} | grep part | awk '{{print $1}}'").split()
    if not partitions:
        raise Exception("No partitions created!")
    
    print(f"\nCreated partitions: {partitions}")
    return f"/dev/{input('Enter root partition (e.g., sda1): ').strip()}"

def prepare_chroot(mount_point):
    """Prepare chroot environment with all mounts"""
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

def setup_autologin_oobe(mount_point):
    os.makedirs(f"{mount_point}/etc/systemd/system/getty@tty1.service.d", exist_ok=True)
    with open(f"{mount_point}/etc/systemd/system/getty@tty1.service.d/override.conf", "w") as f:
        f.write("""[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear %I $TERM
""")

    with open(f"{mount_point}/root/.bash_profile", "a") as f:
        f.write("""
if [ ! -f /etc/oobe_completed ]; then
    echo "Starting MainiX OOBE setup..."
    wget -O /tmp/oobe.py https://example.com/oobe.py || curl -o /tmp/oobe.py https://example.com/oobe.py
    python3 /tmp/oobe.py
    rm -f /tmp/oobe.py
    systemctl disable getty@tty1.service.d/override.conf
    touch /etc/oobe_completed
    reboot
fi
""")

def setup_mainix_identity(mount_point):
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

def install_grub(mount_point, disk_dev):
    run_command(f"chroot {mount_point} apt-get update -y")
    run_command(f"chroot {mount_point} apt-get install -y grub-pc linux-image-amd64")
    
    run_command(f"chroot {mount_point} grub-install {disk_dev}")
    
    with open(f"{mount_point}/etc/default/grub", "w") as f:
        f.write('GRUB_DISTRIBUTOR="MainiX"\n')
        f.write('GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n')
    
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
        setup_autologin_oobe(args.mount_point)
        
        try:
            install_grub(args.mount_point, disk_dev)
        except subprocess.CalledProcessError:
            print("\033[1;33mGRUB installation failed, retrying...\033[0m")
            run_command(f"chroot {args.mount_point} apt-get install -f -y")
            install_grub(args.mount_point, disk_dev)
        
        print("\n\033[1;32mInstallation complete! Rebooting...\033[0m")
        time.sleep(3)
        os.system("reboot")

    except Exception as e:
        print(f"\n\033[1;31mError: {str(e)}\033[0m")
        print("Try: umount -R /mnt && swapoff -a")
        exit(1)

if __name__ == "__main__":
    main()
