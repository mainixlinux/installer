#!/usr/bin/env python3
import curses
import subprocess
import os
# если ты это читаешь, то иди нахуй, опенсурса не сущевствует
import time
import sys

class MainiXInstaller:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_step = 0
        self.steps = [
            "Connect to Internet",
            "Select Repository",
            "Disk Partitioning",
            "User Accounts",
            "System Installation",
            "System Configuration",
            "Bootloader Installation",
            "Completion"
        ]
        self.username = ""
        self.password = ""
        self.root_password = ""
        self.disk = ""
        self.root_part = ""
        self.repo = 0
        self.repositories = [
            "Rolling Updates (unstable)",
            "Regular Updates (stable)"
        ]
        self.log_file = "/var/log/mainix_installer.log"
        
    def draw_progress(self, message):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        for i, step in enumerate(self.steps):
            color = curses.color_pair(1) if i == self.current_step else curses.color_pair(2)
            self.stdscr.addstr(i+2, 2, f"{'>>' if i == self.current_step else '  '} {step}", color)
        
        self.stdscr.addstr(h-3, 2, f"Action: {message}", curses.color_pair(3))
        
        progress = int((self.current_step / (len(self.steps)-1)) * 100) if len(self.steps) > 1 else 0
        progress_bar = '#' * (progress//10) + ' ' * (10 - (progress//10))
        self.stdscr.addstr(h-2, 2, f"Progress: [{progress_bar}] {progress}%")
        
        self.stdscr.refresh()
    
    def get_user_input(self, prompt, default=""):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(h//2, 2, prompt)
        if default:
            self.stdscr.addstr(f" (default: {default}): ")
        else:
            self.stdscr.addstr(": ")
        
        curses.echo()
        try:
            user_input = self.stdscr.getstr(h//2, len(prompt) + (len(default) + 12 if default else 2), 50).decode().strip()
        except curses.error:
            user_input = ""
        curses.noecho()
        
        return user_input if user_input else default
    
    def show_error(self, message):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(h-4, 2, "ERROR:", curses.color_pair(4))
        self.stdscr.addstr(h-3, 2, message)
        self.stdscr.addstr(h-2, 2, "Press any key to continue...")
        self.stdscr.getch()
    
    def run_command(self, cmd, message, background=False):
        self.draw_progress(message)
        
        try:
            if background:
                process = subprocess.Popen(cmd, shell=True)
                process.wait()
                return process.returncode == 0
            else:
                result = subprocess.run(cmd, shell=True, check=True)
                return True
        except subprocess.CalledProcessError as e:
            self.show_error(f"Command failed: {cmd}\nError: {e.stderr}" if e.stderr else str(e))
            return False
    
    def internet_setup(self):
        self.draw_progress("Checking internet connection...")
        
        if not self.run_command("ping -c 1 8.8.8.8", "Testing connection..."):
            self.show_error("No internet connection! Configure it manually.")
            return False
        return True
    
    def select_repository(self):
        while True:
            self.draw_progress("Repository selection")
            for i, repo in enumerate(self.repositories):
                self.stdscr.addstr(10+i, 2, f"{i+1}. {repo}")
            
            choice = self.get_user_input("Select repository (1-2)")
            if choice in ["1", "2"]:
                self.repo = int(choice) - 1
                return True
            self.show_error("Invalid choice! Enter 1 or 2")
    
    def disk_partition(self):
        self.draw_progress("Disk configuration")
        
        # Show available disks for reference
        try:
            disks = subprocess.check_output("lsblk -d -n -o NAME,SIZE", shell=True).decode()
            h, w = self.stdscr.getmaxyx()
            self.stdscr.addstr(10, 2, "Available disks:")
            for i, line in enumerate(disks.splitlines()):
                self.stdscr.addstr(12+i, 4, f"/dev/{line}")
        except subprocess.CalledProcessError:
            pass
        
        # Get disk device
        self.disk = self.get_user_input("Enter disk device (e.g. /dev/sda)")
        if not os.path.exists(self.disk):
            self.show_error(f"Device {self.disk} does not exist!")
            return False
        
        # Show partitions for reference
        try:
            parts = subprocess.check_output(f"lsblk -l -n -o NAME,SIZE {self.disk}", shell=True).decode()
            self.stdscr.addstr(16, 2, "Available partitions:")
            for i, line in enumerate(parts.splitlines()):
                if line.strip() and not line.startswith(self.disk[5:]):
                    self.stdscr.addstr(18+i, 4, f"/dev/{line}")
        except subprocess.CalledProcessError:
            pass
        
        # Get root partition
        self.root_part = self.get_user_input("Enter root partition (e.g. /dev/sda1)")
        if not os.path.exists(self.root_part):
            self.show_error(f"Partition {self.root_part} does not exist!")
            return False
        
        return True
    
    def user_setup(self):
        self.draw_progress("User configuration")
        
        while True:
            self.username = self.get_user_input("Enter username")
            if self.username:
                break
            self.show_error("Username cannot be empty!")
        
        while True:
            self.password = self.get_user_input("Enter user password")
            if self.password:
                break
            self.show_error("Password cannot be empty!")
        
        while True:
            self.root_password = self.get_user_input("Enter root password")
            if self.root_password:
                break
            self.show_error("Root password cannot be empty!")
        
        return True
    
    def install_system(self):
        # Format and mount
        if not self.run_command(f"mkfs.ext4 -F {self.root_part}", "Formatting partition..."):
            return False
            
        if not self.run_command(f"mount {self.root_part} /mnt", "Mounting partition..."):
            return False
        
        # Base system install
        repo_url = "http://deb.debian.org/debian"
        if self.repo == 0:
            cmd = f"debootstrap --include=systemd-sysv,sudo,network-manager unstable /mnt {repo_url}"
        else:
            cmd = f"debootstrap --include=systemd-sysv,sudo,network-manager stable /mnt {repo_url}"
            
        if not self.run_command(cmd, "Installing base system..."):
            return False

        # Configure system
        config_commands = [
            'echo "deb http://deb.debian.org/debian unstable main" > /mnt/etc/apt/sources.list.d/unstable.list',
            'echo "APT::Default-Release \\"stable\\";" > /mnt/etc/apt/apt.conf.d/99defaultrelease',
            'chroot /mnt apt update',
            'chroot /mnt apt install -y budgie-desktop lightdm network-manager-gnome',
            'chroot /mnt systemctl enable lightdm NetworkManager'
        ]
        
        for cmd in config_commands:
            if not self.run_command(cmd, "Configuring system..."):
                return False
        
        return True
    
    def system_config(self):
        # User setup
        user_commands = [
            f"chroot /mnt useradd -m {self.username}",
            f"chroot /mnt usermod -aG sudo {self.username}",
            f"echo '{self.username}:{self.password}' | chroot /mnt chpasswd",
            f"echo 'root:{self.root_password}' | chroot /mnt chpasswd"
        ]
        
        for cmd in user_commands:
            if not self.run_command(cmd, "Configuring users..."):
                return False
        
        # System identity
        os_release = '''NAME="MainiX"
PRETTY_NAME="MainiX Linux"
ID=mainix'''
        if not self.run_command(f'echo \'{os_release}\' > /mnt/etc/os-release', "Setting OS identity..."):
            return False
            
        return True
    
    def install_bootloader(self):
        bl_commands = [
            "chroot /mnt apt install -y grub-efi-amd64",
            f"chroot /mnt grub-install {self.disk}",
            r"sed -i 's/GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR=\"MainiX\"/' /mnt/etc/default/grub",
            r"sed -i 's/Debian/MainiX/g' /mnt/etc/default/grub",
            "chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg"
        ]
        
        for cmd in bl_commands:
            if not self.run_command(cmd, "Installing bootloader..."):
                return False
        
        return True
    
    def complete(self):
        self.draw_progress("Installation complete!")
        self.stdscr.addstr(15, 2, "MainiX installation complete. Press any key to reboot...")
        self.stdscr.getch()
        self.run_command("reboot", "Rebooting...")
        return True
    
    def run(self):
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        
        steps = [
            self.internet_setup,
            self.select_repository,
            self.disk_partition,
            self.user_setup,
            self.install_system,
            self.system_config,
            self.install_bootloader,
            self.complete
        ]
        
        for i, step in enumerate(steps):
            self.current_step = i
            if not step():
                self.show_error("Installation failed! Press any key to exit.")
                self.stdscr.getch()
                sys.exit(1)

def main(stdscr):
    installer = MainiXInstaller(stdscr)
    installer.run()

if __name__ == "__main__":
    curses.wrapper(main)
