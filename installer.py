#!/usr/bin/env python3
import curses
import subprocess
import time
import sys
import os
import select

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
        self.active_processes = []
        
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
        
        if self.active_processes:
            self.stdscr.addstr(h-5, 2, f"Background tasks: {len(self.active_processes)} running")
        
        self.stdscr.refresh()
    
    def run_command(self, cmd, message, background=False):
        self.draw_progress(message)
        
        if background:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            self.active_processes.append(process)
            return True
        else:
            try:
                result = subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
                return True
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else str(e)
                self.stdscr.addstr(20, 2, f"Error in command: {cmd}")
                self.stdscr.addstr(21, 2, f"Error details: {error_msg[:50]}...")
                self.stdscr.addstr(22, 2, "Press any key to restart installer...")
                self.stdscr.refresh()
                self.stdscr.getch()
                self.restart_installer()
                return False
    
    def wait_for_background(self, message="Waiting for background tasks..."):
        while self.active_processes:
            self.draw_progress(message)
            
            for process in self.active_processes[:]:
                if process.poll() is not None:
                    self.active_processes.remove(process)
                    if process.returncode != 0:
                        error_output = process.stderr.read() if process.stderr else "Unknown error"
                        self.stdscr.addstr(22, 2, f"Task failed: {error_output[:50]}...")
                        self.stdscr.refresh()
                        time.sleep(3)
                        return False
            
            time.sleep(1)
        return True
    
    def restart_installer(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def internet_setup(self):
        self.draw_progress("Checking internet connection...")
        
        if not self.run_command("ping -c 1 8.8.8.8", "Testing connection..."):
            self.run_command("iwctl", "Configuring Wi-Fi...", background=True)
            return self.wait_for_background("Finishing Wi-Fi setup...")
        return True
    
    def select_repository(self):
        while True:
            self.draw_progress("Repository selection")
            
            for i, repo in enumerate(self.repositories):
                self.stdscr.addstr(10+i, 2, f"{i+1}. {repo}")
            
            self.stdscr.addstr(14, 2, "Select repository (number): ")
            curses.echo()
            repo_input = self.stdscr.getstr(14, 28, 2).decode()
            curses.noecho()
            
            try:
                repo_num = int(repo_input)
                if 1 <= repo_num <= len(self.repositories):
                    self.repo = repo_num - 1
                    break
                else:
                    self.stdscr.addstr(16, 2, "Invalid repository number! Try again.")
                    self.stdscr.getch()
            except ValueError:
                self.stdscr.addstr(16, 2, "Please enter a valid number!")
                self.stdscr.getch()
        
        return True
    
    def disk_partition(self):
        # Выбор диска
        while True:
            self.draw_progress("Выберите диск для установки")
            
            # Получаем список дисков (исключая loop устройства и разделы)
            disks = []
            try:
                lsblk_output = subprocess.getoutput("lsblk -d -n -o NAME,SIZE,MODEL").split('\n')
                for line in lsblk_output:
                    if line.strip():
                        parts = line.split(maxsplit=2)
                        disk_name = parts[0]
                        # Исключаем loop устройства и разделы
                        if not disk_name.startswith('loop') and not any(c in disk_name for c in ['0','1','2','3','4','5','6','7','8','9']):
                            size = parts[1]
                            model = parts[2] if len(parts) > 2 else "Unknown"
                            disks.append((f"/dev/{disk_name}", f"{disk_name} ({size}, {model})"))
            except Exception as e:
                self.stdscr.addstr(10, 2, f"Ошибка получения списка дисков: {str(e)}")
                self.stdscr.getch()
                return False
    
            if not disks:
                self.stdscr.addstr(10, 2, "Не найдено подходящих дисков!")
                self.stdscr.getch()
                return False
    
            # Отображаем список дисков
            for i, (_, disk_info) in enumerate(disks):
                self.stdscr.addstr(10 + i, 2, f"{i + 1}. {disk_info}")
    
            self.stdscr.addstr(10 + len(disks) + 1, 2, "Выберите диск (номер) или Q для выхода: ")
            curses.echo()
            disk_input = self.stdscr.getstr(10 + len(disks) + 1, 40, 3).decode().strip().upper()
            curses.noecho()
    
            if disk_input == 'Q':
                return False
    
            try:
                disk_num = int(disk_input)
                if 1 <= disk_num <= len(disks):
                    self.disk, _ = disks[disk_num - 1]
                    break
                else:
                    self.stdscr.addstr(10 + len(disks) + 3, 2, "Неверный номер диска! Попробуйте снова.")
                    self.stdscr.getch()
            except ValueError:
                self.stdscr.addstr(10 + len(disks) + 3, 2, "Введите число или Q для выхода!")
                self.stdscr.getch()
    
        # Разметка диска
        self.draw_progress(f"Разметка диска {self.disk} (запуск cfdisk)")
        if subprocess.run(f"cfdisk {self.disk}", shell=True).returncode != 0:
            self.stdscr.addstr(20, 2, "Ошибка при разметке диска!")
            self.stdscr.getch()
            return False
    
        # Выбор раздела для корневой файловой системы
        while True:
            self.draw_progress(f"Выберите раздел на {self.disk} для корневой системы")
            
            # Получаем список разделов на выбранном диске
            partitions = []
            try:
                lsblk_output = subprocess.getoutput(f"lsblk -l -n -o NAME,SIZE,FSTYPE {self.disk}").split('\n')
                for line in lsblk_output:
                    if line.strip() and not line.startswith(self.disk[5:]):  # Исключаем сам диск
                        parts = line.split()
                        if len(parts) >= 2:
                            part_name = parts[0]
                            size = parts[1]
                            fstype = parts[2] if len(parts) > 2 else "unknown"
                            partitions.append((f"/dev/{part_name}", f"{part_name} ({size}, {fstype})"))
            except Exception as e:
                self.stdscr.addstr(10, 2, f"Ошибка получения списка разделов: {str(e)}")
                self.stdscr.getch()
                return False
    
            if not partitions:
                self.stdscr.addstr(10, 2, "На диске нет разделов! Создайте их в cfdisk.")
                self.stdscr.getch()
                return False
    
            # Отображаем список разделов
            for i, (_, part_info) in enumerate(partitions):
                self.stdscr.addstr(10 + i, 2, f"{i + 1}. {part_info}")
    
            self.stdscr.addstr(10 + len(partitions) + 1, 2, "Выберите раздел для / (номер) или Q для выхода: ")
            curses.echo()
            part_input = self.stdscr.getstr(10 + len(partitions) + 1, 45, 3).decode().strip().upper()
            curses.noecho()
    
            if part_input == 'Q':
                return False
    
            try:
                part_num = int(part_input)
                if 1 <= part_num <= len(partitions):
                    self.root_part, _ = partitions[part_num - 1]
                    break
                else:
                    self.stdscr.addstr(10 + len(partitions) + 3, 2, "Неверный номер раздела! Попробуйте снова.")
                    self.stdscr.getch()
            except ValueError:
                self.stdscr.addstr(10 + len(partitions) + 3, 2, "Введите число или Q для выхода!")
                self.stdscr.getch()
    
        # Проверка существования раздела
        if not os.path.exists(self.root_part):
            self.stdscr.addstr(10 + len(partitions) + 3, 2, f"Ошибка: Раздел {self.root_part} не найден!")
            self.stdscr.getch()
            return False
    
        return True
        
        subprocess.run(f"cfdisk {self.disk}", shell=True)
        partitions = subprocess.getoutput(f"lsblk {self.disk} -o NAME,SIZE -n").split('\n')[1:]
        self.stdscr.addstr(19, 2, "Select root partition (number): ")
        curses.echo()
        part_num = int(self.stdscr.getstr(19, 30, 2).decode())
        curses.noecho()
        self.root_part = f"/dev/{partitions[part_num-1].split()[0]}"
        
        if not os.path.exists(self.root_part):
            self.stdscr.addstr(21, 2, f"Error: Partition {self.root_part} not found!")
            self.stdscr.getch()
            return False
            
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
                self.stdscr.addstr(12, 2, " " * 30)
        
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
    
    def install_system(self):
        if not self.run_command(f"mkfs.ext4 -F {self.root_part}", "Formatting root partition..."):
            return False
            
        if not self.run_command(f"mount {self.root_part} /mnt", "Mounting root partition..."):
            return False
        
        repo_url = "http://deb.debian.org/debian"
        if self.repo == 0:
            cmd = f"debootstrap --include=systemd-sysv,sudo,network-manager unstable /mnt {repo_url}"
        else:
            cmd = f"debootstrap --include=systemd-sysv,sudo,network-manager stable /mnt {repo_url}"
            
        if not self.run_command(cmd, "Installing base system...", background=True):
            return False
        
        if not self.wait_for_background("Finishing base installation..."):
            return False

        if not self.run_command('echo "deb http://deb.debian.org/debian unstable main" > /mnt/etc/apt/sources.list.d/unstable.list', 
                              "Adding unstable repo..."):
            return False
            
        if not self.run_command('echo "APT::Default-Release \"stable\";" > /mnt/etc/apt/apt.conf.d/99defaultrelease', 
                              "Setting default release..."):
            return False
            
        if not self.run_command('chroot /mnt apt update', "Updating package lists...", background=True):
            return False
            
        if not self.run_command('chroot /mnt apt install -y budgie-desktop lightdm network-manager-gnome', 
                              "Installing Budgie desktop...", background=True):
            return False
        
        return self.wait_for_background("Finishing desktop installation...")
    
    def system_config(self):
        
        if not self.run_command(f"chroot /mnt useradd -m {self.username}", "Creating user..."):
            return False
            
        if not self.run_command(f"chroot /mnt usermod -aG sudo {self.username}", "Adding to sudo group..."):
            return False
            
        if not self.run_command(f"echo '{self.username}:{self.password}' | chroot /mnt chpasswd", 
                              "Setting user password..."):
            return False
            
        if not self.run_command(f"echo 'root:{self.root_password}' | chroot /mnt chpasswd", 
                              "Setting root password..."):
            return False
        
        
        os_release = '''NAME="MainiX"
PRETTY_NAME="MainiX Linux"
ID=mainix'''
        if not self.run_command(f'echo \'{os_release}\' > /mnt/etc/os-release', "Renaming system..."):
            return False

        
        if not self.run_command("chroot /mnt systemctl enable lightdm NetworkManager", 
                              "Enabling services...", background=True):
            return False
        
        return self.wait_for_background("Finishing system configuration...")
    
    def install_bootloader(self):
        if not self.run_command("chroot /mnt apt install -y grub-efi-amd64", "Installing GRUB...", background=True):
            return False
            
        if not self.run_command(f"chroot /mnt grub-install {self.disk}", "Installing bootloader...", background=True):
            return False
        
        
        rename_commands = [
            r"sed -i 's/GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR=\"MainiX\"/' /mnt/etc/default/grub",
            r"sed -i 's/Debian/MainiX/g' /mnt/etc/default/grub",
            "chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg"
        ]

        for cmd in rename_commands:
            if not self.run_command(cmd, "Configuring GRUB...", background=True):
                return False
        
        return self.wait_for_background("Finishing bootloader setup...")
    
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
                self.stdscr.addstr(20, 2, "Error! Press any key to restart installer...")
                self.stdscr.getch()
                self.restart_installer()
                break

def main(stdscr):
    installer = MainiXInstaller(stdscr)
    installer.run()

if __name__ == "__main__":
    curses.wrapper(main)
