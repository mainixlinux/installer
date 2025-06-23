#!/usr/bin/env python3
import os
import subprocess
import argparse

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
    print("\n\033[1;32m=== Disk Partitioning ===\033[0m")
    run_command("stty sane")
    run_command("reset")
    os.system(f"cfdisk {disk_dev}")
    
    partitions = subprocess.getoutput(
        f"lsblk -ln {disk_dev} | grep part | awk '{{print $1}}'").split()
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
        
        for fs in ['dev', 'proc', 'sys']:
            target = f"{args.mount_point}/{fs}"
            if not os.path.exists(target):
                os.makedirs(target)
            run_command(f"mount --bind /{fs} {target}")
        
        run_command(f"chroot {args.mount_point} apt-get update -y")
        run_command(f"chroot {args.mount_point} apt-get install -y sudo")
        
        os_release = f"{args.mount_point}/etc/os-release"
        with open(os_release, 'w') as f:
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
        
        service_dir = f"{args.mount_point}/etc/systemd/system/getty@tty1.service.d"
        os.makedirs(service_dir, exist_ok=True)
        
        with open(f"{service_dir}/override.conf", 'w') as f:
            f.write("""[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear %I $TERM
""")
        
        run_command(f"chroot {args.mount_point} apt-get install -y grub-pc")
        run_command(f"chroot {args.mount_point} grub-install {disk_dev}")
        
        with open(f"{args.mount_point}/root/.bash_profile", 'a') as f:
            f.write("""
if [ ! -f /etc/oobe_completed ]; then
    wget -O /tmp/oobe.py https://example.com/oobe.py
    python3 /tmp/oobe.py
    rm -f /etc/systemd/system/getty@tty1.service.d/override.conf
    systemctl daemon-reload
    touch /etc/oobe_completed
fi
""")
        
        print("\n\033[1;32mInstallation complete! Rebooting...\033[0m")
        run_command("sleep 5")
        run_command("reboot")

    except Exception as e:
        print(f"\n\033[1;31mInstallation failed: {str(e)}\033[0m")
        exit(1)

if __name__ == "__main__":
    main()
