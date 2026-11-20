"""
OmniAI Studio - Multi-Key Pools & Auto-Failover Manager
Engineered by VIKA-BUILDS.
Configure API keys or key pools with automatic rate limit failover rotation.
Compact, space-efficient design.
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
    ("openai", "OpenAI (GPT-4o / DALL-E)", "sk-proj-... or sk-..."),
    ("gemini", "Google Gemini (1.5 & 2.0)", "AIzaSy..."),
    ("claude", "Anthropic Claude (3.5 & 3.7)", "sk-ant-api03-..."),
    ("groq", "Groq (Llama 3.3 Free & Fast)", "gsk_..."),
    ("deepseek", "DeepSeek (V3 & R1)", "sk-..."),
    ("openrouter", "OpenRouter (300+ Models)", "sk-or-v1-..."),
    ("mistral", "Mistral AI", "from console.mistral.ai"),
    ("stability", "Stability AI (SD3 / Core)", "sk-... (from platform.stability.ai)"),
    ("replicate", "Replicate (FLUX & Video)", "r8_... (from replicate.com)")
]


class KeysTab(ctk.CTkFrame):
    def __init__(self, master, status_callback=None):
        super().__init__(master, fg_color="transparent")
        self.status_callback = status_callback

        self.key_entries: Dict[str, ctk.CTkEntry] = {}
        self.key_status_badges: Dict[str, ctk.CTkLabel] = {}
        self.pool_badges: Dict[str, ctk.CTkLabel] = {}

        self._build_ui()
        self._update_all_pool_badges()

    @property
    def key_textboxes(self):
        """Backward-compatibility alias."""
        return self.key_entries

    def _build_ui(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=12, pady=8)

        # Compact Header Banner
        banner = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.COLOR_CARD_ALT,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        banner.pack(fill="x", padx=8, pady=(0, 8))

        b_title = ctk.CTkLabel(
            banner,
            text="API Keys & Multi-Key Failover Pools",
            font=theme.FONT_HEADING,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        b_title.pack(anchor="w", padx=14, pady=(8, 2))

        b_desc = ctk.CTkLabel(
            banner,
            text=(
                "Enter API keys below. For rate-limit failover (HTTP 429), separate multiple keys "
                "with commas or click 'Pool...' for the multi-line editor. All keys are encrypted locally."
            ),
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left",
        )
        b_desc.pack(anchor="w", padx=14, pady=(0, 8))

        # Compact Provider Key Cards
        for key_id, label_text, hint in KEY_ITEMS:
            self._create_provider_card(key_id, label_text, hint)

        # Custom Endpoint Section
        self._create_custom_endpoint_section()

        # Action Toolbar
        self._create_actions_bar()

    def _create_provider_card(self, key_id: str, label_text: str, hint: str):
        card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        card.pack(fill="x", padx=8, pady=3)

        # Header Row: Provider Name | Pool Badge | Test Button | Status
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(6, 2))

        lbl = ctk.CTkLabel(
            header,
            text=label_text,
            font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        lbl.pack(side="left")

        pool_badge = ctk.CTkLabel(
            header,
            text="0 Keys",
            font=theme.FONT_BADGE,
            text_color="#94A3B8",
        )
        pool_badge.pack(side="left", padx=8)
        self.pool_badges[key_id] = pool_badge

        badge = ctk.CTkLabel(
            header,
            text="Untested",
            font=theme.FONT_BADGE,
            text_color="#64748B",
            width=110,
            anchor="e",
        )
        badge.pack(side="right")
        self.key_status_badges[key_id] = badge

        btn_test = ctk.CTkButton(
            header,
            text="Test",
            width=65,
            height=24,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=lambda k=key_id: self._test_provider_key(k),
        )
        btn_test.pack(side="right", padx=(0, 8))

        # Input Row: Single-line Compact Entry + Pool Editor button
        input_row = ctk.CTkFrame(card, fg_color="transparent")
        input_row.pack(fill="x", padx=12, pady=(2, 6))

        saved_keys = cfg.get_keys(key_id)
        saved_str = ", ".join(saved_keys)

        entry = ctk.CTkEntry(
            input_row,
            height=28,
            font=theme.FONT_CODE,
            fg_color=theme.COLOR_INPUT,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            corner_radius=6,
            placeholder_text=f"Enter key or multiple comma-separated keys ({hint})",
        )
        if saved_str:
            entry.insert(0, saved_str)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.key_entries[key_id] = entry

        entry.bind("<KeyRelease>", lambda e, k=key_id: self._on_keys_text_changed(k))

        btn_pool = ctk.CTkButton(
            input_row,
            text="Pool...",
            width=55,
            height=28,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=lambda k=key_id, l=label_text: self._open_pool_dialog(k, l),
        )
        btn_pool.pack(side="right")

    def _open_pool_dialog(self, key_id: str, label_text: str):
        """Dedicated multi-line editor for multi-key failover pools."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Key Pool — {label_text}")
        dialog.geometry("540x360")
        dialog.transient(self)
        dialog.grab_set()

        lbl = ctk.CTkLabel(
            dialog,
            text=f"Manage Key Pool for {label_text}",
            font=theme.FONT_HEADING,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        lbl.pack(anchor="w", padx=16, pady=(14, 2))

        sub = ctk.CTkLabel(
            dialog,
            text="Paste 1 or more keys below (one key per line). When one key hits rate limits (HTTP 429), OmniAI automatically rotates to the next active key.",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left",
            wraplength=500,
        )
        sub.pack(anchor="w", padx=16, pady=(0, 8))

        txt = ctk.CTkTextbox(
            dialog,
            font=theme.FONT_CODE,
            fg_color=theme.COLOR_INPUT,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            corner_radius=6,
            wrap="none",
        )
        txt.pack(fill="both", expand=True, padx=16, pady=4)

        current_raw = self.key_entries[key_id].get().strip()
        keys_list = parse_keys_string(current_raw)
        if keys_list:
            txt.insert("1.0", "\n".join(keys_list))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 14))

        def apply_pool():
            content = txt.get("1.0", "end-1c")
            keys = parse_keys_string(content)
            self.key_entries[key_id].delete(0, "end")
            self.key_entries[key_id].insert(0, ", ".join(keys))
            self._on_keys_text_changed(key_id)
            cfg.set_keys(key_id, keys)
            key_pools.emit_event("keys_updated", key_id, {"count": len(keys)})
            dialog.destroy()

        btn_apply = ctk.CTkButton(
            btn_row,
            text="Apply Pool",
            width=100,
            height=30,
            font=theme.FONT_BODY_BOLD,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=apply_pool,
        )
        btn_apply.pack(side="right")

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=80,
            height=30,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=dialog.destroy,
        )
        btn_cancel.pack(side="right", padx=8)

    def _on_keys_text_changed(self, key_id: str):
        entry = self.key_entries.get(key_id)
        if not entry:
            return
        raw = entry.get()
        keys = parse_keys_string(raw)
        badge = self.pool_badges.get(key_id)
        if badge:
            if len(keys) == 0:
                badge.configure(text="0 Keys", text_color="#94A3B8")
            elif len(keys) == 1:
                badge.configure(text="1 Key Active 🟢", text_color=theme.COLOR_SUCCESS)
            else:
                badge.configure(text=f"🔄 {len(keys)} Keys Pool (Auto-Failover) 🟢", text_color=theme.COLOR_SUCCESS)

    def _update_all_pool_badges(self):
        for key_id in self.key_entries:
            self._on_keys_text_changed(key_id)

    def _create_custom_endpoint_section(self):
        card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        card.pack(fill="x", padx=8, pady=(8, 4))

        # Header Row
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(6, 2))

        title = ctk.CTkLabel(
            header,
            text="Custom OpenAI-Compatible Endpoint (Ollama / LocalAI / LM Studio)",
            font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        title.pack(side="left")

        self.cust_status_badge = ctk.CTkLabel(
            header,
            text="Untested",
            font=theme.FONT_BADGE,
            text_color="#64748B",
            width=110,
            anchor="e",
        )
        self.cust_status_badge.pack(side="right")

        btn_test_cust = ctk.CTkButton(
            header,
            text="Test",
            width=65,
            height=24,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._test_custom_endpoint,
        )
        btn_test_cust.pack(side="right", padx=(0, 8))

        cust = cfg.get_custom_endpoint()

        # Row 1: Base URL
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=2)
        url_lbl = ctk.CTkLabel(row1, text="Base URL:", width=85, font=theme.FONT_SMALL, anchor="w", text_color=theme.COLOR_TEXT_MUTED)
        url_lbl.pack(side="left")
        self.cust_url_entry = ctk.CTkEntry(row1, height=28, font=theme.FONT_CODE, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.cust_url_entry.insert(0, cust.get("base_url", "http://localhost:11434/v1"))
        self.cust_url_entry.pack(side="left", fill="x", expand=True)

        # Row 2: API Key
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=2)
        key_lbl = ctk.CTkLabel(row2, text="API Key:", width=85, font=theme.FONT_SMALL, anchor="w", text_color=theme.COLOR_TEXT_MUTED)
        key_lbl.pack(side="left")
        self.cust_key_entry = ctk.CTkEntry(row2, height=28, font=theme.FONT_CODE, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER, placeholder_text="Optional for local models")
        self.cust_key_entry.insert(0, cust.get("api_key", ""))
        self.cust_key_entry.pack(side="left", fill="x", expand=True)

        # Row 3: Model Name
        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=12, pady=(2, 6))
        mod_lbl = ctk.CTkLabel(row3, text="Model Name:", width=85, font=theme.FONT_SMALL, anchor="w", text_color=theme.COLOR_TEXT_MUTED)
        mod_lbl.pack(side="left")
        self.cust_model_entry = ctk.CTkEntry(row3, height=28, font=theme.FONT_CODE, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.cust_model_entry.insert(0, cust.get("model_name", "llama3:latest"))
        self.cust_model_entry.pack(side="left", fill="x", expand=True)

    def _create_actions_bar(self):
        actions = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        actions.pack(fill="x", padx=8, pady=8)

        btn_save_all = ctk.CTkButton(
            actions,
            text="Save All Key Pools",
            font=theme.FONT_BODY_BOLD,
            height=32,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._save_all_keys,
        )
        btn_save_all.pack(side="left", padx=10, pady=8)

        btn_export = ctk.CTkButton(
            actions,
            text="Backup Config",
            width=110,
            height=32,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._export_config,
        )
        btn_export.pack(side="left", padx=4, pady=8)

        btn_import = ctk.CTkButton(
            actions,
            text="Restore Config",
            width=110,
            height=32,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._import_config,
        )
        btn_import.pack(side="left", padx=4, pady=8)

        btn_erase = ctk.CTkButton(
            actions,
            text="Erase All Keys",
            width=115,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_ERROR,
            hover_color="#B91C1C",
            text_color="#FFFFFF",
            command=self._erase_all_keys,
        )
        btn_erase.pack(side="right", padx=10, pady=8)

    def _save_all_keys(self):
        total_keys_count = 0
        for key_id, entry in self.key_entries.items():
            raw = entry.get()
            keys = parse_keys_string(raw)
            cfg.set_keys(key_id, keys)
            total_keys_count += len(keys)

        cfg.set_custom_endpoint(
            base_url=self.cust_url_entry.get().strip(),
            api_key=self.cust_key_entry.get().strip(),
            model_name=self.cust_model_entry.get().strip(),
        )

        self._update_all_pool_badges()
        key_pools.emit_event("keys_updated", "all", {"count": total_keys_count})
        messagebox.showinfo(
            "Saved",
            f"Successfully saved {total_keys_count} API keys across all key pools!",
        )
        if self.status_callback:
            self.status_callback(
                f"Saved {total_keys_count} keys with auto-failover ready."
            )

    def _test_provider_key(self, key_id: str):
        entry = self.key_entries.get(key_id)
        if not entry:
            return
        raw = entry.get()
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
            "replicate": "Replicate",
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
            model_name=self.cust_model_entry.get().strip(),
        )
        self.cust_status_badge.configure(text="Testing...", text_color="#F59E0B")

        def run():
            success, latency, msg = engine.test_connection("Custom OpenAI Endpoint")
            self.after(
                0,
                lambda: self._apply_test_result(
                    self.cust_status_badge, success, latency, msg
                ),
            )

        threading.Thread(target=run, daemon=True).start()

    def _apply_test_result(self, badge: ctk.CTkLabel, success: bool, latency: int, msg: str):
        if success:
            badge.configure(text=f"🟢 {msg}", text_color=theme.COLOR_SUCCESS)
        else:
            badge.configure(text=f"🔴 {msg[:25]}", text_color=theme.COLOR_ERROR)

    def _export_config(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Config", "*.json")]
        )
        if path:
            if cfg.export_to_file(path):
                messagebox.showinfo("Export Successful", f"Backup saved to:\n{path}")
            else:
                messagebox.showerror("Export Failed", "Could not export.")

    def _import_config(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Config", "*.json")])
        if path and os.path.exists(path):
            if cfg.import_from_file(path):
                for key_id, entry in self.key_entries.items():
                    entry.delete(0, "end")
                    entry.insert(0, ", ".join(cfg.get_keys(key_id)))
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
        if messagebox.askyesno(
            "Erase Keys",
            "Are you sure you want to erase ALL saved keys from this portable copy?",
        ):
            cfg.erase_all_keys()
            for key_id, entry in self.key_entries.items():
                entry.delete(0, "end")
                self.key_status_badges[key_id].configure(
                    text="Erased", text_color="#64748B"
                )
            self.cust_key_entry.delete(0, "end")
            self.cust_status_badge.configure(text="Erased", text_color="#64748B")
            self._update_all_pool_badges()
            messagebox.showinfo("Keys Erased", "All API keys have been wiped.")
