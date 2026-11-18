"""
OmniAI Studio - Custom API & Gateway Documentation Tab
Engineered by VIKA-BUILDS.
Features live API server management, cybernetic HUD traffic & failover monitor,
and interactive code documentation for Python, JS, cURL, VS Code, and Cursor.
"""

import os
import webbrowser
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import pyperclip

from config import cfg
from api_server import server_manager, api_logs, logs_lock
from key_pool import key_pools
import ui.theme as theme

class DocsTab(ctk.CTkFrame):
    def __init__(self, master, status_callback=None):
        super().__init__(master, fg_color="transparent")
        self.status_callback = status_callback

        self._build_ui()
        self._start_logs_auto_refresh()

    def _build_ui(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=14, pady=12)

        # ----------------------------------------------------
        # 1. API SERVER CONTROLLER CARD
        # ----------------------------------------------------
        server_card = ctk.CTkFrame(self.scroll_frame, fg_color=theme.COLOR_CARD, corner_radius=10, border_width=1, border_color=theme.COLOR_BORDER)
        server_card.pack(fill="x", padx=10, pady=(0, 10))

        header_row = ctk.CTkFrame(server_card, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(14, 6))

        title = ctk.CTkLabel(header_row, text="Local AI Gateway Server (OpenAI Compatible)", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        title.pack(side="left")

        self.server_status_badge = ctk.CTkLabel(
            header_row,
            text="Server Running: http://localhost:8080/v1" if server_manager.is_running() else "Server Stopped",
            font=theme.FONT_BADGE,
            text_color=theme.COLOR_SUCCESS if server_manager.is_running() else theme.COLOR_ERROR
        )
        self.server_status_badge.pack(side="right")

        desc = ctk.CTkLabel(
            server_card,
            text="Exposes an OpenAI-compatible REST API at http://localhost:8080/v1.\nUse your configured AI models and multi-key auto-failover in Cursor, VS Code Continue, LangChain, or any external project.\nArchitecture & API Engine by VIKA-BUILDS.",
            font=theme.FONT_BODY,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left"
        )
        desc.pack(anchor="w", padx=16, pady=(0, 10))

        # Controls Row
        ctrl_frame = ctk.CTkFrame(server_card, fg_color="#F9FAFB", corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        ctrl_frame.pack(fill="x", padx=16, pady=(0, 14))

        self.btn_toggle_server = ctk.CTkButton(
            ctrl_frame,
            text="Stop Gateway" if server_manager.is_running() else "Start Gateway",
            font=theme.FONT_BODY_BOLD,
            width=130,
            height=34,
            fg_color=theme.COLOR_ERROR if server_manager.is_running() else theme.COLOR_ACCENT,
            hover_color="#B91C1C" if server_manager.is_running() else theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._toggle_server
        )
        self.btn_toggle_server.pack(side="left", padx=12, pady=10)

        s_cfg = cfg.get_server_config()
        
        host_lbl = ctk.CTkLabel(ctrl_frame, text="Host:", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        host_lbl.pack(side="left", padx=(10, 2))

        self.host_menu = ctk.CTkOptionMenu(
            ctrl_frame,
            values=["127.0.0.1 (Local Only)", "0.0.0.0 (Local Network / LAN)"],
            width=180,
            height=30,
            font=theme.FONT_SMALL,
            fg_color="#FFFFFF",
            button_color="#E5E7EB",
            text_color="#111827"
        )
        self.host_menu.set("0.0.0.0 (Local Network / LAN)" if s_cfg.get("host") == "0.0.0.0" else "127.0.0.1 (Local Only)")
        self.host_menu.pack(side="left", padx=4)

        port_lbl = ctk.CTkLabel(ctrl_frame, text="Port:", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        port_lbl.pack(side="left", padx=(10, 2))

        self.port_entry = ctk.CTkEntry(ctrl_frame, width=70, height=30, font=theme.FONT_CODE, fg_color="#FFFFFF", border_color=theme.COLOR_BORDER)
        self.port_entry.insert(0, str(s_cfg.get("port", 8080)))
        self.port_entry.pack(side="left", padx=4)

        btn_swagger = ctk.CTkButton(
            ctrl_frame,
            text="Swagger Docs",
            width=120,
            height=30,
            font=theme.FONT_SMALL,
            fg_color="#FFFFFF",
            hover_color="#E5E7EB",
            text_color="#374151",
            border_width=1,
            border_color=theme.COLOR_BORDER,
            command=self._open_swagger_docs
        )
        btn_swagger.pack(side="right", padx=12)

        # Master Key Row
        key_row = ctk.CTkFrame(server_card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(0, 14))

        mkey_lbl = ctk.CTkLabel(key_row, text="Master API Key:", font=theme.FONT_BODY_BOLD, width=120, anchor="w", text_color=theme.COLOR_TEXT_MAIN)
        mkey_lbl.pack(side="left")

        self.master_key_entry = ctk.CTkEntry(
            key_row,
            font=theme.FONT_CODE,
            fg_color=theme.COLOR_INPUT,
            border_color=theme.COLOR_BORDER,
            placeholder_text="Leave blank to allow unauthenticated access"
        )
        self.master_key_entry.insert(0, s_cfg.get("master_key", ""))
        self.master_key_entry.pack(side="left", fill="x", expand=True, padx=8)

        btn_copy_key = ctk.CTkButton(
            key_row,
            text="Copy Key",
            width=90,
            height=30,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._copy_master_key
        )
        btn_copy_key.pack(side="left", padx=4)

        btn_new_key = ctk.CTkButton(
            key_row,
            text="Generate",
            width=85,
            height=30,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._generate_new_key
        )
        btn_new_key.pack(side="left", padx=4)

        btn_save_srv = ctk.CTkButton(
            key_row,
            text="Apply",
            width=75,
            height=30,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._apply_server_settings
        )
        btn_save_srv.pack(side="left", padx=(4, 0))

        # ----------------------------------------------------
        # 2. TRAFFIC & FAILOVER MONITOR
        # ----------------------------------------------------
        log_card = ctk.CTkFrame(self.scroll_frame, fg_color=theme.COLOR_CARD, corner_radius=10, border_width=1, border_color=theme.COLOR_BORDER)
        log_card.pack(fill="x", padx=10, pady=(0, 10))

        log_head = ctk.CTkFrame(log_card, fg_color="transparent")
        log_head.pack(fill="x", padx=16, pady=(10, 4))

        log_title = ctk.CTkLabel(log_head, text="Gateway Traffic Monitor", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        log_title.pack(side="left")

        self.btn_clear_logs = ctk.CTkButton(
            log_head,
            text="Clear Logs",
            width=85,
            height=24,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._clear_logs
        )
        self.btn_clear_logs.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            height=120,
            font=theme.FONT_CODE,
            fg_color="#F9FAFB",
            border_width=1,
            border_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            corner_radius=8,
            wrap="none"
        )
        self.log_textbox.pack(fill="x", padx=16, pady=(0, 12))
        self.log_textbox.insert("end", "[SYSTEM] Gateway traffic monitor initialized. Monitoring requests...\n")

        # ----------------------------------------------------
        # 3. CODE SNIPPETS & INTEGRATION DOCUMENTATION
        # ----------------------------------------------------
        docs_card = ctk.CTkFrame(self.scroll_frame, fg_color=theme.COLOR_CARD, corner_radius=10, border_width=1, border_color=theme.COLOR_BORDER)
        docs_card.pack(fill="x", padx=10, pady=(0, 10))

        d_head = ctk.CTkFrame(docs_card, fg_color="transparent")
        d_head.pack(fill="x", padx=16, pady=(14, 6))

        d_title = ctk.CTkLabel(d_head, text="Integration Documentation & Code Snippets", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        d_title.pack(side="left")

        self.tabview = ctk.CTkTabview(docs_card, height=330, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        self.tabview.add("Python (OpenAI SDK)")
        self.tabview.add("Python (Requests)")
        self.tabview.add("JavaScript / Node.js")
        self.tabview.add("cURL Command")
        self.tabview.add("Cursor & VS Code")
        self.tabview.add("Image / Video API")

        self._populate_snippets()

    def _populate_snippets(self):
        s_cfg = cfg.get_server_config()
        port = s_cfg.get("port", 8080)
        base_url = f"http://localhost:{port}/v1"
        key = s_cfg.get("master_key", "sk-omni-live-yourkey")

        py_sdk_code = f'''# OmniAI Studio — Python Integration
# Engineered by VIKA-BUILDS
from openai import OpenAI

client = OpenAI(
    base_url="{base_url}",
    api_key="{key}"
)

# Chat with any model (Gemini, Claude, GPT-4o, Groq, DeepSeek, etc.)
response = client.chat.completions.create(
    model="gemini-1.5-flash",  # or "gpt-4o", "claude-3-5-sonnet", "deepseek-chat", "llama-3.3-70b-versatile"
    messages=[
        {{"role": "system", "content": "You are a senior engineer."}},
        {{"role": "user", "content": "Explain async await simply."}}
    ],
    temperature=0.7,
    stream=True  # Live token streaming supported!
)

for chunk in response:
    content = chunk.choices[0].delta.content or ""
    print(content, end="", flush=True)
'''
        self._add_snippet_tab("Python (OpenAI SDK)", py_sdk_code)

        py_req_code = f'''import requests

url = "{base_url}/chat/completions"
headers = {{
    "Authorization": "Bearer {key}",
    "Content-Type": "application/json"
}}
payload = {{
    "model": "deepseek-chat",  # Auto-routes with multi-key failover!
    "messages": [
        {{"role": "user", "content": "Hello from custom Python project!"}}
    ],
    "temperature": 0.7,
    "stream": False
}}

resp = requests.post(url, headers=headers, json=payload)
print(resp.json()["choices"][0]["message"]["content"])
'''
        self._add_snippet_tab("Python (Requests)", py_req_code)

        js_code = f'''import OpenAI from "openai";

const openai = new OpenAI({{
  baseURL: "{base_url}",
  apiKey: "{key}",
}});

async function main() {{
  const completion = await openai.chat.completions.create({{
    model: "claude-3-5-sonnet",
    messages: [{{ role: "user", content: "Write a quick Express route." }}],
    stream: false,
  }});

  console.log(completion.choices[0].message.content);
}}

main();
'''
        self._add_snippet_tab("JavaScript / Node.js", js_code)

        curl_code = f'''curl {base_url}/chat/completions \\
  -H "Authorization: Bearer {key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "model": "gpt-4o",
    "messages": [{{"role": "user", "content": "Hello from terminal!"}}],
    "temperature": 0.7
  }}'
'''
        self._add_snippet_tab("cURL Command", curl_code)

        ide_code = f'''// Add to Continue.dev or Open-WebUI configuration:
{{
  "models": [
    {{
      "title": "OmniAI Gateway (Gemini 1.5 Flash)",
      "provider": "openai",
      "model": "gemini-1.5-flash",
      "apiBase": "{base_url}",
      "apiKey": "{key}"
    }},
    {{
      "title": "OmniAI Gateway (DeepSeek R1 Reasoner)",
      "provider": "openai",
      "model": "deepseek-reasoner",
      "apiBase": "{base_url}",
      "apiKey": "{key}"
    }}
  ]
}}
'''
        self._add_snippet_tab("Cursor & VS Code", ide_code)

        img_code = f'''import requests

resp = requests.post(
    "{base_url}/images/generations",
    headers={{"Authorization": "Bearer {key}", "Content-Type": "application/json"}},
    json={{
        "prompt": "Cyberpunk flying car over neon Tokyo, 8k render",
        "model": "pollinations",  # or "dall-e-3", "stability", "flux"
        "size": "1024x1024"
    }}
)
print("Image saved to:", resp.json()["data"][0]["local_path"])
'''
        self._add_snippet_tab("Image / Video API", img_code)

    def _add_snippet_tab(self, tab_name: str, code: str):
        tab_frame = self.tabview.tab(tab_name)
        for w in tab_frame.winfo_children():
            w.destroy()

        top_row = ctk.CTkFrame(tab_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=4, pady=(4, 6))

        btn_copy = ctk.CTkButton(
            top_row,
            text="Copy Code",
            width=110,
            height=28,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=lambda c=code: self._copy_snippet(c)
        )
        btn_copy.pack(side="right")

        txt = ctk.CTkTextbox(tab_frame, font=theme.FONT_CODE, fg_color="#F9FAFB", border_width=1, border_color=theme.COLOR_BORDER, text_color=theme.COLOR_TEXT_MAIN, corner_radius=6, wrap="none")
        txt.insert("1.0", code)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _copy_snippet(self, code: str):
        try:
            pyperclip.copy(code)
            messagebox.showinfo("Copied", "Code snippet copied to clipboard.")
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(code)

    def _toggle_server(self):
        if server_manager.is_running():
            server_manager.stop()
            self.btn_toggle_server.configure(text="Start Gateway", fg_color=theme.COLOR_ACCENT, hover_color=theme.COLOR_ACCENT_HOVER, text_color="#FFFFFF")
            self.server_status_badge.configure(text="Server Stopped", text_color=theme.COLOR_ERROR)
            if self.status_callback:
                self.status_callback("API Gateway stopped.")
        else:
            host_choice = self.host_menu.get()
            host = "0.0.0.0" if "0.0.0.0" in host_choice else "127.0.0.1"
            try:
                port = int(self.port_entry.get().strip())
            except ValueError:
                port = 8080
            
            server_manager.start(host=host, port=port)
            self.btn_toggle_server.configure(text="Stop Gateway", fg_color=theme.COLOR_ERROR, hover_color="#B91C1C", text_color="#FFFFFF")
            self.server_status_badge.configure(text=f"Server Running: http://localhost:{port}/v1", text_color=theme.COLOR_SUCCESS)
            self.btn_toggle_server.configure(text="⏹️ Stop Server", fg_color=theme.COLOR_ERROR, hover_color="#DC2626", text_color="#FFFFFF")
            self.server_status_badge.configure(text=f"🟢 Server Running: http://localhost:{port}/v1", text_color=theme.COLOR_SUCCESS)
            if self.status_callback:
                self.status_callback(f"API Gateway active on port {port}.")

    def _open_swagger_docs(self):
        s_cfg = cfg.get_server_config()
        port = s_cfg.get("port", 8080)
        webbrowser.open(f"http://localhost:{port}/docs")

    def _copy_master_key(self):
        key = self.master_key_entry.get().strip()
        if key:
            pyperclip.copy(key)
            messagebox.showinfo("Copied", "Master API Key copied to clipboard!")

    def _generate_new_key(self):
        if messagebox.askyesno("Generate Key", "Generate a new Master API Key? External applications using the old key will need to be updated."):
            new_key = cfg.generate_new_master_key()
            self.master_key_entry.delete(0, "end")
            self.master_key_entry.insert(0, new_key)
            self._populate_snippets()

    def _apply_server_settings(self):
        host_choice = self.host_menu.get()
        host = "0.0.0.0" if "0.0.0.0" in host_choice else "127.0.0.1"
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            port = 8080
            self.port_entry.delete(0, "end")
            self.port_entry.insert(0, "8080")

        master_key = self.master_key_entry.get().strip()
        cfg.set_server_config(enabled=server_manager.is_running(), host=host, port=port, master_key=master_key)
        self._populate_snippets()
        messagebox.showinfo("Saved", "Gateway server settings applied!")

    def _clear_logs(self):
        with logs_lock:
            api_logs.clear()
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.insert("end", "[SYSTEM] Logs cleared.\n")

    def _start_logs_auto_refresh(self):
        def refresh():
            if not self.winfo_exists():
                return
            
            if server_manager.is_running():
                s_cfg = cfg.get_server_config()
                p = s_cfg.get("port", 8080)
                self.server_status_badge.configure(text=f"Server Running: http://localhost:{p}/v1", text_color=theme.COLOR_SUCCESS)
                self.btn_toggle_server.configure(text="Stop Gateway", fg_color=theme.COLOR_ERROR, hover_color="#B91C1C", text_color="#FFFFFF")
            else:
                self.server_status_badge.configure(text="Server Stopped", text_color=theme.COLOR_ERROR)
                self.btn_toggle_server.configure(text="Start Gateway", fg_color=theme.COLOR_ACCENT, hover_color=theme.COLOR_ACCENT_HOVER, text_color="#FFFFFF")

            with logs_lock:
                entries = list(api_logs[:30])

            if entries:
                log_text = ""
                for e in entries:
                    stat_icon = "🟢" if e["status"] == 200 else "🔴"
                    log_text += f"[{e['time']}] {stat_icon} {e['method']} {e['path']} -> {e['status']} ({e['latency_ms']}ms) [Model: {e['model']}] {e['note']}\n"
                
                self.log_textbox.delete("1.0", "end")
                self.log_textbox.insert("1.0", log_text)

            self.after(1500, refresh)

        self.after(1000, refresh)
