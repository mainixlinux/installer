#!/usr/bin/env python3
import curses
import subprocess
import time
import sys
import os
import shutil
from typing import List, Tuple

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
        self.screen_session = "mainix_install"
        
    def draw_progress(self, message: str) -> None:
        """Update the progress display"""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Draw steps
        for i, step in enumerate(self.steps):
            color = curses.color_pair(1) if i == self.current_step else curses.color_pair(2)
            self.stdscr.addstr(i+2, 2, f"{'>>' if i == self.current_step else '  '} {step}", color)
        
        # Status message
        self.stdscr.addstr(h-3, 2, f"Action: {message}", curses.color_pair(3))
        
        # Progress bar
        progress = int((self.current_step / (len(self.steps)-1)) * 100) if len(self.steps) > 1 else 0
        progress_bar = '#' * (progress//10) + ' ' * (10 - (progress//10))
        self.stdscr.addstr(h-2, 2, f"Progress: [{progress_bar}] {progress}%")
        
        # Show last log entries
        self.show_log_tail()
        
        self.stdscr.refresh()
    
    def show_log_tail(self, lines: int = 5) -> None:
        """Show last lines from log file"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                log_lines = f.readlines()[-lines:]
            h, w = self.stdscr.getmaxyx()
            for i, line in enumerate(log_lines):
                self.stdscr.addstr(h-10+i, 2, line.strip()[:w-4])
    
    def run_command(self, cmd: str, message: str, background: bool = False) -> bool:
        """Execute a command either in foreground or background TTY"""
        self.draw_progress(message)
        
        # Log the command
        with open(self.log_file, 'a') as log:
            log.write(f"\n=== Executing: {cmd} ===\n")
        
        if background:
            # Run in separate screen session with logging
            screen_cmd = (
                f"screen -L -Logfile {self.log_file} -S {self.screen_session} -dm "
                f"bash -c '{cmd}; echo $? > /tmp/mainix_exit_code'"
            )
            
            try:
                subprocess.run(screen_cmd, shell=True, check=True)
                return True
            except subprocess.CalledProcessError as e:
                self.show_error(f"Failed to start background task: {str(e)}", cmd)
                return False
        else:
            try:
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                with open(self.log_file, 'a') as log:
                    if result.stdout:
                        log.write(f"STDOUT: {result.stdout}\n")
                    if result.stderr: 
                        log.write(f"STDERR: {result.stderr}\n")
                return True
            except subprocess.CalledProcessError as e:
                self.show_error(e.stderr if e.stderr else str(e), cmd)
                return False
    
    def check_background_task(self, timeout: int = 3600) -> bool:
        """Wait for background task to complete with timeout"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if screen session still exists
            if subprocess.run(
                f"screen -list | grep -q {self.screen_session}", 
                shell=True
            ).returncode != 0:
                break
            
            self.draw_progress("Running installation...")
            time.sleep(1)
        else:
            self.show_error("Background task timed out")
            return False
        
        # Check exit code
        try:
            with open('/tmp/mainix_exit_code', 'r') as f:
                exit_code = int(f.read().strip())
            return exit_code == 0
        except Exception as e:
            self.show_error(f"Failed to get exit status: {str(e)}")
            return False
    
    def show_error(self, error: str, cmd: str = None) -> None:
        """Display error message and wait for user input"""
        h, w = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(h-8, 2, "ERROR!", curses.color_pair(4))
        if cmd:
            self.stdscr.addstr(h-7, 2, f"Command: {cmd}")
        self.stdscr.addstr(h-6, 2, f"Details: {error[:w-4]}")
        self.stdscr.addstr(h-5, 2, f"See {self.log_file} for full logs")
        self.stdscr.addstr(h-4, 2, "Press any key to continue...")
        self.stdscr.refresh()
        self.stdscr.getch()
    
    def internet_setup(self) -> bool:
        """Test and configure internet connection"""
        if not self.run_command("ping -c 1 8.8.8.8", "Testing connection..."):
            if not self.run_command("iwctl", "Starting WiFi setup...", background=True):
                return False
            return self.check_background_task()
        return True
    
    def select_repository(self) -> bool:
        """Select package repository"""
        while True:
            self.draw_progress("Repository selection")
            
            for i, repo in enumerate(self.repositories):
                self.stdscr.addstr(10+i, 2, f"{i+1}. {repo}")
            
            self.stdscr.addstr(14, 2, "Select repository (number): ")
            curses.echo()
            try:
                repo_input = self.stdscr.getstr(14, 28, 2).decode()
                repo_num = int(repo_input)
                if 1 <= repo_num <= len(self.repositories):
                    self.repo = repo_num - 1
                    curses.noecho()
                    return True
            except (ValueError, curses.error):
                pass
            curses.noecho()
            self.show_error("Invalid repository number!")
        
    def disk_partition(self) -> bool:
        """Handle disk partitioning with interactive cfdisk"""
        # Disk selection
        disks = self.get_disks()
        if not disks:
            self.show_error("No suitable disks found!")
            return False
        
        disk_choice = self.show_menu(
            "Select installation disk",
            [d[1] for d in disks],
            "Select disk (number): "
        )
        if disk_choice is None:
            return False
        self.disk = disks[disk_choice][0]
        
        # Launch cfdisk interactively
        self.stdscr.clear()
        self.stdscr.refresh()
        
        # Save current terminal settings
        subprocess.run("stty sane", shell=True)
        
        # Run cfdisk in foreground
        try:
            cfdisk_result = subprocess.run(
                f"cfdisk {self.disk}",
                shell=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            self.show_error(f"cfdisk failed: {str(e)}")
            return False
        finally:
            # Restore curses window
            curses.endwin()
            self.stdscr.refresh()
        
        # Refresh partition table
        self.draw_progress("Refreshing partition table...")
        subprocess.run(f"partprobe {self.disk}", shell=True)
        time.sleep(2)  # Wait for changes to be detected
        
        # Partition selection
        partitions = self.get_partitions()
        if not partitions:
            self.show_error("No partitions found! Did you create and write them in cfdisk?")
            return False
        
        part_choice = self.show_menu(
            "Select root partition",
            [p[1] for p in partitions],
            "Select partition (number): "
        )
        if part_choice is None:
            return False
        
        self.root_part = partitions[part_choice][0]
        if not os.path.exists(self.root_part):
            self.show_error(f"Partition {self.root_part} not found!")
            return False
            
        return True    
    def get_disks(self) -> List[Tuple[str, str]]:
        """Get list of available disks"""
        disks = []
        try:
            lsblk_output = subprocess.getoutput(
                "lsblk -d -n -o NAME,SIZE,MODEL"
            ).split('\n')
            
            for line in lsblk_output:
                if line.strip():
                    parts = line.split(maxsplit=2)
                    disk_name = parts[0]
                    # Exclude loop devices and partitions
                    if not disk_name.startswith('loop') and not any(c.isdigit() for c in disk_name):
                        size = parts[1]
                        model = parts[2] if len(parts) > 2 else "Unknown"
                        disks.append((f"/dev/{disk_name}", f"{disk_name} ({size}, {model})"))
        except Exception as e:
            self.show_error(f"Error getting disk list: {str(e)}")
        return disks
    
    def get_partitions(self) -> List[Tuple[str, str]]:
        """Get list of partitions on selected disk"""
        partitions = []
        try:
            lsblk_output = subprocess.getoutput(
                f"lsblk -l -n -o NAME,SIZE,FSTYPE {self.disk}"
            ).split('\n')
            
            for line in lsblk_output:
                if line.strip() and not line.startswith(self.disk[5:]):
                    parts = line.split()
                    if len(parts) >= 2:
                        part_name = parts[0]
                        size = parts[1]
                        fstype = parts[2] if len(parts) > 2 else "unknown"
                        partitions.append((f"/dev/{part_name}", f"{part_name} ({size}, {fstype})"))
        except Exception as e:
            self.show_error(f"Error getting partition list: {str(e)}")
        return partitions
    
    def show_menu(self, title: str, items: List[str], prompt: str) -> int:
        """Display a menu and get user selection"""
        while True:
            self.draw_progress(title)
            
            for i, item in enumerate(items):
                self.stdscr.addstr(10+i, 2, f"{i+1}. {item}")
            
            self.stdscr.addstr(10+len(items)+1, 2, prompt)
            curses.echo()
            try:
                user_input = self.stdscr.getstr(10+len(items)+1, len(prompt)+2, 3).decode().strip()
                if user_input.upper() == 'Q':
                    return None
                choice = int(user_input) - 1
                if 0 <= choice < len(items):
                    curses.noecho()
                    return choice
            except (ValueError, curses.error):
                pass
            curses.noecho()
            self.show_error("Invalid selection!")
    
    def user_setup(self) -> bool:
        """Configure user accounts"""
        self.draw_progress("User configuration")
        
        while True:
            self.stdscr.addstr(10, 2, "Username: ")
            curses.echo()
            self.username = self.stdscr.getstr(10, 20, 20).decode().strip()
            curses.noecho()
            if self.username:
                break
            self.show_error("Username cannot be empty!")
        
        while True:
            self.stdscr.addstr(11, 2, "User password: ")
            self.password = self.stdscr.getstr(11, 24, 20).decode().strip()
            if self.password:
                break
            self.show_error("Password cannot be empty!")
        
        while True:
            self.stdscr.addstr(12, 2, "Root password: ")
            self.root_password = self.stdscr.getstr(12, 16, 20).decode().strip()
            if self.root_password:
                break
            self.show_error("Root password cannot be empty!")
        
        return True
    
    def install_system(self) -> bool:
        """Install base system"""
        # Format and mount
        if not self.run_command(f"mkfs.ext4 -F {self.root_part}", "Formatting partition..."):
            return False
            
        if not self.run_command(f"mount {self.root_part} /mnt", "Mounting partition..."):
            return False
        
        # Base system install
        repo_url = "http://deb.debian.org/debian"
        if self.repo == 0:
            cmd = ("debootstrap --include=systemd-sysv,sudo,network-manager "
                  f"unstable /mnt {repo_url}")
        else:
            cmd = ("debootstrap --include=systemd-sysv,sudo,network-manager "
                  f"stable /mnt {repo_url}")
            
        if not self.run_command(cmd, "Installing base system...", background=True):
            return False
        
        if not self.check_background_task():
            return False

        # Configure repositories
        repo_cmds = [
            'echo "deb http://deb.debian.org/debian unstable main" > /mnt/etc/apt/sources.list.d/unstable.list',
            'echo "APT::Default-Release \"stable\";" > /mnt/etc/apt/apt.conf.d/99defaultrelease'
        ]
        
        for cmd in repo_cmds:
            if not self.run_command(cmd, "Configuring repositories..."):
                return False
        
        # Install packages
        pkg_cmds = [
            "chroot /mnt apt update",
            "chroot /mnt apt install -y budgie-desktop lightdm network-manager-gnome",
            "chroot /mnt systemctl enable lightdm NetworkManager"
        ]
        
        for cmd in pkg_cmds:
            if not self.run_command(cmd, "Installing packages...", background=True):
                return False
            if not self.check_background_task():
                return False
        
        return True
    
    def system_config(self) -> bool:
        """Configure system settings"""
        # User setup
        user_cmds = [
            f"chroot /mnt useradd -m {self.username}",
            f"chroot /mnt usermod -aG sudo {self.username}",
            f"echo '{self.username}:{self.password}' | chroot /mnt chpasswd",
            f"echo 'root:{self.root_password}' | chroot /mnt chpasswd"
        ]
        
        for cmd in user_cmds:
            if not self.run_command(cmd, "Configuring users..."):
                return False
        
        # System identity
        os_release = '''NAME="MainiX"
PRETTY_NAME="MainiX Linux"
ID=mainix'''
        if not self.run_command(f'echo \'{os_release}\' > /mnt/etc/os-release', 
                              "Setting OS identity..."):
            return False
            
        return True
    
    def install_bootloader(self) -> bool:
        """Install and configure bootloader"""
        bl_cmds = [
            "chroot /mnt apt install -y grub-efi-amd64",
            f"chroot /mnt grub-install {self.disk}",
            r"sed -i 's/GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR=\"MainiX\"/' /mnt/etc/default/grub",
            r"sed -i 's/Debian/MainiX/g' /mnt/etc/default/grub",
            "chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg"
        ]
        
        for cmd in bl_cmds:
            if not self.run_command(cmd, "Configuring bootloader...", background=True):
                return False
            if not self.check_background_task():
                return False
        
        return True
    
    def complete(self) -> bool:
        """Finalize installation"""
        self.draw_progress("Installation complete!")
        self.stdscr.addstr(15, 2, "MainiX installation complete. Press any key to reboot...")
        self.stdscr.getch()
        self.run_command("reboot", "Rebooting system...")
        return True
    
    def run(self) -> None:
        """Main installation loop"""
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        
        # Initialize log
        with open(self.log_file, 'w') as f:
            f.write("MainiX Installer Log\n")
        
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
                self.show_error("Installation failed", "Restarting installer...")
                time.sleep(2)
                self.restart_installer()
                break
    
    def restart_installer(self) -> None:
        """Restart the installer"""
        python = sys.executable
        os.execl(python, python, *sys.argv)

def main(stdscr):
    installer = MainiXInstaller(stdscr)
    installer.run()

if __name__ == "__main__":
    # Check for required tools
    if not shutil.which("screen"):
        print("Error: 'screen' is required but not installed")
        sys.exit(1)
    
    curses.wrapper(main)
