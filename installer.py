#!/usr/bin/env python3
import os
import subprocess
import getpass
import shutil
import argparse
import sys

def run_command(cmd, check=True):
    """Execute shell command with better error handling"""
    print(f"\n\033[1;34mExecuting: {cmd}\033[0m")
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
            print(f"\033[1;33m{result.stderr}\033[0m")
        return result
    except subprocess.CalledProcessError as e:
        print(f"\033[1;31mCommand failed: {e}\033[0m")
        print(f"\033[1;31mError output: {e.stderr}\033[0m")
        if check:
            raise
        return e

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='MainiX Installation Script')
    parser.add_argument('--resume-from', type=int, choices=range(1, 8), 
                      help='Resume installation from specific step (1-7)')
    parser.add_argument('--disk', help='Specify disk to use (e.g. sda)')
    parser.add_argument('--root-part', help='Specify root partition (e.g. sda1)')
    parser.add_argument('--mount-point', default='/mnt', help='Specify mount point')
    return parser.parse_args()

def ensure_ready(args):
    if not os.path.exists(args.mount_point):
        os.makedirs(args.mount_point)
    
    required_mounts = {
        '/dev': f"{args.mount_point}/dev",
        '/proc': f"{args.mount_point}/proc",
        '/sys': f"{args.mount_point}/sys"
    }
    
    for src, dest in required_mounts.items():
        if not os.path.ismount(dest):
            print(f"Mounting {src} to {dest}")
            os.makedirs(dest, exist_ok=True)
            run_command(f"mount --bind {src} {dest}")
    
    # Check if essential packages are installed when resuming
    if args.resume_from and args.resume_from >= 4:
        print("Checking essential packages...")
        result = run_command(f"chroot {args.mount_point} dpkg -l sudo", check=False)
        if result.returncode != 0:
            print("Installing essential packages...")
            run_command(f"chroot {args.mount_point} apt-get update -y")
            run_command(f"chroot {args.mount_point} apt-get install -y sudo passwd login")

def step_partitioning(args):
    """Step 1: Disk partitioning"""
    print("\n\033[1;32m=== Step 1: Manual Disk Partitioning ===\033[0m")
    if args.disk:
        disk_dev = f"/dev/{args.disk}"
    else:
        disks = subprocess.getoutput("lsblk -d -o NAME -n").split()
        print(f"Available disks: {', '.join(disks)}")
        disk = input("Select disk to install (e.g., sda): ").strip()
        disk_dev = f"/dev/{disk}"
    
    print(f"\nStarting cfdisk for {disk_dev}")
    print("Please create at least one root partition (/)")
    input("Press Enter to launch cfdisk...")
    run_command(f"cfdisk {disk_dev}")
    
    if args.root_part:
        root_part = f"/dev/{args.root_part}"
    else:
        partitions = subprocess.getoutput(f"lsblk -ln {disk_dev} | grep part | awk '{{print $1}}'").split()
        print(f"\nAvailable partitions: {partisons}")
        root_part = f"/dev/{input('Enter root partition (e.g., sda1): ').strip()}"
    
    print(f"\nFormatting {root_part} as ext4...")
    run_command(f"mkfs.ext4 -F {root_part}")
    run_command(f"mount {root_part} {args.mount_point}")
    
    return disk_dev, root_part

def step_user_config(args):
    """Step 4: User configuration"""
    print("\n\033[1;32m=== Step 4: User Configuration ===\033[0m")
    ensure_ready(args)
    
    hostname = input("Enter hostname [mainix]: ").strip() or "mainix"
    username = input("Enter username [user]: ").strip() or "user"
    user_password = getpass.getpass("Enter user password: ")
    root_password = getpass.getpass("Enter root password: ")
    
    with open(f'{args.mount_point}/etc/hostname', 'w') as f:
        f.write(hostname)
    
    result = run_command(f"chroot {args.mount_point} id -u {username}", check=False)
    if result.returncode != 0:
        print(f"Creating user {username}")
        run_command(f"chroot {args.mount_point} bash -c 'mkdir -p /etc/skel'")
        run_command(f"chroot {args.mount_point} bash -c 'adduser --disabled-password --gecos \"\" {username}'")
        run_command(f"chroot {args.mount_point} bash -c 'usermod -aG sudo {username}'")
    else:
        print(f"User {username} already exists")
    
    run_command(f"chroot {args.mount_point} bash -c 'echo \"{username}:{user_password}\" | chpasswd'")
    run_command(f"chroot {args.mount_point} bash -c 'echo \"root:{root_password}\" | chpasswd'")

def main():
    args = parse_arguments()
    steps = [
        step_partitioning,
        lambda args: step_base_install(args),
        lambda args: step_essential_packages(args),
        step_user_config,
        lambda args: step_system_branding(args),
        lambda args: step_desktop_install(args),
        lambda args: step_grub_install(args, disk_dev=None if not hasattr(args, 'disk_dev') else args.disk_dev)
    ]
    
    start_step = args.resume_from or 1
    disk_dev = None
    
    try:
        for i, step in enumerate(steps[start_step-1:], start=start_step):
            print(f"\n\033[1;35m=== Starting installation from step {i} ===\033[0m")
            
            if i == 1:
                args.disk_dev, args.root_part = step(args)
            else:
                step(args)
                
    except Exception as e:
        print(f"\n\033[1;31mInstallation failed at step {i}: {e}\033[0m")
        sys.exit(1)
    
    print("\n\033[1;32m=== Installation Complete! ===\033[0m")
    print("System will reboot in 10 seconds...")
    run_command("sleep 10")
    run_command("reboot")

if __name__ == "__main__":
    main()
