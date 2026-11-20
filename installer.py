"""
OmniAI Studio - Modern Windows Setup & Installer
Installs OmniAI Studio to %LOCALAPPDATA%\\Programs\\OmniAI_Studio,
creates Desktop and Start Menu shortcuts, registers in Windows Add/Remove Programs,
and sets up persistent user data storage in %APPDATA%\\OmniAI_Studio.
Engineered by VIKA-BUILDS.
"""

import os
import sys
import shutil
import tempfile
import subprocess
import winreg
from typing import Optional

# Ensure CustomTkinter can be imported
import customtkinter as ctk

APP_NAME = "OmniAI Studio"
APP_EXE_NAME = "OmniAI_Studio.exe"
APP_VERSION = "2.2.0"
APP_PUBLISHER = "VIKA-BUILDS"
APP_DESCRIPTION = "Universal AI Desktop Studio & Local Gateway with Multi-Key Auto-Failover"

def get_bundle_dir() -> str:
    """Returns directory containing payload files (PyInstaller temp or script dir)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_default_install_dir() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        local_app_data = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(local_app_data, "Programs", "OmniAI_Studio")

def get_special_folder(folder_name: str) -> Optional[str]:
    """Retrieve actual Windows special folder path (handling OneDrive redirects)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            val, _ = winreg.QueryValueEx(k, folder_name)
            return os.path.expandvars(val)
    except Exception:
        pass
    
    if folder_name.lower() == "desktop":
        return os.path.join(os.path.expanduser("~"), "Desktop")
    elif folder_name.lower() == "programs":
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs")
    return None

def create_windows_shortcut(target_exe: str, link_file: str, icon_path: Optional[str] = None, description: str = ""):
    """Create a standard Windows .lnk shortcut using WScript.Shell."""
    try:
        target_dir = os.path.dirname(target_exe)
        icon_line = f'oLink.IconLocation = "{icon_path},0"\n' if icon_path and os.path.exists(icon_path) else ""
        vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{link_file}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_exe}"
oLink.WorkingDirectory = "{target_dir}"
oLink.Description = "{description}"
{icon_line}oLink.Save
'''
        with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="utf-8") as f:
            f.write(vbs_content)
            vbs_path = f.name

        subprocess.run(["cscript", "//nologo", vbs_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(vbs_path):
            os.remove(vbs_path)
        return True
    except Exception as e:
        print(f"Error creating shortcut {link_file}: {e}")
        return False

def register_in_add_remove_programs(install_dir: str, target_exe: str, icon_path: str):
    """Register in Windows Registry HKCU so it shows up in Windows Installed Apps."""
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniAI_Studio"
    uninstall_cmd = f'cmd.exe /c "{os.path.join(install_dir, "uninstall.bat")}"'
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "OmniAI Studio")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{target_exe},0")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_cmd)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "Comments", 0, winreg.REG_SZ, APP_DESCRIPTION)
        return True
    except Exception as e:
        print(f"Error registering in Add/Remove programs: {e}")
        return False

def create_uninstall_script(install_dir: str):
    """Create clean uninstall.bat in the installation directory."""
    script = f'''@echo off
title Uninstall OmniAI Studio
echo ========================================================
echo   Uninstalling OmniAI Studio (VIKA-BUILDS)
echo ========================================================
echo.
echo Are you sure you want to remove OmniAI Studio from this PC?
set /p CONFIRM="Type Y to confirm, or press Enter to cancel: "
if /i not "%CONFIRM%"=="Y" exit /b 0

echo.
echo Closing any running OmniAI Studio processes...
taskkill /f /im OmniAI_Studio.exe >nul 2>&1
taskkill /f /im UniversalAI_Studio.exe >nul 2>&1

echo Removing Desktop and Start Menu shortcuts...
del /q "%USERPROFILE%\\Desktop\\OmniAI Studio.lnk" >nul 2>&1
del /q "%USERPROFILE%\\OneDrive\\Desktop\\OmniAI Studio.lnk" >nul 2>&1
del /q "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\OmniAI Studio.lnk" >nul 2>&1

echo Unregistering from Windows Add/Remove programs...
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OmniAI_Studio" /f >nul 2>&1

echo.
echo Removing program files...
cd /d "%TEMP%"
timeout /t 1 /nobreak >nul
rd /s /q "{install_dir}" >nul 2>&1

echo.
echo ========================================================
echo   OmniAI Studio has been uninstalled successfully.
echo   Your saved API keys and chats remain safe in:
echo   %APPDATA%\\OmniAI_Studio
echo ========================================================
echo.
pause
'''
    bat_path = os.path.join(install_dir, "uninstall.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(script)
    return bat_path

def perform_install(target_dir: str, create_desktop: bool = True, create_start_menu: bool = True, status_callback=None) -> tuple:
    """Executes the full installation workflow."""
    if status_callback:
        status_callback("Preparing installation folder...", 0.1)

    os.makedirs(target_dir, exist_ok=True)

    # Initialize user data directory in %APPDATA%
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    user_data_dir = os.path.join(app_data, "OmniAI_Studio")
    os.makedirs(user_data_dir, exist_ok=True)
    os.makedirs(os.path.join(user_data_dir, "chat_history"), exist_ok=True)
    os.makedirs(os.path.join(user_data_dir, "generated_images"), exist_ok=True)
    os.makedirs(os.path.join(user_data_dir, "generated_videos"), exist_ok=True)

    if status_callback:
        status_callback("Extracting program files...", 0.3)

    bundle_dir = get_bundle_dir()
    
    # Locate OmniAI_Studio.exe binary
    src_exe = os.path.join(bundle_dir, APP_EXE_NAME)
    if not os.path.exists(src_exe):
        # Fallback to adjacent dist/ or UniversalAI_Studio.exe
        candidates = [
            os.path.join(bundle_dir, "dist", APP_EXE_NAME),
            os.path.join(bundle_dir, "dist", "UniversalAI_Studio.exe"),
            os.path.join(bundle_dir, "UniversalAI_Studio.exe"),
            os.path.join(os.path.dirname(bundle_dir), APP_EXE_NAME),
            os.path.join(os.path.dirname(bundle_dir), "UniversalAI_Studio.exe")
        ]
        for c in candidates:
            if os.path.exists(c):
                src_exe = c
                break

    dst_exe = os.path.join(target_dir, APP_EXE_NAME)
    if os.path.exists(src_exe):
        shutil.copy2(src_exe, dst_exe)
    else:
        return False, f"Could not find application binary '{APP_EXE_NAME}' to install."

    # Copy Icon if present
    src_icon = os.path.join(bundle_dir, "app_icon.ico")
    dst_icon = os.path.join(target_dir, "app_icon.ico")
    if os.path.exists(src_icon):
        shutil.copy2(src_icon, dst_icon)
    elif os.path.exists(dst_exe):
        dst_icon = dst_exe

    if status_callback:
        status_callback("Creating uninstaller script...", 0.6)

    create_uninstall_script(target_dir)

    if status_callback:
        status_callback("Creating Windows shortcuts...", 0.8)

    # 1. Desktop Shortcut
    if create_desktop:
        desktop_dir = get_special_folder("Desktop")
        if desktop_dir and os.path.exists(desktop_dir):
            link_path = os.path.join(desktop_dir, "OmniAI Studio.lnk")
            create_windows_shortcut(dst_exe, link_path, icon_path=dst_icon, description=APP_DESCRIPTION)

    # 2. Start Menu Shortcut
    if create_start_menu:
        programs_dir = get_special_folder("Programs")
        if programs_dir and os.path.exists(programs_dir):
            link_path = os.path.join(programs_dir, "OmniAI Studio.lnk")
            create_windows_shortcut(dst_exe, link_path, icon_path=dst_icon, description=APP_DESCRIPTION)

    if status_callback:
        status_callback("Registering in Windows Settings...", 0.95)

    register_in_add_remove_programs(target_dir, dst_exe, dst_icon)

    if status_callback:
        status_callback("Installation successfully completed!", 1.0)

    return True, dst_exe

class InstallerGUI(ctk.CTk):
    def __init__(self):
        # Set minimal clean theme
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title("OmniAI Studio Setup — VIKA-BUILDS")
        self.geometry("560x440")
        self.resizable(False, False)
        self.configure(fg_color="#FAFAFA")

        self.installed_exe: Optional[str] = None
        self.install_dir = get_default_install_dir()

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w = 560
        h = 440
        x = max(0, (self.winfo_screenwidth() - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_ui(self):
        # Header card
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=80, border_width=1, border_color="#E5E7EB")
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(fill="both", padx=24, pady=14)

        title = ctk.CTkLabel(h_inner, text="OmniAI Studio Setup", font=("Segoe UI", 16, "bold"), text_color="#111827", anchor="w")
        title.pack(fill="x")

        sub = ctk.CTkLabel(h_inner, text="Version 2.2 — Built by VIKA-BUILDS (Standard Windows Installation)", font=("Segoe UI", 10), text_color="#6B7280", anchor="w")
        sub.pack(fill="x")

        # Body area
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        desc = ctk.CTkLabel(
            body,
            text="This will install OmniAI Studio onto your computer. Once installed, the app can be restarted normally from your Start Menu or Desktop like any other software.\nAll your API keys, failover pools, and chat histories will be safely preserved across updates and restarts.",
            font=("Segoe UI", 10),
            text_color="#4B5563",
            justify="left",
            wraplength=510
        )
        desc.pack(anchor="w", pady=(0, 14))

        # Target directory box
        dir_lbl = ctk.CTkLabel(body, text="Installation Folder:", font=("Segoe UI", 10, "bold"), text_color="#111827", anchor="w")
        dir_lbl.pack(fill="x", pady=(0, 4))

        dir_box = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E5E7EB")
        dir_box.pack(fill="x", pady=(0, 14))

        self.path_lbl = ctk.CTkLabel(dir_box, text=self.install_dir, font=("Consolas", 9), text_color="#374151", anchor="w")
        self.path_lbl.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        # Options check marks
        self.chk_desktop = ctk.CTkCheckBox(
            body,
            text="Create Desktop Shortcut",
            font=("Segoe UI", 10),
            text_color="#111827",
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
            fg_color="#18181B"
        )
        self.chk_desktop.select()
        self.chk_desktop.pack(anchor="w", pady=4)

        self.chk_start_menu = ctk.CTkCheckBox(
            body,
            text="Create Start Menu Shortcut (searchable via Windows Start)",
            font=("Segoe UI", 10),
            text_color="#111827",
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
            fg_color="#18181B"
        )
        self.chk_start_menu.select()
        self.chk_start_menu.pack(anchor="w", pady=4)

        self.chk_launch = ctk.CTkCheckBox(
            body,
            text="Launch OmniAI Studio when installation completes",
            font=("Segoe UI", 10),
            text_color="#111827",
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
            fg_color="#18181B"
        )
        self.chk_launch.select()
        self.chk_launch.pack(anchor="w", pady=4)

        # Progress bar (hidden initially)
        self.progress_bar = ctk.CTkProgressBar(body, mode="determinate", height=8, progress_color="#18181B")
        self.progress_bar.set(0)

        self.status_lbl = ctk.CTkLabel(body, text="", font=("Segoe UI", 9), text_color="#6B7280", anchor="w")

        # Bottom Action Bar
        bottom = ctk.CTkFrame(self, fg_color="#FFFFFF", height=56, corner_radius=0, border_width=1, border_color="#E5E7EB")
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        self.btn_cancel = ctk.CTkButton(
            bottom,
            text="Cancel",
            width=80,
            height=32,
            font=("Segoe UI", 10),
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(6, 20), pady=12)

        self.btn_action = ctk.CTkButton(
            bottom,
            text="Install Now",
            width=110,
            height=32,
            font=("Segoe UI", 10, "bold"),
            fg_color="#18181B",
            hover_color="#3F3F46",
            text_color="#FFFFFF",
            command=self._on_action_click
        )
        self.btn_action.pack(side="right", padx=6, pady=12)

    def _on_action_click(self):
        if self.installed_exe:
            # Finished state: launch app and close
            if self.chk_launch.get():
                try:
                    subprocess.Popen([self.installed_exe], cwd=os.path.dirname(self.installed_exe))
                except Exception as e:
                    print(f"Error launching: {e}")
            self.destroy()
            return

        # Start installation
        self.btn_action.configure(state="disabled", text="Installing...")
        self.btn_cancel.configure(state="disabled")
        self.chk_desktop.configure(state="disabled")
        self.chk_start_menu.configure(state="disabled")
        self.chk_launch.configure(state="disabled")

        self.progress_bar.pack(fill="x", pady=(12, 4))
        self.status_lbl.pack(fill="x", pady=(0, 4))

        def update_status(text: str, progress: float):
            self.status_lbl.configure(text=text)
            self.progress_bar.set(progress)
            self.update()

        success, result = perform_install(
            target_dir=self.install_dir,
            create_desktop=bool(self.chk_desktop.get()),
            create_start_menu=bool(self.chk_start_menu.get()),
            status_callback=update_status
        )

        if success:
            self.installed_exe = result
            self.status_lbl.configure(text=f"Installed successfully to: {self.install_dir}", text_color="#059669")
            self.btn_action.configure(state="normal", text="Finish & Launch")
            self.btn_cancel.configure(state="normal", text="Close")
        else:
            self.status_lbl.configure(text=f"Install error: {result}", text_color="#DC2626")
            self.btn_action.configure(state="normal", text="Retry")
            self.btn_cancel.configure(state="normal")

def main():
    # Silent install support
    if "--silent" in sys.argv or "-s" in sys.argv:
        target = get_default_install_dir()
        success, res = perform_install(target)
        sys.exit(0 if success else 1)

    app = InstallerGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
