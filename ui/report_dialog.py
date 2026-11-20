"""
OmniAI Studio - Feedback, Bug Reporting & Feature Request Dialog
Engineered by VIKA-BUILDS.
Allows users to easily submit bug reports, request features, or send feedback
via GitHub Issues, Clipboard export, file saving, or direct social contact.
"""

import os
import sys
import platform
import urllib.parse
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pyperclip

from config import cfg, IS_PORTABLE
import ui.theme as theme

TEMPLATE_BUG = """### 🐛 Bug Description
Describe what happened clearly and concisely.

### 🔁 Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error or unexpected behavior

### 🎯 Expected Behavior
What should have happened instead?

### 📝 Additional Context / Error Messages
Paste any error text or status code shown in the app.
"""

TEMPLATE_FEATURE = """### ✨ Feature Description
Describe the new feature or enhancement you would like to see.

### 💡 Use Case & Workflow
How would you use this feature, and why would it be valuable?

### 🎨 Proposed Ideas or References (Optional)
Any specific UI layout, API provider, or tool you have in mind?
"""

TEMPLATE_FEEDBACK = """### 💬 General Feedback
Share your thoughts, suggestions, or user experience feedback for OmniAI Studio.

### ⭐ What do you like most?
What features are working best for you?

### 🛠 What could be improved?
What would make the app faster, cleaner, or easier to use?
"""


class ReportDialog(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)

        self.title("Feedback, Bug Report & Feature Request — OmniAI Studio")
        self.geometry("640x680")
        self.minsize(580, 560)
        self.transient(master) if master else None
        self.grab_set()

        self.report_type = "🐛 Bug Report"

        self._build_ui()

    def _get_system_diagnostics(self) -> str:
        """Gather non-sensitive environment diagnostics for bug reports."""
        os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
        py_ver = sys.version.split()[0]
        prov = cfg.get_setting("active_provider", "Unknown")
        model = cfg.get_setting("active_model", "Unknown")
        mode = "Portable Standalone" if IS_PORTABLE else "Standard Installed"
        theme_mode = cfg.get_setting("theme", "Dark")
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return (
            f"**Environment Diagnostics:**\n"
            f"- **App Version**: OmniAI Studio v2.3.0 ({mode})\n"
            f"- **OS**: {os_info}\n"
            f"- **Python**: {py_ver}\n"
            f"- **Active Provider**: {prov}\n"
            f"- **Active Model**: {model}\n"
            f"- **Theme**: {theme_mode}\n"
            f"- **Timestamp**: {time_str}\n"
        )

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(
            self,
            fg_color=theme.COLOR_CARD_ALT,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        header.pack(fill="x", padx=16, pady=(16, 10))

        h_title = ctk.CTkLabel(
            header,
            text="💡 Report an Issue or Request a Feature",
            font=theme.FONT_HEADING,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        h_title.pack(anchor="w", padx=14, pady=(10, 2))

        h_desc = ctk.CTkLabel(
            header,
            text=(
                "Help us make OmniAI Studio better. Submit bugs, suggest capabilities, "
                "or share feedback directly with VIKA-BUILDS."
            ),
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left",
            wraplength=580,
        )
        h_desc.pack(anchor="w", padx=14, pady=(0, 10))

        # Main scrollable body
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=4)

        # 1. Type Selector (Segmented Button)
        type_lbl = ctk.CTkLabel(
            body,
            text="Feedback Category:",
            font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        type_lbl.pack(anchor="w", padx=2, pady=(4, 4))

        self.type_seg = ctk.CTkSegmentedButton(
            body,
            values=["🐛 Bug Report", "✨ Feature Request", "💬 General Feedback"],
            command=self._on_type_changed,
            selected_color=theme.COLOR_ACCENT,
            selected_hover_color=theme.COLOR_ACCENT_HOVER,
            font=theme.FONT_SMALL,
        )
        self.type_seg.set("🐛 Bug Report")
        self.type_seg.pack(fill="x", padx=2, pady=(0, 12))

        # 2. Subject / Title
        subj_lbl = ctk.CTkLabel(
            body,
            text="Title / Short Summary:",
            font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        subj_lbl.pack(anchor="w", padx=2, pady=(4, 4))

        self.subj_entry = ctk.CTkEntry(
            body,
            height=32,
            font=theme.FONT_BODY,
            fg_color=theme.COLOR_INPUT,
            border_color=theme.COLOR_BORDER,
            placeholder_text="e.g. Model failover timeout on rate limit or Add voice input tab",
        )
        self.subj_entry.pack(fill="x", padx=2, pady=(0, 12))

        # 3. Detailed Description Textbox
        desc_lbl = ctk.CTkLabel(
            body,
            text="Detailed Description:",
            font=theme.FONT_BODY_BOLD,
            text_color=theme.COLOR_TEXT_MAIN,
        )
        desc_lbl.pack(anchor="w", padx=2, pady=(4, 4))

        self.desc_textbox = ctk.CTkTextbox(
            body,
            height=180,
            font=theme.FONT_CODE,
            fg_color=theme.COLOR_INPUT,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            corner_radius=6,
        )
        self.desc_textbox.pack(fill="x", padx=2, pady=(0, 12))
        self.desc_textbox.insert("1.0", TEMPLATE_BUG)

        # 4. System Diagnostics Checkbox & Preview
        self.diag_var = ctk.BooleanVar(value=True)
        self.diag_check = ctk.CTkCheckBox(
            body,
            text="Attach System Diagnostics (App version, OS, provider info)",
            variable=self.diag_var,
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_TEXT_MAIN,
            checkbox_height=18,
            checkbox_width=18,
            corner_radius=4,
        )
        self.diag_check.pack(anchor="w", padx=2, pady=(4, 6))

        # Toast / Status Label
        self.status_toast = ctk.CTkLabel(
            body,
            text="",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_SUCCESS,
        )
        self.status_toast.pack(anchor="w", padx=2, pady=(2, 6))

        # Bottom Button Bar
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(10, 16))

        # Left: Quick Social / Direct Contact
        btn_insta = ctk.CTkButton(
            btn_bar,
            text="📷 Instagram DM",
            width=115,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            command=self._open_instagram,
        )
        btn_insta.pack(side="left", padx=(0, 6))

        btn_save = ctk.CTkButton(
            btn_bar,
            text="💾 Save File",
            width=90,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            command=self._save_to_file,
        )
        btn_save.pack(side="left", padx=4)

        btn_copy = ctk.CTkButton(
            btn_bar,
            text="📋 Copy Report",
            width=105,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MAIN,
            command=self._copy_to_clipboard,
        )
        btn_copy.pack(side="left", padx=4)

        # Right: Primary GitHub Issue Button & Close
        btn_close = ctk.CTkButton(
            btn_bar,
            text="Close",
            width=65,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_CARD_HOVER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MUTED,
            command=self.destroy,
        )
        btn_close.pack(side="right", padx=(6, 0))

        btn_github = ctk.CTkButton(
            btn_bar,
            text="🐙 Open GitHub Issue",
            width=150,
            height=32,
            font=theme.FONT_BODY_BOLD,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._submit_github_issue,
        )
        btn_github.pack(side="right", padx=4)

    def _on_type_changed(self, choice: str):
        self.report_type = choice
        self.desc_textbox.delete("1.0", "end")
        if choice == "🐛 Bug Report":
            self.desc_textbox.insert("1.0", TEMPLATE_BUG)
            self.subj_entry.configure(placeholder_text="e.g. Model failover timeout on rate limit")
        elif choice == "✨ Feature Request":
            self.desc_textbox.insert("1.0", TEMPLATE_FEATURE)
            self.subj_entry.configure(placeholder_text="e.g. Add Whisper voice input or PDF document attachment")
        else:
            self.desc_textbox.insert("1.0", TEMPLATE_FEEDBACK)
            self.subj_entry.configure(placeholder_text="e.g. Feedback on drawer animation and light mode")

    def _assemble_report(self) -> tuple[str, str]:
        """Compile the full title and markdown body including diagnostics."""
        subj = self.subj_entry.get().strip() or f"{self.report_type} from OmniAI Studio user"
        desc = self.desc_textbox.get("1.0", "end-1c").strip()

        body_parts = [
            f"## {self.report_type}",
            desc,
        ]

        if self.diag_var.get():
            body_parts.append("\n---\n")
            body_parts.append(self._get_system_diagnostics())

        body = "\n\n".join(body_parts)
        return subj, body

    def _submit_github_issue(self):
        """Open browser directly to GitHub Issues with pre-filled title and markdown body."""
        subj, body = self._assemble_report()

        # Always copy to clipboard as safe backup
        pyperclip.copy(body)

        repo_url = cfg.get_setting("developer_github", "https://github.com/vkenterprisesltd725-maker")
        # Ensure it points to repo issues
        if "omni-ai" not in repo_url:
            repo_url = "https://github.com/vkenterprisesltd725-maker/omni-ai"

        encoded_title = urllib.parse.quote(subj)
        encoded_body = urllib.parse.quote(body)
        issue_url = f"{repo_url.rstrip('/')}/issues/new?title={encoded_title}&body={encoded_body}"

        self.status_toast.configure(
            text="✓ GitHub Issue opened in browser! (Also copied report to clipboard)",
            text_color=theme.COLOR_SUCCESS,
        )

        try:
            webbrowser.open(issue_url)
        except Exception as e:
            messagebox.showerror("Browser Error", f"Could not launch browser:\n{e}\n\nReport copied to clipboard!")

    def _copy_to_clipboard(self):
        subj, body = self._assemble_report()
        full_text = f"Subject: {subj}\n\n{body}"
        pyperclip.copy(full_text)
        self.status_toast.configure(
            text="✓ Full report copied to clipboard successfully!",
            text_color=theme.COLOR_SUCCESS,
        )

    def _save_to_file(self):
        subj, body = self._assemble_report()
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in subj[:30]).strip("_")
        default_file = f"OmniAI_Report_{safe_name}.md"

        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile=default_file,
            filetypes=[("Markdown Document", "*.md"), ("Plain Text", "*.txt")],
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"# OmniAI Studio Report: {subj}\n\n")
                    f.write(body)
                self.status_toast.configure(
                    text=f"✓ Report saved to {os.path.basename(path)}",
                    text_color=theme.COLOR_SUCCESS,
                )
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    def _open_instagram(self):
        insta_url = cfg.get_setting("developer_instagram", "https://instagram.com/vikaskhatik725")
        try:
            webbrowser.open(insta_url)
        except Exception:
            pass


def open_report_dialog(parent=None):
    """Convenience helper to launch ReportDialog."""
    return ReportDialog(parent)
