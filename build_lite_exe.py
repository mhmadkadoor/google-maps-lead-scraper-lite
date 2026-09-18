"""
Build Script for Local Lead Finder (Lite Edition)
Compiles the free demo application into a standalone Windows .exe using PyInstaller.
"""

import os
import sys
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def get_customtkinter_path():
    import customtkinter
    return os.path.dirname(customtkinter.__file__)


def build():
    print("=" * 60)
    print("Building Local Lead Finder LITE Standalone Windows Executable")
    print("=" * 60)

    icon_path = os.path.join(PROJECT_ROOT, "app_icon.ico")
    icon_arg = [f"--icon={icon_path}"] if os.path.exists(icon_path) else []

    ctk_path = get_customtkinter_path()
    add_data_ctk = f"{ctk_path};customtkinter"
    add_data_icon = f"{icon_path};." if os.path.exists(icon_path) else None

    for folder in ["build", "dist"]:
        target = os.path.join(PROJECT_ROOT, folder)
        if os.path.exists(target):
            shutil.rmtree(target, ignore_errors=True)

    entry_point = os.path.join(PROJECT_ROOT, "main.py")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name=LocalLeadFinder_Lite",
        *icon_arg,
        f"--add-data={add_data_ctk}",
    ]
    if add_data_icon:
        cmd.append(f"--add-data={add_data_icon}")

    cmd.extend([
        "--hidden-import=customtkinter",
        "--hidden-import=playwright",
        "--hidden-import=playwright.sync_api",
        "--hidden-import=openpyxl",
        "--hidden-import=pandas",
        "--collect-all=customtkinter",
        "--collect-all=playwright",
        entry_point,
    ])

    print("Executing PyInstaller command...")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        exe_path = os.path.join(PROJECT_ROOT, "dist", "LocalLeadFinder_Lite.exe")
        print("=" * 60)
        print("LITE BUILD SUCCESSFUL!")
        print(f"Executable: {exe_path}")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"File size: {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print(f"Build failed with code: {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
