"""
OmniAI Studio - Modern Windows Setup & Uninstaller Suite
Engineered by VIKA-BUILDS.

Features:
1. Resilient Installation:
   - Installs OmniAI Studio to %LOCALAPPDATA%\\Programs\\OmniAI_Studio
   - Gracefully terminates running instances and uses rename-first fallback to prevent [Errno 13] file locks
   - Installs self-contained GUI Uninstaller (Uninstall_OmniAI_Studio.exe)
   - Creates Desktop & Start Menu shortcuts
   - Registers in Windows Add/Remove Programs (Settings > Apps)
2. Interactive Uninstallation GUI Screen:
   - Modern CustomTkinter interface
   - Options to keep or wipe user data/API keys
   - Clean removal of shortcuts, registry entries, and program binaries
"""

import os
import sys
import time
import shutil
import tempfile
import threading
import subprocess
import winreg
from typing import Optional, Tuple, Callable

# Ensure CustomTkinter can be imported
import customtkinter as ctk

APP_NAME = "OmniAI Studio"
APP_EXE_NAME = "OmniAI_Studio.exe"
UNINSTALLER_EXE_NAME = "Uninstall_OmniAI_Studio.exe"
APP_VERSION = "2.3.0"
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


def get_user_data_dir() -> str:
    app_data = os.environ.get("APPDATA")
    if not app_data:
        app_data = os.path.expanduser("~")
    return os.path.join(app_data, "OmniAI_Studio")


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


def run_hidden_command(cmd, check=False) -> subprocess.CompletedProcess:
    """Run command with zero console window or screen flash on Windows."""
    creationflags = 0x08000000  # CREATE_NO_WINDOW
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0  # SW_HIDE
    return subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        startupinfo=startupinfo,
        check=check
    )


def kill_running_processes():
    """Terminate running instances to prevent file lock errors with zero CMD flashes."""
    for proc_name in [APP_EXE_NAME, "UniversalAI_Studio.exe", "OmniAI_Studio"]:
        try:
            run_hidden_command(["taskkill", "/f", "/im", proc_name])
        except Exception:
            pass
    time.sleep(0.5)


def safe_copy_file(src: str, dst: str):
    """
    Safely copies src to dst.
    If dst is currently locked by a running process, renames dst to a temp .old file
    first (which Windows NTFS permits for running binaries), then copies src to dst.
    """
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source file not found: {src}")

    dst_dir = os.path.dirname(dst)
    os.makedirs(dst_dir, exist_ok=True)

    try:
        shutil.copy2(src, dst)
        return
    except (PermissionError, OSError):
        # File is locked; attempt rename-first strategy
        if os.path.exists(dst):
            old_path = dst + f".old_{int(time.time())}"
            try:
                os.rename(dst, old_path)
            except Exception:
                pass
        shutil.copy2(src, dst)


def clean_stale_old_files(directory: str):
    """Cleans up previously renamed .old_* files that are no longer locked."""
    if not os.path.exists(directory):
        return
    for item in os.listdir(directory):
        if ".old_" in item:
            full = os.path.join(directory, item)
            try:
                os.remove(full)
            except Exception:
                pass


def create_windows_shortcut(target_exe: str, link_file: str, icon_path: Optional[str] = None, description: str = "") -> bool:
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

        run_hidden_command(["cscript", "//nologo", vbs_path], check=True)
        if os.path.exists(vbs_path):
            os.remove(vbs_path)
        return True
    except Exception as e:
        print(f"Error creating shortcut {link_file}: {e}")
        return False


def register_in_add_remove_programs(install_dir: str, target_exe: str, uninstaller_exe: str, icon_path: str):
    """Register in Windows Registry HKCU so it appears in Settings > Apps & Installed Apps."""
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniAI_Studio"
    uninstall_cmd = f'"{uninstaller_exe}" --uninstall'
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "OmniAI Studio")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{target_exe},0")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_cmd)
            winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'{uninstall_cmd} --silent')
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "Comments", 0, winreg.REG_SZ, APP_DESCRIPTION)
        return True
    except Exception as e:
        print(f"Error registering in Add/Remove programs: {e}")
        return False


def unregister_from_add_remove_programs():
    """Remove registration from Windows Registry."""
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniAI_Studio")
    except Exception:
        pass


# =============================================================================
# INSTALLATION WORKFLOW
# =============================================================================
def perform_install(target_dir: str, create_desktop: bool = True, create_start_menu: bool = True, status_callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
    """Executes the full installation workflow."""
    try:
        if status_callback:
            status_callback("Closing running instances...", 0.1)
        kill_running_processes()

        if status_callback:
            status_callback("Preparing installation folder...", 0.2)
        os.makedirs(target_dir, exist_ok=True)
        clean_stale_old_files(target_dir)

        # Initialize user data directory in %APPDATA%
        user_data_dir = get_user_data_dir()
        os.makedirs(user_data_dir, exist_ok=True)
        os.makedirs(os.path.join(user_data_dir, "chat_history"), exist_ok=True)
        os.makedirs(os.path.join(user_data_dir, "generated_images"), exist_ok=True)
        os.makedirs(os.path.join(user_data_dir, "generated_videos"), exist_ok=True)

        bundle_dir = get_bundle_dir()

        # Locate OmniAI_Studio.exe binary
        src_exe = os.path.join(bundle_dir, APP_EXE_NAME)
        if not os.path.exists(src_exe):
            candidates = [
                os.path.join(bundle_dir, "dist", APP_EXE_NAME),
                os.path.join(bundle_dir, "dist", "UniversalAI_Studio.exe"),
                os.path.join(bundle_dir, "UniversalAI_Studio.exe"),
                os.path.join(os.path.dirname(bundle_dir), APP_EXE_NAME),
                os.path.join(os.path.dirname(bundle_dir), "dist", APP_EXE_NAME),
            ]
            for c in candidates:
                if os.path.exists(c):
                    src_exe = c
                    break

        if not os.path.exists(src_exe):
            return False, f"Could not find application binary '{APP_EXE_NAME}' to install."

        if status_callback:
            status_callback("Extracting OmniAI Studio application files...", 0.4)

        dst_exe = os.path.join(target_dir, APP_EXE_NAME)
        safe_copy_file(src_exe, dst_exe)

        # Copy Icon if present
        src_icon = os.path.join(bundle_dir, "app_icon.ico")
        dst_icon = os.path.join(target_dir, "app_icon.ico")
        if os.path.exists(src_icon):
            safe_copy_file(src_icon, dst_icon)
        elif os.path.exists(dst_exe):
            dst_icon = dst_exe

        if status_callback:
            status_callback("Installing GUI uninstaller...", 0.6)

        # Deploy GUI Uninstaller: copy running installer executable as Uninstall_OmniAI_Studio.exe
        dst_uninstaller = os.path.join(target_dir, UNINSTALLER_EXE_NAME)
        current_installer = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
        if os.path.exists(current_installer) and current_installer.lower().endswith(".exe"):
            safe_copy_file(current_installer, dst_uninstaller)
        else:
            # Fallback copy if running from dist
            cand_setup = os.path.join(bundle_dir, "OmniAI_Studio_Setup.exe")
            if os.path.exists(cand_setup):
                safe_copy_file(cand_setup, dst_uninstaller)
            else:
                # Use dst_exe as uninstaller host with --uninstall flag
                dst_uninstaller = dst_exe

        if status_callback:
            status_callback("Creating Windows shortcuts...", 0.8)

        # 1. Desktop Shortcut
        if create_desktop:
            for desk_folder in ["Desktop", os.path.join(os.path.expanduser("~"), "Desktop"), os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")]:
                if os.path.exists(desk_folder):
                    link_path = os.path.join(desk_folder, "OmniAI Studio.lnk")
                    create_windows_shortcut(dst_exe, link_path, icon_path=dst_icon, description=APP_DESCRIPTION)
                    break

        # 2. Start Menu Shortcuts
        if create_start_menu:
            programs_dir = get_special_folder("Programs")
            if programs_dir and os.path.exists(programs_dir):
                # App launch shortcut
                link_app = os.path.join(programs_dir, "OmniAI Studio.lnk")
                create_windows_shortcut(dst_exe, link_app, icon_path=dst_icon, description=APP_DESCRIPTION)
                # Uninstaller shortcut
                if os.path.exists(dst_uninstaller):
                    link_uninst = os.path.join(programs_dir, "Uninstall OmniAI Studio.lnk")
                    create_windows_shortcut(dst_uninstaller, link_uninst, icon_path=dst_icon, description="Uninstall OmniAI Studio")

        if status_callback:
            status_callback("Registering in Windows Installed Apps...", 0.95)

        register_in_add_remove_programs(target_dir, dst_exe, dst_uninstaller, dst_icon)

        if status_callback:
            status_callback("Installation successfully completed!", 1.0)

        return True, dst_exe

    except Exception as e:
        return False, str(e)


# =============================================================================
# UNINSTALLATION WORKFLOW
# =============================================================================
def perform_uninstall(target_dir: str, remove_data: bool = False, status_callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
    """Executes the full uninstallation workflow."""
    try:
        if status_callback:
            status_callback("Closing running OmniAI Studio processes...", 0.15)
        kill_running_processes()

        if status_callback:
            status_callback("Removing Desktop and Start Menu shortcuts...", 0.4)

        # Remove Desktop Shortcuts
        desktop_paths = [
            os.path.join(os.path.expanduser("~"), "Desktop", "OmniAI Studio.lnk"),
            os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "OmniAI Studio.lnk")
        ]
        for p in desktop_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        # Remove Start Menu Shortcuts
        programs_dir = get_special_folder("Programs")
        if programs_dir and os.path.exists(programs_dir):
            for s_name in ["OmniAI Studio.lnk", "Uninstall OmniAI Studio.lnk"]:
                p = os.path.join(programs_dir, s_name)
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        if status_callback:
            status_callback("Unregistering from Windows Settings...", 0.6)
        unregister_from_add_remove_programs()

        if remove_data:
            if status_callback:
                status_callback("Wiping user settings, keys, and chat history...", 0.75)
            user_data = get_user_data_dir()
            if os.path.exists(user_data):
                try:
                    shutil.rmtree(user_data, ignore_errors=True)
                except Exception:
                    pass

        if status_callback:
            status_callback("Removing installed program files...", 0.9)

        # Remove all files in target_dir except the currently running uninstaller
        current_exe = os.path.abspath(sys.executable).lower()
        if os.path.exists(target_dir):
            for item in os.listdir(target_dir):
                full_p = os.path.join(target_dir, item)
                if full_p.lower() == current_exe:
                    continue  # Will be deleted by self-cleanup script
                try:
                    if os.path.isdir(full_p):
                        shutil.rmtree(full_p, ignore_errors=True)
                    else:
                        os.remove(full_p)
                except Exception:
                    pass

        # Schedule self-deletion of uninstaller and target_dir on exit
        bat_path = os.path.join(tempfile.gettempdir(), f"omni_cleanup_{int(time.time())}.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write("timeout /t 2 /nobreak > nul\n")
            f.write(f'del /f /q "{current_exe}" >nul 2>&1\n')
            f.write(f'rd /s /q "{target_dir}" >nul 2>&1\n')
            f.write('del "%~f0"\n')

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=0x00000008 | 0x08000000,
            startupinfo=si,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        if status_callback:
            status_callback("OmniAI Studio has been successfully uninstalled.", 1.0)

        return True, "Uninstalled successfully."

    except Exception as e:
        return False, str(e)


# =============================================================================
# INSTALLER GUI SCREEN
# =============================================================================
class InstallerGUI(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title("OmniAI Studio Setup — VIKA-BUILDS")
        self.geometry("560x450")
        self.resizable(False, False)
        self.configure(fg_color="#FAFAFA")

        self.installed_exe: Optional[str] = None
        self.install_dir = get_default_install_dir()

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w, h = 560, 450
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

        sub = ctk.CTkLabel(h_inner, text=f"Version {APP_VERSION} — Built by VIKA-BUILDS (Standard Windows Installation)", font=("Segoe UI", 10), text_color="#6B7280", anchor="w")
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

        # Options checkboxes
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
            if self.chk_launch.get():
                try:
                    os.startfile(self.installed_exe)
                except Exception:
                    try:
                        creationflags = 0x08000000
                        subprocess.Popen([self.installed_exe], cwd=os.path.dirname(self.installed_exe), creationflags=creationflags)
                    except Exception as e:
                        print(f"Error launching: {e}")
            self.destroy()
            return

        self.btn_action.configure(state="disabled", text="Installing...")
        self.btn_cancel.configure(state="disabled")
        self.chk_desktop.configure(state="disabled")
        self.chk_start_menu.configure(state="disabled")
        self.chk_launch.configure(state="disabled")

        self.progress_bar.pack(fill="x", pady=(10, 4))
        self.status_lbl.pack(fill="x", pady=(0, 4))

        def run_thread():
            def update_ui(text: str, progress: float):
                self.after(0, lambda: (self.status_lbl.configure(text=text), self.progress_bar.set(progress)))

            success, result = perform_install(
                target_dir=self.install_dir,
                create_desktop=bool(self.chk_desktop.get()),
                create_start_menu=bool(self.chk_start_menu.get()),
                status_callback=update_ui
            )

            def on_finish():
                if success:
                    self.installed_exe = result
                    self.status_lbl.configure(text=f"Installed successfully to: {self.install_dir}", text_color="#059669")
                    self.btn_action.configure(state="normal", text="Finish & Launch")
                    self.btn_cancel.configure(state="normal", text="Close")
                else:
                    self.status_lbl.configure(text=f"Install error: {result}", text_color="#DC2626")
                    self.btn_action.configure(state="normal", text="Retry")
                    self.btn_cancel.configure(state="normal")

            self.after(0, on_finish)

        threading.Thread(target=run_thread, daemon=True).start()


# =============================================================================
# UNINSTALLER GUI SCREEN
# =============================================================================
class UninstallerGUI(ctk.CTk):
    """Modern interactive GUI screen for uninstallation."""
    def __init__(self):
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title("OmniAI Studio Uninstaller — VIKA-BUILDS")
        self.geometry("560x460")
        self.resizable(False, False)
        self.configure(fg_color="#FAFAFA")

        self.install_dir = get_default_install_dir()
        self.uninstalled_done = False

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w, h = 560, 460
        x = max(0, (self.winfo_screenwidth() - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=80, border_width=1, border_color="#E5E7EB")
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(fill="both", padx=24, pady=14)

        title = ctk.CTkLabel(h_inner, text="🗑️  Uninstall OmniAI Studio", font=("Segoe UI", 16, "bold"), text_color="#DC2626", anchor="w")
        title.pack(fill="x")

        sub = ctk.CTkLabel(h_inner, text=f"Remove OmniAI Studio v{APP_VERSION} from your computer", font=("Segoe UI", 10), text_color="#6B7280", anchor="w")
        sub.pack(fill="x")

        # Body area
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        # Warning / Info Card
        card = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E7EB")
        card.pack(fill="x", pady=(0, 14))

        msg = ctk.CTkLabel(
            card,
            text="Are you sure you want to uninstall OmniAI Studio?\nThis will remove the application binaries, Start Menu shortcuts, and Windows registration.",
            font=("Segoe UI", 10),
            text_color="#374151",
            justify="left",
            wraplength=490
        )
        msg.pack(anchor="w", padx=14, pady=12)

        # Options check marks
        self.chk_shortcuts = ctk.CTkCheckBox(
            body,
            text="Remove Desktop and Start Menu Shortcuts",
            font=("Segoe UI", 10),
            text_color="#111827",
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
            fg_color="#DC2626",
            hover_color="#B91C1C"
        )
        self.chk_shortcuts.select()
        self.chk_shortcuts.pack(anchor="w", pady=4)

        self.chk_files = ctk.CTkCheckBox(
            body,
            text="Remove Program Executables and Assets",
            font=("Segoe UI", 10),
            text_color="#111827",
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
            fg_color="#DC2626",
            hover_color="#B91C1C"
        )
        self.chk_files.select()
        self.chk_files.pack(anchor="w", pady=4)

        self.chk_wipe_data = ctk.CTkCheckBox(
            body,
            text="Delete all API Keys, Failover Pools, and Chat Histories (%APPDATA%\\OmniAI_Studio)",
            font=("Segoe UI", 10),
            text_color="#B91C1C",
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
            fg_color="#DC2626",
            hover_color="#B91C1C"
        )
        self.chk_wipe_data.deselect()  # Unchecked by default to prevent accidental data loss
        self.chk_wipe_data.pack(anchor="w", pady=4)

        note_lbl = ctk.CTkLabel(
            body,
            text="(Tip: Leaving personal data unchecked allows you to reinstall anytime without re-entering keys.)",
            font=("Segoe UI", 9),
            text_color="#6B7280",
            anchor="w"
        )
        note_lbl.pack(anchor="w", padx=26, pady=(0, 10))

        # Progress bar (hidden initially)
        self.progress_bar = ctk.CTkProgressBar(body, mode="determinate", height=8, progress_color="#DC2626")
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

        self.btn_uninstall = ctk.CTkButton(
            bottom,
            text="Uninstall Now",
            width=120,
            height=32,
            font=("Segoe UI", 10, "bold"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            text_color="#FFFFFF",
            command=self._on_uninstall_click
        )
        self.btn_uninstall.pack(side="right", padx=6, pady=12)

    def _on_uninstall_click(self):
        if self.uninstalled_done:
            self.destroy()
            return

        self.btn_uninstall.configure(state="disabled", text="Uninstalling...")
        self.btn_cancel.configure(state="disabled")
        self.chk_shortcuts.configure(state="disabled")
        self.chk_files.configure(state="disabled")
        self.chk_wipe_data.configure(state="disabled")

        self.progress_bar.pack(fill="x", pady=(10, 4))
        self.status_lbl.pack(fill="x", pady=(0, 4))

        remove_data = bool(self.chk_wipe_data.get())

        def run_thread():
            def update_ui(text: str, progress: float):
                self.after(0, lambda: (self.status_lbl.configure(text=text), self.progress_bar.set(progress)))

            success, result = perform_uninstall(
                target_dir=self.install_dir,
                remove_data=remove_data,
                status_callback=update_ui
            )

            def on_finish():
                if success:
                    self.uninstalled_done = True
                    self.status_lbl.configure(text="OmniAI Studio has been successfully uninstalled from your PC.", text_color="#059669")
                    self.btn_uninstall.configure(state="normal", text="Close", fg_color="#18181B", hover_color="#3F3F46")
                    self.btn_cancel.pack_forget()
                else:
                    self.status_lbl.configure(text=f"Uninstall error: {result}", text_color="#DC2626")
                    self.btn_uninstall.configure(state="normal", text="Retry")
                    self.btn_cancel.configure(state="normal")

            self.after(0, on_finish)

        threading.Thread(target=run_thread, daemon=True).start()


def main():
    # Detect if uninstall mode is requested via CLI argument or binary name
    is_uninstall_arg = any(arg in sys.argv for arg in ["--uninstall", "-u", "/uninstall"])
    is_uninstall_name = "uninstall" in os.path.basename(sys.executable).lower()

    if is_uninstall_arg or is_uninstall_name:
        # Silent uninstall
        if "--silent" in sys.argv or "-s" in sys.argv:
            success, _ = perform_uninstall(get_default_install_dir())
            sys.exit(0 if success else 1)
        app = UninstallerGUI()
        app.mainloop()
    else:
        # Silent install
        if "--silent" in sys.argv or "-s" in sys.argv:
            target = get_default_install_dir()
            success, _ = perform_install(target)
            sys.exit(0 if success else 1)
        app = InstallerGUI()
        app.mainloop()


if __name__ == "__main__":
    main()
