#!/usr/bin/env python3
import curses
import subprocess
import time
import sys
import os

class MainiXInstaller:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_step = 0
        self.steps = [
            "Connect to Internet",
            "Disk Partitioning",
            "User Accounts",
            "Select Profile",
            "Formatting",
            "System Installation",
            "System Configuration",
            "Bootloader Installation",
            "Completion"
        ]
        self.username = ""
        self.password = ""
        self.root_password = ""
        self.disk = ""
        self.profile = 0
        self.profiles = [
            "Desktop",
            "FTP Server",
            "Web Server",
            "Base"
        ]
        
    def draw_progress(self, message):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Draw progress steps
        for i, step in enumerate(self.steps):
            color = curses.color_pair(1) if i == self.current_step else curses.color_pair(2)
            self.stdscr.addstr(i+2, 2, f"{'>>' if i == self.current_step else '  '} {step}", color)
        
        # Current action
        self.stdscr.addstr(h-3, 2, f"Action: {message}", curses.color_pair(3))
        
        # Progress calculation
        progress = int((self.current_step / (len(self.steps)-1)) * 100) if len(self.steps) > 1 else 0
        progress_bar = '#' * (progress//10) + ' ' * (10 - progress//10)
        self.stdscr.addstr(h-2, 2, f"Progress: [{progress_bar}] {progress}%")
        
        self.stdscr.refresh()
    
    def run_command(self, cmd, message):
        self.draw_progress(message)
        try:
            subprocess.run(cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.stdscr.addstr(20, 2, f"Error in command: {cmd}")
            self.stdscr.addstr(21, 2, "Press any key to restart installer...")
            self.stdscr.getch()
            self.restart_installer()
            return False
    
    def restart_installer(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def internet_setup(self):
        self.draw_progress("Checking internet connection...")
        time.sleep(2)
        
        if not self.run_command("ping -c 1 8.8.8.8", "Testing connection..."):
            self.draw_progress("Configuring Wi-Fi...")
            time.sleep(1)
            subprocess.run("iwctl", shell=True)
        
        return True
    
    def disk_partition(self):
        while True:
            self.draw_progress("Listing disks...")
            disks = subprocess.getoutput("lsblk -d -o NAME,SIZE -n").split('\n')
            
            for i, disk in enumerate(disks):
                self.stdscr.addstr(10+i, 2, f"{i+1}. {disk}")
            
            self.stdscr.addstr(15, 2, "Select disk (number): ")
            curses.echo()
            disk_input = self.stdscr.getstr(15, 23, 2).decode()
            curses.noecho()
            
            try:
                disk_num = int(disk_input)
                if 1 <= disk_num <= len(disks):
                    self.disk = f"/dev/{disks[disk_num-1].split()[0]}"
                    break
                else:
                    self.stdscr.addstr(17, 2, "Invalid disk number! Try again.")
                    self.stdscr.getch()
            except ValueError:
                self.stdscr.addstr(17, 2, "Please enter a valid number!")
                self.stdscr.getch()
        
        self.run_command(f"cfdisk {self.disk}", "Partitioning disk...")
        return True
    
    def user_setup(self):
        self.draw_progress("User configuration")
        
        while not self.username:
            self.stdscr.addstr(10, 2, "Username: ")
            curses.echo()
            self.username = self.stdscr.getstr(10, 20, 20).decode().strip()
            curses.noecho()
            if not self.username:
                self.stdscr.addstr(12, 2, "Username cannot be empty!")
                self.stdscr.getch()
                self.stdscr.addstr(12, 2, " " * 30)  # Clear error message
        
        while not self.password:
            self.stdscr.addstr(11, 2, "User password: ")
            self.password = self.stdscr.getstr(11, 24, 20).decode().strip()
            if not self.password:
                self.stdscr.addstr(12, 2, "Password cannot be empty!")
                self.stdscr.getch()
                self.stdscr.addstr(12, 2, " " * 30)
        
        while not self.root_password:
            self.stdscr.addstr(12, 2, "Root password: ")
            self.root_password = self.stdscr.getstr(12, 16, 20).decode().strip()
            if not self.root_password:
                self.stdscr.addstr(13, 2, "Root password cannot be empty!")
                self.stdscr.getch()
                self.stdscr.addstr(13, 2, " " * 30)
        
        curses.noecho()
        return True
    
    def select_profile(self):
        while True:
            self.draw_progress("Profile selection")
            
            for i, profile in enumerate(self.profiles):
                self.stdscr.addstr(10+i, 2, f"{i+1}. {profile}")
            
            self.stdscr.addstr(14, 2, "Select profile (number): ")
            curses.echo()
            profile_input = self.stdscr.getstr(14, 28, 2).decode()
            curses.noecho()
            
            try:
                profile_num = int(profile_input)
                if 1 <= profile_num <= len(self.profiles):
                    self.profile = profile_num - 1
                    break
                else:
                    self.stdscr.addstr(16, 2, "Invalid profile number! Try again.")
                    self.stdscr.getch()
            except ValueError:
                self.stdscr.addstr(16, 2, "Please enter a valid number!")
                self.stdscr.getch()
        
        return True
    
    def format_disk(self):
        self.run_command(f"mkfs.ext4 {self.disk}1 &", "Formatting as ext4...")
        self.run_command(f"mount {self.disk}1 /mnt &", "Mounting partition...")
        return True
    
    def install_system(self):
        self.run_command("pacstrap /mnt base linux linux-firmware &", "Installing base system...")
        
        if self.profile == 0:  # Budgie
            self.run_command("arch-chroot /mnt pacman -S --noconfirm budgie-desktop lightdm lightdm-gtk-greeter networkmanager network-manager-applet nm-connection-editor &", "Installing Budgie...")
        elif self.profile == 1:  # FTP+SSH
            self.run_command("arch-chroot /mnt pacman -S --noconfirm openssh vsftpd mc networkmanager nmcli htop &", "Installing server packages...")
        elif self.profile == 2:  # nginx
            self.run_command("arch-chroot /mnt pacman -S --noconfirm openssh nginx nmcli networkmanager htop &", "Installing web server...")
        elif self.profile == 3:
            self.run_command("arch-chroot /mnt pacman -S --noconfirm openssh nmcli networkmanager htop &", "Installing ...")
        
        return True
    
    def system_config(self):
        self.run_command(f"arch-chroot /mnt useradd -m {self.username} &", "Creating user...")
        self.run_command(f"echo '{self.username}:{self.password}' & | arch-chroot /mnt chpasswd &", "Setting user password...")
        self.run_command(f"echo 'root:{self.root_password}' & | arch-chroot /mnt chpasswd &", "Setting root password...")
        
        # Rename system
        os_release = '''NAME="MainiX"
PRETTY_NAME="MainiX Linux"
ID=mainix'''
        self.run_command(f'echo \'{os_release}\' > /mnt/etc/os-release', "Setting system (1/2)...")

        for cmd in grub_config_commands:
            self.run_command(cmd, "Updating GRUB configuration...")

        if self.profile == 0:  # Budgie
            self.run_command("arch-chroot /mnt systemctl enable lightdm &", "Setting system (2/2)...")
        elif self.profile == 1:  # FTP+SSH
            self.run_command("arch-chroot /mnt systemctl enable sshd vsftpd &", "Setting system (2/3)...")
        elif self.profile == 2:  # nginx
            self.run_command("arch-chroot /mnt systemctl enable sshd nginx &", "Setting system (2/3)...")
	elif self.profile == 3:  # base
            self.run_command("arch-chroot /mnt systemctl enable sshd &", "Setting system (2/3)...")
	
        return True
    
    def install_bootloader(self):
        self.run_command(f"arch-chroot /mnt grub-install {self.disk}", "Installing GRUB...")
        rename_commands = [
            r"sed -i 's/GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR=\"MainiX\"/' /mnt/etc/default/grub",
            
            r"sed -i 's/Arch Linux/MainiX Linux/g' /mnt/etc/default/grub",
            r"sed -i 's/Arch/MainiX/g' /mnt/etc/grub.d/10_linux",
            "arch-chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg"
        ]

        for cmd in rename_commands:
            self.run_command(cmd, "Installing GRUB...")
        return True
    
    def complete(self):
        self.draw_progress("Installation complete!")
        self.stdscr.addstr(15, 2, "MainiX installation complete. Press any key to reboot...")
        self.stdscr.getch()
        subprocess.run("reboot", shell=True)
    
    def run(self):
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        
        steps = [
            self.internet_setup,
            self.disk_partition,
            self.user_setup,
            self.select_profile,
            self.format_disk,
            self.install_system,
            self.system_config,
            self.install_bootloader,
            self.complete
        ]
        
        for i, step in enumerate(steps):
            self.current_step = i
            if not step():
                self.stdscr.addstr(20, 2, "Error! Press any key to restart installer...")
                self.stdscr.getch()
                self.restart_installer()
                break

def main(stdscr):
    installer = MainiXInstaller(stdscr)
    installer.run()

if __name__ == "__main__":
    curses.wrapper(main)
