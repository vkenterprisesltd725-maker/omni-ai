"""
OmniAI Studio - Image Generation Studio Tab
Engineered by VIKA-BUILDS.
Supports DALL-E 3, Stability AI, Replicate FLUX.1, and Free Pollinations FLUX.
"""

import os
import time
import threading
from typing import List, Optional
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from config import cfg, OUTPUTS_IMAGE_DIR
from api_engine import engine, IMAGE_PROVIDERS
import ui.theme as theme

STYLE_PRESETS = [
    "Photorealistic",
    "Cinematic Film",
    "Anime / Manga",
    "3D Render (Unreal Engine)",
    "Cyberpunk Neon",
    "Fantasy Concept Art",
    "Vintage Oil Painting",
    "Vector Graphic / Minimalist",
    "None"
]

ASPECT_RATIOS = [
    "1:1 Square",
    "16:9 Landscape",
    "9:16 Portrait",
    "4:3 Standard",
    "3:2 Photo"
]

class ImageTab(ctk.CTkFrame):
    def __init__(self, master, status_callback=None):
        super().__init__(master, fg_color="transparent")
        self.status_callback = status_callback
        
        self.is_generating = False
        self.current_image_path: Optional[str] = None
        self.current_pil_image: Optional[Image.Image] = None
        self.session_gallery: List[str] = []

        self._build_ui()

    def _build_ui(self):
        self.split_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.split_frame.pack(fill="both", expand=True, padx=14, pady=12)

        # ----------------------------------------------------
        # LEFT CONTROLS PANEL
        # ----------------------------------------------------
        self.left_panel = ctk.CTkFrame(self.split_frame, fg_color=theme.COLOR_CARD, corner_radius=10, width=380, border_width=1, border_color=theme.COLOR_BORDER)
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))
        self.left_panel.pack_propagate(False)

        panel_title = ctk.CTkLabel(self.left_panel, text="Image Studio", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        panel_title.pack(anchor="w", padx=16, pady=(16, 4))

        panel_sub = ctk.CTkLabel(self.left_panel, text="FLUX & DALL-E Text-to-Image • VIKA-BUILDS", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_DIM)
        panel_sub.pack(anchor="w", padx=16, pady=(0, 10))

        # Provider Selector
        prov_lbl = ctk.CTkLabel(self.left_panel, text="AI Engine / Provider:", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        prov_lbl.pack(anchor="w", padx=16, pady=(4, 2))

        self.provider_combo = ctk.CTkComboBox(
            self.left_panel,
            values=IMAGE_PROVIDERS,
            width=345,
            fg_color=theme.COLOR_INPUT,
            border_color=theme.COLOR_BORDER,
            command=self._on_provider_change
        )
        self.provider_combo.set(cfg.get_setting("image_settings", {}).get("provider", IMAGE_PROVIDERS[0]))
        self.provider_combo.pack(padx=16, pady=(0, 8))

        # Row: Aspect Ratio & Quality
        row_settings = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_settings.pack(fill="x", padx=16, pady=4)

        aspect_lbl = ctk.CTkLabel(row_settings, text="Aspect Ratio:", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        aspect_lbl.grid(row=0, column=0, sticky="w", padx=(0, 10))

        quality_lbl = ctk.CTkLabel(row_settings, text="Quality:", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        quality_lbl.grid(row=0, column=1, sticky="w")

        self.aspect_combo = ctk.CTkComboBox(row_settings, values=ASPECT_RATIOS, width=170, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.aspect_combo.set("1:1 Square")
        self.aspect_combo.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(2, 6))

        self.quality_combo = ctk.CTkComboBox(row_settings, values=["Standard", "HD"], width=155, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.quality_combo.set("Standard")
        self.quality_combo.grid(row=1, column=1, sticky="w", pady=(2, 6))

        # Style Preset
        style_lbl = ctk.CTkLabel(self.left_panel, text="Artistic Style Preset:", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        style_lbl.pack(anchor="w", padx=16, pady=(4, 2))

        self.style_combo = ctk.CTkComboBox(self.left_panel, values=STYLE_PRESETS, width=345, fg_color=theme.COLOR_INPUT, border_color=theme.COLOR_BORDER)
        self.style_combo.set("Photorealistic")
        self.style_combo.pack(padx=16, pady=(0, 8))

        # Prompt Input
        prompt_lbl = ctk.CTkLabel(self.left_panel, text="Prompt Description:", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        prompt_lbl.pack(anchor="w", padx=16, pady=(4, 2))

        self.prompt_text = ctk.CTkTextbox(
            self.left_panel,
            height=110,
            font=theme.FONT_BODY,
            corner_radius=8,
            fg_color=theme.COLOR_INPUT,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            wrap="word"
        )
        self.prompt_text.pack(fill="x", padx=16, pady=(0, 8))
        self.prompt_text.insert("1.0", "A futuristic cyberpunk city with neon reflections in rain puddles, ultra-detailed 8k masterpiece")

        # Negative Prompt
        neg_lbl = ctk.CTkLabel(self.left_panel, text="Negative Prompt (Optional):", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        neg_lbl.pack(anchor="w", padx=16, pady=(2, 2))

        self.neg_entry = ctk.CTkEntry(
            self.left_panel,
            placeholder_text="blur, distorted, low quality, bad anatomy",
            font=theme.FONT_BODY,
            fg_color=theme.COLOR_INPUT,
            border_color=theme.COLOR_BORDER,
            width=345
        )
        self.neg_entry.pack(padx=16, pady=(0, 14))

        # Generate Button
        self.btn_generate = ctk.CTkButton(
            self.left_panel,
            text="Generate Image",
            font=theme.FONT_HEADING,
            height=44,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._generate_image_threaded
        )
        self.btn_generate.pack(fill="x", padx=16, pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(self.left_panel, mode="indeterminate", width=345, progress_color=theme.COLOR_ACCENT)
        self.progress_label = ctk.CTkLabel(self.left_panel, text="Ready to create artwork.", font=theme.FONT_SMALL, text_color=theme.COLOR_TEXT_MUTED)
        self.progress_label.pack(padx=16, pady=(2, 10))

        # ----------------------------------------------------
        # RIGHT PREVIEW & GALLERY PANEL
        # ----------------------------------------------------
        self.right_panel = ctk.CTkFrame(self.split_frame, fg_color=theme.COLOR_CARD, corner_radius=10, border_width=1, border_color=theme.COLOR_BORDER)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.preview_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.preview_header.pack(fill="x", padx=16, pady=(12, 6))

        self.meta_label = ctk.CTkLabel(self.preview_header, text="Generated Art Canvas", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        self.meta_label.pack(side="left")

        self.btn_open_folder = ctk.CTkButton(
            self.preview_header,
            text="Output Folder",
            width=115,
            height=28,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            command=self._open_output_folder
        )
        self.btn_open_folder.pack(side="right", padx=(4, 0))

        self.btn_open_viewer = ctk.CTkButton(
            self.preview_header,
            text="Open in Photos",
            width=120,
            height=28,
            font=theme.FONT_SMALL,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#374151",
            state="disabled",
            command=self._open_in_windows_viewer
        )
        self.btn_open_viewer.pack(side="right", padx=4)

        self.btn_save = ctk.CTkButton(
            self.preview_header,
            text="Save As...",
            width=90,
            height=28,
            font=theme.FONT_SMALL,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            state="disabled",
            command=self._save_image_as
        )
        self.btn_save.pack(side="right", padx=4)

        # Image Canvas Frame
        self.canvas_frame = ctk.CTkFrame(self.right_panel, fg_color="#F9FAFB", corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        self.canvas_frame.pack(fill="both", expand=True, padx=16, pady=6)

        self.canvas_label = ctk.CTkLabel(
            self.canvas_frame,
            text="Your generated artwork will appear here.\n\nSelect a provider on the left and click 'Generate Image'.\n(Pollinations FLUX requires no API key)",
            font=theme.FONT_BODY,
            text_color="#9CA3AF"
        )
        self.canvas_label.pack(fill="both", expand=True, padx=20, pady=20)

        # Gallery Strip at bottom
        self.gallery_frame = ctk.CTkFrame(self.right_panel, fg_color="#F9FAFB", height=90, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        self.gallery_frame.pack(fill="x", padx=16, pady=(6, 12))
        self.gallery_frame.pack_propagate(False)

        gal_title = ctk.CTkLabel(self.gallery_frame, text="Session Gallery:", font=theme.FONT_BADGE, text_color=theme.COLOR_TEXT_MUTED)
        gal_title.pack(anchor="w", padx=10, pady=(4, 2))

        self.gallery_scroll = ctk.CTkScrollableFrame(self.gallery_frame, orientation="horizontal", fg_color="transparent", height=55)
        self.gallery_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 4))

    def _on_provider_change(self, choice: str):
        cfg.set_setting("image_settings", {"provider": choice})

    def _open_output_folder(self):
        try:
            os.startfile(OUTPUTS_IMAGE_DIR)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_in_windows_viewer(self):
        if self.current_image_path and os.path.exists(self.current_image_path):
            try:
                os.startfile(self.current_image_path)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _save_image_as(self):
        if not self.current_pil_image:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All Files", "*.*")]
        )
        if path:
            try:
                self.current_pil_image.save(path)
                messagebox.showinfo("Saved", f"Image saved successfully to:\n{path}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    def _generate_image_threaded(self):
        if self.is_generating:
            return

        prompt = self.prompt_text.get("1.0", "end-1c").strip()
        if not prompt:
            messagebox.showwarning("Empty Prompt", "Please enter a prompt to generate an image.")
            return

        provider = self.provider_combo.get()
        negative_prompt = self.neg_entry.get().strip()
        aspect_ratio = self.aspect_combo.get()
        style = self.style_combo.get()
        quality = self.quality_combo.get()

        self.is_generating = True
        self.btn_generate.configure(state="disabled", text="Generating Image...")
        self.progress_bar.pack(padx=16, pady=(4, 6), before=self.progress_label)
        self.progress_bar.start()
        self.progress_label.configure(text=f"Generating with {provider}...")

        if self.status_callback:
            self.status_callback(f"Rendering image with {provider}...")

        def run():
            t0 = time.time()
            try:
                pil_img, img_path, meta = engine.generate_image(
                    provider_name=provider,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    aspect_ratio=aspect_ratio,
                    style=style,
                    quality=quality
                )
                dur = time.time() - t0
                self.after(0, lambda: self._on_generate_success(pil_img, img_path, meta, dur))
            except Exception as e:
                self.after(0, lambda: self._on_generate_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _on_generate_success(self, pil_img: Image.Image, img_path: str, meta: str, dur: float):
        self.is_generating = False
        self.btn_generate.configure(state="normal", text="Generate Image")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.configure(text=f"Done in {dur:.1f}s ({meta})", text_color=theme.COLOR_SUCCESS)

        self.current_image_path = img_path
        self.current_pil_image = pil_img
        self.session_gallery.append(img_path)

        self.btn_save.configure(state="normal")
        self.btn_open_viewer.configure(state="normal")
        self.meta_label.configure(text=f"Artwork: {meta} ({pil_img.width}x{pil_img.height})")

        self._display_image(pil_img)
        self._add_to_gallery_strip(img_path, pil_img)

        if self.status_callback:
            self.status_callback(f"Image generated successfully in {dur:.1f}s")

    def _on_generate_error(self, err_msg: str):
        self.is_generating = False
        self.btn_generate.configure(state="normal", text="Generate Image")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.configure(text="Generation failed.", text_color=theme.COLOR_ERROR)
        
        messagebox.showerror("Image Generation Error", f"Failed to generate image:\n\n{err_msg}")
        if self.status_callback:
            self.status_callback(f"Image error: {err_msg[:40]}")

    def _display_image(self, pil_img: Image.Image):
        canvas_w = max(self.canvas_frame.winfo_width() - 40, 480)
        canvas_h = max(self.canvas_frame.winfo_height() - 40, 360)

        img_copy = pil_img.copy()
        img_copy.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)

        ctk_img = ctk.CTkImage(light_image=img_copy, dark_image=img_copy, size=img_copy.size)
        self.canvas_label.configure(image=ctk_img, text="")
        self.canvas_label.image = ctk_img

    def _add_to_gallery_strip(self, img_path: str, pil_img: Image.Image):
        thumb = pil_img.copy()
        thumb.thumbnail((50, 50))
        ctk_thumb = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)

        btn = ctk.CTkButton(
            self.gallery_scroll,
            image=ctk_thumb,
            text="",
            width=54,
            height=54,
            fg_color="#FFFFFF",
            hover_color=theme.COLOR_BORDER,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            command=lambda p=img_path: self._load_from_gallery(p)
        )
        btn.image = ctk_thumb
        btn.pack(side="left", padx=4, pady=2)

    def _load_from_gallery(self, path: str):
        if os.path.exists(path):
            img = Image.open(path)
            self.current_image_path = path
            self.current_pil_image = img
            self.meta_label.configure(text=f"Loaded: {os.path.basename(path)} ({img.width}x{img.height})")
            self._display_image(img)
            self.btn_save.configure(state="normal")
            self.btn_open_viewer.configure(state="normal")
