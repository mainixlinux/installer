#!/usr/bin/env python3
import curses
import subprocess
import time
import sys
import os
import shutil
from typing import List, Tuple, Optional
# если ты это читаешь иди нахуй отсюда опенсурса не сущевствует
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
        
        for i, step in enumerate(self.steps):
            color = curses.color_pair(1) if i == self.current_step else curses.color_pair(2)
            self.stdscr.addstr(i+2, 2, f"{'>>' if i == self.current_step else '  '} {step}", color)
        
        self.stdscr.addstr(h-3, 2, f"Action: {message}", curses.color_pair(3))
        
        progress = int((self.current_step / (len(self.steps)-1)) * 100) if len(self.steps) > 1 else 0
        progress_bar = '#' * (progress//10) + ' ' * (10 - (progress//10))
        self.stdscr.addstr(h-2, 2, f"Progress: [{progress_bar}] {progress}%")
        
        self.show_log_tail()
        self.stdscr.refresh()
    
    def show_log_tail(self, lines: int = 5) -> None:
        """Show last lines from log file"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    log_lines = f.readlines()[-lines:]
                h, w = self.stdscr.getmaxyx()
                for i, line in enumerate(log_lines):
                    if i < h-12:
                        self.stdscr.addstr(h-12+i, 2, line.strip()[:w-4])
            except Exception:
                pass
    
    def log_command(self, cmd: str) -> None:
        """Log command execution"""
        with open(self.log_file, 'a') as f:
            f.write(f"\n=== Executing: {cmd} ===\n")
    
    def log_output(self, stdout: str, stderr: str) -> None:
        """Log command output"""
        with open(self.log_file, 'a') as f:
            if stdout:
                f.write(f"STDOUT: {stdout}\n")
            if stderr:
                f.write(f"STDERR: {stderr}\n")
    
    def run_command(self, cmd: str, message: str, background: bool = False) -> bool:
        """Execute a command either in foreground or background"""
        self.draw_progress(message)
        self.log_command(cmd)
        
        if background:
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
                self.log_output(result.stdout, result.stderr)
                return True
            except subprocess.CalledProcessError as e:
                self.log_output(e.stdout, e.stderr)
                self.show_error(e.stderr if e.stderr else str(e), cmd)
                return False
    
    def check_background_task(self, timeout: int = 3600) -> bool:
        """Wait for background task to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
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
        
        try:
            with open('/tmp/mainix_exit_code', 'r') as f:
                exit_code = int(f.read().strip())
            return exit_code == 0
        except Exception as e:
            self.show_error(f"Failed to get exit status: {str(e)}")
            return False
    
    def show_error(self, error: str, cmd: str = None) -> None:
        """Display error message"""
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
        """Configure internet connection"""
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
            
            choice = self.get_user_choice(len(self.repositories), "Select repository (number): ")
            if choice is None:
                return False
            
            self.repo = choice
            return True
    
    def disk_partition(self) -> bool:
        """Interactive disk partitioning"""
        # Disk selection
        disks = self.get_available_disks()
        if not disks:
            self.show_error("No suitable disks found!")
            return False
        
        self.draw_progress("Select installation disk")
        for i, (dev, size, model) in enumerate(disks):
            self.stdscr.addstr(10+i, 2, f"{i+1}. {dev} ({size}, {model})")
        
        disk_choice = self.get_user_choice(len(disks), "Select disk (number): ")
        if disk_choice is None:
            return False
        self.disk = disks[disk_choice][0]
        
        # Interactive cfdisk
        if not self.run_interactive_cfdisk():
            return False
        
        # Wait and refresh partition table
        time.sleep(2)
        self.run_command(f"partprobe {self.disk}", "Refreshing partition table...")
        time.sleep(2)
        
        # Partition selection
        partitions = self.get_disk_partitions()
        if not partitions:
            self.show_error("No partitions found! Please:")
            self.stdscr.addstr(21, 2, "1. Create partitions in cfdisk")
            self.stdscr.addstr(22, 2, "2. Select 'Write' to save changes")
            self.stdscr.addstr(23, 2, "3. Make sure partition table type is correct")
            self.stdscr.getch()
            return False
        
        self.draw_progress("Select root partition")
        for i, (dev, size, fstype) in enumerate(partitions):
            self.stdscr.addstr(10+i, 2, f"{i+1}. {dev} ({size}, {fstype})")
        
        part_choice = self.get_user_choice(len(partitions), "Select partition (number): ")
        if part_choice is None:
            return False
        self.root_part = partitions[part_choice][0]
        
        # Verify partition
        if not self.verify_partition():
            return False
            
        return True
    
    def get_available_disks(self) -> List[Tuple[str, str, str]]:
        """Get list of available disks"""
        try:
            output = subprocess.check_output(
                "lsblk -d -n -o NAME,SIZE,MODEL,PATH,RO,RM,ROTA",
                shell=True,
                universal_newlines=True
            ).splitlines()
            
            disks = []
            for line in output:
                if line.strip():
                    parts = line.split(maxsplit=6)
                    # Skip read-only and removable devices
                    if parts[4] == '0' and parts[5] == '0':
                        disks.append((f"/dev/{parts[0]}", parts[1], parts[2]))
            return disks
        except Exception as e:
            self.log_output("", f"Failed to get disks: {e}")
            return []
    
    def run_interactive_cfdisk(self) -> bool:
        """Run cfdisk in interactive mode"""
        self.stdscr.clear()
        self.stdscr.refresh()
        curses.endwin()  # Temporarily disable curses
        
        try:
            # Reset terminal and run cfdisk
            subprocess.run("stty sane", shell=True)
            result = subprocess.run(
                f"cfdisk {self.disk}",
                shell=True
            )
            return result.returncode == 0
        except Exception as e:
            self.log_output("", f"cfdisk failed: {e}")
            return False
        finally:
            # Restore curses
            curses.flushinp()
            self.stdscr.refresh()
            curses.doupdate()
    
    def get_disk_partitions(self) -> List[Tuple[str, str, str]]:
        """Get partitions on selected disk"""
        try:
            output = subprocess.check_output(
                f"lsblk -l -n -o NAME,SIZE,FSTYPE,MOUNTPOINT {self.disk}",
                shell=True,
                universal_newlines=True
            ).splitlines()
            
            partitions = []
            for line in output:
                if line.strip() and not line.startswith(self.disk[5:]):
                    parts = line.split(maxsplit=3)
                    if len(parts) >= 3:
                        # Skip extended and swap partitions
                        if not any(x in parts[2].lower() for x in ['extended', 'swap']):
                            partitions.append((f"/dev/{parts[0]}", parts[1], parts[2]))
            return partitions
        except Exception as e:
            self.log_output("", f"Failed to get partitions: {e}")
            return []
    
    def verify_partition(self) -> bool:
        """Verify partition exists and is usable"""
        checks = [
            f"test -b {self.root_part}",
            f"lsblk -n -o FSTYPE {self.root_part} | grep -v '^$'",
            f"blockdev --getsize64 {self.root_part} | grep -v '^0$'"
        ]
        
        for check in checks:
            if subprocess.call(check, shell=True) != 0:
                self.show_error(f"Partition verification failed: {check}")
                return False
        return True
    
    def get_user_choice(self, max_num: int, prompt: str) -> Optional[int]:
        """Get validated user choice"""
        while True:
            self.stdscr.addstr(20, 2, prompt)
            curses.echo()
            try:
                choice = self.stdscr.getstr(20, len(prompt)+2, 3).decode()
                if choice.lower() == 'q':
                    curses.noecho()
                    return None
                choice = int(choice) - 1
                if 0 <= choice < max_num:
                    curses.noecho()
                    return choice
            except (ValueError, curses.error):
                pass
            curses.noecho()
            self.show_error(f"Please enter number 1-{max_num} or Q to cancel")
    
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
    # Check for required tools
    required_tools = ["screen", "lsblk", "partprobe", "cfdisk"]
    missing = [tool for tool in required_tools if not shutil.which(tool)]
    
    if missing:
        stdscr.addstr(0, 0, f"Error: Missing required tools: {', '.join(missing)}")
        stdscr.addstr(1, 0, "Press any key to exit...")
        stdscr.getch()
        sys.exit(1)
    
    installer = MainiXInstaller(stdscr)
    installer.run()

if __name__ == "__main__":
    curses.wrapper(main)
