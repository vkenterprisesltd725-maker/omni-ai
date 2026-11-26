"""
OmniAI Studio - Automatic Update Checker & In-Place Updater
Engineered by VIKA-BUILDS.
Queries GitHub Releases, compares versions, prompts user, and handles seamless downloading/updating.
"""

import os
import sys
import re
import time
import threading
import subprocess
import webbrowser
from typing import Dict, Any, Optional, Tuple, Callable
import requests
import customtkinter as ctk
from tkinter import messagebox

from config import cfg, APP_VERSION, APP_NAME, GITHUB_REPO, IS_PORTABLE
import ui.theme as theme


def parse_version_tuple(v_str: str) -> Tuple[int, ...]:
    """Parse version strings like 'v2.3.0', '2.3.0', 'v2.4' into a comparable tuple (2, 3, 0)."""
    clean = re.sub(r"^[vV]", "", str(v_str).strip())
    parts = []
    for piece in clean.split("."):
        digits = re.findall(r"\d+", piece)
        if digits:
            parts.append(int(digits[0]))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(latest_tag: str, current_ver: str) -> bool:
    """Return True if latest_tag is strictly newer than current_ver."""
    try:
        return parse_version_tuple(latest_tag) > parse_version_tuple(current_ver)
    except Exception:
        return False


def query_latest_release(repo: str = GITHUB_REPO, timeout: int = 8) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Queries GitHub API for the latest published release.
    Returns: (is_update_available, release_dict, error_message)
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {
        "User-Agent": f"OmniAI-Studio-Updater/{APP_VERSION}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            tag = data.get("tag_name", "")
            is_newer = is_newer_version(tag, APP_VERSION)
            return is_newer, data, ""
        elif resp.status_code == 404:
            return False, None, "No published releases found on repository."
        else:
            return False, None, f"GitHub HTTP {resp.status_code}"
    except Exception as e:
        return False, None, str(e)


def get_recommended_asset(release_data: Dict[str, Any], is_portable: bool) -> Optional[Dict[str, Any]]:
    """Find the best asset for the currently running edition (Portable or Setup)."""
    assets = release_data.get("assets", [])
    if not assets:
        return None
    target_name = "OmniAI_Studio_Portable.exe" if is_portable else "OmniAI_Studio_Setup.exe"
    for a in assets:
        if a.get("name", "").lower() == target_name.lower():
            return a
    # Fallback to any executable asset
    for a in assets:
        if a.get("name", "").lower().endswith(".exe"):
            return a
    return assets[0]


class UpdateDialog(ctk.CTkToplevel):
    """Modern modal dialog alerting user of an available update with direct download and install."""
    def __init__(self, parent, release_data: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.release_data = release_data
        self.tag_name = release_data.get("tag_name", "vNext")
        self.release_name = release_data.get("name", f"OmniAI Studio {self.tag_name}")
        self.release_body = release_data.get("body", "No release notes provided.").strip()
        self.html_url = release_data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest")

        self.recommended_asset = get_recommended_asset(release_data, IS_PORTABLE)
        self.download_thread: Optional[threading.Thread] = None
        self.cancel_download = False

        self.title(f"OmniAI Studio Update Available ({self.tag_name})")
        self.geometry("560x540")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent window
        self.update_idletasks()
        try:
            px = parent.winfo_x()
            py = parent.winfo_y()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - 560) // 2
            y = py + (ph - 540) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=18, pady=16)

        # Header Card
        header_card = ctk.CTkFrame(
            container,
            fg_color=theme.COLOR_CARD_ALT,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        header_card.pack(fill="x", pady=(0, 12))

        h_row = ctk.CTkFrame(header_card, fg_color="transparent")
        h_row.pack(fill="x", padx=14, pady=(12, 4))

        title_lbl = ctk.CTkLabel(
            h_row,
            text="🚀  New Update Available!",
            font=theme.FONT_HEADING,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        title_lbl.pack(side="left")

        # Version Pill Badge
        ver_badge = ctk.CTkLabel(
            h_row,
            text=f"v{APP_VERSION}  ➔  {self.tag_name}",
            font=theme.FONT_BADGE,
            fg_color="#059669",
            text_color="#FFFFFF",
            corner_radius=6,
            height=24,
            padx=8,
        )
        ver_badge.pack(side="right")

        # Release Title Subtext
        sub_lbl = ctk.CTkLabel(
            header_card,
            text=self.release_name,
            font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
            justify="left",
            wraplength=510,
        )
        sub_lbl.pack(anchor="w", padx=14, pady=(0, 12))

        # Changelog / Highlights Card
        notes_frame = ctk.CTkFrame(
            container,
            fg_color=theme.COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        notes_frame.pack(fill="both", expand=True, pady=(0, 12))

        notes_header = ctk.CTkLabel(
            notes_frame,
            text="Release Highlights & Changelog:",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
        )
        notes_header.pack(anchor="w", padx=12, pady=(10, 4))

        # Scrollable text preview
        self.txt_notes = ctk.CTkTextbox(
            notes_frame,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_INPUT,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            wrap="word",
        )
        self.txt_notes.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.txt_notes.insert("1.0", self.release_body)
        self.txt_notes.configure(state="disabled")

        # Download Progress Area (hidden until download starts)
        self.progress_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=8, progress_color=theme.COLOR_ACCENT)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(4, 2))

        self.progress_lbl = ctk.CTkLabel(
            self.progress_frame,
            text="Ready to download...",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
        )
        self.progress_lbl.pack(anchor="w")

        # Action Buttons Row
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(4, 0))

        # Left: Skip & Remind Later
        self.btn_skip = ctk.CTkButton(
            btn_row,
            text="Skip This Version",
            width=110,
            height=32,
            font=theme.FONT_SMALL,
            fg_color="transparent",
            hover_color=theme.COLOR_CARD_HOVER,
            text_color=theme.COLOR_TEXT_DIM,
            command=self._on_skip,
        )
        self.btn_skip.pack(side="left", padx=(0, 6))

        self.btn_later = ctk.CTkButton(
            btn_row,
            text="Later",
            width=70,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            command=self.destroy,
        )
        self.btn_later.pack(side="left")

        # Right: GitHub Release & Update Now
        self.btn_update = ctk.CTkButton(
            btn_row,
            text="⚡ Update Now",
            width=120,
            height=32,
            font=theme.FONT_BODY_BOLD,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_BORDER_GLOW,
            text_color="#FFFFFF",
            command=self._start_update_download,
        )
        self.btn_update.pack(side="right", padx=(6, 0))

        self.btn_github = ctk.CTkButton(
            btn_row,
            text="🌐 View on GitHub",
            width=120,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            command=lambda: webbrowser.open(self.html_url),
        )
        self.btn_github.pack(side="right")

    def _on_skip(self):
        cfg.set_setting("skipped_update_version", self.tag_name)
        if hasattr(self.parent, "set_status"):
            self.parent.set_status(f"Skipped update notification for {self.tag_name}.")
        self.destroy()

    def _start_update_download(self):
        if not self.recommended_asset:
            # Fallback to browser if asset is not directly downloadable
            webbrowser.open(self.html_url)
            self.destroy()
            return

        self.btn_update.configure(state="disabled", text="Downloading...")
        self.btn_skip.configure(state="disabled")
        self.btn_later.configure(state="disabled")

        self.download_thread = threading.Thread(target=self._download_worker, daemon=True)
        self.download_thread.start()

    def _download_worker(self):
        asset = self.recommended_asset
        download_url = asset.get("browser_download_url")
        filename = asset.get("name", "OmniAI_Studio_Update.exe")
        expected_size = asset.get("size", 0)

        # Target directory: if portable, save next to executable; otherwise in user Temp
        if IS_PORTABLE and getattr(sys, "frozen", False):
            target_dir = os.path.dirname(os.path.abspath(sys.executable))
            save_path = os.path.join(target_dir, f"{filename}.new")
        else:
            temp_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "OmniAI_Update")
            os.makedirs(temp_dir, exist_ok=True)
            save_path = os.path.join(temp_dir, filename)

        try:
            headers = {"User-Agent": f"OmniAI-Studio-Updater/{APP_VERSION}"}
            with requests.get(download_url, headers=headers, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get("content-length", expected_size))
                downloaded = 0
                t_last_ui = time.time()

                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if self.cancel_download:
                            return
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            now = time.time()
                            if now - t_last_ui > 0.1:
                                t_last_ui = now
                                fraction = (downloaded / total_bytes) if total_bytes > 0 else 0.5
                                mb_down = downloaded / (1024 * 1024)
                                mb_tot = total_bytes / (1024 * 1024)
                                percent = int(fraction * 100)
                                self.after(0, lambda f=fraction, d=mb_down, t=mb_tot, p=percent: self._update_progress(f, d, t, p))

            # Download finished successfully
            self.after(0, lambda: self._on_download_complete(save_path, filename))

        except Exception as e:
            self.after(0, lambda err=str(e): self._on_download_error(err))

    def _update_progress(self, fraction: float, downloaded_mb: float, total_mb: float, percent: int):
        self.progress_bar.set(fraction)
        self.progress_lbl.configure(text=f"Downloading {self.recommended_asset.get('name', 'update')}... {downloaded_mb:.1f}MB / {total_mb:.1f}MB ({percent}%)")

    def _on_download_error(self, err_msg: str):
        self.progress_lbl.configure(text=f"Download failed: {err_msg[:45]}")
        self.btn_update.configure(state="normal", text="Retry Download")
        self.btn_later.configure(state="normal")
        messagebox.showerror(
            "Download Error",
            f"Could not download update asset directly:\n{err_msg}\n\nClick 'View on GitHub' to download manually from GitHub releases."
        )

    def _on_download_complete(self, downloaded_file: str, filename: str):
        self.progress_bar.set(1.0)
        self.progress_lbl.configure(text="Download complete! Ready to install.")

        ans = messagebox.askyesno(
            "Update Ready",
            f"OmniAI Studio {self.tag_name} has been downloaded successfully!\n\nWould you like to install and restart now?"
        )
        if not ans:
            self.destroy()
            return

        self._execute_in_place_update(downloaded_file)

    def _execute_in_place_update(self, downloaded_file: str):
        """Replaces the running executable or executes the installer and shuts down."""
        try:
            if IS_PORTABLE and getattr(sys, "frozen", False):
                current_exe = os.path.abspath(sys.executable)
                # Create a small detached updater script in temp dir
                bat_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"omni_updater_{int(time.time())}.bat")
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write("@echo off\n")
                    f.write("timeout /t 2 /nobreak > nul\n")
                    f.write(f'del /f /q "{current_exe}"\n')
                    f.write(f'move /y "{downloaded_file}" "{current_exe}"\n')
                    f.write(f'start "" "{current_exe}"\n')
                    f.write('del "%~f0"\n')

                # Run detached script
                subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=0x00000008 | 0x08000000)
                if hasattr(self.parent, "_on_close"):
                    self.parent._on_close()
                else:
                    self.parent.destroy()
                sys.exit(0)

            elif not IS_PORTABLE and "setup" in downloaded_file.lower():
                # Launch installer setup
                subprocess.Popen([downloaded_file], creationflags=0x00000008)
                if hasattr(self.parent, "_on_close"):
                    self.parent._on_close()
                else:
                    self.parent.destroy()
                sys.exit(0)

            else:
                # If running from source, launch the downloaded executable directly
                subprocess.Popen([downloaded_file], creationflags=0x00000008)
                self.destroy()

        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to launch update process:\n{e}\n\nPlease run {downloaded_file} manually.")
            self.destroy()


def check_for_updates_interactive(parent_app, is_manual: bool = False):
    """
    Checks GitHub for newer release.
    If is_manual is True, gives immediate feedback (e.g. 'Checking...', 'Up to date!').
    If is_manual is False (auto-startup check), only prompts when an update is actually available.
    """
    if is_manual and hasattr(parent_app, "set_status"):
        parent_app.set_status("Checking for updates on GitHub...")

    def worker():
        is_newer, release_data, err = query_latest_release()
        def on_ui():
            if is_newer and release_data:
                tag = release_data.get("tag_name", "")
                skipped = cfg.get_setting("skipped_update_version", "")
                if is_manual or tag != skipped:
                    UpdateDialog(parent_app, release_data)
                    if hasattr(parent_app, "set_status"):
                        parent_app.set_status(f"Update available: {tag}")
            elif is_manual:
                if err:
                    messagebox.showwarning(
                        "Update Check",
                        f"Could not connect to GitHub to check for updates:\n{err}\n\nPlease check your internet connection."
                    )
                else:
                    messagebox.showinfo(
                        "Up to Date",
                        f"You're running the latest version!\n\nOmniAI Studio v{APP_VERSION} is currently up to date."
                    )
                if hasattr(parent_app, "set_status"):
                    parent_app.set_status(f"OmniAI Studio v{APP_VERSION} is up to date.")

        try:
            parent_app.after(0, on_ui)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()
