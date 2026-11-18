"""
OmniAI Studio - Multi-Key Pools & Auto-Failover Manager
Engineered by VIKA-BUILDS.
Configure multiple API keys per provider with automatic rate limit failover rotation.
"""

import os
import threading
from typing import Dict, List, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import cfg, CONFIG_FILE, parse_keys_string
from api_engine import engine, PROVIDERS
from key_pool import key_pools
import ui.theme as theme

KEY_ITEMS = [
    ("openai", "OpenAI Keys (GPT-4o / DALL-E)", "sk-proj-... or sk-... (One key per line)"),
    ("gemini", "Google Gemini Keys (1.5 & 2.0)", "AIzaSy... (One key per line)"),
    ("claude", "Anthropic Claude Keys", "sk-ant-api03-... (One key per line)"),
    ("groq", "Groq Keys (Llama 3.3 Free)", "gsk_... (One key per line)"),
    ("deepseek", "DeepSeek Keys (V3 & R1)", "sk-... (One key per line)"),
    ("openrouter", "OpenRouter Keys (300+ Models)", "sk-or-v1-... (One key per line)"),
    ("mistral", "Mistral AI Keys", "from console.mistral.ai"),
    ("stability", "Stability AI Keys (SD3 / Core)", "sk-... (from platform.stability.ai)"),
    ("replicate", "Replicate Keys (FLUX & Video)", "r8_... (from replicate.com/account)")
]

class KeysTab(ctk.CTkFrame):
    def __init__(self, master, status_callback=None):
        super().__init__(master, fg_color="transparent")
        self.status_callback = status_callback

        self.key_textboxes: Dict[str, ctk.CTkTextbox] = {}
        self.key_status_badges: Dict[str, ctk.CTkLabel] = {}
        self.pool_badges: Dict[str, ctk.CTkLabel] = {}

        self._build_ui()
        self._update_all_pool_badges()

    def _build_ui(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=14, pady=12)

        # Header Card
        banner = ctk.CTkFrame(self.scroll_frame, fg_color=theme.COLOR_CARD_ALT, corner_radius=10, border_width=1, border_color=theme.COLOR_BORDER)
        banner.pack(fill="x", padx=10, pady=(0, 12))

        b_title = ctk.CTkLabel(banner, text="Multi-Key Pools & Auto-Failover", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        b_title.pack(anchor="w", padx=18, pady=(14, 4))

        b_desc = ctk.CTkLabel(
            banner,
            text="Add MULTIPLE API keys for any model (one key per line or comma-separated).\nWhen one key reaches its rate limit (HTTP 429 or quota exceeded), the engine rotates to the next key automatically.\nAll keys are locally obfuscated and saved in 'portable_config.json' beside the executable.",
            font=theme.FONT_BODY,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left"
        )
        b_desc.pack(anchor="w", padx=18, pady=(0, 14))

        # Providers Key Cards
        for key_id, label_text, hint in KEY_ITEMS:
            self._create_provider_card(key_id, label_text, hint)

        # Custom Endpoint Section
        self._create_custom_endpoint_section()

        # Action Buttons
        self._create_actions_bar()

    def _create_provider_card(self, key_id: str, label_text: str, hint: str):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=theme.COLOR_CARD, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        card.pack(fill="x", padx=10, pady=6)

        # Card Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(10, 4))

        lbl = ctk.CTkLabel(header, text=label_text, font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        lbl.pack(side="left")

        pool_badge = ctk.CTkLabel(header, text="0 Keys", font=theme.FONT_BADGE, text_color="#94A3B8")
        pool_badge.pack(side="left", padx=12)
        self.pool_badges[key_id] = pool_badge

        badge = ctk.CTkLabel(header, text="Untested", font=theme.FONT_BADGE, text_color="#64748B", width=120)
        badge.pack(side="right")
        self.key_status_badges[key_id] = badge

        btn_test = ctk.CTkButton(
            header,
            text="Test Pool",
            width=85,
            height=26,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=lambda k=key_id: self._test_provider_key(k)
        )
        btn_test.pack(side="right", padx=8)

        # Multi-line Textbox for Keys
        saved_keys = cfg.get_keys(key_id)
        saved_str = "\n".join(saved_keys)

        txt = ctk.CTkTextbox(
            card,
            height=65,
            font=theme.FONT_CODE,
            fg_color=theme.COLOR_INPUT,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            corner_radius=6,
            wrap="none"
        )
        if saved_str:
            txt.insert("1.0", saved_str)
        txt.pack(fill="x", padx=14, pady=(2, 8))
        self.key_textboxes[key_id] = txt

        txt.bind("<KeyRelease>", lambda e, k=key_id: self._on_keys_text_changed(k))

        hint_lbl = ctk.CTkLabel(card, text=f"Tip: Enter 1 or more keys separated by newlines or commas. {hint}", font=theme.FONT_SMALL, text_color="#64748B")
        hint_lbl.pack(anchor="w", padx=14, pady=(0, 8))

    def _on_keys_text_changed(self, key_id: str):
        raw = self.key_textboxes[key_id].get("1.0", "end-1c")
        keys = parse_keys_string(raw)
        badge = self.pool_badges.get(key_id)
        if badge:
            if len(keys) == 0:
                badge.configure(text="0 Keys Configured", text_color="#94A3B8")
            elif len(keys) == 1:
                badge.configure(text="1 Key Active 🟢", text_color=theme.COLOR_SUCCESS)
            else:
                badge.configure(text=f"🔄 {len(keys)} Keys Pool (Auto-Failover Active) 🟢", text_color=theme.COLOR_SUCCESS)

    def _update_all_pool_badges(self):
        for key_id in self.key_textboxes:
            self._on_keys_text_changed(key_id)

    def _create_custom_endpoint_section(self):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=theme.COLOR_CARD, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        card.pack(fill="x", padx=10, pady=(10, 6))

        title = ctk.CTkLabel(card, text="Custom OpenAI-Compatible Endpoint (Ollama / LocalAI / LM Studio)", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        title.pack(anchor="w", padx=16, pady=(10, 4))

        cust = cfg.get_custom_endpoint()

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=4)
        url_lbl = ctk.CTkLabel(row1, text="Base URL:", width=90, font=theme.FONT_SMALL, anchor="w", text_color=theme.COLOR_TEXT_MUTED)
        url_lbl.pack(side="left")
        self.cust_url_entry = ctk.CTkEntry(row1, font=theme.FONT_CODE, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.cust_url_entry.insert(0, cust.get("base_url", "http://localhost:11434/v1"))
        self.cust_url_entry.pack(side="left", fill="x", expand=True)

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)
        key_lbl = ctk.CTkLabel(row2, text="API Key:", width=90, font=theme.FONT_SMALL, anchor="w", text_color=theme.COLOR_TEXT_MUTED)
        key_lbl.pack(side="left")
        self.cust_key_entry = ctk.CTkEntry(row2, font=theme.FONT_CODE, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER, placeholder_text="Optional for local models")
        self.cust_key_entry.insert(0, cust.get("api_key", ""))
        self.cust_key_entry.pack(side="left", fill="x", expand=True)

        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=(4, 12))
        mod_lbl = ctk.CTkLabel(row3, text="Model Name:", width=90, font=theme.FONT_SMALL, anchor="w", text_color=theme.COLOR_TEXT_MUTED)
        mod_lbl.pack(side="left")
        self.cust_model_entry = ctk.CTkEntry(row3, font=theme.FONT_CODE, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.cust_model_entry.insert(0, cust.get("model_name", "llama3:latest"))
        self.cust_model_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_test_cust = ctk.CTkButton(
            row3,
            text="Test Endpoint",
            width=110,
            height=30,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._test_custom_endpoint
        )
        btn_test_cust.pack(side="right")

        self.cust_status_badge = ctk.CTkLabel(card, text="Untested", font=theme.FONT_BADGE, text_color="#64748B")
        self.cust_status_badge.pack(anchor="e", padx=16, pady=(0, 8))

    def _create_actions_bar(self):
        actions = ctk.CTkFrame(self.scroll_frame, fg_color=theme.COLOR_CARD, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        actions.pack(fill="x", padx=10, pady=10)

        btn_save_all = ctk.CTkButton(
            actions,
            text="Save All Key Pools",
            font=theme.FONT_BODY_BOLD,
            height=36,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._save_all_keys
        )
        btn_save_all.pack(side="left", padx=12, pady=10)

        btn_export = ctk.CTkButton(
            actions,
            text="Backup Config",
            width=115,
            height=36,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._export_config
        )
        btn_export.pack(side="left", padx=4, pady=10)

        btn_import = ctk.CTkButton(
            actions,
            text="Restore Config",
            width=115,
            height=36,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._import_config
        )
        btn_import.pack(side="left", padx=4, pady=10)

        btn_erase = ctk.CTkButton(
            actions,
            text="Erase All Keys",
            width=125,
            height=36,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_ERROR,
            hover_color="#B91C1C",
            text_color="#FFFFFF",
            command=self._erase_all_keys
        )
        btn_erase.pack(side="right", padx=12, pady=10)

    def _save_all_keys(self):
        total_keys_count = 0
        for key_id, txt in self.key_textboxes.items():
            raw = txt.get("1.0", "end-1c")
            keys = parse_keys_string(raw)
            cfg.set_keys(key_id, keys)
            total_keys_count += len(keys)

        cfg.set_custom_endpoint(
            base_url=self.cust_url_entry.get().strip(),
            api_key=self.cust_key_entry.get().strip(),
            model_name=self.cust_model_entry.get().strip()
        )

        self._update_all_pool_badges()
        messagebox.showinfo("Saved", f"Successfully saved {total_keys_count} API keys across all key pools!")
        if self.status_callback:
            self.status_callback(f"Saved {total_keys_count} keys with auto-failover ready.")

    def _test_provider_key(self, key_id: str):
        raw = self.key_textboxes[key_id].get("1.0", "end-1c")
        keys = parse_keys_string(raw)
        cfg.set_keys(key_id, keys)

        badge = self.key_status_badges[key_id]
        badge.configure(text="Testing...", text_color="#F59E0B")

        prov_map = {
            "openai": "OpenAI (Official)",
            "gemini": "Google Gemini",
            "claude": "Anthropic Claude",
            "groq": "Groq (Free & Ultra-Fast)",
            "deepseek": "DeepSeek",
            "openrouter": "OpenRouter (300+ Models)",
            "mistral": "Mistral AI",
            "stability": "Stability AI",
            "replicate": "Replicate"
        }
        prov_name = prov_map.get(key_id, "OpenAI (Official)")

        def run():
            success, latency, msg = engine.test_connection(prov_name)
            self.after(0, lambda: self._apply_test_result(badge, success, latency, msg))

        threading.Thread(target=run, daemon=True).start()

    def _test_custom_endpoint(self):
        cfg.set_custom_endpoint(
            base_url=self.cust_url_entry.get().strip(),
            api_key=self.cust_key_entry.get().strip(),
            model_name=self.cust_model_entry.get().strip()
        )
        self.cust_status_badge.configure(text="Testing...", text_color="#F59E0B")

        def run():
            success, latency, msg = engine.test_connection("Custom OpenAI Endpoint")
            self.after(0, lambda: self._apply_test_result(self.cust_status_badge, success, latency, msg))

        threading.Thread(target=run, daemon=True).start()

    def _apply_test_result(self, badge: ctk.CTkLabel, success: bool, latency: int, msg: str):
        if success:
            badge.configure(text=f"🟢 {msg}", text_color=theme.COLOR_SUCCESS)
        else:
            badge.configure(text=f"🔴 {msg[:25]}", text_color=theme.COLOR_ERROR)

    def _export_config(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Config", "*.json")])
        if path:
            if cfg.export_to_file(path):
                messagebox.showinfo("Export Successful", f"Backup saved to:\n{path}")
            else:
                messagebox.showerror("Export Failed", "Could not export.")

    def _import_config(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Config", "*.json")])
        if path and os.path.exists(path):
            if cfg.import_from_file(path):
                for key_id, txt in self.key_textboxes.items():
                    txt.delete("1.0", "end")
                    txt.insert("1.0", "\n".join(cfg.get_keys(key_id)))
                cust = cfg.get_custom_endpoint()
                self.cust_url_entry.delete(0, "end")
                self.cust_url_entry.insert(0, cust.get("base_url", ""))
                self.cust_key_entry.delete(0, "end")
                self.cust_key_entry.insert(0, cust.get("api_key", ""))
                self.cust_model_entry.delete(0, "end")
                self.cust_model_entry.insert(0, cust.get("model_name", ""))
                self._update_all_pool_badges()
                messagebox.showinfo("Import Successful", "Configuration restored!")
            else:
                messagebox.showerror("Import Failed", "Invalid configuration file.")

    def _erase_all_keys(self):
        if messagebox.askyesno("Erase Keys", "Are you sure you want to erase ALL saved keys from this portable copy?"):
            cfg.erase_all_keys()
            for key_id, txt in self.key_textboxes.items():
                txt.delete("1.0", "end")
                self.key_status_badges[key_id].configure(text="Erased", text_color="#64748B")
            self.cust_key_entry.delete(0, "end")
            self.cust_status_badge.configure(text="Erased", text_color="#64748B")
            self._update_all_pool_badges()
            messagebox.showinfo("Keys Erased", "All API keys have been wiped.")
