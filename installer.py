#!/usr/bin/env python3
import os
import subprocess
import getpass
import shutil
import locale
#ыъъыъыъыъыъыъъыъыъъыъыъыъъыъыъ

def run_command(cmd, check=True):
    print(f"Executing: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            errors='replace'
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        print(f"Output: {e.stdout}")
        print(f"Errors: {e.stderr}")
        if check:
            raise
        return e

def get_input(prompt, default=None):
    prompt = prompt.encode('utf-8', errors='replace').decode('utf-8')
    if default:
        default = default.encode('utf-8', errors='replace').decode('utf-8')
        response = input(f"{prompt} [{default}]: ").strip()
        return response.encode('utf-8', errors='replace').decode('utf-8') or default
    response = input(f"{prompt}: ").strip()
    return response.encode('utf-8', errors='replace').decode('utf-8')

def main():
    print("=== Install MainiX ===")
    
    print("\n=== Disk Partitioning (MBR) ===")
    disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
    print(f"Available disks: {', '.join(disks)}")
    disk = get_input("Select disk to install (e.g., sda)").strip()
    disk_dev = f"/dev/{disk}"
    
    run_command(f"cfdisk" {disk_dev}1)
    run_command(f"mkfs.ext4 -F {disk_dev}1")
    
    run_command(f"mount {disk_dev}1 /mnt")
    
    print("\n=== User Configuration ===")
    hostname = get_input("Hostname", "mainix")
    username = get_input("Username", "user")
    user_password = getpass.getpass("User password: ")
    root_password = getpass.getpass("Root password: ")
    
    print("\n=== Installing Base System ===")
    run_command("pacman -Sy debootstrap")
    run_command("debootstrap stable /mnt http://deb.debian.org/debian/")
    
    run_command("chroot /mnt apt-get install -y locales")
    run_command("chroot /mnt sed -i 's/^# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen")
    run_command("chroot /mnt locale-gen en_US.UTF-8")
    run_command("chroot /mnt update-locale LANG=en_US.UTF-8")
    run_command("chroot /mnt apt-get install -y console-setup")
    run_command("chroot /mnt setupcon --force")
    
    with open('/mnt/etc/hostname', 'w', encoding='utf-8') as f:
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
HOME_URL="https://mainix.org/"
SUPPORT_URL="https://mainix.org/support/"
BUG_REPORT_URL="https://mainix.org/bugs/"
"""
    with open('/mnt/etc/os-release', 'w', encoding='utf-8') as f:
        f.write(os_release)
    
    print("\n=== Installing Budgie Desktop ===")
    run_command("chroot /mnt apt-get update -y")
    run_command("chroot /mnt apt-get install -y budgie-desktop lightdm gnome-terminal nautilus gedit")
    run_command("chroot /mnt apt-get install -y adwaita-icon-theme-full")
    
    run_command("chroot /mnt gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'")
    run_command("chroot /mnt gsettings set org.gnome.desktop.interface icon-theme 'Adwaita'")
    
    if os.path.exists("wallpaper.jpg"):
        wallpaper_dir = "/mnt/usr/share/backgrounds/"
        os.makedirs(wallpaper_dir, exist_ok=True)
        shutil.copy("wallpaper.png", wallpaper_dir)
        run_command("chroot /mnt gsettings set org.gnome.desktop.background picture-uri 'file:///usr/share/backgrounds/wallpaper.png'")
        run_command("chroot /mnt gsettings set org.gnome.desktop.background picture-options 'scaled'")
    
    print("\n=== Installing GRUB (MBR) ===")
    run_command("chroot /mnt apt-get install -y grub-pc")
    run_command("mount --bind /dev /mnt/dev")
    run_command("mount --bind /proc /mnt/proc")
    run_command("mount --bind /sys /mnt/sys")
    run_command(f"chroot /mnt grub-install {disk_dev}")
    run_command("chroot /mnt update-grub")
    
    if os.path.exists("grub.jpg"):
        grub_wallpaper_dir = "/mnt/boot/grub/"
        shutil.copy("grub.png", grub_wallpaper_dir)
        run_command("chroot /mnt sed -i 's/^#GRUB_BACKGROUND=.*/GRUB_BACKGROUND=\"\\/boot\\/grub\\/grub.png\"/' /etc/default/grub")
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
