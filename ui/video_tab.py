"""
OmniAI Studio - Video Studio Tab
Engineered by VIKA-BUILDS.
Supports Replicate Minimax Video-01, Luma Dream Machine, and Pollinations Video.
"""

import os
import time
import threading
from typing import Optional
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from config import cfg, OUTPUTS_VIDEO_DIR
from api_engine import engine, VIDEO_PROVIDERS
import ui.theme as theme

class VideoTab(ctk.CTkFrame):
    def __init__(self, master, status_callback=None):
        super().__init__(master, fg_color="transparent")
        self.status_callback = status_callback

        self.is_generating = False
        self.cancel_event = threading.Event()
        self.current_video_path: Optional[str] = None
        self.current_video_url: Optional[str] = None
        self.starting_image_path: Optional[str] = None

        self._build_ui()

    def _build_ui(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=14, pady=12)

        # ----------------------------------------------------
        # LEFT CONTROLS PANEL
        # ----------------------------------------------------
        self.left_panel = ctk.CTkFrame(self.container, fg_color=theme.COLOR_CARD, corner_radius=10, width=400, border_width=1, border_color=theme.COLOR_BORDER)
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))
        self.left_panel.pack_propagate(False)

        panel_title = ctk.CTkLabel(self.left_panel, text="Video Studio", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        panel_title.pack(anchor="w", padx=16, pady=(16, 4))

        panel_sub = ctk.CTkLabel(self.left_panel, text="Text & Image-to-Video Engine • VIKA-BUILDS", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_DIM)
        panel_sub.pack(anchor="w", padx=16, pady=(0, 10))

        # Provider Selector
        prov_lbl = ctk.CTkLabel(self.left_panel, text="Video Engine / Provider:", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        prov_lbl.pack(anchor="w", padx=16, pady=(4, 2))

        self.provider_combo = ctk.CTkComboBox(
            self.left_panel,
            values=VIDEO_PROVIDERS,
            width=365,
            fg_color=theme.COLOR_INPUT,
            border_color=theme.COLOR_BORDER
        )
        self.provider_combo.set(VIDEO_PROVIDERS[0])
        self.provider_combo.pack(padx=16, pady=(0, 10))

        # Aspect Ratio & Duration
        row_opts = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_opts.pack(fill="x", padx=16, pady=4)

        aspect_lbl = ctk.CTkLabel(row_opts, text="Aspect Ratio:", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        aspect_lbl.grid(row=0, column=0, sticky="w", padx=(0, 10))

        dur_lbl = ctk.CTkLabel(row_opts, text="Duration:", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        dur_lbl.grid(row=0, column=1, sticky="w")

        self.aspect_combo = ctk.CTkComboBox(row_opts, values=["16:9 Landscape", "9:16 Portrait / Reels", "1:1 Square"], width=180, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.aspect_combo.set("16:9 Landscape")
        self.aspect_combo.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(2, 6))

        self.dur_combo = ctk.CTkComboBox(row_opts, values=["5 Seconds", "10 Seconds"], width=170, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.dur_combo.set("5 Seconds")
        self.dur_combo.grid(row=1, column=1, sticky="w", pady=(2, 6))

        # Prompt Input
        prompt_lbl = ctk.CTkLabel(self.left_panel, text="Video Motion Prompt:", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        prompt_lbl.pack(anchor="w", padx=16, pady=(6, 2))

        self.prompt_text = ctk.CTkTextbox(
            self.left_panel,
            height=100,
            font=theme.FONT_BODY,
            corner_radius=8,
            fg_color=theme.COLOR_INPUT,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            wrap="word"
        )
        self.prompt_text.pack(fill="x", padx=16, pady=(0, 8))
        self.prompt_text.insert("1.0", "Cinematic drone flythrough of a glowing futuristic sci-fi metropolis at dusk, 4k hyperrealistic slow motion")

        # Optional Starting Frame (Image-to-Video)
        frame_lbl = ctk.CTkLabel(self.left_panel, text="First Frame (Image-to-Video):", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        frame_lbl.pack(anchor="w", padx=16, pady=(6, 2))

        self.img_btn_row = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.img_btn_row.pack(fill="x", padx=16, pady=(0, 8))

        self.btn_pick_img = ctk.CTkButton(
            self.img_btn_row,
            text="Upload Start Frame",
            width=175,
            height=32,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._pick_start_frame
        )
        self.btn_pick_img.pack(side="left")

        self.btn_clear_img = ctk.CTkButton(
            self.img_btn_row,
            text="Remove",
            width=80,
            height=32,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_ERROR,
            hover_color="#B91C1C",
            text_color="#FFFFFF",
            state="disabled",
            command=self._clear_start_frame
        )
        self.btn_clear_img.pack(side="left", padx=6)

        self.frame_name_lbl = ctk.CTkLabel(self.left_panel, text="No initial image selected (Text-to-Video mode)", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        self.frame_name_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        # Generate Button
        self.btn_generate = ctk.CTkButton(
            self.left_panel,
            text="Generate Video",
            font=theme.FONT_HEADING,
            height=44,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._generate_video_threaded
        )
        self.btn_generate.pack(fill="x", padx=16, pady=(0, 8))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.left_panel, mode="indeterminate", width=365, progress_color=theme.COLOR_ACCENT)
        self.progress_label = ctk.CTkLabel(self.left_panel, text="Ready to generate video.", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        self.progress_label.pack(padx=16, pady=(2, 10))

        # ----------------------------------------------------
        # RIGHT VIDEO PREVIEW PANEL
        # ----------------------------------------------------
        self.right_panel = ctk.CTkFrame(self.container, fg_color=theme.COLOR_CARD, corner_radius=10, border_width=1, border_color=theme.COLOR_BORDER)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.header.pack(fill="x", padx=16, pady=(16, 8))

        self.title_lbl = ctk.CTkLabel(self.header, text="Generated Video Player & Controls", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        self.title_lbl.pack(side="left")

        self.btn_open_folder = ctk.CTkButton(
            self.header,
            text="Videos Folder",
            width=110,
            height=28,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._open_videos_folder
        )
        self.btn_open_folder.pack(side="right", padx=(4, 0))

        self.btn_save_video = ctk.CTkButton(
            self.header,
            text="Save MP4 As...",
            width=115,
            height=28,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            state="disabled",
            command=self._save_video_as
        )
        self.btn_save_video.pack(side="right", padx=4)

        # Video box
        self.video_box = ctk.CTkFrame(self.right_panel, fg_color="#F9FAFB", corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        self.video_box.pack(fill="both", expand=True, padx=16, pady=8)

        self.preview_label = ctk.CTkLabel(
            self.video_box,
            text="Ready for AI Video Creation\n\n1. Type your motion prompt\n2. (Optional) Upload an initial image frame\n3. Click 'Generate Video'\n\nAfter generation, your MP4 video can be played directly.",
            font=theme.FONT_BODY,
            text_color="#9CA3AF"
        )
        self.preview_label.pack(fill="both", expand=True, padx=20, pady=20)

        # Bottom Player Controls
        self.playback_bar = ctk.CTkFrame(self.right_panel, fg_color="#F9FAFB", height=60, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        self.playback_bar.pack(fill="x", padx=16, pady=(8, 16))

        self.btn_play = ctk.CTkButton(
            self.playback_bar,
            text="Play in Media Player",
            font=theme.FONT_BODY_BOLD,
            height=38,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            state="disabled",
            command=self._play_video_in_player
        )
        self.btn_play.pack(side="left", padx=14, pady=10)

        self.status_vid_lbl = ctk.CTkLabel(self.playback_bar, text="No video generated yet.", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        self.status_vid_lbl.pack(side="right", padx=16)

    def _pick_start_frame(self):
        filetypes = [("Image files", "*.png;*.jpg;*.jpeg;*.webp"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Select First Frame Image", filetypes=filetypes)
        if path and os.path.exists(path):
            self.starting_image_path = path
            fname = os.path.basename(path)
            self.frame_name_lbl.configure(text=f"Image-to-Video: {fname}", text_color=theme.COLOR_SUCCESS)
            self.btn_clear_img.configure(state="normal")

    def _clear_start_frame(self):
        self.starting_image_path = None
        self.frame_name_lbl.configure(text="No initial image selected (Text-to-Video mode)", text_color=theme.COLOR_TEXT_MUTED)
        self.btn_clear_img.configure(state="disabled")

    def _open_videos_folder(self):
        try:
            os.startfile(OUTPUTS_VIDEO_DIR)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _play_video_in_player(self):
        if self.current_video_path and os.path.exists(self.current_video_path):
            try:
                os.startfile(self.current_video_path)
            except Exception as e:
                messagebox.showerror("Player Error", str(e))

    def _save_video_as(self):
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")]
        )
        if dest:
            try:
                with open(self.current_video_path, "rb") as src, open(dest, "wb") as dst:
                    dst.write(src.read())
                messagebox.showinfo("Saved", f"Video successfully saved to:\n{dest}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    def _generate_video_threaded(self):
        if self.is_generating:
            return

        prompt = self.prompt_text.get("1.0", "end-1c").strip()
        if not prompt:
            messagebox.showwarning("Empty Prompt", "Please enter a description for the video.")
            return

        provider = self.provider_combo.get()
        aspect_ratio = self.aspect_combo.get()
        start_frame = self.starting_image_path

        self.is_generating = True
        self.cancel_event.clear()
        self.btn_generate.configure(state="disabled", text="Rendering Video...")
        self.progress_bar.pack(padx=16, pady=(4, 6), before=self.progress_label)
        self.progress_bar.start()

        def status_update(msg: str):
            self.after(0, lambda: self.progress_label.configure(text=msg))
            if self.status_callback:
                self.after(0, lambda: self.status_callback(msg))

        def run():
            t0 = time.time()
            try:
                vid_path, vid_url = engine.generate_video(
                    provider_name=provider,
                    prompt=prompt,
                    starting_image_path=start_frame,
                    aspect_ratio=aspect_ratio,
                    status_callback=status_update,
                    cancel_event=self.cancel_event
                )
                dur = time.time() - t0
                self.after(0, lambda: self._on_video_success(vid_path, vid_url, dur))
            except Exception as e:
                self.after(0, lambda: self._on_video_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _on_video_success(self, vid_path: str, vid_url: str, dur: float):
        self.is_generating = False
        self.btn_generate.configure(state="normal", text="Generate Video")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.configure(text=f"Video rendered in {dur:.1f}s", text_color=theme.COLOR_SUCCESS)

        self.current_video_path = vid_path
        self.current_video_url = vid_url

        self.btn_play.configure(state="normal")
        self.btn_save_video.configure(state="normal")
        self.status_vid_lbl.configure(text=f"Ready: {os.path.basename(vid_path)}")

        poster_path = vid_path.replace(".mp4", "_frame.png")
        if os.path.exists(poster_path):
            try:
                pil_img = Image.open(poster_path)
                pil_img.thumbnail((640, 360))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                self.preview_label.configure(image=ctk_img, text="")
                self.preview_label.image = ctk_img
            except Exception:
                pass
        else:
            self.preview_label.configure(
                image=None,
                text=f"Video generated successfully.\nSaved to: {vid_path}\nClick 'Play in Media Player' below to view.",
                text_color=theme.COLOR_TEXT_MAIN
            )

        if self.status_callback:
            self.status_callback(f"Video complete ({dur:.1f}s)")

    def _on_video_error(self, err_msg: str):
        self.is_generating = False
        self.btn_generate.configure(state="normal", text="Generate Video")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.configure(text="Video generation failed.", text_color=theme.COLOR_ERROR)

        messagebox.showerror("Video Generation Error", f"Failed to generate video:\n\n{err_msg}")
        if self.status_callback:
            self.status_callback(f"Video error: {err_msg[:40]}")
