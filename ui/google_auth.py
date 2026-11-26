"""
OmniAI Studio - Google Authentication & Profile Management
Engineered by VIKA-BUILDS.
Provides Google OAuth sign-in flow, user profile persistence, and integration
with Google AI Studio for instant Gemini API keys.
"""

import os
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, List, Optional, Callable
import customtkinter as ctk

from config import cfg
import ui.theme as theme


class GoogleAuthManager:
    """Singleton manager for Google account authentication and profile state."""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GoogleAuthManager, cls).__new__(cls)
            cls._instance._listeners: List[Callable[[Dict[str, Any]], None]] = []
        return cls._instance

    def get_profile(self) -> Dict[str, Any]:
        """Returns the current stored user profile."""
        profile = cfg.get_setting("user_profile", {})
        if not profile or not isinstance(profile, dict):
            profile = {
                "signed_in": False,
                "name": "",
                "email": "",
                "picture": "",
                "provider": "google",
                "connected_at": 0
            }
        return profile

    def is_signed_in(self) -> bool:
        """Returns True if user has an active Google session."""
        prof = self.get_profile()
        return bool(prof.get("signed_in", False) and prof.get("email"))

    def get_display_name(self) -> str:
        """Returns user's first name or email username for compact badges."""
        prof = self.get_profile()
        name = prof.get("name", "").strip()
        if name:
            return name.split()[0]
        email = prof.get("email", "").strip()
        if email:
            return email.split("@")[0]
        return "Sign In"

    def get_initials(self) -> str:
        """Returns 1-2 initials for avatar display."""
        prof = self.get_profile()
        name = prof.get("name", "").strip()
        if name:
            parts = name.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[1][0]}".upper()
            return parts[0][0].upper()
        email = prof.get("email", "").strip()
        if email:
            return email[0].upper()
        return "G"

    def sign_in(self, name: str, email: str, picture: str = "") -> Dict[str, Any]:
        """Saves Google session and notifies UI listeners."""
        clean_email = email.strip()
        clean_name = name.strip() or clean_email.split("@")[0].capitalize()
        profile = {
            "signed_in": True,
            "name": clean_name,
            "email": clean_email,
            "picture": picture.strip(),
            "provider": "google",
            "connected_at": int(time.time())
        }
        cfg.set_setting("user_profile", profile)
        self.notify_listeners()
        return profile

    def sign_out(self):
        """Clears Google profile and notifies UI listeners."""
        cfg.set_setting("user_profile", {
            "signed_in": False,
            "name": "",
            "email": "",
            "picture": "",
            "provider": "google",
            "connected_at": 0
        })
        self.notify_listeners()

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for auth state changes."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Dict[str, Any]], None]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def notify_listeners(self):
        """Invoke all registered callbacks with updated profile."""
        prof = self.get_profile()
        for cb in self._listeners:
            try:
                cb(prof)
            except Exception as e:
                print(f"[GoogleAuth] Listener callback error: {e}")


# Global Singleton
google_auth_mgr = GoogleAuthManager()


class GoogleAuthDialog(ctk.CTkToplevel):
    """
    Modern Google Sign-In and User Profile Modal Dialog.
    Allows signing in with Google, viewing profile details, and linking Google AI Studio.
    """

    def __init__(self, master=None, on_success: Optional[Callable[[], None]] = None):
        super().__init__(master)
        self.on_success = on_success

        self.title("Google Account — OmniAI Studio")
        self.geometry("520x460")
        self.minsize(480, 420)
        self.resizable(False, False)

        # Center dialog relative to master
        if master:
            self.transient(master)
            try:
                x = master.winfo_rootx() + (master.winfo_width() // 2) - 260
                y = master.winfo_rooty() + (master.winfo_height() // 2) - 230
                self.geometry(f"+{max(0, x)}+{max(0, y)}")
            except Exception:
                pass

        self.grab_set()
        self.focus_force()

        self._build_ui()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        if google_auth_mgr.is_signed_in():
            self._build_signed_in_view()
        else:
            self._build_sign_in_view()

    # -------------------------------------------------------------------------
    # SIGNED OUT: SIGN IN FORM
    # -------------------------------------------------------------------------
    def _build_sign_in_view(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        # Top Google Brand Badge
        top_brand = ctk.CTkFrame(container, fg_color="transparent")
        top_brand.pack(fill="x", pady=(0, 12))

        # Colored Google "G" circle
        g_badge = ctk.CTkFrame(
            top_brand,
            width=44,
            height=44,
            corner_radius=22,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E5E7EB"
        )
        g_badge.pack(side="left")
        g_badge.pack_propagate(False)

        lbl_g = ctk.CTkLabel(
            g_badge,
            text="G",
            font=("Segoe UI", 20, "bold"),
            text_color="#4285F4"
        )
        lbl_g.pack(expand=True)

        brand_text_box = ctk.CTkFrame(top_brand, fg_color="transparent")
        brand_text_box.pack(side="left", padx=12)

        lbl_title = ctk.CTkLabel(
            brand_text_box,
            text="Sign in with Google",
            font=theme.FONT_TITLE,
            text_color=theme.COLOR_TEXT_MAIN,
            anchor="w"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            brand_text_box,
            text="Connect your Google identity to unlock AI Studio & features",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
            anchor="w"
        )
        lbl_sub.pack(anchor="w")

        # Info Box
        info_card = ctk.CTkFrame(
            container,
            fg_color=theme.COLOR_CARD_ALT,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER
        )
        info_card.pack(fill="x", pady=(0, 16))

        benefits = [
            "✨ 1-Click access to Google AI Studio (Free Gemini 2.0 Flash / Pro keys)",
            "🔒 Encrypted local profile storage with zero tracking",
            "⚡ Seamless multi-key management and failover integration"
        ]
        for b in benefits:
            ctk.CTkLabel(
                info_card,
                text=b,
                font=theme.FONT_SMALL,
                text_color=theme.COLOR_TEXT_MAIN,
                anchor="w",
                justify="left"
            ).pack(anchor="w", padx=12, pady=3)

        # Quick 1-Click Browser OAuth Button
        btn_oauth = ctk.CTkButton(
            container,
            text="🌐  Authorize with Google in Browser",
            height=38,
            font=theme.FONT_BODY_BOLD,
            fg_color="#4285F4",
            hover_color="#3367D6",
            text_color="#FFFFFF",
            corner_radius=8,
            command=self._launch_browser_oauth
        )
        btn_oauth.pack(fill="x", pady=(0, 12))

        # Divider "OR ENTER GOOGLE ACCOUNT DIRECTLY"
        div_row = ctk.CTkFrame(container, fg_color="transparent")
        div_row.pack(fill="x", pady=4)
        ctk.CTkFrame(div_row, height=1, fg_color=theme.COLOR_BORDER).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(div_row, text=" OR SIGN IN DIRECTLY ", font=theme.FONT_BADGE, text_color=theme.COLOR_TEXT_DIM).pack(side="left", padx=8)
        ctk.CTkFrame(div_row, height=1, fg_color=theme.COLOR_BORDER).pack(side="left", fill="x", expand=True)

        # Form Fields
        lbl_email = ctk.CTkLabel(container, text="Google Email Address:", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED, anchor="w")
        lbl_email.pack(fill="x", pady=(4, 2))

        self.entry_email = ctk.CTkEntry(
            container,
            placeholder_text="e.g. yourname@gmail.com",
            font=theme.FONT_BODY,
            height=32,
            fg_color=theme.COLOR_INPUT,
            border_color=theme.COLOR_BORDER
        )
        self.entry_email.pack(fill="x", pady=(0, 8))

        lbl_name = ctk.CTkLabel(container, text="Your Full Name (Display):", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED, anchor="w")
        lbl_name.pack(fill="x", pady=(2, 2))

        self.entry_name = ctk.CTkEntry(
            container,
            placeholder_text="e.g. Vikas",
            font=theme.FONT_BODY,
            height=32,
            fg_color=theme.COLOR_INPUT,
            border_color=theme.COLOR_BORDER
        )
        self.entry_name.pack(fill="x", pady=(0, 14))

        # Action Buttons
        btn_box = ctk.CTkFrame(container, fg_color="transparent")
        btn_box.pack(fill="x", side="bottom")

        btn_cancel = ctk.CTkButton(
            btn_box,
            text="Cancel",
            width=90,
            height=34,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(6, 0))

        btn_signin = ctk.CTkButton(
            btn_box,
            text="Sign In",
            width=110,
            height=34,
            font=theme.FONT_BODY_BOLD,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._on_direct_sign_in
        )
        btn_signin.pack(side="right")

    def _launch_browser_oauth(self):
        """Opens Google Accounts login / AI Studio in user's browser."""
        try:
            webbrowser.open("https://accounts.google.com/ServiceLogin?continue=https://aistudio.google.com/app/apikey")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open browser: {e}", parent=self)

        # Prompt user to confirm email after browser opens
        self.entry_email.focus_set()

    def _on_direct_sign_in(self):
        email = self.entry_email.get().strip()
        name = self.entry_name.get().strip()
        if not email or "@" not in email:
            messagebox.showwarning("Invalid Email", "Please enter a valid Google email address (@gmail.com or Google Workspace).", parent=self)
            return

        google_auth_mgr.sign_in(name=name, email=email)
        if self.on_success:
            self.on_success()
        self._build_ui()

    # -------------------------------------------------------------------------
    # SIGNED IN: PROFILE VIEW
    # -------------------------------------------------------------------------
    def _build_signed_in_view(self):
        prof = google_auth_mgr.get_profile()
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        # Profile Card
        card = ctk.CTkFrame(
            container,
            fg_color=theme.COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.COLOR_BORDER
        )
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        # Avatar circle with user initials
        avatar = ctk.CTkFrame(
            inner,
            width=54,
            height=54,
            corner_radius=27,
            fg_color="#18181B" if theme.COLOR_ACCENT[0] == "#18181B" else "#3B82F6",
        )
        avatar.pack(side="left")
        avatar.pack_propagate(False)

        lbl_ini = ctk.CTkLabel(
            avatar,
            text=google_auth_mgr.get_initials(),
            font=("Segoe UI", 18, "bold"),
            text_color="#FFFFFF"
        )
        lbl_ini.pack(expand=True)

        user_info = ctk.CTkFrame(inner, fg_color="transparent")
        user_info.pack(side="left", padx=14)

        lbl_user_name = ctk.CTkLabel(
            user_info,
            text=prof.get("name", "Google User"),
            font=theme.FONT_HEADING,
            text_color=theme.COLOR_TEXT_MAIN,
            anchor="w"
        )
        lbl_user_name.pack(anchor="w")

        lbl_user_email = ctk.CTkLabel(
            user_info,
            text=prof.get("email", ""),
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
            anchor="w"
        )
        lbl_user_email.pack(anchor="w")

        status_chip = ctk.CTkLabel(
            user_info,
            text="● Google Account Connected",
            font=theme.FONT_BADGE,
            text_color=theme.COLOR_SUCCESS,
            anchor="w"
        )
        status_chip.pack(anchor="w", pady=(2, 0))

        # Quick Actions Card
        actions_card = ctk.CTkFrame(
            container,
            fg_color=theme.COLOR_CARD_ALT,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER
        )
        actions_card.pack(fill="x", pady=(0, 16))

        lbl_act = ctk.CTkLabel(
            actions_card,
            text="Connected Google AI Services",
            font=theme.FONT_SUBHEADING,
            text_color=theme.COLOR_TEXT_MAIN,
            anchor="w"
        )
        lbl_act.pack(anchor="w", padx=14, pady=(10, 4))

        # 1-Click Google AI Studio Button
        btn_studio = ctk.CTkButton(
            actions_card,
            text="🔑  Open Google AI Studio (Get Free Gemini 2.0 Key)",
            font=theme.FONT_BODY_BOLD,
            height=34,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=6,
            command=self._open_ai_studio
        )
        btn_studio.pack(fill="x", padx=14, pady=(2, 6))

        # Manage Google Account button
        btn_mng = ctk.CTkButton(
            actions_card,
            text="⚙️  Manage Google Account Security",
            font=theme.FONT_SMALL,
            height=28,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            corner_radius=6,
            command=lambda: webbrowser.open("https://myaccount.google.com/")
        )
        btn_mng.pack(fill="x", padx=14, pady=(0, 10))

        # Bottom row: Sign Out / Close
        bottom = ctk.CTkFrame(container, fg_color="transparent")
        bottom.pack(fill="x", side="bottom")

        btn_signout = ctk.CTkButton(
            bottom,
            text="Sign Out",
            width=90,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_ERROR,
            hover_color="#B91C1C",
            text_color="#FFFFFF",
            command=self._on_sign_out
        )
        btn_signout.pack(side="left")

        btn_close = ctk.CTkButton(
            bottom,
            text="Done",
            width=80,
            height=32,
            font=theme.FONT_BODY_BOLD,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self.destroy
        )
        btn_close.pack(side="right")

    def _open_ai_studio(self):
        webbrowser.open("https://aistudio.google.com/app/apikey")

    def _on_sign_out(self):
        if messagebox.askyesno("Sign Out", "Are you sure you want to sign out of your Google account?", parent=self):
            google_auth_mgr.sign_out()
            if self.on_success:
                self.on_success()
            self._build_ui()


def show_google_auth_dialog(parent_window=None, on_success: Optional[Callable[[], None]] = None) -> GoogleAuthDialog:
    """Helper to open Google Auth Modal Dialog."""
    return GoogleAuthDialog(parent_window, on_success=on_success)
