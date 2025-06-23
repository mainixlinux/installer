#!/usr/bin/env python3
import os
import subprocess
import getpass

def run(cmd):
    print(f"\n\033[1;34mRunning: {cmd}\033[0m")
    subprocess.run(cmd, shell=True, check=True)

def select_profile():
    print("\n\033[1;32m=== Select System Profile ===\033[0m")
    print("1. Base")
    print("2. Desktop")
    print("3. Web-server (nginx + PHP)")
    choice = input("Your choice [1-3]: ").strip()
    return choice

def setup_base():
    print("\n\033[1;32m=== Minimal Setup ===\033[0m")
    run("apt-get update")
    run("apt-get install -y network-manager")

def setup_desktop():
    print("\n\033[1;32m=== Desktop Setup ===\033[0m")
    run("apt-get install -y budgie-desktop lightdm "
        "gnome-terminal firefox telegram-desktop "
        "adwaita-icon-theme-full")
    
    run("sudo -u $(logname) dbus-launch gsettings set "
        "org.gnome.desktop.interface gtk-theme 'Adwaita-dark'")
    
    if os.path.exists("/tmp/wallpaper.png"):
        run("mv /tmp/wallpaper.png /usr/share/backgrounds/")
        run("sudo -u $(logname) dbus-launch gsettings set "
            "org.gnome.desktop.background picture-uri "
            "'file:///usr/share/backgrounds/wallpaper.png'")

def setup_webserver():
    print("\n\033[1;32m=== Web Server Setup ===\033[0m")
    run("apt-get install -y nginx php-fpm openssh-server screen")
    run("systemctl enable nginx php-fpm ssh")

def main():
    try:
        profile = select_profile()
        
        if profile == "1":
            setup_base()
        elif profile == "2":
            setup_desktop()
        elif profile == "3":
            setup_webserver()
        
        run("systemctl enable NetworkManager")
        run("systemctl start NetworkManager")
        
        print("\n\033[1;32mSetup completed! Please reboot.\033[0m")
        
    except Exception as e:
        print(f"\n\033[1;31mError: {e}\033[0m")

if __name__ == "__main__":
    main()
