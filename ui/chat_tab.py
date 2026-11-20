"""
OmniAI Studio - Chat & Multimodal Vision Tab
Engineered by VIKA-BUILDS.
Supports live token streaming, image attachments, multi-turn dialogue,
live Multi-Key Failover telemetry, chat history persistence,
and mid-conversation model switching.
"""

import os
import re
import json
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import pyperclip

from config import cfg, OUTPUTS_IMAGE_DIR, BASE_DIR
from api_engine import engine, PROVIDERS, is_model_free
from key_pool import key_pools
import ui.theme as theme

# ---------------------------------------------------------------------------
# Chat history directory
# ---------------------------------------------------------------------------
CHAT_HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_filename(text: str, max_len: int = 40) -> str:
    """Turn arbitrary text into a safe, short filename fragment."""
    text = text.strip()[:max_len]
    text = re.sub(r'[\\/:*?"<>|\r\n]+', '_', text)
    text = re.sub(r'_+', '_', text).strip('_ ')
    return text or "untitled"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatTab(ctk.CTkFrame):
    def __init__(self, master, status_callback=None):
        super().__init__(master, fg_color="transparent")
        self.status_callback = status_callback

        # Conversation state
        self.messages: List[Dict[str, Any]] = []
        self.current_attached_image: Optional[str] = None
        self.is_generating = False
        self.cancel_event = threading.Event()
        self.active_assistant_label: Optional[ctk.CTkLabel] = None
        self.active_copy_btn: Optional[ctk.CTkButton] = None
        self.active_assistant_text = ""

        # High-performance streaming buffer (eliminates Tkinter event flooding & UI freezes)
        self._stream_buffer: List[str] = []
        self._stream_lock = threading.Lock()
        self._stream_timer: Optional[str] = None
        self._stream_done_flag: bool = False
        self._stream_done_full: str = ""
        self._stream_err_flag: bool = False
        self._stream_err_msg: str = ""

        # Chat history state
        self.current_conversation_id: Optional[str] = None
        self.current_conversation_title: Optional[str] = None
        self.current_conversation_file: Optional[str] = None
        self.is_history_visible: bool = False  # Hidden by default; toggled via three-line menu button (☰)

        # Free models filter & model cache
        self.free_only_mode: bool = False
        self.raw_models_cache: List[str] = []

        self._build_ui()
        self._update_failover_telemetry()
        self._refresh_history_list()

        # Listen to failover events
        key_pools.register_listener(self._on_key_failover_event)

    # ===================================================================
    # UI CONSTRUCTION
    # ===================================================================

    def _build_ui(self):
        # Main horizontal layout: history sidebar | chat area
        self.main_hbox = ctk.CTkFrame(self, fg_color="transparent")
        self.main_hbox.pack(fill="both", expand=True)

        # ---- LEFT: Chat History Sidebar ----
        self._build_history_sidebar()

        # ---- RIGHT: Chat Area ----
        self.chat_area = ctk.CTkFrame(self.main_hbox, fg_color="transparent")
        self.chat_area.pack(side="left", fill="both", expand=True)

        self._build_top_bar()
        self._build_chat_viewport()
        self._build_attachment_bar()
        self._build_input_dock()

        # Kick off model list for the default provider
        self._on_provider_change(self.provider_combo.get())

    # -----------------------------------------------------------------
    # History sidebar
    # -----------------------------------------------------------------
    # History sidebar (Drawer - toggled via three-line menu button ☰)
    # -----------------------------------------------------------------
    def _build_history_sidebar(self):
        self.history_sidebar = ctk.CTkFrame(
            self.main_hbox,
            width=230,
            fg_color="#F7F7F8",
            corner_radius=0,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        # Note: Do not pack here by default; toggled via three-line menu button (☰)
        self.history_sidebar.pack_propagate(False)

        # Header Row: "Conversations" Title + Close Button
        header_row = ctk.CTkFrame(self.history_sidebar, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=(10, 4))

        lbl_title = ctk.CTkLabel(
            header_row,
            text="Conversations",
            font=theme.FONT_HEADING,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        lbl_title.pack(side="left")

        btn_close = ctk.CTkButton(
            header_row,
            text="✕",
            width=26,
            height=26,
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent",
            hover_color="#FEE2E2",
            text_color=theme.COLOR_TEXT_MUTED,
            command=self._toggle_history_sidebar,
        )
        btn_close.pack(side="right")

        # "New Chat" button
        btn_new = ctk.CTkButton(
            self.history_sidebar,
            text="+ New Chat",
            font=theme.FONT_BODY_BOLD,
            height=32,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._new_chat,
        )
        btn_new.pack(fill="x", padx=8, pady=(4, 6))

        # Section label
        lbl = ctk.CTkLabel(
            self.history_sidebar,
            text="SAVED SESSIONS",
            font=("Segoe UI", 8, "bold"),
            text_color=theme.COLOR_TEXT_DIM,
            anchor="w",
        )
        lbl.pack(fill="x", padx=12, pady=(4, 2))

        # Scrollable list
        self.history_list_frame = ctk.CTkScrollableFrame(
            self.history_sidebar,
            fg_color="transparent",
        )
        self.history_list_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Drawer Bottom: Developer Contact Links
        drawer_bottom = ctk.CTkFrame(
            self.history_sidebar,
            fg_color="#FFFFFF",
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        drawer_bottom.pack(fill="x", side="bottom", padx=8, pady=8)

        lbl_dev_c = ctk.CTkLabel(
            drawer_bottom,
            text="DEVELOPER CONTACT",
            font=("Segoe UI", 8, "bold"),
            text_color="#9CA3AF",
            anchor="w",
        )
        lbl_dev_c.pack(fill="x", padx=8, pady=(6, 2))

        import webbrowser
        btn_box = ctk.CTkFrame(drawer_bottom, fg_color="transparent")
        btn_box.pack(fill="x", padx=6, pady=(0, 6))

        btn_d_git = ctk.CTkButton(
            btn_box,
            text="🐙 Git",
            font=("Segoe UI", 9),
            height=26,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color=theme.COLOR_TEXT_MAIN,
            command=lambda: webbrowser.open(cfg.get_setting("developer_github", "https://github.com/vkenterprisesltd725-maker")),
        )
        btn_d_git.pack(side="left", fill="x", expand=True, padx=(0, 2))

        btn_d_insta = ctk.CTkButton(
            btn_box,
            text="📷 Insta",
            font=("Segoe UI", 9),
            height=26,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color=theme.COLOR_TEXT_MAIN,
            command=lambda: webbrowser.open(cfg.get_setting("developer_instagram", "https://instagram.com/vikaskhatik725")),
        )
        btn_d_insta.pack(side="left", fill="x", expand=True, padx=(2, 0))

    def _toggle_history_sidebar(self):
        """Toggle the conversation history drawer open/close."""
        if self.is_history_visible:
            self.history_sidebar.pack_forget()
            self.is_history_visible = False
            if hasattr(self, "btn_history_menu"):
                self.btn_history_menu.configure(
                    fg_color="#F3F4F6",
                    text_color="#1F2937",
                )
            if self.status_callback:
                self.status_callback("History collapsed")
        else:
            self.history_sidebar.pack(side="left", fill="y", before=self.chat_area)
            self.is_history_visible = True
            if hasattr(self, "btn_history_menu"):
                self.btn_history_menu.configure(
                    fg_color=theme.COLOR_ACCENT,
                    text_color="#FFFFFF",
                )
            self._refresh_history_list()
            if self.status_callback:
                self.status_callback("History opened")

    def _refresh_history_list(self):
        """Reload the sidebar list from disk."""
        for w in self.history_list_frame.winfo_children():
            w.destroy()

        entries = self._list_history_files()
        for entry in entries:
            self._add_history_item(entry)

    def _list_history_files(self) -> List[Dict[str, Any]]:
        """Return conversation metadata sorted most-recent first."""
        results = []
        if not os.path.isdir(CHAT_HISTORY_DIR):
            return results
        for fname in os.listdir(CHAT_HISTORY_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(CHAT_HISTORY_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append({
                    "id": data.get("id", ""),
                    "title": data.get("title", "Untitled"),
                    "updated_at": data.get("updated_at", ""),
                    "file": fpath,
                })
            except Exception:
                continue
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results

    def _add_history_item(self, entry: Dict[str, Any]):
        """Add one row to the sidebar history list."""
        row = ctk.CTkFrame(self.history_list_frame, fg_color="transparent", height=44)
        row.pack(fill="x", padx=4, pady=1)
        row.pack_propagate(False)

        title_text = entry.get("title", "Untitled")
        if len(title_text) > 28:
            title_text = title_text[:26] + "..."

        # Format date
        date_str = ""
        try:
            dt = datetime.fromisoformat(entry["updated_at"])
            date_str = dt.strftime("%b %d, %H:%M")
        except Exception:
            pass

        btn = ctk.CTkButton(
            row,
            text=title_text,
            font=theme.FONT_SMALL,
            anchor="w",
            height=26,
            fg_color="transparent",
            hover_color="#E5E7EB",
            text_color=theme.COLOR_TEXT_MAIN,
            command=lambda eid=entry["id"], ef=entry["file"]: self._load_conversation(eid, ef),
        )
        btn.pack(fill="x", side="top", padx=2, pady=(2, 0))

        bottom_row = ctk.CTkFrame(row, fg_color="transparent", height=14)
        bottom_row.pack(fill="x", padx=6, pady=0)

        date_lbl = ctk.CTkLabel(
            bottom_row,
            text=date_str,
            font=("Segoe UI", 8),
            text_color=theme.COLOR_TEXT_DIM,
            anchor="w",
        )
        date_lbl.pack(side="left")

        del_btn = ctk.CTkButton(
            bottom_row,
            text="x",
            width=18,
            height=14,
            font=("Segoe UI", 8),
            fg_color="transparent",
            hover_color="#FEE2E2",
            text_color=theme.COLOR_TEXT_DIM,
            command=lambda ef=entry["file"]: self._delete_conversation(ef),
        )
        del_btn.pack(side="right")

    # -----------------------------------------------------------------
    # Top telemetry & controls bar
    # -----------------------------------------------------------------
    def _build_top_bar(self):
        self.top_bar = ctk.CTkFrame(
            self.chat_area,
            fg_color=theme.COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        self.top_bar.pack(fill="x", padx=14, pady=(12, 6))

        # History drawer toggle button
        self.btn_history_menu = ctk.CTkButton(
            self.top_bar,
            text="🕘 History",
            width=78,
            height=28,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            corner_radius=6,
            command=self._toggle_history_sidebar,
        )
        self.btn_history_menu.grid(row=0, column=0, padx=(10, 4), pady=8, sticky="w")

        # Provider selector
        prov_lbl = ctk.CTkLabel(
            self.top_bar, text="Provider:", font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        prov_lbl.grid(row=0, column=1, padx=(6, 4), pady=8, sticky="w")

        provider_names = list(PROVIDERS.keys())
        default_prov = cfg.get_setting("active_provider", "Pollinations (Free - No Key)")
        if default_prov not in provider_names:
            default_prov = provider_names[0]

        self.provider_combo = ctk.CTkComboBox(
            self.top_bar,
            values=provider_names,
            width=195,
            fg_color=theme.COLOR_INPUT,
            border_color=theme.COLOR_BORDER,
            command=self._on_provider_change,
        )
        self.provider_combo.set(default_prov)
        self.provider_combo.grid(row=0, column=2, padx=4, pady=8, sticky="w")

        # Model selector
        mod_lbl = ctk.CTkLabel(
            self.top_bar, text="Model:", font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        mod_lbl.grid(row=0, column=3, padx=(10, 4), pady=8, sticky="w")

        self.model_combo = ctk.CTkComboBox(
            self.top_bar, values=["Loading available models..."], width=190,
            fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER,
            command=self._on_model_change,
        )
        self.model_combo.grid(row=0, column=4, padx=4, pady=8, sticky="w")

        # Refresh Live Models button (sleek icon button)
        self.btn_refresh_models = ctk.CTkButton(
            self.top_bar,
            text="↻",
            width=30,
            height=28,
            font=("Segoe UI Symbol", 13),
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._fetch_models_threaded,
        )
        self.btn_refresh_models.grid(row=0, column=5, padx=(2, 2), pady=8, sticky="w")
        self.btn_fetch = self.btn_refresh_models

        # Free Models Filter Pill Toggle
        self.btn_free_filter = ctk.CTkButton(
            self.top_bar,
            text="🆓 Free",
            width=64,
            height=28,
            font=("Segoe UI", 11, "bold"),
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            corner_radius=6,
            command=self._toggle_free_filter,
        )
        self.btn_free_filter.grid(row=0, column=6, padx=(2, 6), pady=8, sticky="w")

        # Temperature
        temp_lbl = ctk.CTkLabel(
            self.top_bar, text="Temp:", font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
        )
        temp_lbl.grid(row=0, column=7, padx=(6, 2), pady=8, sticky="w")

        self.temp_slider = ctk.CTkSlider(
            self.top_bar, from_=0.0, to=1.5, number_of_steps=15, width=65,
            progress_color=theme.COLOR_ACCENT,
        )
        self.temp_slider.set(cfg.get_setting("temperature", 0.7))
        self.temp_slider.grid(row=0, column=8, padx=2, pady=8, sticky="w")

        self.temp_val_lbl = ctk.CTkLabel(
            self.top_bar,
            text=f"{self.temp_slider.get():.1f}",
            font=theme.FONT_SMALL,
            width=22,
            text_color=theme.COLOR_TEXT_MUTED,
        )
        self.temp_val_lbl.grid(row=0, column=9, padx=(2, 4), pady=8, sticky="w")
        self.temp_slider.configure(
            command=lambda v: self.temp_val_lbl.configure(text=f"{float(v):.1f}")
        )

        # Persona button
        self.btn_sys = ctk.CTkButton(
            self.top_bar,
            text="Persona",
            width=65,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._open_system_prompt_dialog,
        )
        self.btn_sys.grid(row=0, column=10, padx=4, pady=8, sticky="w")

        # Telemetry & Quota Limit pills (right-aligned)
        self.failover_node_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.failover_node_frame.grid(row=0, column=11, padx=(6, 12), pady=8, sticky="e")
        self.top_bar.grid_columnconfigure(11, weight=1)

        self.telemetry_pill = ctk.CTkLabel(
            self.failover_node_frame,
            text="Key 1: Active",
            font=theme.FONT_BADGE,
            fg_color="transparent",
            text_color=theme.COLOR_TEXT_DIM,
            corner_radius=6,
            height=26,
            padx=6,
        )
        self.telemetry_pill.pack(side="right")

        # Live Limits Inspector Pill Button
        self.btn_limits_pill = ctk.CTkButton(
            self.failover_node_frame,
            text="⚡ Limits",
            width=86,
            height=26,
            font=theme.FONT_BADGE,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            corner_radius=6,
            command=self._open_limits_inspector,
        )
        self.btn_limits_pill.pack(side="right", padx=(0, 6))

    # -----------------------------------------------------------------
    # Chat viewport
    # -----------------------------------------------------------------
    def _build_chat_viewport(self):
        self.chat_container = ctk.CTkScrollableFrame(self.chat_area, fg_color="transparent")
        self.chat_container.pack(fill="both", expand=True, padx=14, pady=4)
        self._add_welcome_banner()

    # -----------------------------------------------------------------
    # Attachment bar (hidden by default)
    # -----------------------------------------------------------------
    def _build_attachment_bar(self):
        self.attach_frame = ctk.CTkFrame(
            self.chat_area,
            fg_color="#F3F4F6",
            corner_radius=6,
            height=36,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        self.attach_lbl = ctk.CTkLabel(
            self.attach_frame, text="", font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        self.attach_lbl.pack(side="left", padx=12, pady=4)

        self.attach_del = ctk.CTkButton(
            self.attach_frame,
            text="Remove",
            width=65,
            height=24,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_ERROR,
            hover_color="#B91C1C",
            text_color="#FFFFFF",
            command=self._remove_attachment,
        )
        self.attach_del.pack(side="right", padx=8, pady=4)

    # -----------------------------------------------------------------
    # Input & action dock
    # -----------------------------------------------------------------
    def _build_input_dock(self):
        self.bottom_bar = ctk.CTkFrame(
            self.chat_area,
            fg_color=theme.COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        self.bottom_bar.pack(fill="x", padx=14, pady=(4, 12))

        # Text input
        self.input_text = ctk.CTkTextbox(
            self.bottom_bar,
            height=72,
            font=theme.FONT_BODY,
            corner_radius=8,
            fg_color=theme.COLOR_INPUT,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            wrap="word",
        )
        self.input_text.pack(fill="x", padx=12, pady=(10, 6))
        self.input_text.bind("<Return>", self._on_enter_press)

        # Button row
        self.btn_row = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        self.btn_row.pack(fill="x", padx=12, pady=(0, 10))

        # Left buttons: Attach (icon), Clear, Export
        self.btn_attach = ctk.CTkButton(
            self.btn_row,
            text="📎",
            width=36,
            height=32,
            font=("Segoe UI Symbol", 13),
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            corner_radius=8,
            command=self._attach_image_dialog,
        )
        self.btn_attach.pack(side="left", padx=(0, 6))

        self.btn_clear = ctk.CTkButton(
            self.btn_row,
            text="🗑 Clear",
            width=70,
            height=32,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            corner_radius=8,
            command=self._clear_chat,
        )
        self.btn_clear.pack(side="left", padx=4)

        self.btn_export = ctk.CTkButton(
            self.btn_row,
            text="📥 Export",
            width=75,
            height=32,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            corner_radius=8,
            command=self._export_chat,
        )
        self.btn_export.pack(side="left", padx=4)

        # Right button: Single unified Action Button (Send <-> Stop)
        self.btn_action = ctk.CTkButton(
            self.btn_row,
            text="↑",
            width=40,
            height=32,
            font=("Segoe UI", 16, "bold"),
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=8,
            command=self._on_action_click,
        )
        self.btn_action.pack(side="right", padx=0)

    @property
    def btn_send(self):
        return self.btn_action

    @property
    def btn_stop(self):
        return self.btn_action

    def _set_action_button_state(self, is_generating: bool):
        if is_generating:
            self.btn_action.configure(
                text="■",
                font=("Segoe UI", 13, "bold"),
                fg_color=theme.COLOR_ERROR,
                hover_color="#B91C1C",
                state="normal"
            )
        else:
            self.btn_action.configure(
                text="↑",
                font=("Segoe UI", 16, "bold"),
                fg_color=theme.COLOR_ACCENT,
                hover_color=theme.COLOR_ACCENT_HOVER,
                state="normal"
            )

    def _on_action_click(self):
        if self.is_generating:
            self._stop_generation()
        else:
            self._send_message()

    # ===================================================================
    # WELCOME BANNER
    # ===================================================================

    def _add_welcome_banner(self):
        welcome_frame = ctk.CTkFrame(
            self.chat_container,
            fg_color=theme.COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        welcome_frame.pack(fill="x", padx=16, pady=16)

        title = ctk.CTkLabel(
            welcome_frame,
            text="Welcome to OmniAI Studio",
            font=theme.FONT_HEADING,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        title.pack(anchor="w", padx=18, pady=(14, 4))

        desc = ctk.CTkLabel(
            welcome_frame,
            text=(
                "Built by VIKA-BUILDS for universal AI orchestration.\n"
                "Multi-Key Auto-Failover  |  Multimodal Vision  |  Background API Gateway"
            ),
            font=theme.FONT_BODY,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left",
            wraplength=680,
        )
        desc.pack(anchor="w", padx=18, pady=(0, 14))

    # ===================================================================
    # PROVIDER / MODEL SWITCHING & REAL-TIME FETCHING
    # ===================================================================

    def _clean_model_name(self, text: str) -> str:
        """Strip [FREE] visual badge from model name for internal engine calls."""
        if not text:
            return ""
        val = str(text).strip()
        if val.startswith("[FREE] "):
            return val[7:].strip()
        return val

    def _on_provider_change(self, choice: str):
        cfg.set_setting("active_provider", choice)
        self._update_failover_telemetry()
        self._update_limits_pill(choice)
        self._fetch_models_threaded()

    def _on_model_change(self, choice: str):
        clean = self._clean_model_name(choice)
        if clean and not any(clean.startswith(p) for p in ("No key", "Fetching", "No models", "Loading", "No free models")):
            cfg.set_setting("active_model", clean)

    def on_tab_visible(self):
        """Called whenever Chat tab is switched to; re-evaluates models if keys were updated."""
        self._update_failover_telemetry()
        self._update_limits_pill()
        curr = self.model_combo.get()
        if not curr or any(curr.startswith(p) for p in ("No key", "No models", "Loading")):
            self._fetch_models_threaded()

    # ===================================================================
    # TELEMETRY & QUOTA PILLS
    # ===================================================================

    def _update_failover_telemetry(self):
        prov = self.provider_combo.get()
        prov_id = PROVIDERS.get(prov, {}).get("id", "openai")
        pool = key_pools.get_pool(prov_id)
        stats = pool.get_stats()

        total = stats["total_keys"]
        active = stats["active_keys"]
        cooldown = stats["cooldown_keys"]

        if total == 0:
            if prov_id == "pollinations":
                self.telemetry_pill.configure(
                    text="Free Mode - No Key Required",
                    fg_color="transparent",
                    text_color=theme.COLOR_TEXT_DIM,
                )
            else:
                self.telemetry_pill.configure(
                    text="0 Keys Configured",
                    fg_color="transparent",
                    text_color=theme.COLOR_ERROR,
                )
        elif total == 1:
            self.telemetry_pill.configure(
                text="Key 1: Active",
                fg_color="transparent",
                text_color=theme.COLOR_TEXT_DIM,
            )
        else:
            if cooldown > 0:
                self.telemetry_pill.configure(
                    text=f"Pool: {active} Active / {cooldown} Cooldown",
                    fg_color="transparent",
                    text_color=theme.COLOR_TEXT_DIM,
                )
            else:
                self.telemetry_pill.configure(
                    text=f"Multi-Key Pool: {total} Ready",
                    fg_color="transparent",
                    text_color=theme.COLOR_TEXT_DIM,
                )

    def _update_limits_pill(self, prov: str = ""):
        if not hasattr(self, "btn_limits_pill"):
            return
        if not prov:
            prov = self.provider_combo.get()
        prov_id = PROVIDERS.get(prov, {}).get("id", "openai")
        pool = key_pools.get_pool(prov_id)
        limits = pool.get_latest_rate_limits() or engine.latest_provider_limits.get(prov_id, {})

        if prov_id == "pollinations":
            self.btn_limits_pill.configure(text="⚡ Free Mode")
        elif prov_id == "groq" and not limits:
            self.btn_limits_pill.configure(text="⚡ 30 RPM Free")
        elif prov_id == "gemini" and not limits:
            self.btn_limits_pill.configure(text="⚡ 15 RPM Free")
        elif limits:
            req_rem = limits.get("req_remaining")
            req_lim = limits.get("req_limit")
            tok_rem = limits.get("tok_remaining")
            if req_rem is not None and req_lim is not None:
                self.btn_limits_pill.configure(text=f"⚡ {req_rem}/{req_lim} RPM")
            elif tok_rem is not None:
                try:
                    tok_val = int(tok_rem)
                    self.btn_limits_pill.configure(text=f"⚡ {tok_val//1000}k TPM")
                except Exception:
                    self.btn_limits_pill.configure(text="⚡ Limits: OK")
            else:
                self.btn_limits_pill.configure(text="⚡ Limits: OK")
        else:
            self.btn_limits_pill.configure(text="⚡ Limits")

    def _on_key_failover_event(self, event: Dict[str, Any]):
        evt_type = event.get("type")
        if evt_type in ("failover", "keys_updated"):
            self.after(0, self._update_failover_telemetry)
            if evt_type == "keys_updated":
                self.after(0, self._fetch_models_threaded)
            if self.status_callback and evt_type == "failover":
                p = event.get("provider", "")
                old_k = event.get("old_key", "")
                new_k = event.get("new_key", "")
                self.after(
                    0,
                    lambda: self.status_callback(
                        f"Auto-switched key: {p} ({old_k} -> {new_k})"
                    ),
                )
        elif evt_type == "rate_limit_update":
            self.after(0, self._update_limits_pill)

    # ===================================================================
    # FREE MODELS FILTER & REAL-TIME MODEL FETCHING
    # ===================================================================

    def _toggle_free_filter(self):
        self.free_only_mode = not self.free_only_mode
        if self.free_only_mode:
            self.btn_free_filter.configure(
                text="✓ Free",
                fg_color="#059669",
                hover_color="#047857",
                text_color="#FFFFFF"
            )
            if self.status_callback:
                self.status_callback("Showing 100% Free models only.")
        else:
            self.btn_free_filter.configure(
                text="🆓 Free",
                fg_color=theme.COLOR_CARD_HOVER,
                hover_color=theme.COLOR_BORDER,
                text_color=theme.COLOR_TEXT_MAIN
            )
            if self.status_callback:
                self.status_callback("Showing all available models.")

        prov = self.provider_combo.get()
        if self.raw_models_cache:
            self._apply_fetched_models(prov, self.raw_models_cache)
        else:
            self._fetch_models_threaded()

    def _fetch_models_threaded(self):
        prov = self.provider_combo.get()
        prov_info = PROVIDERS.get(prov, PROVIDERS.get("Custom OpenAI Endpoint", {}))
        prov_id = prov_info.get("id", "openai")

        # Check if keys are entered for this provider
        pool = key_pools.get_pool(prov_id)
        has_key = bool(pool.get_active_key() or cfg.get_key(prov_id))
        is_free = (prov_id == "pollinations")

        if not has_key and not is_free:
            self.model_combo.configure(values=["No key entered (Add in Keys tab)"])
            self.model_combo.set("No key entered (Add in Keys tab)")
            if self.status_callback:
                self.status_callback(f"No key for {prov}. Add your API key in Keys tab.")
            return

        if hasattr(self, "btn_refresh_models"):
            self.btn_refresh_models.configure(state="disabled", text="...")
        self.model_combo.configure(values=["Fetching live models..."])
        self.model_combo.set("Fetching live models...")

        if self.status_callback:
            self.status_callback(f"Querying available models for {prov}...")

        def run():
            fetched = engine.fetch_available_models(prov)
            try:
                self.after(0, lambda: self._apply_fetched_models(prov, fetched))
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()

    def _apply_fetched_models(self, prov: str, models: List[str]):
        if hasattr(self, "btn_refresh_models"):
            self.btn_refresh_models.configure(state="normal", text="↻")

        if self.provider_combo.get() != prov:
            return

        self.raw_models_cache = [self._clean_model_name(m) for m in models if m]

        if not self.raw_models_cache:
            self.model_combo.configure(values=["No models found (Check key)"])
            self.model_combo.set("No models found (Check key)")
            if self.status_callback:
                self.status_callback(f"Could not load models for {prov}. Check API key.")
            return

        # Filter by Free-Only mode if enabled
        if self.free_only_mode:
            models_to_show = [
                m for m in self.raw_models_cache
                if is_model_free(prov, m, engine.openrouter_free_model_ids)
            ]
            if not models_to_show:
                self.model_combo.configure(values=["No free models for this provider"])
                self.model_combo.set("No free models for this provider")
                if self.status_callback:
                    self.status_callback(f"No 100% free models found for {prov}.")
                return
        else:
            models_to_show = self.raw_models_cache

        # Format visual badge [FREE] for free models
        display_values = []
        for m in models_to_show:
            if is_model_free(prov, m, engine.openrouter_free_model_ids):
                display_values.append(f"[FREE] {m}")
            else:
                display_values.append(m)

        self.model_combo.configure(values=display_values)
        saved_model = self._clean_model_name(cfg.get_setting("active_model", ""))
        matching = [dv for dv in display_values if self._clean_model_name(dv) == saved_model]

        if matching:
            self.model_combo.set(matching[0])
        else:
            self.model_combo.set(display_values[0])
            cfg.set_setting("active_model", self._clean_model_name(display_values[0]))

        if self.status_callback:
            free_cnt = sum(1 for m in models_to_show if is_model_free(prov, m, engine.openrouter_free_model_ids))
            self.status_callback(f"Loaded {len(models_to_show)} models ({free_cnt} free) for {prov}.")

        self._update_limits_pill(prov)

    # ===================================================================
    # API LIMITS & QUOTA INSPECTOR MODAL
    # ===================================================================

    def _open_limits_inspector(self, provider: Optional[str] = None):
        prov = provider or self.provider_combo.get()
        prov_info = PROVIDERS.get(prov, {})
        prov_id = prov_info.get("id", "openai")

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"API Rate Limits & Quotas — {prov}")
        dialog.geometry("540x510")
        dialog.transient(self)
        dialog.grab_set()

        # Header card
        header = ctk.CTkFrame(dialog, fg_color=theme.COLOR_CARD_ALT, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        header.pack(fill="x", padx=16, pady=(16, 10))

        h_top = ctk.CTkFrame(header, fg_color="transparent")
        h_top.pack(fill="x", padx=14, pady=(10, 4))

        title = ctk.CTkLabel(h_top, text=f"⚡ {prov}", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        title.pack(side="left")

        pool = key_pools.get_pool(prov_id)
        stats = pool.get_stats()
        key_count = stats["total_keys"]
        key_status_text = f"{key_count} Keys" if key_count > 1 else ("1 Key" if key_count == 1 else "No Key")
        badge = ctk.CTkLabel(h_top, text=key_status_text, font=theme.FONT_BADGE, text_color=theme.COLOR_TEXT_DIM)
        badge.pack(side="right")

        active_k = pool.get_active_key()
        masked_key = active_k.get_masked() if active_k else "None configured"
        desc = ctk.CTkLabel(
            header,
            text=f"Active Key: {masked_key} • Failover Pool: {stats['active_keys']} Active, {stats['cooldown_keys']} Cooldown",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED
        )
        desc.pack(anchor="w", padx=14, pady=(0, 10))

        # Content frame
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=4)

        loading_lbl = ctk.CTkLabel(content, text="Querying provider quota and rate limits...", font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_MUTED)
        loading_lbl.pack(pady=30)

        def populate(quota_data: Dict[str, Any]):
            loading_lbl.pack_forget()

            # Rate Limits Section
            rl_card = ctk.CTkFrame(content, fg_color=theme.COLOR_CARD, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
            rl_card.pack(fill="x", pady=6)

            rl_header = ctk.CTkLabel(rl_card, text="Rate Limits & Quota Telemetry", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
            rl_header.pack(anchor="w", padx=14, pady=(8, 4))

            limits = quota_data.get("limits", {})
            req_rem = limits.get("req_remaining")
            req_lim = limits.get("req_limit")
            tok_rem = limits.get("tok_remaining")
            tok_lim = limits.get("tok_limit")
            req_reset = limits.get("req_reset")
            tok_reset = limits.get("tok_reset")

            info_text = quota_data.get("info", "")
            if info_text:
                info_lbl = ctk.CTkLabel(rl_card, text=info_text, font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED, justify="left", wraplength=480)
                info_lbl.pack(anchor="w", padx=14, pady=(0, 8))

            if req_rem or req_lim:
                req_frame = ctk.CTkFrame(rl_card, fg_color="transparent")
                req_frame.pack(fill="x", padx=14, pady=(0, 6))
                r_lbl = ctk.CTkLabel(req_frame, text=f"Requests Remaining: {req_rem or 'N/A'} / {req_lim or 'N/A'}", font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_MAIN)
                r_lbl.pack(side="left")
                if req_reset:
                    res_lbl = ctk.CTkLabel(req_frame, text=f"Reset in: {req_reset}s", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_DIM)
                    res_lbl.pack(side="right")

            if tok_rem or tok_lim:
                tok_frame = ctk.CTkFrame(rl_card, fg_color="transparent")
                tok_frame.pack(fill="x", padx=14, pady=(0, 8))
                t_lbl = ctk.CTkLabel(tok_frame, text=f"Tokens Remaining: {tok_rem or 'N/A'} / {tok_lim or 'N/A'}", font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_MAIN)
                t_lbl.pack(side="left")
                if tok_reset:
                    res2_lbl = ctk.CTkLabel(tok_frame, text=f"Reset in: {tok_reset}s", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_DIM)
                    res2_lbl.pack(side="right")

            # Account Balance Section
            bal = quota_data.get("balance")
            if bal:
                bal_card = ctk.CTkFrame(content, fg_color=theme.COLOR_CARD, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
                bal_card.pack(fill="x", pady=6)

                b_head = ctk.CTkLabel(bal_card, text="Account Balance & Credit Usage", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
                b_head.pack(anchor="w", padx=14, pady=(8, 4))

                b_val = ctk.CTkLabel(bal_card, text=f"Balance: {bal}", font=theme.FONT_BODY, text_color=theme.COLOR_ACCENT)
                b_val.pack(anchor="w", padx=14, pady=(0, 8))

            # Free Models Status
            free_card = ctk.CTkFrame(content, fg_color=theme.COLOR_CARD, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
            free_card.pack(fill="x", pady=6)

            is_free = quota_data.get("is_free", False) or is_model_free(prov, "")
            status_symbol = "✓" if is_free else "ℹ"
            status_text = "This provider has 100% Free / Free-Tier models available in OmniAI Studio." if is_free else "This provider uses standard pay-per-token pricing."

            f_lbl = ctk.CTkLabel(free_card, text=f"{status_symbol} {status_text}", font=theme.FONT_SMALL, text_color="#059669" if is_free else theme.COLOR_TEXT_MUTED, wraplength=480, justify="left")
            f_lbl.pack(anchor="w", padx=14, pady=8)

        def query():
            data = engine.check_provider_balance_and_limits(prov_id)
            try:
                dialog.after(0, lambda: populate(data))
            except Exception:
                pass

        threading.Thread(target=query, daemon=True).start()

        # Bottom buttons
        btn_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(8, 16))

        btn_close = ctk.CTkButton(btn_bar, text="Close", width=80, fg_color=theme.COLOR_CARD_HOVER, hover_color=theme.COLOR_BORDER, text_color=theme.COLOR_TEXT_MAIN, command=dialog.destroy)
        btn_close.pack(side="right")

    # ===================================================================
    # SYSTEM PROMPT DIALOG
    # ===================================================================

    def _open_system_prompt_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("System Instructions & Persona")
        dialog.geometry("500x340")
        dialog.transient(self)
        dialog.grab_set()

        lbl = ctk.CTkLabel(
            dialog, text="System Persona Prompt:",
            font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN,
        )
        lbl.pack(anchor="w", padx=16, pady=(16, 6))

        txt = ctk.CTkTextbox(
            dialog, font=theme.FONT_BODY, height=180, fg_color=theme.COLOR_INPUT,
        )
        txt.pack(fill="both", expand=True, padx=16, pady=6)
        txt.insert(
            "1.0",
            cfg.get_setting("system_prompt", "You are a helpful, versatile AI assistant."),
        )

        def save():
            val = txt.get("1.0", "end-1c").strip()
            cfg.set_setting("system_prompt", val)
            dialog.destroy()
            if self.status_callback:
                self.status_callback("Persona saved.")

        btn_save = ctk.CTkButton(
            dialog, text="Save Persona", command=save,
            fg_color=theme.COLOR_ACCENT, text_color="#FFFFFF",
        )
        btn_save.pack(pady=(6, 16))

    # ===================================================================
    # ATTACHMENTS
    # ===================================================================

    def _attach_image_dialog(self):
        filetypes = [
            ("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"),
            ("All files", "*.*"),
        ]
        path = filedialog.askopenfilename(
            title="Select Vision Image to Attach", filetypes=filetypes,
        )
        if path and os.path.exists(path):
            self.current_attached_image = path
            fname = os.path.basename(path)
            size_kb = os.path.getsize(path) // 1024
            self.attach_lbl.configure(text=f"Image: {fname} ({size_kb} KB)")
            self.attach_frame.pack(
                fill="x", padx=14, pady=(2, 2), before=self.bottom_bar,
            )

    def _remove_attachment(self):
        self.current_attached_image = None
        self.attach_frame.pack_forget()

    # ===================================================================
    # INPUT HANDLING
    # ===================================================================

    def _on_enter_press(self, event):
        if not event.state & 0x1:  # plain Enter (no Shift)
            self._send_message()
            return "break"

    def _clear_chat(self):
        if messagebox.askyesno("Clear Chat", "Clear all messages from the conversation view?"):
            if self.is_generating:
                self.cancel_event.set()
                self.is_generating = False
            if self._stream_timer is not None:
                try:
                    self.after_cancel(self._stream_timer)
                except Exception:
                    pass
                self._stream_timer = None
            self._set_action_button_state(False)

            self.messages.clear()
            self.current_conversation_id = None
            self.current_conversation_title = None
            self.current_conversation_file = None
            for widget in self.chat_container.winfo_children():
                widget.destroy()
            self._add_welcome_banner()
            if self.status_callback:
                self.status_callback("Chat cleared.")

    def _export_chat(self):
        if not self.messages:
            messagebox.showinfo("Export Chat", "No conversation messages to export.")
            return
        filetypes = [("Markdown File", "*.md"), ("Plain Text", "*.txt")]
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=filetypes)
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("# OmniAI Studio — Conversation Log\n")
                    f.write("Built by VIKA-BUILDS\n\n")
                    for m in self.messages:
                        role = m["role"].upper()
                        model_tag = ""
                        if m.get("model"):
                            model_tag = f" [{m['model']}]"
                        f.write(f"### {role}{model_tag}\n{m['content']}\n\n")
                messagebox.showinfo("Export Successful", f"Conversation saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("Export Failed", str(e))

    def _stop_generation(self):
        if self.is_generating:
            self.cancel_event.set()
            self.btn_action.configure(state="disabled")
            if self.status_callback:
                self.status_callback("Stopping generation...")

    # ===================================================================
    # SEND / STREAM
    # ===================================================================

    def _send_message(self):
        if self.is_generating:
            return

        user_text = self.input_text.get("1.0", "end-1c").strip()
        if not user_text and not self.current_attached_image:
            return

        self.input_text.delete("1.0", "end")

        img_attached = self.current_attached_image
        self._remove_attachment()

        provider = self.provider_combo.get()
        model = self._clean_model_name(self.model_combo.get())

        # Check if provider has no key configured or error
        if any(model.startswith(p) for p in ("No key", "Fetching", "No models", "Loading", "No free models")):
            messagebox.showwarning(
                "Model Unavailable",
                f"Please enter an API key for {provider} in the Keys tab before sending a message."
            )
            return

        # Store message with model/provider metadata
        msg_entry: Dict[str, Any] = {
            "role": "user",
            "content": user_text,
            "model": "",
            "provider": "",
            "timestamp": _iso_now(),
        }
        self.messages.append(msg_entry)

        # Auto-title on first user message
        if self.current_conversation_title is None and user_text:
            self.current_conversation_title = _sanitize_filename(user_text, 40)

        self._append_message_card(role="user", text=user_text, image_path=img_attached)

        system_prompt = cfg.get_setting("system_prompt", "")
        temperature = float(self.temp_slider.get())

        self.active_assistant_label, self.active_copy_btn = self._append_assistant_placeholder(
            provider, model,
        )
        self.active_assistant_text = ""

        self.is_generating = True
        self.cancel_event.clear()
        self._set_action_button_state(True)
        if self.status_callback:
            self.status_callback(f"Thinking with {model} ({provider})...")

        # Store which model/provider for the upcoming assistant message
        self._pending_model = model
        self._pending_provider = provider

        # Clear stream buffer and flags
        with self._stream_lock:
            self._stream_buffer.clear()
            self._stream_done_flag = False
            self._stream_done_full = ""
            self._stream_err_flag = False
            self._stream_err_msg = ""

        # Launch throttled drain loop (~28 FPS)
        self._start_stream_drain_loop()

        def on_chunk(chunk: str):
            # Pure thread-safe buffer append — ZERO Tkinter event loop flooding!
            with self._stream_lock:
                self._stream_buffer.append(chunk)

        def on_done(full: str):
            with self._stream_lock:
                self._stream_done_full = full
                self._stream_done_flag = True
            try:
                self.after(0, self._drain_stream_buffer)
            except Exception:
                pass

        def on_err(err: str):
            with self._stream_lock:
                self._stream_err_msg = err
                self._stream_err_flag = True
            try:
                self.after(0, self._drain_stream_buffer)
            except Exception:
                pass

        def thread_target():
            engine.chat_stream(
                provider_name=provider,
                model=model,
                messages=self.messages,
                system_prompt=system_prompt,
                temperature=temperature,
                image_path=img_attached,
                callback_chunk=on_chunk,
                callback_done=on_done,
                callback_err=on_err,
                cancel_event=self.cancel_event,
            )

        threading.Thread(target=thread_target, daemon=True).start()

    def _start_stream_drain_loop(self):
        """Cancel any previous timer and start the frame-rate throttled UI updater."""
        if self._stream_timer is not None:
            try:
                self.after_cancel(self._stream_timer)
            except Exception:
                pass
            self._stream_timer = None
        self._drain_stream_buffer()

    def _drain_stream_buffer(self):
        """Drain accumulated chunks at ~28 FPS. Keeps Windows message queue completely responsive."""
        new_text = ""
        done_flag = False
        done_full = ""
        err_flag = False
        err_msg = ""

        with self._stream_lock:
            if self._stream_buffer:
                new_text = "".join(self._stream_buffer)
                self._stream_buffer.clear()
            if self._stream_err_flag:
                err_flag = True
                err_msg = self._stream_err_msg
                self._stream_err_flag = False
            elif self._stream_done_flag:
                done_flag = True
                done_full = self._stream_done_full
                self._stream_done_flag = False

        if new_text and self.active_assistant_label:
            self.active_assistant_text += new_text
            self.active_assistant_label.configure(text=self.active_assistant_text)
            self._scroll_to_bottom()

        if err_flag:
            self._on_stream_err(err_msg)
            return

        if done_flag:
            self._on_stream_done(done_full, self.active_copy_btn)
            return

        if self.is_generating:
            self._stream_timer = self.after(35, self._drain_stream_buffer)
        else:
            self._stream_timer = None

    def _on_stream_done(self, full_text: str, copy_btn: ctk.CTkButton):
        self.is_generating = False
        if self._stream_timer is not None:
            try:
                self.after_cancel(self._stream_timer)
            except Exception:
                pass
            self._stream_timer = None

        self._set_action_button_state(False)

        # Flush any remaining chunks in the buffer
        remaining = ""
        with self._stream_lock:
            if self._stream_buffer:
                remaining = "".join(self._stream_buffer)
                self._stream_buffer.clear()

        if remaining:
            self.active_assistant_text += remaining

        final_text = full_text or self.active_assistant_text
        if self.active_assistant_label and final_text:
            self.active_assistant_label.configure(text=final_text)
            self._scroll_to_bottom()

        if final_text:
            msg_entry: Dict[str, Any] = {
                "role": "assistant",
                "content": final_text,
                "model": getattr(self, "_pending_model", ""),
                "provider": getattr(self, "_pending_provider", ""),
                "timestamp": _iso_now(),
            }
            self.messages.append(msg_entry)
            copy_btn.configure(
                state="normal",
                command=lambda: self._copy_to_clipboard(final_text),
            )

            # Auto-save conversation to disk
            self._save_conversation()

        self._update_failover_telemetry()
        if self.status_callback:
            self.status_callback("Ready.")

    def _on_stream_err(self, err_text: str):
        self.is_generating = False
        if self._stream_timer is not None:
            try:
                self.after_cancel(self._stream_timer)
            except Exception:
                pass
            self._stream_timer = None

        self._set_action_button_state(False)
        if self.active_assistant_label:
            self.active_assistant_label.configure(
                text=f"Error: {err_text}",
                text_color=theme.COLOR_ERROR,
            )
            self._scroll_to_bottom()
        self._update_failover_telemetry()
        if self.status_callback:
            self.status_callback(f"Error: {err_text[:60]}")
        self._update_failover_telemetry()
        if self.status_callback:
            self.status_callback(f"Error: {err_text[:60]}")

    # ===================================================================
    # CLIPBOARD
    # ===================================================================

    def _copy_to_clipboard(self, text: str):
        try:
            pyperclip.copy(text)
            if self.status_callback:
                self.status_callback("Copied to clipboard!")
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(text)

    # ===================================================================
    # SCROLL
    # ===================================================================

    def _scroll_to_bottom(self):
        try:
            self.chat_container._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    # ===================================================================
    # MESSAGE CARDS (BUBBLES)
    # ===================================================================

    def _append_message_card(
        self,
        role: str,
        text: str,
        image_path: Optional[str] = None,
        model: str = "",
        provider: str = "",
        timestamp_str: str = "",
    ):
        is_user = role == "user"

        msg_frame = ctk.CTkFrame(
            self.chat_container,
            fg_color=theme.COLOR_USER_BUBBLE if is_user else theme.COLOR_ASSISTANT_BUBBLE,
            corner_radius=12,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        msg_frame.pack(fill="x", padx=16, pady=6, anchor="e" if is_user else "w")

        # Header row
        header = ctk.CTkFrame(msg_frame, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        badge_text = "You" if is_user else (model or "Assistant")
        badge_color = theme.COLOR_TEXT_MAIN if is_user else theme.COLOR_TEXT_DIM

        user_badge = ctk.CTkLabel(
            header, text=badge_text, font=theme.FONT_BADGE,
            text_color=badge_color,
        )
        user_badge.pack(side="left")

        # Timestamp
        time_text = timestamp_str or time.strftime("%H:%M:%S")
        time_lbl = ctk.CTkLabel(
            header, text=time_text, font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_DIM,
        )
        time_lbl.pack(side="right")

        # Provider attribution for assistant messages loaded from history
        if not is_user and provider:
            prov_lbl = ctk.CTkLabel(
                header, text=f"via {provider}", font=("Segoe UI", 8),
                text_color=theme.COLOR_TEXT_DIM,
            )
            prov_lbl.pack(side="right", padx=(0, 8))

        # Attached image thumbnail
        if image_path and os.path.exists(image_path):
            try:
                pil_thumb = Image.open(image_path)
                pil_thumb.thumbnail((260, 190))
                ctk_thumb = ctk.CTkImage(
                    light_image=pil_thumb, dark_image=pil_thumb, size=pil_thumb.size,
                )
                img_lbl = ctk.CTkLabel(msg_frame, image=ctk_thumb, text="")
                img_lbl.image = ctk_thumb
                img_lbl.pack(anchor="w", padx=12, pady=4)
            except Exception:
                pass

        # Text content
        if text:
            content_lbl = ctk.CTkLabel(
                msg_frame,
                text=text,
                font=theme.FONT_BODY,
                text_color=theme.COLOR_TEXT_MAIN,
                justify="left",
                wraplength=680,
            )
            content_lbl.pack(anchor="w", padx=12, pady=(2, 10))

        # Copy & Edit buttons for messages
        if text:
            actions_bar = ctk.CTkFrame(msg_frame, fg_color="transparent")
            actions_bar.pack(anchor="e", padx=12, pady=(0, 6))

            if is_user:
                # Edit button for user message
                btn_edit = ctk.CTkButton(
                    actions_bar,
                    text="✎",
                    width=26,
                    height=22,
                    font=("Segoe UI Symbol", 11),
                    fg_color="#F3F4F6",
                    hover_color="#E5E7EB",
                    text_color="#374151",
                    corner_radius=4,
                    command=lambda t=text: self._edit_sent_message(t),
                )
                btn_edit.pack(side="left", padx=2)

            # Copy button for both user and assistant
            copy_btn = ctk.CTkButton(
                actions_bar,
                text="⧉",
                width=26,
                height=22,
                font=("Segoe UI Symbol", 11),
                fg_color="#F3F4F6",
                hover_color="#E5E7EB",
                text_color="#374151",
                corner_radius=4,
                command=lambda t=text: self._copy_to_clipboard(t),
            )
            copy_btn.pack(side="left", padx=2)

        self._scroll_to_bottom()

    def _edit_sent_message(self, text: str):
        """Load a previously sent user message back into the input box for editing."""
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", text)
        self.input_text.focus_set()
        if self.status_callback:
            self.status_callback("Message loaded into input for editing.")

    def _append_assistant_placeholder(
        self, provider: str, model: str,
    ) -> Tuple[ctk.CTkLabel, ctk.CTkButton]:
        msg_frame = ctk.CTkFrame(
            self.chat_container,
            fg_color=theme.COLOR_ASSISTANT_BUBBLE,
            corner_radius=12,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        msg_frame.pack(fill="x", padx=16, pady=6, anchor="w")

        header = ctk.CTkFrame(msg_frame, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        # Model badge
        bot_badge = ctk.CTkLabel(
            header,
            text=model,
            font=theme.FONT_BADGE,
            text_color=theme.COLOR_TEXT_DIM,
        )
        bot_badge.pack(side="left")

        # Provider label
        prov_lbl = ctk.CTkLabel(
            header,
            text=f"via {provider}",
            font=("Segoe UI", 8),
            text_color=theme.COLOR_TEXT_DIM,
        )
        prov_lbl.pack(side="left", padx=(6, 0))

        copy_btn = ctk.CTkButton(
            header,
            text="⧉",
            width=26,
            height=22,
            font=("Segoe UI Symbol", 11),
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            corner_radius=4,
            state="disabled",
        )
        copy_btn.pack(side="right")

        content_lbl = ctk.CTkLabel(
            msg_frame,
            text="Streaming response...",
            font=theme.FONT_BODY,
            text_color=theme.COLOR_TEXT_MAIN,
            justify="left",
            wraplength=680,
        )
        content_lbl.pack(anchor="w", padx=12, pady=(4, 10))

        self._scroll_to_bottom()
        return content_lbl, copy_btn

    # ===================================================================
    # CHAT HISTORY PERSISTENCE
    # ===================================================================

    def _new_chat(self):
        """Start a fresh conversation."""
        if self.is_generating:
            self.cancel_event.set()
            self.is_generating = False
        if self._stream_timer is not None:
            try:
                self.after_cancel(self._stream_timer)
            except Exception:
                pass
            self._stream_timer = None
        self._set_action_button_state(False)

        self.messages.clear()
        self.current_conversation_id = None
        self.current_conversation_title = None
        self.current_conversation_file = None
        for widget in self.chat_container.winfo_children():
            widget.destroy()
        self._add_welcome_banner()
        if self.status_callback:
            self.status_callback("New conversation started.")

    def _save_conversation(self):
        """Auto-save the current conversation to a JSON file."""
        if not self.messages:
            return

        now = _iso_now()

        if self.current_conversation_id is None:
            self.current_conversation_id = str(uuid.uuid4())

        title = self.current_conversation_title or "Untitled"

        # Build data
        data = {
            "id": self.current_conversation_id,
            "title": title,
            "created_at": now if self.current_conversation_file is None else None,
            "updated_at": now,
            "messages": self.messages,
            "provider": self.provider_combo.get(),
            "model": self._clean_model_name(self.model_combo.get()),
        }

        # Preserve created_at from existing file
        if self.current_conversation_file and os.path.exists(self.current_conversation_file):
            try:
                with open(self.current_conversation_file, "r", encoding="utf-8") as f:
                    old = json.load(f)
                data["created_at"] = old.get("created_at", now)
            except Exception:
                data["created_at"] = now
        else:
            data["created_at"] = data["created_at"] or now

        # Determine file path
        if self.current_conversation_file is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = _sanitize_filename(title)
            fname = f"{ts}_{safe_title}.json"
            self.current_conversation_file = os.path.join(CHAT_HISTORY_DIR, fname)

        try:
            with open(self.current_conversation_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ChatHistory] Error saving: {e}")

        # Refresh sidebar
        self._refresh_history_list()

    def _load_conversation(self, conv_id: str, filepath: str):
        """Load a saved conversation from disk."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load conversation:\n{e}")
            return

        # Clear current view
        self.messages = data.get("messages", [])
        self.current_conversation_id = data.get("id", conv_id)
        self.current_conversation_title = data.get("title", "Untitled")
        self.current_conversation_file = filepath

        for widget in self.chat_container.winfo_children():
            widget.destroy()

        # Replay messages into the UI
        for msg in self.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            model = msg.get("model", "")
            provider = msg.get("provider", "")
            ts = msg.get("timestamp", "")

            # Format timestamp for display
            ts_display = ""
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    ts_display = dt.strftime("%H:%M:%S")
                except Exception:
                    ts_display = ""

            self._append_message_card(
                role=role,
                text=content,
                model=model,
                provider=provider,
                timestamp_str=ts_display,
            )

        if self.status_callback:
            self.status_callback(f"Loaded: {self.current_conversation_title}")

    def _delete_conversation(self, filepath: str):
        """Delete a saved conversation file."""
        fname = os.path.basename(filepath)
        if not messagebox.askyesno("Delete Conversation", f"Delete '{fname}'?"):
            return
        try:
            os.remove(filepath)
        except Exception as e:
            messagebox.showerror("Delete Error", str(e))
            return

        # If we just deleted the active conversation, reset
        if self.current_conversation_file == filepath:
            self._new_chat()

        self._refresh_history_list()
        if self.status_callback:
            self.status_callback("Conversation deleted.")
