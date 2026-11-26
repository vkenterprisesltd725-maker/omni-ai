"""
OmniAI Studio - 1-Click Free API Hub & Clipboard Auto-Detector
Engineered by VIKA-BUILDS.
Instant direct consoles for free official AI keys and intelligent clipboard auto-detection.
"""

import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, List, Optional, Tuple, Callable
import customtkinter as ctk

from config import cfg, parse_keys_string
from api_engine import engine
from key_pool import key_pools
import ui.theme as theme


FREE_CONSOLE_CATALOG = [
    {
        "id": "gemini",
        "name": "Google AI Studio (Gemini 2.0 & 1.5)",
        "badge": "15 RPM Free Tier",
        "desc": "Official free access to Gemini 2.0 Flash, Gemini 1.5 Pro & Flash. No credit card required.",
        "url": "https://aistudio.google.com/app/apikey",
        "prefix": "AIzaSy",
        "hint": "AIzaSy..."
    },
    {
        "id": "groq",
        "name": "Groq Cloud (Llama 3.3 70B & Whisper)",
        "badge": "Ultra-Fast 500+ tok/s",
        "desc": "Instant free inference on Llama 3.3, Llama 3.1 8B, and Whisper speech models.",
        "url": "https://console.groq.com/keys",
        "prefix": "gsk_",
        "hint": "gsk_..."
    },
    {
        "id": "cerebras",
        "name": "Cerebras Cloud (World's Fastest Inference)",
        "badge": "1M Free Tokens / Day",
        "desc": "Ultra-fast 2,000+ tokens/sec on Llama 3.3 70B and 3.1 8B. Generous daily free quota.",
        "url": "https://cloud.cerebras.ai/platform/",
        "prefix": "csk-",
        "hint": "csk-..."
    },
    {
        "id": "github_models",
        "name": "GitHub Models (Free AI Token)",
        "badge": "50 Req / Day Free",
        "desc": "Official GitHub PAT token access to GPT-4o, Claude 3.5 Sonnet, and Llama 3 via Azure.",
        "url": "https://github.com/settings/tokens",
        "prefix": "ghp_",
        "hint": "ghp_... or github_pat_..."
    },
    {
        "id": "openrouter",
        "name": "OpenRouter Free Models",
        "badge": "300+ Models Available",
        "desc": "Access multiple free models tagged with :free including DeepSeek V3, Llama 3, and Mistral.",
        "url": "https://openrouter.ai/keys",
        "prefix": "sk-or-v1-",
        "hint": "sk-or-v1-..."
    },
    {
        "id": "pollinations",
        "name": "Pollinations AI (Built-in Zero Account)",
        "badge": "100% Free - Active Now",
        "desc": "Built right into OmniAI Studio: FLUX image generation, OpenAI, and Qwen text models without any key.",
        "url": "https://pollinations.ai/",
        "prefix": "none",
        "hint": "Zero Key / Zero Account Needed"
    }
]


def detect_provider_from_key(key: str) -> Optional[str]:
    """Detects provider identifier from API key string pattern."""
    k = key.strip()
    if not k:
        return None
    if k.startswith("AIzaSy"):
        return "gemini"
    if k.startswith("gsk_"):
        return "groq"
    if k.startswith("csk-"):
        return "cerebras"
    if k.startswith("ghp_") or k.startswith("github_pat_"):
        return "github_models"
    if k.startswith("sk-ant-api") or k.startswith("sk-ant-"):
        return "claude"
    if k.startswith("sk-or-v1-"):
        return "openrouter"
    if k.startswith("r8_"):
        return "replicate"
    if k.startswith("sk-proj-"):
        return "openai"
    if k.startswith("sk-"):
        # Generic sk- prefix could be OpenAI or DeepSeek
        return "deepseek" if len(k) < 40 else "openai"
    return None


def auto_detect_and_paste_key(parent_widget, on_saved: Optional[Callable[[str, str], None]] = None) -> Tuple[bool, str]:
    """
    Reads clipboard, identifies provider key prefix, adds to key pool,
    saves config, and runs background live validation.
    Returns (success_flag, status_message).
    """
    try:
        raw_clipboard = parent_widget.clipboard_get().strip()
    except Exception:
        return False, "Clipboard is empty or does not contain text."

    # Parse possible multiple keys
    keys = parse_keys_string(raw_clipboard)
    if not keys:
        return False, "Clipboard is empty."

    first_key = keys[0]
    provider = detect_provider_from_key(first_key)
    if not provider:
        return False, f"Unrecognized key format ({first_key[:12]}...). Please copy a valid Gemini, Groq, Cerebras, GitHub, Claude, or OpenAI key."

    # Retrieve existing keys for provider and append new keys
    existing_keys = cfg.get_keys(provider)
    new_added = 0
    for k in keys:
        if k not in existing_keys:
            existing_keys.append(k)
            new_added += 1

    cfg.set_keys(provider, existing_keys)
    key_pools.emit_event("keys_updated", provider, {"count": len(existing_keys)})

    # Notify caller if callback provided
    if on_saved:
        on_saved(provider, ", ".join(existing_keys))

    # Test key asynchronously
    def test_in_background():
        ok, msg = engine.test_key(provider, first_key)
        # We can update the pool status badge or show brief confirmation
        pool = key_pools.get_pool(provider)
        pool.mark_result(first_key, ok, 200 if ok else 400)

    threading.Thread(target=test_in_background, daemon=True).start()

    msg = f"Successfully detected {provider.upper()} API Key ({first_key[:8]}...{first_key[-4:]})!\nSaved to key pool (Total: {len(existing_keys)} keys)."
    return True, msg


class FreeApiHubDialog(ctk.CTkToplevel):
    """
    Modal Hub for 1-Click Free API Consoles & Instant Key Auto-Detection.
    """

    def __init__(self, master=None, on_keys_updated: Optional[Callable[[str, str], None]] = None):
        super().__init__(master)
        self.on_keys_updated = on_keys_updated

        self.title("1-Click Free API Hub — OmniAI Studio")
        self.geometry("620x540")
        self.minsize(580, 480)

        if master:
            self.transient(master)
            try:
                x = master.winfo_rootx() + (master.winfo_width() // 2) - 310
                y = master.winfo_rooty() + (master.winfo_height() // 2) - 270
                self.geometry(f"+{max(0, x)}+{max(0, y)}")
            except Exception:
                pass

        self.grab_set()
        self.focus_force()

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=16)

        # Header Banner
        top_banner = ctk.CTkFrame(
            container,
            fg_color=theme.COLOR_CARD_ALT,
            corner_radius=10,
            border_width=1,
            border_color=theme.COLOR_BORDER
        )
        top_banner.pack(fill="x", pady=(0, 12))

        b_title = ctk.CTkLabel(
            top_banner,
            text="⚡ 1-Click Free API Generator Hub",
            font=theme.FONT_TITLE,
            text_color=theme.COLOR_TEXT_MAIN,
            anchor="w"
        )
        b_title.pack(anchor="w", padx=14, pady=(10, 2))

        b_sub = ctk.CTkLabel(
            top_banner,
            text=(
                "Open official developer consoles in 1 click, copy your free API key, "
                "then click 'Auto-Detect & Paste' below. OmniAI automatically routes, tests, and pools keys."
            ),
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left",
            wraplength=560
        )
        b_sub.pack(anchor="w", padx=14, pady=(0, 10))

        # Top Action Bar: Auto-Detect & Paste
        action_bar = ctk.CTkFrame(
            container,
            fg_color=theme.COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER
        )
        action_bar.pack(fill="x", pady=(0, 12))

        btn_clipboard = ctk.CTkButton(
            action_bar,
            text="📋  Auto-Detect & Paste Key from Clipboard",
            height=36,
            font=theme.FONT_BODY_BOLD,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=6,
            command=self._on_clipboard_click
        )
        btn_clipboard.pack(fill="x", padx=12, pady=10)

        # Scrollable Catalog
        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=(0, 10))

        for item in FREE_CONSOLE_CATALOG:
            self._render_catalog_item(scroll, item)

        # Bottom Close Button
        btn_close = ctk.CTkButton(
            container,
            text="Done",
            width=90,
            height=32,
            font=theme.FONT_BODY_BOLD,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self.destroy
        )
        btn_close.pack(side="right")

    def _render_catalog_item(self, parent, item: dict):
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER
        )
        card.pack(fill="x", pady=4)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        name_lbl = ctk.CTkLabel(
            header,
            text=item["name"],
            font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN
        )
        name_lbl.pack(side="left")

        badge_lbl = ctk.CTkLabel(
            header,
            text=f"  {item['badge']}  ",
            font=theme.FONT_BADGE,
            text_color=theme.COLOR_SUCCESS,
            fg_color=theme.COLOR_CARD_ALT,
            corner_radius=4,
            height=20
        )
        badge_lbl.pack(side="left", padx=8)

        # Status badge if already configured
        p_id = item["id"]
        if p_id != "pollinations":
            keys = cfg.get_keys(p_id)
            if keys:
                stat = ctk.CTkLabel(header, text=f"● {len(keys)} Key(s) Active", font=theme.FONT_BADGE, text_color=theme.COLOR_SUCCESS)
                stat.pack(side="right")

        desc_row = ctk.CTkFrame(card, fg_color="transparent")
        desc_row.pack(fill="x", padx=12, pady=(0, 8))

        desc_lbl = ctk.CTkLabel(
            desc_row,
            text=item["desc"],
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left",
            wraplength=420,
            anchor="w"
        )
        desc_lbl.pack(side="left", fill="x", expand=True)

        btn_open = ctk.CTkButton(
            desc_row,
            text="⚡ Open Console",
            width=115,
            height=28,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#18181B",
            corner_radius=6,
            command=lambda u=item["url"]: webbrowser.open(u)
        )
        btn_open.pack(side="right", padx=(8, 0))

    def _on_clipboard_click(self):
        success, msg = auto_detect_and_paste_key(self, on_saved=self.on_keys_updated)
        if success:
            messagebox.showinfo("Key Added Successfully", msg, parent=self)
            self.destroy()
        else:
            messagebox.showwarning("Clipboard Detection", msg, parent=self)


def show_free_api_hub(parent_window=None, on_keys_updated: Optional[Callable[[str, str], None]] = None) -> FreeApiHubDialog:
    """Helper to open Free API Hub Modal Dialog."""
    return FreeApiHubDialog(parent_window, on_keys_updated=on_keys_updated)
