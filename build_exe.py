"""
OmniAI Studio - Dual-Version Release Packager
Builds BOTH:
1. Portable Standalone Executable (OmniAI_Studio_Portable.exe)
2. Standard Windows Installer Setup (OmniAI_Studio_Setup.exe)
Engineered by VIKA-BUILDS.
"""

import os
import sys
import shutil
import subprocess
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY = os.path.join(BASE_DIR, "main.py")
INSTALLER_PY = os.path.join(BASE_DIR, "installer.py")
ICON_ICO = os.path.join(BASE_DIR, "app_icon.ico")
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")

GIVEAWAY_DIR = os.path.dirname(BASE_DIR)

def build_main_app() -> str:
    print("=" * 65)
    print("[1/2] Compiling Core Application: OmniAI_Studio.exe")
    print("=" * 65)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name=OmniAI_Studio",
        f"--icon={ICON_ICO}",
        "--collect-all=customtkinter",
        "--collect-all=PIL",
        "--collect-all=certifi",
        "--collect-all=uvicorn",
        "--collect-all=fastapi",
        "--collect-all=starlette",
        "--collect-all=pydantic",
        "--collect-all=pydantic_core",
        "--collect-all=anyio",
        "--hidden-import=requests",
        "--hidden-import=pyperclip",
        "--hidden-import=urllib3",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan.on",
        f"--paths={BASE_DIR}",
        MAIN_PY
    ]

    t0 = time.time()
    res = subprocess.run(cmd, cwd=BASE_DIR)
    dur = time.time() - t0

    if res.returncode != 0:
        print(f"[ERROR] Failed to compile OmniAI_Studio.exe (exit code {res.returncode})")
        sys.exit(res.returncode)

    exe_path = os.path.join(DIST_DIR, "OmniAI_Studio.exe")
    if not os.path.exists(exe_path):
        print("[ERROR] OmniAI_Studio.exe not found in dist!")
        sys.exit(1)

    print(f"[SUCCESS] Core app compiled in {dur:.1f}s ({os.path.getsize(exe_path) / (1024*1024):.2f} MB)")
    return exe_path

def build_installer(app_exe_path: str) -> str:
    print("\n" + "=" * 65)
    print("[2/2] Compiling Windows Installer: OmniAI_Studio_Setup.exe")
    print("=" * 65)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name=OmniAI_Studio_Setup",
        f"--icon={ICON_ICO}",
        f"--add-data={app_exe_path};.",
        f"--add-data={ICON_ICO};.",
        "--collect-all=customtkinter",
        f"--paths={BASE_DIR}",
        INSTALLER_PY
    ]

    t0 = time.time()
    res = subprocess.run(cmd, cwd=BASE_DIR)
    dur = time.time() - t0

    if res.returncode != 0:
        print(f"[ERROR] Failed to compile Installer (exit code {res.returncode})")
        sys.exit(res.returncode)

    installer_path = os.path.join(DIST_DIR, "OmniAI_Studio_Setup.exe")
    if not os.path.exists(installer_path):
        print("[ERROR] OmniAI_Studio_Setup.exe not found in dist!")
        sys.exit(1)

    print(f"[SUCCESS] Installer compiled in {dur:.1f}s ({os.path.getsize(installer_path) / (1024*1024):.2f} MB)")
    return installer_path

def package_and_cleanup(app_exe: str, installer_exe: str):
    print("\n" + "=" * 65)
    print("[DEPLOY] Packaging ONLY the TWO versions and cleaning old files")
    print("=" * 65)

    # 1. Prepare Version 1: Portable Version
    portable_exe = os.path.join(GIVEAWAY_DIR, "OmniAI_Studio_Portable.exe")
    shutil.copy2(app_exe, portable_exe)
    print(f"[1] Created: {portable_exe}")

    portable_folder = os.path.join(GIVEAWAY_DIR, "OmniAI_Studio_Portable")
    os.makedirs(portable_folder, exist_ok=True)
    shutil.copy2(app_exe, os.path.join(portable_folder, "OmniAI_Studio_Portable.exe"))
    with open(os.path.join(portable_folder, "portable.mode"), "w") as f:
        f.write("OmniAI Studio Portable Mode Marker\n")
    with open(os.path.join(portable_folder, "README.txt"), "w", encoding="utf-8") as f:
        f.write("OmniAI Studio - Portable Edition (v2.1)\n"
                "Engineered by VIKA-BUILDS.\n\n"
                "HOW TO USE:\n"
                "1. Double-click 'OmniAI_Studio_Portable.exe' to run anywhere.\n"
                "2. All API keys, chat history, and generated outputs stay right here in this folder.\n"
                "3. Carry this folder on a USB stick and plug it into any Windows PC — zero installation required!\n")
    print(f"[1] Created Portable Folder: {portable_folder}")

    # 2. Prepare Version 2: Installer Version
    setup_exe = os.path.join(GIVEAWAY_DIR, "OmniAI_Studio_Setup.exe")
    shutil.copy2(installer_exe, setup_exe)
    print(f"[2] Created: {setup_exe}")

    # 3. Clean up previous version files in giveaway root
    print("\n[CLEANUP] Removing previous version files...")
    old_files = [
        os.path.join(GIVEAWAY_DIR, "UniversalAI_Studio.exe"),
        os.path.join(GIVEAWAY_DIR, "UniversalAI_Studio_README.md"),
    ]
    for of in old_files:
        if os.path.exists(of):
            try:
                os.remove(of)
                print(f"  Deleted old file: {os.path.basename(of)}")
            except Exception as e:
                print(f"  Could not remove {of}: {e}")

    old_dirs = [
        os.path.join(GIVEAWAY_DIR, "UniversalAI_Studio_Portable"),
    ]
    for od in old_dirs:
        if os.path.exists(od):
            try:
                shutil.rmtree(od, ignore_errors=True)
                print(f"  Deleted old folder: {os.path.basename(od)}")
            except Exception as e:
                print(f"  Could not remove {od}: {e}")

    print("\n" + "=" * 65)
    print("SUCCESS: EXACTLY TWO VERSIONS DEPLOYED:")
    print("1. PORTABLE VERSION:  " + portable_exe)
    print("2. INSTALLER SETUP:   " + setup_exe)
    print("=" * 65)

def main():
    app_exe = build_main_app()
    installer_exe = build_installer(app_exe)
    package_and_cleanup(app_exe, installer_exe)

if __name__ == "__main__":
    main()
