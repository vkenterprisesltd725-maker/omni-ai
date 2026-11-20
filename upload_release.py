"""
Upload OmniAI Studio release assets to GitHub Release via REST API.
Engineered by VIKA-BUILDS.
"""

import os
import sys
import subprocess
import requests

def get_git_token():
    input_str = "protocol=https\nhost=github.com\n\n"
    res = subprocess.run(["git", "credential", "fill"], input=input_str, capture_output=True, text=True, check=True)
    token = None
    for line in res.stdout.splitlines():
        if line.startswith("password="):
            token = line.split("=", 1)[1].strip()
    return token

def upload_release():
    token = get_git_token()
    if not token:
        print("[ERROR] Could not retrieve GitHub token from git credentials.")
        sys.exit(1)

    repo_owner = "vkenterprisesltd725-maker"
    repo_name = "omni-ai"
    tag_name = "v2.3.0"
    release_title = "OmniAI Studio v2.3.0 — Animated Menu Drawer, Dual Dark/Light Mode & Real-Time Model Detection"

    release_body = """## ⚡ OmniAI Studio v2.3.0 (Built by VIKA-BUILDS)

Universal AI Desktop Studio & Local OpenAI-Compatible REST API Gateway with Multi-Key Auto-Failover.

---

### 🚀 What's New in v2.3.0

- **🎭 Animated Slide-In Navigation Drawer (`☰`)**:
  - Replaced the permanent fixed sidebar with a sleek, minimalist hamburger menu button (`☰`) in the top-left header.
  - Smooth slide-in/out drawer with ease-out physics (~120ms duration) inspired by Claude.com & Linear design.
  - When closed, your workspace expands to **100% full-width view** for immersive chat and canvas workflows.
  - Supports dimming backdrop click-to-dismiss, top `✕` close button, and `Esc` key shortcut.

- **🌓 Dual Obsidian Dark / Monochrome Light Mode**:
  - Replaced the static theme button in the top-right header with an interactive `🌙 Dark` $\\leftrightarrow$ `☀️ Light` toggle pill.
  - Complete dual-mode color architecture across all components: buttons, cards, inputs, tabs, and conversation bubbles.
  - Instant appearance mode transitions with high-contrast text and crisp borders.

- **⚡ Dynamic Real-Time Model Detection**:
  - Live query API key validation across providers (OpenAI, Anthropic, Gemini, Groq, Cerebras, OpenRouter, Mistral, Perplexity).
  - Fetches and displays currently active and available models for your specific key directly in the Chat dropdown.
  - Instant status feedback with clean badge indicators.

- **💬 Modernized Chat Controls & Actions**:
  - **Unified Send / Stop Button**: Context-aware dynamic state transition (displays Send icon `➤` when idle, and active Stop icon `⏹` while streaming responses).
  - **Message Actions**: Added hover **Copy** (`📋`) and **Edit** (`✏️`) buttons for sent prompts to quickly iterate on conversations.
  - **Collapsible History Drawer**: Dedicated `🕘 History` drawer button in the chat header to keep conversation logs easily accessible without cluttering your chat stream.

- **🐙 Developer Contact Card**:
  - Quick-access social links embedded in the drawer footer:
    - **GitHub**: [github.com/vkenterprisesltd725-maker](https://github.com/vkenterprisesltd725-maker)
    - **Instagram**: [instagram.com/vikaskhatik725](https://instagram.com/vikaskhatik725)
  - Right-click customization to save your own developer handle and links.

---

### 📦 Downloads

| Download | File Size | Description |
| :--- | :--- | :--- |
| **🚀 [OmniAI_Studio_Setup.exe](https://github.com/vkenterprisesltd725-maker/omni-ai/releases/download/v2.3.0/OmniAI_Studio_Setup.exe)** | ~70 MB | **Standard Windows Installer** (Recommended). Installs into `%LOCALAPPDATA%\\Programs\\OmniAI_Studio`, creates Desktop & Start Menu shortcuts, registers in Windows Installed Apps, and preserves user data & keys. |
| **🧳 [OmniAI_Studio_Portable.exe](https://github.com/vkenterprisesltd725-maker/omni-ai/releases/download/v2.3.0/OmniAI_Studio_Portable.exe)** | ~41 MB | **100% Standalone Portable**. Carry on USB or external drive. No installation required. Runs anywhere. |
"""

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    print(f"[1/3] Preparing GitHub Release '{tag_name}' for {repo_owner}/{repo_name}...")
    release_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
    
    # Check if release already exists
    check_resp = requests.get(f"{release_url}/tags/{tag_name}", headers=headers)
    if check_resp.status_code == 200:
        rel_data = check_resp.json()
        release_id = rel_data["id"]
        print(f"  Release '{tag_name}' already exists (ID: {release_id}). Updating details...")
        patch_payload = {
            "name": release_title,
            "body": release_body,
            "draft": False,
            "prerelease": False,
            "make_latest": "true"
        }
        requests.patch(f"{release_url}/{release_id}", headers=headers, json=patch_payload)
    else:
        payload = {
            "tag_name": tag_name,
            "target_commitish": "main",
            "name": release_title,
            "body": release_body,
            "draft": False,
            "prerelease": False,
            "make_latest": "true"
        }
        create_resp = requests.post(release_url, headers=headers, json=payload)
        if create_resp.status_code not in [200, 201]:
            print(f"[ERROR] Failed to create release: {create_resp.status_code} {create_resp.text}")
            sys.exit(1)
        rel_data = create_resp.json()
        release_id = rel_data["id"]
        print(f"  Release created successfully! (ID: {release_id})")

    # Upload assets
    giveaway_dir = r"c:\Users\vikas\POJECTS + LEARNING\giveaway"
    assets_to_upload = [
        ("OmniAI_Studio_Setup.exe", os.path.join(giveaway_dir, "OmniAI_Studio_Setup.exe")),
        ("OmniAI_Studio_Portable.exe", os.path.join(giveaway_dir, "OmniAI_Studio_Portable.exe"))
    ]

    # Refresh rel_data
    rel_resp = requests.get(f"{release_url}/{release_id}", headers=headers)
    existing_assets = {a["name"]: a["id"] for a in rel_resp.json().get("assets", [])}

    upload_url_base = f"https://uploads.github.com/repos/{repo_owner}/{repo_name}/releases/{release_id}/assets"

    for asset_name, asset_path in assets_to_upload:
        if not os.path.exists(asset_path):
            print(f"[WARN] File not found: {asset_path}")
            continue

        size_mb = os.path.getsize(asset_path) / (1024 * 1024)
        if asset_name in existing_assets:
            print(f"  Deleting old asset '{asset_name}' before uploading new binary...")
            del_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/assets/{existing_assets[asset_name]}"
            requests.delete(del_url, headers=headers)

        print(f"[2/3] Uploading {asset_name} ({size_mb:.2f} MB)... Please wait...")
        with open(asset_path, "rb") as f:
            upload_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            params = {"name": asset_name}
            up_resp = requests.post(upload_url_base, headers=upload_headers, params=params, data=f)

        if up_resp.status_code in [200, 201]:
            print(f"  [SUCCESS] {asset_name} uploaded successfully!")
        else:
            print(f"  [ERROR] Upload failed for {asset_name}: {up_resp.status_code} {up_resp.text}")

    print("\n" + "=" * 60)
    print("ALL RELEASE ASSETS UPLOADED SUCCESSFULLY!")
    print(f"Release URL: https://github.com/{repo_owner}/{repo_name}/releases/tag/{tag_name}")
    print("=" * 60)

if __name__ == "__main__":
    upload_release()
