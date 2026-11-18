"""
Universal AI Portable - Key Pool & Auto-Failover Manager
Supports multiple API keys per provider, rate limit detection, automatic cooldowns,
and seamless failover rotation.
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any

RATE_LIMIT_KEYWORDS = [
    "429",
    "rate limit",
    "rate_limit",
    "quota exceeded",
    "insufficient_quota",
    "resource has been exhausted",
    "resource_exhausted",
    "tokens per minute",
    "requests per minute",
    "tpm",
    "rpm",
    "overloaded",
    "too many requests"
]

class KeyItem:
    def __init__(self, key: str):
        self.key = key.strip()
        self.status = "active"  # "active", "cooldown", "invalid"
        self.cooldown_until = 0.0
        self.total_success = 0
        self.total_fails = 0
        self.last_used = 0.0
        self.last_error = ""

    def is_available(self) -> bool:
        if self.status == "invalid":
            return False
        if self.status == "cooldown":
            if time.time() >= self.cooldown_until:
                self.status = "active"
                self.cooldown_until = 0.0
                return True
            return False
        return True

    def mark_cooldown(self, seconds: float = 60.0, error_msg: str = ""):
        self.status = "cooldown"
        self.cooldown_until = time.time() + seconds
        self.total_fails += 1
        self.last_error = error_msg

    def mark_success(self):
        self.status = "active"
        self.cooldown_until = 0.0
        self.total_success += 1
        self.last_used = time.time()

    def mark_invalid(self, error_msg: str = ""):
        self.status = "invalid"
        self.total_fails += 1
        self.last_error = error_msg

    def get_masked(self) -> str:
        k = self.key
        if len(k) <= 8:
            return "●●●●●"
        return f"{k[:4]}...{k[-4:]}"

class ProviderKeyPool:
    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self.keys: List[KeyItem] = []
        self.current_idx = 0
        self.lock = threading.Lock()

    def set_keys(self, key_strings: List[str]):
        with self.lock:
            existing_map = {item.key: item for item in self.keys}
            new_list = []
            for k in key_strings:
                clean_k = k.strip()
                if not clean_k:
                    continue
                if clean_k in existing_map:
                    new_list.append(existing_map[clean_k])
                else:
                    new_list.append(KeyItem(clean_k))
            self.keys = new_list
            if self.current_idx >= len(self.keys):
                self.current_idx = 0

    def get_active_key(self) -> Optional[KeyItem]:
        with self.lock:
            if not self.keys:
                return None
            
            # First check current index
            n = len(self.keys)
            for i in range(n):
                idx = (self.current_idx + i) % n
                item = self.keys[idx]
                if item.is_available():
                    self.current_idx = idx
                    return item
            
            # If all are in cooldown, find the one that expires soonest
            soonest_item = min(self.keys, key=lambda x: x.cooldown_until)
            return soonest_item

    def rotate_to_next(self, failed_key: str, cooldown_secs: float = 60.0, error_msg: str = "") -> Optional[KeyItem]:
        with self.lock:
            for item in self.keys:
                if item.key == failed_key:
                    item.mark_cooldown(cooldown_secs, error_msg)
                    break
            
            # Find next available key
            n = len(self.keys)
            for i in range(1, n + 1):
                idx = (self.current_idx + i) % n
                candidate = self.keys[idx]
                if candidate.is_available() and candidate.key != failed_key:
                    self.current_idx = idx
                    return candidate
            return None

    def mark_success(self, key: str):
        with self.lock:
            for item in self.keys:
                if item.key == key:
                    item.mark_success()
                    break

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total = len(self.keys)
            active = sum(1 for k in self.keys if k.is_available())
            cooldown = sum(1 for k in self.keys if k.status == "cooldown" and not k.is_available())
            return {
                "total_keys": total,
                "active_keys": active,
                "cooldown_keys": cooldown,
                "keys": [
                    {
                        "masked": k.get_masked(),
                        "status": k.status,
                        "cooldown_remaining": max(0, int(k.cooldown_until - time.time())),
                        "success": k.total_success,
                        "fails": k.total_fails
                    }
                    for k in self.keys
                ]
            }

    def is_rate_limit_error(self, status_code: int, error_text: str) -> bool:
        if status_code in [429, 503]:
            return True
        low_txt = str(error_text).lower()
        return any(kw in low_txt for kw in RATE_LIMIT_KEYWORDS)

class KeyPoolManager:
    def __init__(self):
        self.pools: Dict[str, ProviderKeyPool] = {}
        self.event_listeners: List[Callable[[Dict[str, Any]], None]] = []

    def get_pool(self, provider_id: str) -> ProviderKeyPool:
        pid = provider_id.lower()
        if pid not in self.pools:
            self.pools[pid] = ProviderKeyPool(pid)
        return self.pools[pid]

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self.event_listeners.append(callback)

    def emit_event(self, event_type: str, provider: str, details: Dict[str, Any]):
        event = {
            "type": event_type,
            "provider": provider,
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            **details
        }
        for cb in self.event_listeners:
            try:
                cb(event)
            except Exception:
                pass

    def is_rate_limit_error(self, status_code: int, error_text: str) -> bool:
        if status_code in [429, 503]:
            return True
        low_txt = error_text.lower()
        return any(kw in low_txt for kw in RATE_LIMIT_KEYWORDS)

# Global singleton
key_pools = KeyPoolManager()
