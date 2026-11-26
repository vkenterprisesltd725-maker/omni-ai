"""
OmniAI Studio - Main Application
Engineered by VIKA-BUILDS.
Features custom API Gateway, multi-key auto-failover, multimodal vision, image/video creation.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

# Prevent NoneType write errors in --noconsole mode
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w")
    except Exception:
        pass

import customtkinter as ctk
import pyperclip
import webbrowser

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import cfg, OUTPUTS_IMAGE_DIR, OUTPUTS_VIDEO_DIR, IS_PORTABLE, DATA_DIR, APP_VERSION
from api_server import server_manager
import ui.theme as theme
from ui.chat_tab import ChatTab
from ui.image_tab import ImageTab
from ui.video_tab import VideoTab
from ui.keys_tab import KeysTab
from ui.docs_tab import DocsTab
from ui.guide_tab import GuideTab
from ui.report_dialog import open_report_dialog
from ui.updater import check_for_updates_interactive


class UniversalAIApp(ctk.CTk):
    def __init__(self):
        # Saved Theme setup (Default to Light or saved preference)
        self.current_theme = cfg.get_setting("theme", "Light")
        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        super().__init__()

        # Navigation drawer state
        self.is_drawer_open = False
        self.drawer_width = 250
        self.drawer_current_x = -self.drawer_width
        self.drawer_anim_id = None

        # Window Setup
        self.title("OmniAI Studio — VIKA-BUILDS")
        self.geometry("1240x780")
        self.minsize(1000, 640)
        self.configure(fg_color=theme.COLOR_CANVAS)

        # Set official window icon
        try:
            icon_p = os.path.join(CURRENT_DIR, "app_icon.ico")
            if os.path.exists(icon_p):
                self.iconbitmap(icon_p)
        except Exception:
            pass

        self._build_layout()
        self._select_tab("chat")

        # Center and bring window to front
        self.update_idletasks()
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            w, h = 1240, 780
            x = max(0, (screen_w - w) // 2)
            y = max(0, (screen_h - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        self.deiconify()
        self.lift()
        self.focus_force()

        # Keyboard shortcuts: Escape closes navigation drawer
        self.bind("<Escape>", lambda e: self._close_nav_drawer())

        # Start API Gateway in background if enabled
        s_cfg = cfg.get_server_config()
        if s_cfg.get("enabled", True):
            server_manager.start(
                host=s_cfg.get("host", "127.0.0.1"),
                port=s_cfg.get("port", 8080)
            )

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self):
        # ----------------------------------------------------
        # 1. TOP HEADER BAR
        # ----------------------------------------------------
        self.top_header = ctk.CTkFrame(
            self,
            height=52,
            fg_color=theme.COLOR_CARD,
            corner_radius=0,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        self.top_header.pack(fill="x", side="top")
        self.top_header.pack_propagate(False)

        # Left: Three-Line Menu Button (☰) to open Drawer
        self.btn_nav_menu = ctk.CTkButton(
            self.top_header,
            text="☰",
            font=("Segoe UI Symbol", 17, "bold"),
            width=38,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=theme.COLOR_CARD_HOVER,
            text_color=theme.COLOR_TEXT_MAIN,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            command=self._toggle_nav_drawer,
        )
        self.btn_nav_menu.pack(side="left", padx=(14, 6), pady=8)

        # Brand Container on Left
        brand_left = ctk.CTkFrame(self.top_header, fg_color="transparent")
        brand_left.pack(side="left", padx=(2, 16), pady=8)

        # Brand Logo Image
        try:
            from PIL import Image as PILImage
            logo_p = os.path.join(CURRENT_DIR, "assets", "logo.png")
            if os.path.exists(logo_p):
                pil_img = PILImage.open(logo_p)
                self._header_logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(24, 24))
                lbl_icon = ctk.CTkLabel(brand_left, image=self._header_logo_img, text="")
                lbl_icon.pack(side="left", padx=(0, 8))
        except Exception:
            pass

        lbl_logo = ctk.CTkLabel(
            brand_left,
            text="OmniAI Studio",
            font=theme.FONT_TITLE,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        lbl_logo.pack(side="left")

        lbl_ver = ctk.CTkButton(
            brand_left,
            text=f" v{APP_VERSION} PORTABLE " if IS_PORTABLE else f" v{APP_VERSION} ",
            font=theme.FONT_BADGE,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MUTED,
            corner_radius=6,
            height=22,
            border_width=0,
            command=self._manual_check_for_updates,
        )
        lbl_ver.pack(side="left", padx=10)

        # Center: Developer Branding
        dev_badge = ctk.CTkButton(
            self.top_header,
            text="VIKA-BUILDS",
            font=theme.FONT_SUBHEADING,
            height=28,
            corner_radius=14,
            fg_color="transparent",
            hover_color=theme.COLOR_CARD_HOVER,
            border_width=0,
            text_color=theme.COLOR_TEXT_MUTED,
            command=self._show_about_dev,
        )
        dev_badge.pack(side="left", expand=True)

        # Right: Server Status, Key chip & Dark Mode Toggle
        right_box = ctk.CTkFrame(self.top_header, fg_color="transparent")
        right_box.pack(side="right", padx=16, pady=8)

        s_cfg = cfg.get_server_config()
        port = s_cfg.get("port", 8080)
        self.gw_status_lbl = ctk.CTkLabel(
            right_box,
            text=f"Gateway: :{port}",
            font=theme.FONT_BADGE,
            text_color=theme.COLOR_SUCCESS,
            fg_color="transparent",
            corner_radius=6,
            width=110,
            height=26,
        )
        self.gw_status_lbl.pack(side="left", padx=6)

        # Master Key Copy Button
        self.btn_copy_mkey = ctk.CTkButton(
            right_box,
            text="Master Key",
            font=theme.FONT_SMALL,
            height=26,
            width=90,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MUTED,
            command=self._quick_copy_key,
        )
        self.btn_copy_mkey.pack(side="left", padx=4)

        # Dark Mode Toggle Button (Replaces static "Theme" button)
        is_dark = (self.current_theme == "Dark")
        self.theme_toggle_btn = ctk.CTkButton(
            right_box,
            text="☀️ Light" if is_dark else "🌙 Dark",
            font=theme.FONT_SMALL,
            width=76,
            height=26,
            corner_radius=13,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            command=self._toggle_theme,
        )
        self.theme_toggle_btn.pack(side="left", padx=4)

        # Feedback & Bug Report Header Button
        self.btn_report_header = ctk.CTkButton(
            right_box,
            text="💡 Report",
            font=theme.FONT_SMALL,
            width=76,
            height=26,
            corner_radius=13,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            command=self._open_report_dialog,
        )
        self.btn_report_header.pack(side="left", padx=4)

        # ----------------------------------------------------
        # 2. MAIN FULL-WIDTH WORKSPACE CONTAINER
        # ----------------------------------------------------
        self.body_container = ctk.CTkFrame(self, fg_color="transparent")
        self.body_container.pack(fill="both", expand=True)

        # Content Area fills 100% of workspace width
        self.content_area = ctk.CTkFrame(self.body_container, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        self.tab_frames = {
            "chat": ChatTab(self.content_area, status_callback=self.set_status),
            "image": ImageTab(self.content_area, status_callback=self.set_status),
            "video": VideoTab(self.content_area, status_callback=self.set_status),
            "docs": DocsTab(self.content_area, status_callback=self.set_status),
            "keys": KeysTab(self.content_area, status_callback=self.set_status),
            "guide": GuideTab(self.content_area, status_callback=self.set_status)
        }

        for frame in self.tab_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        # ----------------------------------------------------
        # 3. ANIMATED SLIDING NAVIGATION DRAWER (Overlay)
        # ----------------------------------------------------
        # Backdrop for dismiss-on-click
        self.drawer_backdrop = ctk.CTkFrame(
            self.body_container,
            fg_color="transparent",
            corner_radius=0,
        )
        self.drawer_backdrop.bind("<Button-1>", lambda e: self._close_nav_drawer())

        # Drawer Frame
        self.nav_drawer = ctk.CTkFrame(
            self.body_container,
            width=self.drawer_width,
            corner_radius=0,
            fg_color=theme.COLOR_SIDEBAR,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        self.nav_drawer.pack_propagate(False)

        # Drawer Header
        d_header = ctk.CTkFrame(self.nav_drawer, fg_color="transparent")
        d_header.pack(fill="x", padx=14, pady=(14, 8))

        lbl_menu = ctk.CTkLabel(
            d_header,
            text="Menu",
            font=theme.FONT_HEADING,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        lbl_menu.pack(side="left")

        btn_close_d = ctk.CTkButton(
            d_header,
            text="✕",
            width=26,
            height=26,
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent",
            hover_color="#FEE2E2",
            text_color=theme.COLOR_TEXT_MUTED,
            command=self._close_nav_drawer,
        )
        btn_close_d.pack(side="right")

        # Divider
        div = ctk.CTkFrame(self.nav_drawer, height=1, fg_color=theme.COLOR_BORDER)
        div.pack(fill="x", padx=12, pady=(0, 10))

        # Drawer Navigation Items
        self.nav_buttons = {}
        nav_items = [
            ("chat", "💬  Chat"),
            ("image", "🎨  Images"),
            ("video", "🎬  Videos"),
            ("docs", "🔌  API Gateway"),
            ("keys", "🔑  Key Pools"),
            ("guide", "📖  Guides")
        ]

        for tab_id, label in nav_items:
            btn = ctk.CTkButton(
                self.nav_drawer,
                text=label,
                font=theme.FONT_BODY_BOLD,
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=theme.COLOR_TEXT_MUTED,
                anchor="w",
                hover_color=theme.COLOR_CARD_HOVER,
                command=lambda t=tab_id: self._on_drawer_nav_click(t),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[tab_id] = btn

        # Report & Feature Request button in Drawer
        div_rep = ctk.CTkFrame(self.nav_drawer, height=1, fg_color=theme.COLOR_BORDER)
        div_rep.pack(fill="x", padx=14, pady=(8, 6))

        self.btn_drawer_report = ctk.CTkButton(
            self.nav_drawer,
            text="💡  Report Bug / Feature",
            font=theme.FONT_BODY,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            text_color=theme.COLOR_TEXT_MUTED,
            anchor="w",
            hover_color=theme.COLOR_CARD_HOVER,
            command=self._open_report_dialog,
        )
        self.btn_drawer_report.pack(fill="x", padx=12, pady=2)

        self.btn_drawer_update = ctk.CTkButton(
            self.nav_drawer,
            text="🔄  Check for Updates",
            font=theme.FONT_BODY,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            text_color=theme.COLOR_TEXT_MUTED,
            anchor="w",
            hover_color=theme.COLOR_CARD_HOVER,
            command=self._manual_check_for_updates,
        )
        self.btn_drawer_update.pack(fill="x", padx=12, pady=2)

        # Spacer to push developer contact to bottom
        spacer = ctk.CTkFrame(self.nav_drawer, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Drawer Footer: Developer Contact (UI Left Bottom)
        self.dev_box = ctk.CTkFrame(
            self.nav_drawer,
            fg_color=theme.COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        self.dev_box.pack(fill="x", padx=12, pady=(10, 14), side="bottom")

        dev_top = ctk.CTkFrame(self.dev_box, fg_color="transparent")
        dev_top.pack(fill="x", padx=10, pady=(8, 2))

        lbl_dev_badge = ctk.CTkLabel(
            dev_top,
            text="DEVELOPER CONTACT",
            font=("Segoe UI", 8, "bold"),
            text_color=theme.COLOR_TEXT_DIM,
            anchor="w",
        )
        lbl_dev_badge.pack(side="left")

        lbl_dev_name = ctk.CTkLabel(
            self.dev_box,
            text="VIKA-BUILDS",
            font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
            anchor="w",
        )
        lbl_dev_name.pack(fill="x", padx=10, pady=(0, 6))

        links_frame = ctk.CTkFrame(self.dev_box, fg_color="transparent")
        links_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.btn_dev_git = ctk.CTkButton(
            links_frame,
            text="🐙 GitHub",
            font=theme.FONT_SMALL,
            height=28,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            corner_radius=6,
            command=self._open_dev_github,
        )
        self.btn_dev_git.pack(fill="x", pady=2)
        self.btn_dev_git.bind("<Button-3>", lambda e: self._edit_dev_link("git"))

        self.btn_dev_insta = ctk.CTkButton(
            links_frame,
            text="📷 Instagram",
            font=theme.FONT_SMALL,
            height=28,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            corner_radius=6,
            command=self._open_dev_instagram,
        )
        self.btn_dev_insta.pack(fill="x", pady=2)
        self.btn_dev_insta.bind("<Button-3>", lambda e: self._edit_dev_link("insta"))

        # ----------------------------------------------------
        # 4. BOTTOM STATUS BAR
        # ----------------------------------------------------
        self.status_bar = ctk.CTkFrame(
            self,
            height=28,
            fg_color=theme.COLOR_CARD,
            corner_radius=0,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready — Multi-Key Auto-Failover Active",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_DIM,
        )
        self.status_label.pack(side="left", padx=16)

        mode_tag = "Portable" if IS_PORTABLE else "Installed"
        display_path = DATA_DIR if len(DATA_DIR) <= 45 else "..." + DATA_DIR[-40:]
        self.watermark_lbl = ctk.CTkButton(
            self.status_bar,
            text=f"OmniAI Studio ({mode_tag}) • Storage: {display_path}",
            font=theme.FONT_SMALL,
            height=22,
            fg_color="transparent",
            hover_color=theme.COLOR_CARD_HOVER,
            text_color=theme.COLOR_TEXT_DIM,
            command=self._open_data_folder,
        )
        self.watermark_lbl.pack(side="right", padx=16)

        # Background Auto-Check for Updates (2s after startup)
        if cfg.get_setting("auto_check_updates", True):
            self.after(2000, self._auto_check_for_updates)

    # -----------------------------------------------------------------
    # Automatic & Manual Update Checks
    # -----------------------------------------------------------------
    def _auto_check_for_updates(self):
        check_for_updates_interactive(self, is_manual=False)

    def _manual_check_for_updates(self):
        self._close_nav_drawer()
        check_for_updates_interactive(self, is_manual=True)

    # -----------------------------------------------------------------
    # Navigation Drawer Animation & Logic (Claude / Linear Style)
    # -----------------------------------------------------------------
    def _toggle_nav_drawer(self):
        if self.is_drawer_open:
            self._close_nav_drawer()
        else:
            self._open_nav_drawer()

    def _open_nav_drawer(self):
        if self.is_drawer_open:
            return
        self.is_drawer_open = True
        self.drawer_backdrop.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.nav_drawer.lift()
        self.btn_nav_menu.configure(
            fg_color=theme.COLOR_CARD_HOVER,
            border_color=theme.COLOR_BORDER_GLOW,
        )
        self._animate_drawer_slide(target_x=0)

    def _close_nav_drawer(self):
        if not self.is_drawer_open:
            return
        self.is_drawer_open = False
        self.btn_nav_menu.configure(
            fg_color="transparent",
            border_color=theme.COLOR_BORDER,
        )
        self._animate_drawer_slide(target_x=-self.drawer_width, on_complete=self._on_drawer_closed)

    def _on_drawer_closed(self):
        self.drawer_backdrop.place_forget()
        self.nav_drawer.place_forget()

    def _animate_drawer_slide(self, target_x: int, on_complete=None):
        if self.drawer_anim_id:
            try:
                self.after_cancel(self.drawer_anim_id)
            except Exception:
                pass
            self.drawer_anim_id = None

        def step():
            diff = target_x - self.drawer_current_x
            if abs(diff) <= 6:
                self.drawer_current_x = target_x
                if target_x >= 0:
                    self.nav_drawer.place(x=0, y=0, relheight=1.0)
                if on_complete:
                    on_complete()
                self.drawer_anim_id = None
                return

            step_size = int(diff * 0.44)
            if step_size == 0:
                step_size = 5 if diff > 0 else -5

            self.drawer_current_x += step_size
            self.nav_drawer.place(x=self.drawer_current_x, y=0, relheight=1.0)
            self.drawer_anim_id = self.after(14, step)

        step()

    def _on_drawer_nav_click(self, tab_id: str):
        self._select_tab(tab_id)
        self._close_nav_drawer()

    def _open_data_folder(self):
        try:
            os.startfile(DATA_DIR)
        except Exception:
            pass

    def _select_tab(self, tab_id: str):
        for t_id, frame in self.tab_frames.items():
            if t_id == tab_id:
                frame.tkraise()
                if hasattr(frame, "on_tab_visible"):
                    try:
                        frame.on_tab_visible()
                    except Exception:
                        pass
                if t_id in self.nav_buttons:
                    self.nav_buttons[t_id].configure(
                        fg_color=theme.COLOR_CARD_HOVER,
                        border_width=0,
                        text_color=theme.COLOR_TEXT_MAIN,
                    )
            else:
                if t_id in self.nav_buttons:
                    self.nav_buttons[t_id].configure(
                        fg_color="transparent",
                        border_width=0,
                        text_color=theme.COLOR_TEXT_MUTED,
                    )

    def _toggle_theme(self):
        curr = cfg.get_setting("theme", "Light")
        new_mode = "Dark" if curr == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        cfg.set_setting("theme", new_mode)
        self.current_theme = new_mode

        # Update button text & status
        is_dark = (new_mode == "Dark")
        self.theme_toggle_btn.configure(text="☀️ Light" if is_dark else "🌙 Dark")
        self.set_status(f"Appearance theme switched to {new_mode} Mode.")

    def _quick_copy_key(self):
        key = cfg.get_server_config().get("master_key", "")
        if key:
            pyperclip.copy(key)
            self.set_status("Master API Key copied to clipboard.")
            messagebox.showinfo("Copied", f"Master API Key copied:\n{key}")

    def _open_dev_github(self):
        url = cfg.get_setting("developer_github", "https://github.com/vkenterprisesltd725-maker")
        webbrowser.open(url)
        self.set_status(f"Opening Developer GitHub: {url}")

    def _open_dev_instagram(self):
        url = cfg.get_setting("developer_instagram", "https://instagram.com/vikaskhatik725")
        webbrowser.open(url)
        self.set_status(f"Opening Developer Instagram: {url}")

    def _edit_dev_link(self, link_type: str):
        dialog_title = "Edit GitHub URL" if link_type == "git" else "Edit Instagram URL"
        current_val = cfg.get_setting(
            "developer_github" if link_type == "git" else "developer_instagram",
            "https://github.com/vkenterprisesltd725-maker" if link_type == "git" else "https://instagram.com/vikaskhatik725"
        )
        dialog = ctk.CTkInputDialog(text=f"Enter {dialog_title}:", title=dialog_title)
        new_val = dialog.get_input()
        if new_val and new_val.strip():
            if link_type == "git":
                cfg.set_setting("developer_github", new_val.strip())
            else:
                cfg.set_setting("developer_instagram", new_val.strip())
            self.set_status(f"Updated developer {link_type} link!")

    def _open_report_dialog(self):
        self._close_nav_drawer()
        open_report_dialog(self)

    def _show_about_dev(self):
        messagebox.showinfo(
            "About Developer",
            "OmniAI Studio — Portable Gateway Edition\n\n"
            "Engineered by: VIKA-BUILDS\n"
            "Developer: Vikas Kumar Khatik\n"
            "GitHub: https://github.com/vkenterprisesltd725-maker\n"
            "Instagram: https://instagram.com/vikaskhatik725\n\n"
            "Architecture: 100% Portable, Offline Key Security, Multi-Key Failover Pools\n"
            "Open-source & Free for Developers."
        )

    def set_status(self, text: str):
        if hasattr(self, "status_label"):
            self.status_label.configure(text=text)

    def _on_close(self):
        try:
            server_manager.stop()
        except Exception:
            pass
        self.destroy()


def main():
    app = UniversalAIApp()
    app.mainloop()


if __name__ == "__main__":
    main()
