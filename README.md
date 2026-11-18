# ⚡ OmniAI Studio — Version 2.1 (Dual Editions)
*Engineered by VIKA-BUILDS*

Universal AI Desktop Studio & Local OpenAI-Compatible REST API Gateway with Multi-Key Auto-Failover.

---

## 📦 Two Distribution Editions

### 1. 🚀 Installer Edition (`OmniAI_Studio_Setup.exe`)
**Recommended for your main daily PC.**
- Runs a graphical setup wizard.
- Installs to `%LOCALAPPDATA%\Programs\OmniAI_Studio`.
- Automatically adds **Desktop** and **Start Menu** shortcuts.
- Registers in Windows **Settings > Installed Apps** with a clean uninstaller.
- **Persistent Data Storage**: All your API keys, multi-key pools, system personas, chat sessions, and generated media are stored in `%APPDATA%\OmniAI_Studio`. They remain permanently saved across restarts, updates, and reboots.
- Start or restart the app anytime just by typing `OmniAI Studio` in Windows Start Menu or clicking the Desktop icon.

### 2. 🧳 Portable Edition (`OmniAI_Studio_Portable.exe`)
**Zero installation. 100% plug & play.**
- Single standalone executable.
- Carry it on a USB flash drive or external SSD.
- Automatically operates in Portable Mode: all settings, keys, and chat history are saved beside the executable in the local folder.
- Plug it into any other Windows 10/11 computer and launch immediately with zero setup.

---

## 🌟 Core Features

- **💬 Multi-Provider Streaming Chat**:
  Supports OpenAI (`gpt-4o`, `o3-mini`), Google Gemini (`1.5 Flash/Pro`, `2.0`), Anthropic Claude (`3.5 Sonnet`, `Haiku`), Groq (`Llama 3.3 70B Free`), DeepSeek (`V3` & `R1`), OpenRouter (`300+ models`), Pollinations (`100% Free - No Key Required`), and Local Offline Models (`Ollama / LM Studio`).
- **📁 Chat History & Session Management**:
  Dedicated sidebar with `+ New Chat`. Conversations auto-title and auto-save as JSON. Load or delete past discussions instantly.
- **🔄 Mid-Conversation Model Switching**:
  Switch providers or models mid-dialogue. Each message is tagged and displays its generating model badge.
- **🖼️ Multimodal Vision**:
  Attach images, blueprints, and screenshots for analysis with Gemini, Claude, or GPT-4o.
- **🎨 Image Studio**:
  Text-to-Image generation using Pollinations FLUX (Free), OpenAI DALL-E 3, Stability AI, and Replicate.
- **🎬 Video Studio**:
  Text-to-Video and Image-to-Video with Replicate Minimax Video-01 and Pollinations Video with 1-click Windows Media Player playback.
- **🔐 Multi-Key Pools with Auto-Failover**:
  Add multiple keys per provider. If a key hits HTTP 429 rate limit or quota exhaustion, it rotates to the next available key automatically.
- **🌐 Custom OpenAI REST API Gateway**:
  Runs a background server at `http://localhost:8080/v1` so external tools (Cursor IDE, VS Code Continue, LangChain, Next.js, Python scripts) can route through OmniAI Studio.
- **✨ Minimal Monochrome Design**:
  Clean, high-legibility white/grey/black typography inspired by Linear, Notion, and Apple.

---

## 🛡️ License & Credits
- **Architect & Developer**: VIKA-BUILDS
- **License**: MIT License
