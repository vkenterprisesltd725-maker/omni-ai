"""
Configuration Manager for Universal AI Portable Studio
Handles portable persistence, multi-key pools, API gateway server settings,
and key obfuscation.
"""

import os
import sys
import json
import base64
import secrets
from typing import Dict, Any, List, Optional
from key_pool import key_pools

def get_app_data_dir() -> tuple:
    """
    Determines user data directory and mode:
    - Portable mode: when portable.mode, portable_config.json, or --portable flag exists,
      or when the executable name contains 'portable'.
    - Installed/Standard mode: stores user data persistently in %APPDATA%/OmniAI_Studio
      (e.g., C:/Users/<user>/AppData/Roaming/OmniAI_Studio).
    Returns (data_directory, is_portable_flag).
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        exe_name = os.path.basename(sys.executable).lower()
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))
        exe_name = "python"

    has_portable_flag = "--portable" in sys.argv
    has_portable_marker = os.path.exists(os.path.join(exe_dir, "portable.mode"))
    has_portable_config = os.path.exists(os.path.join(exe_dir, "portable_config.json"))
    is_exe_named_portable = "portable" in exe_name

    if has_portable_flag or has_portable_marker or has_portable_config or is_exe_named_portable:
        return exe_dir, True

    # Standard Windows AppData directory for installed applications
    app_data = os.environ.get("APPDATA")
    if not app_data:
        app_data = os.path.expanduser("~")
    data_dir = os.path.join(app_data, "OmniAI_Studio")
    return data_dir, False

APP_VERSION = "2.3.0"
APP_NAME = "OmniAI Studio"
GITHUB_REPO = "vkenterprisesltd725-maker/omni-ai"

DATA_DIR, IS_PORTABLE = get_app_data_dir()
BASE_DIR = DATA_DIR  # Backwards compatibility
CONFIG_FILE = os.path.join(DATA_DIR, "portable_config.json" if IS_PORTABLE else "config.json")
OUTPUTS_IMAGE_DIR = os.path.join(DATA_DIR, "generated_images")
OUTPUTS_VIDEO_DIR = os.path.join(DATA_DIR, "generated_videos")
CHAT_HISTORY_DIR = os.path.join(DATA_DIR, "chat_history")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUTS_IMAGE_DIR, exist_ok=True)
os.makedirs(OUTPUTS_VIDEO_DIR, exist_ok=True)
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": "Light",
    "color_accent": "blue",
    "active_provider": "Pollinations (Free - No Key)",
    "active_model": "openai",
    "system_prompt": "You are a helpful, versatile, and brilliant AI assistant.",
    "temperature": 0.7,
    "max_tokens": 4096,
    "api_server": {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8080,
        "master_key": f"sk-omni-{secrets.token_hex(12)}"
    },
    "keys": {
        "openai": [],
        "gemini": [],
        "claude": [],
        "groq": [],
        "cerebras": [],
        "github_models": [],
        "deepseek": [],
        "openrouter": [],
        "mistral": [],
        "stability": [],
        "replicate": [],
        "fal": []
    },
    "custom_endpoint": {
        "name": "Custom Model / Ollama",
        "base_url": "http://localhost:11434/v1",
        "api_key": "",
        "model_name": "llama3:latest"
    },
    "image_settings": {
        "provider": "Pollinations FLUX (Free - No Key)",
        "aspect_ratio": "1:1 Square",
        "style": "Photorealistic"
    },
    "video_settings": {
        "provider": "Replicate (Minimax / Luma Dream Machine)",
        "aspect_ratio": "16:9 Landscape"
    },
    "auto_check_updates": True,
    "skipped_update_version": "",
    "developer_github": "https://github.com/vkenterprisesltd725-maker",
    "developer_instagram": "https://instagram.com/vikaskhatik725"
}

_SALT = b"OmniAIPortableStudio2026"

def _obfuscate(text: str) -> str:
    if not text:
        return ""
    try:
        raw = text.encode("utf-8")
        xored = bytes(b ^ _SALT[i % len(_SALT)] for i, b in enumerate(raw))
        return base64.b64encode(xored).decode("ascii")
    except Exception:
        return text

def _deobfuscate(text: str) -> str:
    if not text:
        return ""
    try:
        raw = base64.b64decode(text.encode("ascii"))
        xored = bytes(b ^ _SALT[i % len(_SALT)] for i, b in enumerate(raw))
        return xored.decode("utf-8")
    except Exception:
        return text

def parse_keys_string(raw: Any) -> List[str]:
    """Parse string (newline, comma, semicolon separated) or list into clean list of keys."""
    if isinstance(raw, list):
        clean = []
        for k in raw:
            if isinstance(k, str) and k.strip():
                clean.append(k.strip())
        return clean
    if not isinstance(raw, str) or not raw.strip():
        return []
    
    # Replace separators with newlines
    normalized = raw.replace(",", "\n").replace(";", "\n")
    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    return lines

class ConfigManager:
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load configuration and initialize key pools."""
        if not os.path.exists(CONFIG_FILE):
            # Auto-migrate from adjacent portable config if present
            if getattr(sys, "frozen", False):
                legacy_dir = os.path.dirname(os.path.abspath(sys.executable))
            else:
                legacy_dir = os.path.dirname(os.path.abspath(__file__))
            legacy_config = os.path.join(legacy_dir, "portable_config.json")
            if os.path.exists(legacy_config) and os.path.abspath(legacy_config) != os.path.abspath(CONFIG_FILE):
                try:
                    import shutil
                    shutil.copy2(legacy_config, CONFIG_FILE)
                except Exception:
                    pass

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.config = json.loads(json.dumps(DEFAULT_CONFIG))
                self._deep_update(self.config, data)

                # Deobfuscate keys
                if "keys" in self.config:
                    for provider in self.config["keys"]:
                        val = self.config["keys"][provider]
                        if isinstance(val, list):
                            deob_list = []
                            for k in val:
                                if isinstance(k, str) and k.startswith("ENC:"):
                                    deob_list.append(_deobfuscate(k[4:]))
                                elif isinstance(k, str):
                                    deob_list.append(k)
                            self.config["keys"][provider] = deob_list
                        elif isinstance(val, str):
                            if val.startswith("ENC:"):
                                self.config["keys"][provider] = parse_keys_string(_deobfuscate(val[4:]))
                            else:
                                self.config["keys"][provider] = parse_keys_string(val)
                
                if "custom_endpoint" in self.config and "api_key" in self.config["custom_endpoint"]:
                    cust_key = self.config["custom_endpoint"]["api_key"]
                    if isinstance(cust_key, str) and cust_key.startswith("ENC:"):
                        self.config["custom_endpoint"]["api_key"] = _deobfuscate(cust_key[4:])
                
                self._sync_key_pools()
                return
            except Exception as e:
                print(f"[Config] Error loading config: {e}")
        
        self.config = json.loads(json.dumps(DEFAULT_CONFIG))
        self._sync_key_pools()

    def _sync_key_pools(self):
        """Sync loaded keys into KeyPoolManager."""
        keys_dict = self.config.get("keys", {})
        for provider, k_list in keys_dict.items():
            pool = key_pools.get_pool(provider)
            if isinstance(k_list, list):
                pool.set_keys(k_list)
            elif isinstance(k_list, str):
                pool.set_keys(parse_keys_string(k_list))

    def _deep_update(self, base: dict, override: dict):
        for k, v in override.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

    def save(self):
        """Save configuration to disk with obfuscated keys."""
        try:
            to_save = json.loads(json.dumps(self.config))
            if "keys" in to_save:
                for provider in to_save["keys"]:
                    raw_val = to_save["keys"][provider]
                    if isinstance(raw_val, list):
                        enc_list = []
                        for k in raw_val:
                            if k.strip():
                                enc_list.append("ENC:" + _obfuscate(k.strip()))
                        to_save["keys"][provider] = enc_list
                    elif isinstance(raw_val, str) and raw_val.strip():
                        to_save["keys"][provider] = ["ENC:" + _obfuscate(k) for k in parse_keys_string(raw_val)]
                    else:
                        to_save["keys"][provider] = []
            
            if "custom_endpoint" in to_save and "api_key" in to_save["custom_endpoint"]:
                cust_key = to_save["custom_endpoint"]["api_key"]
                if cust_key:
                    to_save["custom_endpoint"]["api_key"] = "ENC:" + _obfuscate(cust_key)
                else:
                    to_save["custom_endpoint"]["api_key"] = ""

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=2, ensure_ascii=False)
            
            self._sync_key_pools()
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get_keys(self, provider: str) -> List[str]:
        raw = self.config.get("keys", {}).get(provider.lower(), [])
        if isinstance(raw, list):
            return [k.strip() for k in raw if k.strip()]
        elif isinstance(raw, str):
            return parse_keys_string(raw)
        return []

    def get_key(self, provider: str) -> str:
        """Returns current active key from KeyPool."""
        pool = key_pools.get_pool(provider)
        active_item = pool.get_active_key()
        if active_item:
            return active_item.key
        
        # Fallback to direct config list
        keys = self.get_keys(provider)
        return keys[0] if keys else ""

    def set_keys(self, provider: str, keys: List[str]):
        if "keys" not in self.config:
            self.config["keys"] = {}
        clean_keys = [k.strip() for k in keys if k.strip()]
        self.config["keys"][provider.lower()] = clean_keys
        key_pools.get_pool(provider).set_keys(clean_keys)
        self.save()

    def set_key(self, provider: str, key_val: str):
        keys = parse_keys_string(key_val)
        self.set_keys(provider, keys)

    def get_server_config(self) -> Dict[str, Any]:
        return self.config.get("api_server", DEFAULT_CONFIG["api_server"])

    def set_server_config(self, enabled: bool, host: str, port: int, master_key: str):
        self.config["api_server"] = {
            "enabled": enabled,
            "host": host.strip(),
            "port": int(port),
            "master_key": master_key.strip()
        }
        self.save()

    def generate_new_master_key(self) -> str:
        new_key = f"sk-omni-{secrets.token_hex(12)}"
        if "api_server" not in self.config:
            self.config["api_server"] = DEFAULT_CONFIG["api_server"].copy()
        self.config["api_server"]["master_key"] = new_key
        self.save()
        return new_key

    def get_custom_endpoint(self) -> Dict[str, str]:
        return self.config.get("custom_endpoint", DEFAULT_CONFIG["custom_endpoint"])

    def set_custom_endpoint(self, base_url: str, api_key: str, model_name: str):
        self.config["custom_endpoint"] = {
            "name": "Custom Endpoint",
            "base_url": base_url.strip(),
            "api_key": api_key.strip(),
            "model_name": model_name.strip()
        }
        self.save()

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set_setting(self, key: str, value: Any):
        self.config[key] = value
        self.save()

    def erase_all_keys(self):
        """Erase all saved API keys for privacy."""
        for provider in self.config.get("keys", {}):
            self.config["keys"][provider] = []
            key_pools.get_pool(provider).set_keys([])
        if "custom_endpoint" in self.config:
            self.config["custom_endpoint"]["api_key"] = ""
        self.save()

    def export_to_file(self, filepath: str) -> bool:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception:
            return False

    def import_from_file(self, filepath: str) -> bool:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._deep_update(self.config, data)
            self.save()
            return True
        except Exception:
            return False

# Global singleton
cfg = ConfigManager()
