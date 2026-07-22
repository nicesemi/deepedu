"""
deepedu.school — 本地算力一体机引擎
在 Mac 上运行 Ollama 推理服务，通过 ngrok 暴露 API 供 Vercel 前端调用。
"""

import asyncio
import os
import json
import re
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# ── Config ──
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN", "")
PORT = int(os.environ.get("PORT", "8765"))

# ── Models ──
class ChatRequest(BaseModel):
    messages: list[dict]
    temperature: float = 0.3
    max_tokens: int = 1024

class ChatResponse(BaseModel):
    answer: str
    model: str
    source: str = "local_ollama"

# ── BKT Engine ──
class BKTEngine:
    def __init__(self, p_learned=0.15, p_guess=0.25, p_slip=0.10, p_known_init=0.05):
        self.p_learned = p_learned
        self.p_guess = p_guess
        self.p_slip = p_slip
        self.p_known_init = p_known_init
        self.states = {}

    def get_p_known(self, node_id: str) -> float:
        return self.states.get(node_id, self.p_known_init)

    def update(self, node_id: str, correct: bool) -> float:
        p_known = self.get_p_known(node_id)
        if correct:
            p_corr_known = 1 - self.p_slip
            p_corr_not = self.p_guess
        else:
            p_corr_known = self.p_slip
            p_corr_not = 1 - self.p_guess
        p_obs = p_known * p_corr_known + (1 - p_known) * p_corr_not
        if p_obs > 0:
            p_known_obs = p_known * p_corr_known / p_obs
        else:
            p_known_obs = p_known
        p_new = p_known_obs + (1 - p_known_obs) * self.p_learned
        self.states[node_id] = p_new
        return p_new

bkt = BKTEngine()


# ── Math Solver ──
SYSTEM_PROMPT = """你是 deepedu.school 本地算力引擎的 AI 辅导老师。
面向 K-12 学生，用中文分步讲解，给出完整解题过程。
回答末尾用一句话鼓励学生。"""


async def check_ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{OLLAMA_HOST}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def pull_model_if_needed():
    """Pull the model if not available"""
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.get(f"{OLLAMA_HOST}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            if OLLAMA_MODEL not in models and OLLAMA_MODEL.split(":")[0] not in models:
                print(f"Pulling model {OLLAMA_MODEL}...")
                await c.post(f"{OLLAMA_HOST}/api/pull", json={"name": OLLAMA_MODEL})
                print(f"Model {OLLAMA_MODEL} pulled successfully.")
    except Exception as e:
        print(f"Failed to pull model: {e}")


# ── App ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"deepedu.school local engine starting on port {PORT}...")
    if await check_ollama_available():
        print("Ollama detected, checking model...")
        await pull_model_if_needed()
    else:
        print("WARNING: Ollama not available. Please install: curl -fsSL https://ollama.com/install.sh | sh")
    yield

app = FastAPI(title="deepedu.school Local Engine", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    ollama_ok = await check_ollama_available()
    return {
        "status": "ok",
        "ollama": ollama_ok,
        "model": OLLAMA_MODEL if ollama_ok else None,
        "port": PORT
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    ollama_ok = await check_ollama_available()
    if not ollama_ok:
        return ChatResponse(
            answer="本地 Ollama 引擎未运行。请先安装 Ollama（ollama.com），然后运行 `ollama serve`。",
            model="none", source="error"
        )

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + req.messages

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": req.temperature,
                        "num_predict": req.max_tokens
                    }
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return ChatResponse(
                    answer=data.get("message", {}).get("content", ""),
                    model=OLLAMA_MODEL,
                    source="local_ollama"
                )
            else:
                return ChatResponse(answer=f"Ollama 返回错误: {resp.status_code}", model=OLLAMA_MODEL, source="error")
    except Exception as e:
        return ChatResponse(answer=f"推理引擎异常: {str(e)}", model=OLLAMA_MODEL, source="error")


@app.get("/bkt/{node_id}")
def get_bkt_state(node_id: str):
    return {"node_id": node_id, "p_known": round(bkt.get_p_known(node_id), 4)}


@app.post("/bkt/update")
def update_bkt(node_id: str, correct: bool):
    p = bkt.update(node_id, correct)
    return {"node_id": node_id, "p_known": round(p, 4), "mastered": p > 0.85}


@app.get("/bkt/all")
def all_bkt():
    return {"states": {k: round(v, 4) for k, v in bkt.states.items()}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
