#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import getpass
import shutil
import sys

def set_locale():
    os.environ["LANG"] = "en_US.UTF-8"
    os.environ["LC_ALL"] = "en_US.UTF-8"
    subprocess.run(["loadkeys", "us"], check=True)

def run_command(cmd, sudo=False, shell=False):
    if sudo:
        cmd = ["sudo"] + cmd
    try:
        subprocess.run(cmd, check=True, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка выполнения команды: {' '.join(cmd) if not shell else cmd}")
        print(f"Сообщение об ошибке: {e}")
        sys.exit(1)

def select_language():
    print("Выберите язык / Select language:")
    print("1. Русский")
    print("2. English")
    choice = input("Ваш выбор / Your choice (1/2): ").strip()
    
    if choice == "1":
        return "ru"
    else:
        return "en"

def get_translation(lang):
    """СПАСИБО ДИКПИКУ ЗА ПЕРЕВОД"""
    translations = {
        "ru": {
            "title": "=== Установщик MainiX 2 (Oak) ===",
            "disk_part": "\n[1/7] Разметка диска",
            "available_disks": "Доступные диски:",
            "enter_disk": "Введите диск для установки (например sda, nvme0n1): ",
            "formatting": "Форматирование разделов...",
            "root_part": "Введите корневой раздел (например {}): ",
            "efi_part": "Введите EFI раздел (если есть, иначе оставьте пустым): ",
            "base_install": "\n[2/7] Установка базовой системы",
            "user_config": "\n[3/7] Настройка пользователя",
            "hostname": "Введите имя компьютера: ",
            "username": "Введите имя пользователя: ",
            "user_pass": "Введите пароль пользователя: ",
            "root_pass": "Введите пароль root: ",
            "desktop_install": "\n[4/7] Установка Budgie Desktop",
            "bootloader": "\n[5/7] Установка загрузчика",
            "appearance": "\n[6/7] Настройка внешнего вида",
            "services": "\n[7/7] Включение служб",
            "complete": "\nУстановка завершена! Теперь можно перезагрузиться в MainiX 2 (Oak).",
            "error": "Ошибка: {}",
            "canceled": "\nУстановка отменена."
        },
        "en": {
            "title": "=== MainiX 2 (Oak) Installer ===",
            "disk_part": "\n[1/7] Disk partitioning",
            "available_disks": "Available disks:",
            "enter_disk": "Enter disk to install to (e.g. sda, nvme0n1): ",
            "formatting": "Formatting partitions...",
            "root_part": "Enter root partition (e.g. {}): ",
            "efi_part": "Enter EFI partition (if any, else leave blank): ",
            "base_install": "\n[2/7] Installing base system",
            "user_config": "\n[3/7] User configuration",
            "hostname": "Enter computer name: ",
            "username": "Enter username: ",
            "user_pass": "Enter user password: ",
            "root_pass": "Enter root password: ",
            "desktop_install": "\n[4/7] Installing Budgie Desktop",
            "bootloader": "\n[5/7] Installing bootloader",
            "appearance": "\n[6/7] Configuring appearance",
            "services": "\n[7/7] Enabling services",
            "complete": "\nInstallation complete! You can now reboot into MainiX 2 (Oak).",
            "error": "Error: {}",
            "canceled": "\nInstallation canceled."
        }
    }
    return translations.get(lang, translations["en"])

def detect_efi():
    return os.path.exists("/sys/firmware/efi/efivars")

def partition_disk(disk, lang_data):
    print(lang_data["formatting"])
    
    if detect_efi():
        run_command(f"parted /dev/{disk} --script mklabel gpt", shell=True)
        run_command(f"parted /dev/{disk} --script mkpart ESP fat32 1MiB 513MiB", shell=True)
        run_command(f"parted /dev/{disk} --script set 1 boot on", shell=True)
        run_command(f"parted /dev/{disk} --script mkpart primary ext4 513MiB 100%", shell=True)
        
        efi_part = f"{disk}1"
        root_part = f"{disk}2"
    else:
        run_command(f"parted /dev/{disk} --script mklabel msdos", shell=True)
        run_command(f"parted /dev/{disk} --script mkpart primary ext4 1MiB 100%", shell=True)
        run_command(f"parted /dev/{disk} --script set 1 boot on", shell=True)
        
        efi_part = None
        root_part = f"{disk}1"
    
    if efi_part:
        run_command(["mkfs.fat", "-F32", f"/dev/{efi_part}"])
    run_command(["mkfs.ext4", f"/dev/{root_part}"])
    
    return root_part, efi_part

def main():
    set_locale()
    lang = select_language()
    msg = get_translation(lang)
    
    print(msg["title"])
    
    print(msg["disk_part"])
    disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
    print(msg["available_disks"], " ".join(disks))
    disk = input(msg["enter_disk"])
    
    root_part, efi_part = partition_disk(disk, msg)
    
    print(msg["base_install"])
    run_command(["mount", f"/dev/{root_part}", "/mnt"])
    if efi_part:
        os.makedirs("/mnt/boot/EFI", exist_ok=True)
        run_command(["mount", f"/dev/{efi_part}", "/mnt/boot/EFI"])
    
    run_command(["pacstrap", "/mnt", "base", "base-devel", "linux-zen", "linux-firmware"])
    
    print(msg["user_config"])
    hostname = input(msg["hostname"])
    username = input(msg["username"])
    user_password = getpass.getpass(msg["user_pass"])
    root_password = getpass.getpass(msg["root_pass"])
    
    run_command(["genfstab", "-U", "/mnt", "-p", "/mnt/etc/fstab"])
    
    chroot_commands = """
    echo "{hostname}" > /etc/hostname
    ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
    echo "ru_RU.UTF-8 UTF-8" >> /etc/locale.gen
    echo "LANG=en_US.UTF-8" > /etc/locale.conf
    locale-gen
    
    echo "root:{root_password}" | chpasswd
    useradd -m -G wheel -s /bin/bash {username}
    echo "{username}:{user_password}" | chpasswd
    sed -i 's/^# %wheel ALL=(ALL) ALL/%wheel ALL=(ALL) ALL/' /etc/sudoers
    
    sed -i 's/Arch Linux/MainiX 2 (Oak)/' /etc/os-release
    sed -i 's/ID=arch/ID=mainix/' /etc/os-release
    sed -i 's/NAME="Arch Linux"/NAME="MainiX 2 (Oak)"/' /etc/os-release
    """
    run_command(["arch-chroot", "/mnt", "bash", "-c", chroot_commands])
    
    print(msg["desktop_install"])
    run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", 
                "budgie-desktop", "gnome-terminal", "networkmanager", 
                "firefox", "gnome-themes-extra", "adwaita-icon-theme", "gdm"])
    
    print(msg["bootloader"])
    bootloader_cmd = "pacman -S --noconfirm grub && "
    
    if efi_part:
        bootloader_cmd += "pacman -S --noconfirm efibootmgr && "
        bootloader_cmd += "grub-install --target=x86_64-efi --bootloader-id=MainiX --efi-directory=/boot/EFI && "
    else:
        bootloader_cmd += f"grub-install --target=i386-pc /dev/{disk} && "
    
    bootloader_cmd += "grub-mkconfig -o /boot/grub/grub.cfg"
    
    run_command(["arch-chroot", "/mnt", "bash", "-c", bootloader_cmd])
    
    print(msg["appearance"])
    if os.path.exists("wallpaper.jpg"):
        os.makedirs("/mnt/usr/share/backgrounds", exist_ok=True)
        shutil.copy("wallpaper.jpg", "/mnt/usr/share/backgrounds/mainix-wallpaper.jpg")
    
    run_command(["arch-chroot", "/mnt", "bash", "-c", 
                "echo 'KEYMAP=ru' > /etc/vconsole.conf && " +
                "echo 'FONT=cyr-sun16' >> /etc/vconsole.conf"])
    
    print(msg["services"])
    run_command(["arch-chroot", "/mnt", "systemctl", "enable", "NetworkManager"])
    run_command(["arch-chroot", "/mnt", "systemctl", "enable", "gdm"])

    run_command(["umount", "-R", "/mnt"])
    print(msg["complete"])

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(get_translation(select_language())["error"].format(e))
    except KeyboardInterrupt:
        print(get_translation(select_language())["canceled"])
    except Exception as e:
        print(f"Critical error: {str(e)}")
        sys.exit(1)
