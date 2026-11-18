"""
OmniAI Studio - Guide & Free Keys Tab
Minimalist documentation and direct links for free API tiers.
Engineered by VIKA-BUILDS.
"""

import webbrowser
import customtkinter as ctk
import ui.theme as theme

GUIDES = [
    {
        "title": "Groq (Free & Fast Llama 3.3)",
        "desc": "Groq provides high-throughput inference completely free of charge. You can generate hundreds of chat completions per day with Llama 3.3 70B and Mixtral.",
        "url": "https://console.groq.com/keys",
        "btn_text": "Get Groq Key"
    },
    {
        "title": "Google AI Studio (Free Gemini 1.5 & 2.0)",
        "desc": "Google offers a generous free tier for Gemini models (15 requests per minute, up to 1 million token context window). Ideal for long documents, code, and vision analysis.",
        "url": "https://aistudio.google.com/app/apikey",
        "btn_text": "Get Gemini Key"
    },
    {
        "title": "Pollinations AI (No Key Required)",
        "desc": "Built right into OmniAI Studio. Generates streaming text chat and high-resolution FLUX images with no account, no credit card, and zero setup required.",
        "url": "https://pollinations.ai",
        "btn_text": "Visit Pollinations"
    },
    {
        "title": "OpenRouter (300+ Models Under One Key)",
        "desc": "Connects you to Claude 3.5 Sonnet, GPT-4o, DeepSeek R1, Llama 3, Qwen, and hundreds of other models using a single unified API key and balance.",
        "url": "https://openrouter.ai/keys",
        "btn_text": "Get OpenRouter Key"
    },
    {
        "title": "Ollama & LM Studio (100% Offline Local AI)",
        "desc": "Run open-source models completely offline on your PC with zero API fees and total privacy. Point the Custom OpenAI Endpoint to http://localhost:11434/v1.",
        "url": "https://ollama.com",
        "btn_text": "Download Ollama"
    }
]

class GuideTab(ctk.CTkFrame):
    def __init__(self, master, status_callback=None):
        super().__init__(master, fg_color="transparent")
        self.status_callback = status_callback
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Header Card
        header = ctk.CTkFrame(scroll, fg_color=theme.COLOR_CARD_ALT, corner_radius=10, border_width=1, border_color=theme.COLOR_BORDER)
        header.pack(fill="x", padx=10, pady=(0, 14))

        title = ctk.CTkLabel(header, text="Portable AI Quick Reference & Free Keys Guide", font=theme.FONT_HEADING, text_color=theme.COLOR_TEXT_MAIN)
        title.pack(anchor="w", padx=16, pady=(14, 4))

        info = ctk.CTkLabel(
            header,
            text="OmniAI Studio runs on any Windows PC directly without installation.\nCarry it on a USB flash drive: your keys, configurations, and downloads stay beside the executable in portable mode.",
            font=theme.FONT_BODY,
            text_color=theme.COLOR_TEXT_MUTED,
            justify="left"
        )
        info.pack(anchor="w", padx=16, pady=(0, 14))

        # Guide cards
        for g in GUIDES:
            card = ctk.CTkFrame(scroll, fg_color=theme.COLOR_CARD, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
            card.pack(fill="x", padx=10, pady=6)

            card_top = ctk.CTkFrame(card, fg_color="transparent")
            card_top.pack(fill="x", padx=16, pady=(12, 4))

            c_title = ctk.CTkLabel(card_top, text=g["title"], font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
            c_title.pack(side="left")

            btn_link = ctk.CTkButton(
                card_top,
                text=g["btn_text"],
                width=150,
                height=28,
                font=theme.FONT_SMALL,
                fg_color="#F3F4F6",
                hover_color="#E5E7EB",
                text_color="#374151",
                command=lambda u=g["url"]: webbrowser.open(u)
            )
            btn_link.pack(side="right")

            c_desc = ctk.CTkLabel(card, text=g["desc"], font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_MUTED, justify="left", wraplength=680)
            c_desc.pack(anchor="w", padx=16, pady=(0, 12))

        # Portable USB instructions card
        usb_card = ctk.CTkFrame(scroll, fg_color=theme.COLOR_CARD_ALT, corner_radius=8, border_width=1, border_color=theme.COLOR_BORDER)
        usb_card.pack(fill="x", padx=10, pady=(10, 10))

        usb_title = ctk.CTkLabel(usb_card, text="Portable USB Usage", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_TEXT_MAIN)
        usb_title.pack(anchor="w", padx=16, pady=(12, 4))

        usb_text = (
            "1. Copy 'UniversalAI_Studio.exe' to any folder, external SSD, or USB thumb drive.\n"
            "2. When launched, it creates 'portable_config.json' and output folders in the same directory.\n"
            "3. Plug into any other Windows PC and run the EXE directly — zero runtime dependencies required.\n"
            "4. When finished on a shared workstation, click 'Erase All Keys' in Key Pools to clear credentials."
        )
        usb_desc = ctk.CTkLabel(usb_card, text=usb_text, font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_MUTED, justify="left")
        usb_desc.pack(anchor="w", padx=16, pady=(0, 14))
