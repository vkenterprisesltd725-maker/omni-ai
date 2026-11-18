"""
Universal AI Portable - Custom API Gateway Server
Exposes an OpenAI-compatible REST API at http://localhost:PORT/v1
allowing any external project, IDE (Cursor/VS Code), LangChain, OpenWebUI,
or script to use all configured AI models with automatic multi-key failover rotation.
"""

import os
import sys
import time
import json
import asyncio
import threading
from typing import Dict, Any, List, Optional, Tuple
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import cfg
from api_engine import engine, PROVIDERS, IMAGE_PROVIDERS
from key_pool import key_pools

app = FastAPI(
    title="OmniAI Portable Gateway API",
    description="Local OpenAI-compatible API Gateway powering all AI models with multi-key failover.",
    version="1.0.0"
)

# Enable CORS for web apps (Next.js, Vite, React, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# LIVE LOGS BUFFER
# -----------------------------------------------------------------------------
MAX_LOGS = 150
api_logs: List[Dict[str, Any]] = []
logs_lock = threading.Lock()

def add_log_entry(method: str, path: str, model: str, provider: str, status_code: int, latency_ms: int, client: str = "", note: str = ""):
    entry = {
        "time": time.strftime("%H:%M:%S"),
        "method": method,
        "path": path,
        "model": model,
        "provider": provider,
        "status": status_code,
        "latency_ms": latency_ms,
        "client": client,
        "note": note
    }
    with logs_lock:
        api_logs.insert(0, entry)
        if len(api_logs) > MAX_LOGS:
            api_logs.pop()

# -----------------------------------------------------------------------------
# AUTHENTICATION
# -----------------------------------------------------------------------------
async def verify_master_key(request: Request):
    s_cfg = cfg.get_server_config()
    master_key = s_cfg.get("master_key", "").strip()
    if not master_key:
        return True  # Open access mode

    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "x-api-key" in request.headers:
        token = request.headers["x-api-key"].strip()

    if token != master_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "Invalid API key. Check Master Key in OmniAI Studio.", "type": "invalid_request_error"}}
        )
    return True

# -----------------------------------------------------------------------------
# MODEL ROUTING HELPER
# -----------------------------------------------------------------------------
def resolve_model_and_provider(requested_model: str) -> Tuple[str, str]:
    """
    Resolves requested model string to (provider_name, clean_model_name).
    Supports prefixes like 'openai/gpt-4o' or direct model names 'gemini-1.5-flash'.
    """
    m = requested_model.lower().strip()

    # Prefix checks
    if "/" in requested_model:
        prefix, clean = requested_model.split("/", 1)
        prefix = prefix.lower().strip()
        if prefix in ["openai"]:
            return "OpenAI (Official)", clean
        elif prefix in ["gemini", "google"]:
            return "Google Gemini", clean
        elif prefix in ["claude", "anthropic"]:
            return "Anthropic Claude", clean
        elif prefix in ["groq"]:
            return "Groq (Free & Ultra-Fast)", clean
        elif prefix in ["deepseek"]:
            return "DeepSeek", clean
        elif prefix in ["mistral"]:
            return "Mistral AI", clean
        elif prefix in ["openrouter"]:
            return "OpenRouter (300+ Models)", clean
        elif prefix in ["pollinations", "free"]:
            return "Pollinations (Free - No Key)", clean
        elif prefix in ["custom", "ollama", "local"]:
            return "Custom OpenAI Endpoint", clean
        elif cfg.get_keys("openrouter"):
            return "OpenRouter (300+ Models)", requested_model

    # Direct name mapping
    if any(k in m for k in ["gpt-4", "gpt-3.5", "o1", "o3", "dall-e"]):
        return "OpenAI (Official)", requested_model
    elif "gemini" in m:
        return "Google Gemini", requested_model
    elif "claude" in m:
        return "Anthropic Claude", requested_model
    elif any(k in m for k in ["gpt-oss", "qwen", "llama", "mixtral", "gemma"]) and cfg.get_keys("groq"):
        return "Groq (Free & Ultra-Fast)", requested_model
    elif "deepseek" in m:
        return "DeepSeek", requested_model
    elif "mistral" in m:
        return "Mistral AI", requested_model
    elif "pollinations" in m:
        return "Pollinations (Free - No Key)", "openai"
    elif cfg.get_keys("openrouter"):
        return "OpenRouter (300+ Models)", requested_model

    # Fallback to active provider or Custom Endpoint
    active_prov = cfg.get_setting("active_provider", "Pollinations (Free - No Key)")
    return active_prov, requested_model

# -----------------------------------------------------------------------------
# SCHEMAS
# -----------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: Any

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False

class ImageGenerationRequest(BaseModel):
    prompt: str
    model: Optional[str] = "pollinations"
    n: Optional[int] = 1
    size: Optional[str] = "1024x1024"
    quality: Optional[str] = "standard"
    style: Optional[str] = "Photorealistic"

class VideoGenerationRequest(BaseModel):
    prompt: str
    provider: Optional[str] = "Pollinations Video (Free AI Generator)"
    aspect_ratio: Optional[str] = "16:9 Landscape"
    duration: Optional[int] = 5

# -----------------------------------------------------------------------------
# ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "online",
        "service": "OmniAI Portable Gateway API",
        "docs_url": "/docs",
        "models_url": "/v1/models",
        "chat_url": "/v1/chat/completions"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/v1/status")
def get_status(auth=Depends(verify_master_key)):
    pools_stat = {}
    for prov_name, info in PROVIDERS.items():
        pid = info["id"]
        pool = key_pools.get_pool(pid)
        pools_stat[pid] = pool.get_stats()
    
    with logs_lock:
        recent_logs = list(api_logs[:20])

    return {
        "gateway": "OmniAI Portable",
        "active_provider": cfg.get_setting("active_provider"),
        "key_pools": pools_stat,
        "recent_requests_count": len(api_logs),
        "recent_logs": recent_logs
    }

@app.get("/v1/models")
def list_models(auth=Depends(verify_master_key)):
    models_list = []
    
    # Aggregate models from all configured providers
    for prov_name, info in PROVIDERS.items():
        prov_id = info["id"]
        default_models = info.get("models", [])
        for m in default_models:
            models_list.append({
                "id": m,
                "object": "model",
                "created": 1730000000,
                "owned_by": prov_id,
                "permission": [],
                "root": m,
                "parent": None
            })
            # Also register with provider prefix for explicit routing (e.g. gemini/gemini-1.5-flash)
            models_list.append({
                "id": f"{prov_id}/{m}",
                "object": "model",
                "created": 1730000000,
                "owned_by": prov_id,
                "permission": [],
                "root": m,
                "parent": None
            })

    return {"object": "list", "data": models_list}

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, raw_req: Request, auth=Depends(verify_master_key)):
    t0 = time.time()
    prov_name, clean_model = resolve_model_and_provider(req.model)
    client_ip = raw_req.client.host if raw_req.client else "unknown"

    # Extract messages format
    dict_messages = [{"role": m.role, "content": m.content if isinstance(m.content, str) else str(m.content)} for m in req.messages]
    system_prompt = cfg.get_setting("system_prompt", "")

    if req.stream:
        # SSE Streaming response
        async def event_generator():
            queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            cmpl_id = f"chatcmpl-{int(time.time()*1000)}"

            def on_chunk(piece: str):
                loop.call_soon_threadsafe(queue.put_nowait, ("chunk", piece))

            def on_done(full_text: str):
                loop.call_soon_threadsafe(queue.put_nowait, ("done", full_text))

            def on_err(err: str):
                loop.call_soon_threadsafe(queue.put_nowait, ("err", err))

            # Run in worker thread
            def worker():
                engine.chat_stream(
                    provider_name=prov_name,
                    model=clean_model,
                    messages=dict_messages,
                    system_prompt=system_prompt,
                    temperature=req.temperature or 0.7,
                    max_tokens=req.max_tokens or 4096,
                    callback_chunk=on_chunk,
                    callback_done=on_done,
                    callback_err=on_err
                )

            threading.Thread(target=worker, daemon=True).start()

            while True:
                msg_type, val = await queue.get()
                if msg_type == "chunk":
                    chunk_payload = {
                        "id": cmpl_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": clean_model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": val},
                                "finish_reason": None
                            }
                        ]
                    }
                    yield f"data: {json.dumps(chunk_payload)}\n\n"
                elif msg_type == "done":
                    # Send final finish chunk and [DONE]
                    final_chunk = {
                        "id": cmpl_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": clean_model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }
                        ]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    dur = int((time.time() - t0) * 1000)
                    add_log_entry("POST", "/v1/chat/completions", clean_model, prov_name, 200, dur, client_ip, "Stream Completed")
                    break
                elif msg_type == "err":
                    err_chunk = {"error": {"message": val, "type": "api_error"}}
                    yield f"data: {json.dumps(err_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    dur = int((time.time() - t0) * 1000)
                    add_log_entry("POST", "/v1/chat/completions", clean_model, prov_name, 500, dur, client_ip, f"Error: {val[:40]}")
                    break

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    else:
        # Non-streaming synchronous response
        try:
            resp_data = await asyncio.to_thread(
                engine.chat_sync,
                provider_name=prov_name,
                model=clean_model,
                messages=dict_messages,
                system_prompt=system_prompt,
                temperature=req.temperature or 0.7,
                max_tokens=req.max_tokens or 4096
            )
            dur = int((time.time() - t0) * 1000)
            add_log_entry("POST", "/v1/chat/completions", clean_model, prov_name, 200, dur, client_ip, "Sync Success")
            return resp_data
        except Exception as e:
            dur = int((time.time() - t0) * 1000)
            add_log_entry("POST", "/v1/chat/completions", clean_model, prov_name, 500, dur, client_ip, f"Error: {str(e)[:40]}")
            raise HTTPException(status_code=500, detail={"error": {"message": str(e), "type": "api_error"}})

@app.post("/v1/images/generations")
async def image_generations(req: ImageGenerationRequest, raw_req: Request, auth=Depends(verify_master_key)):
    t0 = time.time()
    client_ip = raw_req.client.host if raw_req.client else "unknown"

    # Map requested model to provider
    prov = "Pollinations FLUX (Free - No Key)"
    m = (req.model or "").lower()
    if "dall" in m or "openai" in m:
        prov = "OpenAI (DALL-E 3)"
    elif "stability" in m or "sd" in m:
        prov = "Stability AI (SD3 / Core)"
    elif "replicate" in m or "flux" in m:
        prov = "Replicate (FLUX.1 Schnell)"

    try:
        pil_img, filepath, meta = await asyncio.to_thread(
            engine.generate_image,
            provider_name=prov,
            prompt=req.prompt,
            aspect_ratio="1:1 Square" if "1024x1024" in req.size else "16:9 Landscape",
            style=req.style or "Photorealistic",
            quality=req.quality or "Standard"
        )
        dur = int((time.time() - t0) * 1000)
        add_log_entry("POST", "/v1/images/generations", req.model, prov, 200, dur, client_ip, "Image Success")

        # Encode generated image to base64 URL or file path
        with open(filepath, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode("utf-8")

        return {
            "created": int(time.time()),
            "data": [
                {
                    "b64_json": b64_str,
                    "url": f"file:///{filepath.replace(os.sep, '/')}",
                    "local_path": filepath
                }
            ]
        }
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        add_log_entry("POST", "/v1/images/generations", req.model, prov, 500, dur, client_ip, f"Error: {str(e)[:40]}")
        raise HTTPException(status_code=500, detail={"error": {"message": str(e)}})

@app.post("/v1/videos/generations")
async def video_generations(req: VideoGenerationRequest, raw_req: Request, auth=Depends(verify_master_key)):
    t0 = time.time()
    client_ip = raw_req.client.host if raw_req.client else "unknown"

    try:
        vid_path, vid_url = await asyncio.to_thread(
            engine.generate_video,
            provider_name=req.provider,
            prompt=req.prompt,
            duration=req.duration or 5,
            aspect_ratio=req.aspect_ratio or "16:9 Landscape"
        )
        dur = int((time.time() - t0) * 1000)
        add_log_entry("POST", "/v1/videos/generations", "video", req.provider, 200, dur, client_ip, "Video Success")
        return {
            "status": "succeeded",
            "video_url": vid_url,
            "local_path": vid_path
        }
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        add_log_entry("POST", "/v1/videos/generations", "video", req.provider, 500, dur, client_ip, f"Error: {str(e)[:40]}")
        raise HTTPException(status_code=500, detail={"error": {"message": str(e)}})

# -----------------------------------------------------------------------------
# SERVER CONTROLLER THREAD
# -----------------------------------------------------------------------------
class APIServerManager:
    def __init__(self):
        self.server: Optional[uvicorn.Server] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running_flag = False
        self.active_host = "127.0.0.1"
        self.active_port = 8080

    def start(self, host: str = "127.0.0.1", port: int = 8080):
        if self.is_running_flag:
            return

        self.active_host = host
        self.active_port = port

        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        self.is_running_flag = True

        def run():
            try:
                self.server.run()
            except Exception as e:
                print(f"[APIServer] Error: {e}")
            finally:
                self.is_running_flag = False

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.should_exit = True
        self.is_running_flag = False

    def is_running(self) -> bool:
        return self.is_running_flag

    def get_base_url(self) -> str:
        host = "localhost" if self.active_host in ["127.0.0.1", "0.0.0.0"] else self.active_host
        return f"http://{host}:{self.active_port}/v1"

# Global server controller singleton
server_manager = APIServerManager()
