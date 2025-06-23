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

def main():
    print("=== MainiX Installation ===")
    
    print("\n=== Manual Disk Partitioning ===")
    disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
    print(f"Available disks: {', '.join(disks)}")
    disk = get_input("Select disk to partition (e.g., sda)")
    disk_dev = f"/dev/{disk}"
    
    print(f"\nLaunching cfdisk for manual partitioning on {disk_dev}")
    print("Please create at least one partition and set its type to 'Linux'")
    print("Don't forget to mark bootable partition (usually the first one)")
    print("Write changes before exiting!")
    run_command(f"cfdisk {disk_dev}")
    
    partitions = subprocess.getoutput(f"lsblk -lno NAME {disk_dev} | tail -n +2").split()
    if not partitions:
        print("Error: No partitions found!")
        return
    
    print(f"\nAvailable partitions: {', '.join(partitions)}")
    root_part = get_input("Select root partition (e.g., sda1)")
    root_dev = f"/dev/{root_part}"
    
    run_command(f"mkfs.ext4 -F {root_dev}")
    run_command(f"mount {root_dev} /mnt")
    
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
    
    print("\n=== System Branding ===")
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
    
    print("\n=== Installing Budgie Desktop ===")
    run_command("chroot /mnt apt-get update -y")
    run_command("chroot /mnt apt-get install -y budgie-desktop lightdm")
    run_command("chroot /mnt apt-get install -y adwaita-icon-theme-full")
    
    run_command("chroot /mnt gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'")
    run_command("chroot /mnt gsettings set org.gnome.desktop.interface icon-theme 'Adwaita'")
    
    print("\n=== Installing GRUB with MainiX Branding ===")
    run_command("chroot /mnt apt-get install -y grub-pc")
    run_command("mount --bind /dev /mnt/dev")
    run_command("mount --bind /proc /mnt/proc")
    run_command("mount --bind /sys /mnt/sys")
    
    grub_custom = """GRUB_DISTRIBUTOR="MainiX"
GRUB_BACKGROUND="/boot/grub/mainix-grub.png"
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_THEME="/boot/grub/theme/theme.txt"
"""
    with open('/mnt/etc/default/grub', 'a') as f:
        f.write(grub_custom)
    
    run_command(f"chroot /mnt grub-install {disk_dev}")
    run_command("chroot /mnt update-grub")
    
    if os.path.exists("grub.png"):
        grub_wallpaper_dir = "/mnt/boot/grub/"
        os.makedirs(grub_wallpaper_dir, exist_ok=True)
        shutil.copy("grub.png", f"{grub_wallpaper_dir}/mainix-grub.png")
    
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
