"""
Universal AI Portable - API Engine
Direct REST API client supporting OpenAI, Gemini, Claude, Groq, DeepSeek,
OpenRouter, Mistral, Stability AI, Replicate, Fal.ai, Pollinations, and Custom Endpoints.
Features Multi-Key Pool support with automatic rate limit failover rotation.
"""

import os
import time
import json
import base64
import threading
import urllib.parse
from typing import List, Dict, Any, Callable, Optional, Tuple
import requests
import certifi
from PIL import Image
import io

from config import cfg, OUTPUTS_IMAGE_DIR, OUTPUTS_VIDEO_DIR
from key_pool import key_pools

os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
os.environ["SSL_CERT_FILE"] = certifi.where()

PROVIDERS = {
    "OpenAI (Official)": {
        "id": "openai",
        "type": "openai_compat",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini", "o1-mini", "gpt-4-turbo"],
        "key_hint": "sk-proj-... (Supports multiple keys)",
        "has_chat": True,
        "has_image": True,
        "has_video": False
    },
    "Google Gemini": {
        "id": "gemini",
        "type": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-exp"],
        "key_hint": "AIzaSy... (Supports multiple keys)",
        "has_chat": True,
        "has_image": False,
        "has_video": False
    },
    "Anthropic Claude": {
        "id": "claude",
        "type": "claude",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "key_hint": "sk-ant-api03-... (Supports multiple keys)",
        "has_chat": True,
        "has_image": False,
        "has_video": False
    },
    "Groq (Free & Ultra-Fast)": {
        "id": "groq",
        "type": "openai_compat",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "key_hint": "gsk_... (Supports multiple keys)",
        "has_chat": True,
        "has_image": False,
        "has_video": False
    },
    "DeepSeek": {
        "id": "deepseek",
        "type": "openai_compat",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "key_hint": "sk-... (Supports multiple keys)",
        "has_chat": True,
        "has_image": False,
        "has_video": False
    },
    "OpenRouter (300+ Models)": {
        "id": "openrouter",
        "type": "openai_compat",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "meta-llama/llama-3.3-70b-instruct",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "google/gemini-2.0-flash-exp:free",
            "deepseek/deepseek-r1",
            "mistralai/mistral-large-2411"
        ],
        "key_hint": "sk-or-v1-... (Supports multiple keys)",
        "has_chat": True,
        "has_image": False,
        "has_video": False
    },
    "Mistral AI": {
        "id": "mistral",
        "type": "openai_compat",
        "base_url": "https://api.mistral.ai/v1",
        "models": ["mistral-large-latest", "pixtral-12b-2409", "codestral-latest", "mistral-small-latest"],
        "key_hint": "Key from console.mistral.ai",
        "has_chat": True,
        "has_image": False,
        "has_video": False
    },
    "Pollinations (Free - No Key)": {
        "id": "pollinations",
        "type": "pollinations",
        "base_url": "https://text.pollinations.ai",
        "models": ["openai", "mistral", "claude-hybrid", "deepseek"],
        "key_hint": "No API Key Required (100% Free)",
        "has_chat": True,
        "has_image": True,
        "has_video": True
    },
    "Custom OpenAI Endpoint": {
        "id": "custom",
        "type": "openai_compat",
        "base_url": "http://localhost:11434/v1",
        "models": ["llama3:latest", "mistral", "deepseek-r1"],
        "key_hint": "Any local (Ollama/LM Studio) or cloud URL",
        "has_chat": True,
        "has_image": False,
        "has_video": False
    }
}

IMAGE_PROVIDERS = [
    "Pollinations FLUX (Free - No Key)",
    "OpenAI (DALL-E 3)",
    "Stability AI (SD3 / Core)",
    "Replicate (FLUX.1 Schnell)"
]

VIDEO_PROVIDERS = [
    "Replicate (Minimax / Luma Dream Machine)",
    "Pollinations Video (Free AI Generator)"
]

def encode_image_to_base64(image_path: str) -> Tuple[str, str]:
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg"
    if ext == ".png":
        mime = "image/png"
    elif ext == ".webp":
        mime = "image/webp"
    elif ext == ".gif":
        mime = "image/gif"
    
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8"), mime

class AIEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = certifi.where()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "*/*"
        })

    # -------------------------------------------------------------------------
    # CHAT STREAM WITH AUTO-FAILOVER MULTI-KEY ROTATION
    # -------------------------------------------------------------------------
    def chat_stream(
        self,
        provider_name: str,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        image_path: Optional[str] = None,
        callback_chunk: Optional[Callable[[str], None]] = None,
        callback_done: Optional[Callable[[str], None]] = None,
        callback_err: Optional[Callable[[str], None]] = None,
        cancel_event = None
    ):
        """Streaming chat completions with automatic key failover."""
        prov_info = PROVIDERS.get(provider_name, PROVIDERS["Custom OpenAI Endpoint"])
        prov_type = prov_info["type"]
        prov_id = prov_info["id"]

        if prov_id == "custom":
            cust = cfg.get_custom_endpoint()
            base_url = cust.get("base_url", "http://localhost:11434/v1").rstrip("/")
            if not model:
                model = cust.get("model_name", "llama3:latest")
            keys_pool = [cust.get("api_key", "")]
        elif prov_id == "pollinations":
            base_url = prov_info["base_url"].rstrip("/")
            keys_pool = [""]
        else:
            base_url = prov_info["base_url"].rstrip("/")
            pool = key_pools.get_pool(prov_id)
            keys_pool = [k.key for k in pool.keys if k.key]
            if not keys_pool:
                keys_pool = cfg.get_keys(prov_id)

        if prov_id not in ["pollinations", "custom"] and not keys_pool:
            if callback_err:
                callback_err(f"No API keys configured for {provider_name}.\nPlease add your key(s) in the 'API Keys & Endpoints' tab.")
            return

        pool = key_pools.get_pool(prov_id)
        max_attempts = max(1, len(keys_pool))
        last_error = ""

        for attempt in range(max_attempts):
            if cancel_event and cancel_event.is_set():
                break

            active_item = pool.get_active_key()
            api_key = active_item.key if active_item else (keys_pool[0] if keys_pool else "")

            try:
                full_text = ""
                if prov_type == "openai_compat":
                    full_text = self._stream_openai_compat(
                        base_url=base_url,
                        api_key=api_key,
                        model=model,
                        messages=messages,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        image_path=image_path,
                        callback_chunk=callback_chunk,
                        cancel_event=cancel_event
                    )
                elif prov_type == "gemini":
                    full_text = self._stream_gemini(
                        base_url=base_url,
                        api_key=api_key,
                        model=model,
                        messages=messages,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        image_path=image_path,
                        callback_chunk=callback_chunk,
                        cancel_event=cancel_event
                    )
                elif prov_type == "claude":
                    full_text = self._stream_claude(
                        base_url=base_url,
                        api_key=api_key,
                        model=model,
                        messages=messages,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        image_path=image_path,
                        callback_chunk=callback_chunk,
                        cancel_event=cancel_event
                    )
                elif prov_type == "pollinations":
                    full_text = self._stream_pollinations(
                        model=model,
                        messages=messages,
                        system_prompt=system_prompt,
                        callback_chunk=callback_chunk,
                        cancel_event=cancel_event
                    )

                if active_item:
                    pool.mark_success(active_item.key)

                if callback_done:
                    callback_done(full_text)
                return

            except Exception as e:
                last_error = str(e)
                status_code = getattr(e, "status_code", 429 if "429" in last_error else 500)
                
                # Check for rate limit or quota exhaustion to trigger auto-failover
                if pool.is_rate_limit_error(status_code, last_error) and len(keys_pool) > 1 and attempt < max_attempts - 1:
                    next_item = pool.rotate_to_next(api_key, cooldown_secs=60.0, error_msg=last_error)
                    key_pools.emit_event("failover", prov_id, {
                        "old_key": active_item.get_masked() if active_item else "key",
                        "new_key": next_item.get_masked() if next_item else "next",
                        "reason": f"Limit Reached: {last_error[:60]}",
                        "attempt": attempt + 1
                    })
                    time.sleep(0.5)
                    continue
                else:
                    break

        if cancel_event and cancel_event.is_set():
            last_error = "[Generation Stopped by User]"
        if callback_err:
            callback_err(last_error)

    # -------------------------------------------------------------------------
    # SYNCHRONOUS CHAT COMPLETION (FOR CUSTOM API GATEWAY SERVER)
    # -------------------------------------------------------------------------
    def chat_sync(
        self,
        provider_name: str,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Synchronous chat completion with multi-key auto-failover."""
        chunks = []
        err_holder = []
        evt = threading.Event()

        def on_chunk(c):
            chunks.append(c)

        def on_done(text):
            evt.set()

        def on_err(err):
            err_holder.append(err)
            evt.set()

        self.chat_stream(
            provider_name=provider_name,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            callback_chunk=on_chunk,
            callback_done=on_done,
            callback_err=on_err
        )

        evt.wait(timeout=120)
        if err_holder:
            raise RuntimeError(err_holder[0])

        full_content = "".join(chunks)
        return {
            "id": f"chatcmpl-{int(time.time()*1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": full_content},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
                "completion_tokens": len(full_content.split()),
                "total_tokens": sum(len(m.get("content", "").split()) for m in messages) + len(full_content.split())
            }
        }

    def _stream_openai_compat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        image_path: Optional[str],
        callback_chunk: Optional[Callable[[str], None]],
        cancel_event
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if "openrouter.ai" in base_url:
            headers["HTTP-Referer"] = "https://github.com/universal-ai-portable"
            headers["X-Title"] = "Universal AI Portable"

        req_messages = []
        if system_prompt:
            req_messages.append({"role": "system", "content": system_prompt})

        for i, m in enumerate(messages):
            role = m["role"]
            content = m["content"]
            if i == len(messages) - 1 and role == "user" and image_path and os.path.exists(image_path):
                b64, mime = encode_image_to_base64(image_path)
                req_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": content},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                    ]
                })
            else:
                req_messages.append({"role": role, "content": content})

        endpoint = f"{base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": req_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        resp = self.session.post(endpoint, headers=headers, json=payload, stream=True, timeout=(10, 120))
        if resp.status_code != 200:
            try:
                err_text = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err_text = resp.text
            err = RuntimeError(f"HTTP {resp.status_code}: {err_text}")
            err.status_code = resp.status_code
            raise err

        accumulated = ""
        for line in resp.iter_lines(decode_unicode=True):
            if cancel_event and cancel_event.is_set():
                break
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk_json = json.loads(data_str)
                    delta = chunk_json.get("choices", [{}])[0].get("delta", {})
                    content_chunk = delta.get("content", "")
                    reasoning_chunk = delta.get("reasoning_content", "")
                    if reasoning_chunk:
                        content_chunk = reasoning_chunk

                    if content_chunk:
                        accumulated += content_chunk
                        if callback_chunk:
                            callback_chunk(content_chunk)
                except Exception:
                    continue

        return accumulated

    def _stream_gemini(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        image_path: Optional[str],
        callback_chunk: Optional[Callable[[str], None]],
        cancel_event
    ) -> str:
        clean_model = model.replace("models/", "")
        endpoint = f"{base_url}/models/{clean_model}:streamGenerateContent?alt=sse&key={api_key}"

        contents = []
        for i, m in enumerate(messages):
            role = "user" if m["role"] == "user" else "model"
            parts = []
            if i == len(messages) - 1 and role == "user" and image_path and os.path.exists(image_path):
                b64, mime = encode_image_to_base64(image_path)
                parts.append({"inline_data": {"mime_type": mime, "data": b64}})
            parts.append({"text": m["content"]})
            contents.append({"role": role, "parts": parts})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        resp = self.session.post(endpoint, headers={"Content-Type": "application/json"}, json=payload, stream=True, timeout=(10, 120))
        if resp.status_code != 200:
            try:
                err_text = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err_text = resp.text
            err = RuntimeError(f"Gemini API Error {resp.status_code}: {err_text}")
            err.status_code = resp.status_code
            raise err

        accumulated = ""
        for line in resp.iter_lines(decode_unicode=True):
            if cancel_event and cancel_event.is_set():
                break
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:].strip()
                try:
                    data_json = json.loads(data_str)
                    candidates = data_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for p in parts:
                            text_piece = p.get("text", "")
                            if text_piece:
                                accumulated += text_piece
                                if callback_chunk:
                                    callback_chunk(text_piece)
                except Exception:
                    continue

        return accumulated

    def _stream_claude(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        image_path: Optional[str],
        callback_chunk: Optional[Callable[[str], None]],
        cancel_event
    ) -> str:
        endpoint = f"{base_url}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        claude_msgs = []
        for i, m in enumerate(messages):
            role = m["role"]
            if role == "system":
                continue
            if i == len(messages) - 1 and role == "user" and image_path and os.path.exists(image_path):
                b64, mime = encode_image_to_base64(image_path)
                claude_msgs.append({
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                        {"type": "text", "text": m["content"]}
                    ]
                })
            else:
                claude_msgs.append({"role": role, "content": m["content"]})

        payload = {
            "model": model,
            "messages": claude_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        if system_prompt:
            payload["system"] = system_prompt

        resp = self.session.post(endpoint, headers=headers, json=payload, stream=True, timeout=(10, 120))
        if resp.status_code != 200:
            try:
                err_text = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err_text = resp.text
            err = RuntimeError(f"Claude API Error {resp.status_code}: {err_text}")
            err.status_code = resp.status_code
            raise err

        accumulated = ""
        for line in resp.iter_lines(decode_unicode=True):
            if cancel_event and cancel_event.is_set():
                break
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:].strip()
                try:
                    data_json = json.loads(data_str)
                    if data_json.get("type") == "content_block_delta":
                        delta_text = data_json.get("delta", {}).get("text", "")
                        if delta_text:
                            accumulated += delta_text
                            if callback_chunk:
                                callback_chunk(delta_text)
                except Exception:
                    continue

        return accumulated

    def _stream_pollinations(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        callback_chunk: Optional[Callable[[str], None]],
        cancel_event
    ) -> str:
        history_text = ""
        if system_prompt:
            history_text += f"[System Instructions: {system_prompt}]\n\n"
        for m in messages:
            history_text += f"{m['role'].capitalize()}: {m['content']}\n"
        
        endpoint = "https://text.pollinations.ai/"
        payload = {
            "messages": [{"role": "user", "content": history_text}],
            "model": model or "openai",
            "seed": int(time.time()),
            "jsonMode": False
        }

        resp = self.session.post(endpoint, json=payload, timeout=(10, 90))
        if resp.status_code != 200:
            raise RuntimeError(f"Pollinations Error {resp.status_code}: {resp.text}")

        full_text = resp.text
        words = full_text.split(" ")
        accumulated = ""
        for i, word in enumerate(words):
            if cancel_event and cancel_event.is_set():
                break
            piece = word + (" " if i < len(words) - 1 else "")
            accumulated += piece
            if callback_chunk:
                callback_chunk(piece)
            time.sleep(0.015)

        return accumulated

    # -------------------------------------------------------------------------
    # IMAGE GENERATION WITH MULTI-KEY AUTO-FAILOVER
    # -------------------------------------------------------------------------
    def generate_image(
        self,
        provider_name: str,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "1:1 Square",
        style: str = "Photorealistic",
        quality: str = "Standard"
    ) -> Tuple[Image.Image, str, str]:
        timestamp = int(time.time())
        filename = f"gen_image_{timestamp}.png"
        filepath = os.path.join(OUTPUTS_IMAGE_DIR, filename)

        dim_map = {
            "1:1 Square": (1024, 1024),
            "16:9 Landscape": (1280, 720),
            "9:16 Portrait": (720, 1280),
            "4:3 Standard": (1024, 768),
            "3:2 Photo": (1152, 768)
        }
        width, height = dim_map.get(aspect_ratio, (1024, 1024))

        enhanced_prompt = prompt
        if style and style != "None":
            enhanced_prompt = f"{prompt}, {style} style, masterpiece, high details, 8k resolution"

        if "OpenAI" in provider_name:
            pool = key_pools.get_pool("openai")
            keys = [k.key for k in pool.keys if k.key] or cfg.get_keys("openai")
            if not keys:
                raise ValueError("OpenAI API key missing. Add it in the Keys tab.")

            dalle_size = "1024x1024"
            if "Landscape" in aspect_ratio:
                dalle_size = "1792x1024"
            elif "Portrait" in aspect_ratio:
                dalle_size = "1024x1792"

            for attempt in range(max(1, len(keys))):
                active_item = pool.get_active_key()
                key = active_item.key if active_item else keys[0]

                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                body = {
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": dalle_size,
                    "quality": "hd" if quality == "HD" else "standard",
                    "response_format": "b64_json"
                }
                resp = self.session.post("https://api.openai.com/v1/images/generations", headers=headers, json=body, timeout=120)
                if resp.status_code == 200:
                    if active_item:
                        pool.mark_success(key)
                    b64_data = resp.json()["data"][0]["b64_json"]
                    img_bytes = base64.b64decode(b64_data)
                    img = Image.open(io.BytesIO(img_bytes))
                    img.save(filepath, "PNG")
                    return img, filepath, f"OpenAI DALL-E 3 ({dalle_size})"
                
                # Check rate limit failover
                if pool.is_rate_limit_error(resp.status_code, resp.text) and len(keys) > 1 and attempt < len(keys) - 1:
                    pool.rotate_to_next(key, cooldown_secs=60.0, error_msg=resp.text)
                    continue
                else:
                    raise RuntimeError(f"OpenAI Image Error {resp.status_code}: {resp.text}")

        elif "Stability" in provider_name:
            pool = key_pools.get_pool("stability")
            keys = [k.key for k in pool.keys if k.key] or cfg.get_keys("stability")
            if not keys:
                raise ValueError("Stability AI API key missing. Add it in the Keys tab.")

            aspect_ratio_param = "1:1"
            if "16:9" in aspect_ratio:
                aspect_ratio_param = "16:9"
            elif "9:16" in aspect_ratio:
                aspect_ratio_param = "9:16"

            for attempt in range(max(1, len(keys))):
                active_item = pool.get_active_key()
                key = active_item.key if active_item else keys[0]

                headers = {"authorization": f"Bearer {key}", "accept": "image/*"}
                data = {"prompt": enhanced_prompt, "aspect_ratio": aspect_ratio_param, "output_format": "png"}
                if negative_prompt:
                    data["negative_prompt"] = negative_prompt

                resp = self.session.post("https://api.stability.ai/v2beta/stable-image/generate/core", headers=headers, files={"none": ""}, data=data, timeout=90)
                if resp.status_code == 200:
                    if active_item:
                        pool.mark_success(key)
                    img = Image.open(io.BytesIO(resp.content))
                    img.save(filepath, "PNG")
                    return img, filepath, f"Stability Core ({aspect_ratio_param})"

                if pool.is_rate_limit_error(resp.status_code, resp.text) and len(keys) > 1 and attempt < len(keys) - 1:
                    pool.rotate_to_next(key, cooldown_secs=60.0, error_msg=resp.text)
                    continue
                else:
                    raise RuntimeError(f"Stability Error {resp.status_code}: {resp.text}")

        elif "Replicate" in provider_name:
            pool = key_pools.get_pool("replicate")
            keys = [k.key for k in pool.keys if k.key] or cfg.get_keys("replicate")
            if not keys:
                raise ValueError("Replicate API key missing. Add it in the Keys tab.")

            for attempt in range(max(1, len(keys))):
                active_item = pool.get_active_key()
                key = active_item.key if active_item else keys[0]

                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "wait"}
                body = {"input": {"prompt": enhanced_prompt, "aspect_ratio": "16:9" if "16:9" in aspect_ratio else "1:1"}}
                resp = self.session.post("https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions", headers=headers, json=body, timeout=90)
                if resp.status_code in [200, 201]:
                    if active_item:
                        pool.mark_success(key)
                    data = resp.json()
                    out_url = data.get("output")
                    if isinstance(out_url, list) and len(out_url) > 0:
                        out_url = out_url[0]
                    img_resp = self.session.get(out_url, timeout=60)
                    img = Image.open(io.BytesIO(img_resp.content))
                    img.save(filepath, "PNG")
                    return img, filepath, "FLUX.1 Schnell via Replicate"

                if pool.is_rate_limit_error(resp.status_code, resp.text) and len(keys) > 1 and attempt < len(keys) - 1:
                    pool.rotate_to_next(key, cooldown_secs=60.0, error_msg=resp.text)
                    continue
                else:
                    raise RuntimeError(f"Replicate Error {resp.status_code}: {resp.text}")

        else:
            # Pollinations FLUX (Free, High Quality, No Key)
            seed = int(time.time() * 1000) % 1000000
            safe_prompt = urllib.parse.quote(enhanced_prompt)
            url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&model=flux&seed={seed}&nologo=true"
            resp = self.session.get(url, timeout=90)
            if resp.status_code != 200:
                try:
                    err_info = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_info = resp.text[:120]
                raise RuntimeError(f"Pollinations Error ({resp.status_code}): {err_info}")
            
            img = Image.open(io.BytesIO(resp.content))
            img.save(filepath, "PNG")
            return img, filepath, f"Pollinations FLUX ({width}x{height})"

    # -------------------------------------------------------------------------
    # VIDEO GENERATION
    # -------------------------------------------------------------------------
    def generate_video(
        self,
        provider_name: str,
        prompt: str,
        starting_image_path: Optional[str] = None,
        duration: int = 5,
        aspect_ratio: str = "16:9 Landscape",
        status_callback: Optional[Callable[[str], None]] = None,
        cancel_event = None
    ) -> Tuple[str, str]:
        timestamp = int(time.time())
        filename = f"gen_video_{timestamp}.mp4"
        filepath = os.path.join(OUTPUTS_VIDEO_DIR, filename)

        if "Replicate" in provider_name:
            pool = key_pools.get_pool("replicate")
            keys = [k.key for k in pool.keys if k.key] or cfg.get_keys("replicate")
            if not keys:
                raise ValueError("Replicate API key is missing. Set it in the 'API Keys & Endpoints' tab.")

            key = pool.get_active_key().key if pool.get_active_key() else keys[0]
            if status_callback:
                status_callback("Initiating video generation on Replicate...")

            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {"input": {"prompt": prompt, "prompt_optimizer": True}}
            if starting_image_path and os.path.exists(starting_image_path):
                b64, mime = encode_image_to_base64(starting_image_path)
                payload["input"]["first_frame_image"] = f"data:{mime};base64,{b64}"

            init_resp = self.session.post("https://api.replicate.com/v1/models/minimax/video-01/predictions", headers=headers, json=payload, timeout=30)
            if init_resp.status_code not in [200, 201]:
                raise RuntimeError(f"Replicate Video Init Failed {init_resp.status_code}: {init_resp.text}")

            pred = init_resp.json()
            poll_url = pred.get("urls", {}).get("get")
            if not poll_url:
                raise RuntimeError("No polling URL returned by Replicate.")

            start_poll = time.time()
            while True:
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("Video generation cancelled by user.")
                if time.time() - start_poll > 600:
                    raise TimeoutError("Video generation timed out after 10 minutes.")

                poll_resp = self.session.get(poll_url, headers=headers, timeout=20)
                if poll_resp.status_code != 200:
                    time.sleep(3)
                    continue

                res = poll_resp.json()
                status = res.get("status")
                logs = res.get("logs", "")
                last_log = logs.strip().split("\n")[-1] if logs else ""

                if status_callback:
                    status_callback(f"Status: {status.upper()}... {last_log[:50]}")

                if status == "succeeded":
                    video_url = res.get("output")
                    if isinstance(video_url, list):
                        video_url = video_url[0]
                    
                    if status_callback:
                        status_callback("Downloading generated MP4 video...")
                    
                    vid_bytes = self.session.get(video_url, timeout=120).content
                    with open(filepath, "wb") as f:
                        f.write(vid_bytes)
                    return filepath, video_url

                elif status in ["failed", "canceled"]:
                    err = res.get("error", "Generation failed on server")
                    raise RuntimeError(f"Video Generation Error: {err}")

                time.sleep(4)

        else:
            # Pollinations Video Generator
            if status_callback:
                status_callback("Connecting to Pollinations Video Stream...")
            time.sleep(1)

            safe_prompt = urllib.parse.quote(prompt)
            video_url = f"https://video.pollinations.ai/prompt/{safe_prompt}"
            
            try:
                if status_callback:
                    status_callback("Rendering AI video frames...")
                resp = self.session.get(video_url, timeout=60)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(filepath, "wb") as f:
                        f.write(resp.content)
                    return filepath, video_url
            except Exception:
                pass

            if status_callback:
                status_callback("Compiling AI motion frames...")
            
            seed = int(time.time())
            img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1280&height=720&model=flux&seed={seed}&nologo=true"
            img_resp = self.session.get(img_url, timeout=40)
            
            poster_path = filepath.replace(".mp4", "_frame.png")
            with open(poster_path, "wb") as f:
                f.write(img_resp.content)
            
            with open(filepath, "wb") as f:
                f.write(img_resp.content)

            return filepath, img_url

    # -------------------------------------------------------------------------
    # TEST CONNECTION & MODEL DISCOVERY
    # -------------------------------------------------------------------------
    def test_connection(self, provider_name: str) -> Tuple[bool, int, str]:
        prov_info = PROVIDERS.get(provider_name, PROVIDERS["Custom OpenAI Endpoint"])
        prov_type = prov_info["type"]
        prov_id = prov_info["id"]

        pool = key_pools.get_pool(prov_id)
        api_key = pool.get_active_key().key if pool.get_active_key() else cfg.get_key(prov_id)

        if prov_id == "custom":
            cust = cfg.get_custom_endpoint()
            api_key = cust.get("api_key", "")
            base_url = cust.get("base_url", "http://localhost:11434/v1").rstrip("/")
        else:
            base_url = prov_info["base_url"].rstrip("/")

        if prov_id not in ["pollinations", "custom"] and not api_key:
            return False, 0, "No API key entered."

        t0 = time.time()
        try:
            if prov_type == "openai_compat":
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = self.session.get(f"{base_url}/models", headers=headers, timeout=10)
                latency = int((time.time() - t0) * 1000)
                if resp.status_code == 200:
                    return True, latency, f"Connected! ({latency}ms)"
                elif resp.status_code == 401:
                    return False, latency, "401 Unauthorized"
                else:
                    return False, latency, f"HTTP {resp.status_code}"

            elif prov_type == "gemini":
                url = f"{base_url}/models?key={api_key}"
                resp = self.session.get(url, timeout=10)
                latency = int((time.time() - t0) * 1000)
                if resp.status_code == 200:
                    return True, latency, f"Gemini Connected! ({latency}ms)"
                elif resp.status_code in [400, 403]:
                    return False, latency, "Invalid Gemini Key"
                else:
                    return False, latency, f"HTTP {resp.status_code}"

            elif prov_type == "claude":
                headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                body = {"model": "claude-3-5-haiku-20241022", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}
                resp = self.session.post(f"{base_url}/messages", headers=headers, json=body, timeout=10)
                latency = int((time.time() - t0) * 1000)
                if resp.status_code == 200:
                    return True, latency, f"Claude Connected! ({latency}ms)"
                elif resp.status_code == 401:
                    return False, latency, "401 Unauthorized"
                else:
                    return False, latency, f"HTTP {resp.status_code}"

            elif prov_type == "pollinations":
                resp = self.session.get("https://text.pollinations.ai/ping", timeout=8)
                latency = int((time.time() - t0) * 1000)
                return True, latency, f"Pollinations Online! ({latency}ms)"

            return False, 0, "Unknown provider"

        except Exception as e:
            return False, 0, f"Error: {str(e)[:45]}"

    def fetch_available_models(self, provider_name: str) -> List[str]:
        prov_info = PROVIDERS.get(provider_name, PROVIDERS["Custom OpenAI Endpoint"])
        prov_id = prov_info["id"]
        pool = key_pools.get_pool(prov_id)
        api_key = pool.get_active_key().key if pool.get_active_key() else cfg.get_key(prov_id)
        
        if prov_id == "custom":
            cust = cfg.get_custom_endpoint()
            api_key = cust.get("api_key", "")
            base_url = cust.get("base_url", "http://localhost:11434/v1").rstrip("/")
        else:
            base_url = prov_info["base_url"].rstrip("/")

        models = list(prov_info.get("models", []))
        try:
            if prov_info["type"] == "openai_compat":
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = self.session.get(f"{base_url}/models", headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    fetched = [m.get("id") for m in data if m.get("id")]
                    if fetched:
                        return sorted(fetched)
            elif prov_info["type"] == "gemini":
                resp = self.session.get(f"{base_url}/models?key={api_key}", timeout=10)
                if resp.status_code == 200:
                    data = resp.json().get("models", [])
                    fetched = [m.get("name", "").replace("models/", "") for m in data if "generateContent" in str(m.get("supportedGenerationMethods", []))]
                    if fetched:
                        return sorted(fetched)
        except Exception:
            pass

        return models

# Global engine singleton
engine = AIEngine()
