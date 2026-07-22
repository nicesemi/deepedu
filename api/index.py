"""
deepedu.school — Vercel Serverless API
统一入口，Mangum 适配 FastAPI → Vercel
"""

import os
import re
import json
import math
import httpx
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mangum import Mangum

# ── Config ──
SILICONFLOW_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_MODEL = os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")
LOCAL_ENGINE_URL = os.environ.get("LOCAL_ENGINE_URL", "")  # ngrok URL of local Mac
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

app = FastAPI(title="deepedu.school API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Models ──
class ChatRequest(BaseModel):
    message: str
    skill_type: str = "math"
    grade: str = "grade-4"
    history: list[dict] = []

class BKTRequest(BaseModel):
    user_id: str
    node_id: str
    correct: bool

class SearchRequest(BaseModel):
    query: str
    subject: str = ""

# ── Knowledge Base (embedded) ──
KNOWLEDGE_NODES = [
    {"id": "math-num-1", "title": "100 以内加减法", "subject": "math", "grade": "grade-1", "difficulty": 1, "prerequisites": []},
    {"id": "math-num-2", "title": "乘法口诀表", "subject": "math", "grade": "grade-2", "difficulty": 1, "prerequisites": ["math-num-1"]},
    {"id": "math-num-3", "title": "除法初步", "subject": "math", "grade": "grade-2", "difficulty": 2, "prerequisites": ["math-num-2"]},
    {"id": "math-num-4", "title": "分数认识", "subject": "math", "grade": "grade-3", "difficulty": 2, "prerequisites": ["math-num-3"]},
    {"id": "math-num-5", "title": "小数运算", "subject": "math", "grade": "grade-3", "difficulty": 2, "prerequisites": ["math-num-1"]},
    {"id": "math-alg-1", "title": "简易方程", "subject": "math", "grade": "grade-4", "difficulty": 3, "prerequisites": ["math-num-1", "math-num-2"]},
    {"id": "math-alg-2", "title": "鸡兔同笼", "subject": "math", "grade": "grade-4", "difficulty": 3, "prerequisites": ["math-num-2", "math-num-3"]},
    {"id": "math-geo-1", "title": "长方形正方形面积", "subject": "math", "grade": "grade-3", "difficulty": 2, "prerequisites": ["math-num-2"]},
    {"id": "math-geo-2", "title": "三角形面积", "subject": "math", "grade": "grade-4", "difficulty": 3, "prerequisites": ["math-geo-1"]},
    {"id": "math-geo-3", "title": "圆的周长与面积", "subject": "math", "grade": "grade-5", "difficulty": 3, "prerequisites": ["math-num-2"]},
    {"id": "math-frac-1", "title": "分数加减法", "subject": "math", "grade": "grade-4", "difficulty": 3, "prerequisites": ["math-num-4"]},
    {"id": "math-frac-2", "title": "分数乘除法", "subject": "math", "grade": "grade-5", "difficulty": 4, "prerequisites": ["math-frac-1"]},
    {"id": "math-pct-1", "title": "百分数", "subject": "math", "grade": "grade-5", "difficulty": 3, "prerequisites": ["math-num-4", "math-frac-1"]},
    {"id": "eng-abc", "title": "字母与拼读", "subject": "english", "grade": "grade-1", "difficulty": 1, "prerequisites": []},
    {"id": "eng-word-1", "title": "基础词汇 200", "subject": "english", "grade": "grade-2", "difficulty": 1, "prerequisites": ["eng-abc"]},
    {"id": "eng-gram-1", "title": "简单句与疑问句", "subject": "english", "grade": "grade-3", "difficulty": 2, "prerequisites": ["eng-word-1"]},
    {"id": "eng-read-1", "title": "短文阅读理解", "subject": "english", "grade": "grade-4", "difficulty": 3, "prerequisites": ["eng-gram-1"]},
    {"id": "eng-speak-1", "title": "日常口语对话", "subject": "english", "grade": "grade-3", "difficulty": 2, "prerequisites": ["eng-word-1"]},
    {"id": "eng-write-1", "title": "简单写作", "subject": "english", "grade": "grade-5", "difficulty": 4, "prerequisites": ["eng-gram-1", "eng-read-1"]},
]


# ── BKT Engine ──
class BKTEngine:
    """贝叶斯知识追踪 — 追踪学生对每个知识点的掌握概率"""

    def __init__(self, p_learned=0.15, p_guess=0.25, p_slip=0.10, p_known_init=0.05):
        self.p_learned = p_learned
        self.p_guess = p_guess
        self.p_slip = p_slip
        self.p_known_init = p_known_init
        self.states: dict[str, float] = {}

    def get_p_known(self, node_id: str) -> float:
        return self.states.get(node_id, self.p_known_init)

    def update(self, node_id: str, correct: bool) -> float:
        p_known = self.get_p_known(node_id)
        if correct:
            p_correct_given_known = 1 - self.p_slip
            p_correct_given_not_known = self.p_guess
        else:
            p_correct_given_known = self.p_slip
            p_correct_given_not_known = 1 - self.p_guess

        p_obs = p_known * p_correct_given_known + (1 - p_known) * p_correct_given_not_known
        if p_obs > 0:
            p_known_given_obs = p_known * p_correct_given_known / p_obs
        else:
            p_known_given_obs = p_known

        p_known_new = p_known_given_obs + (1 - p_known_given_obs) * self.p_learned
        self.states[node_id] = p_known_new
        return p_known_new

bkt = BKTEngine()


# ── Local Solver (Math) ──
def solve_math_local(q: str) -> str | None:
    q = q.strip()

    # 鸡兔同笼
    for pattern in [
        r'鸡兔[共同].*?(\d+).*?[头只].*?(\d+).*?[脚腿]',
        r'(\d+).*?头.*?(\d+).*?脚',
        r'(\d+).*?只.*?(\d+).*?[脚腿]',
    ]:
        m = re.search(pattern, q)
        if m:
            heads, legs = int(m.group(1)), int(m.group(2))
            rabbits = (legs - 2 * heads) // 2
            chickens = heads - rabbits
            if rabbits >= 0 and chickens >= 0 and 4*rabbits + 2*chickens == legs:
                return (
                    f"## 鸡兔同笼\n\n**已知**：{heads} 头 {legs} 脚\n\n"
                    f"**假设法**：\n1. 假设全是鸡 → {heads}×2 = {heads*2} 只脚\n"
                    f"2. 差 {legs - heads*2} 只脚\n"
                    f"3. 每换一只兔多 2 只脚 → 兔 = {legs - heads*2} ÷ 2 = **{rabbits} 只**\n"
                    f"4. 鸡 = {heads} - {rabbits} = **{chickens} 只**\n\n"
                    f"**验证**：{rabbits}×4+{chickens}×2 = {4*rabbits+2*chickens} = {legs} ✓\n\n**答**：鸡 {chickens} 只，兔 {rabbits} 只。加油，你掌握了假设法！"
                )
            break

    # 一元一次方程
    m = re.search(r'([\d.]*)\s*x\s*([+\-])\s*([\d.]+)\s*=\s*([\d.]+)', q)
    if m:
        a = float(m.group(1)) if m.group(1) else 1.0
        op, b_val = m.group(2), float(m.group(3))
        c = float(m.group(4))
        b_signed = -b_val if op == '-' else b_val
        x = (c - b_signed) / a
        return (
            f"## 解方程：{a}x {'+' if b_signed>=0 else ''} {b_signed} = {c}\n\n"
            f"1. 移项：{a}x = {c} {'+' if b_signed<0 else '-'} {abs(b_signed)}\n"
            f"2. 计算右边：{c - b_signed}\n"
            f"3. x = {c - b_signed} ÷ {a}\n"
            f"4. **x = {x:.2f}**\n\n**验证**：{a}×{x:.2f} {'+' if b_signed>=0 else ''} {b_signed} = {a*x+b_signed:.2f} ≈ {c} ✓\n\n方程解出来了，很棒！"
        )

    # 四则运算
    m = re.search(r'([\d.]+)\s*([+\-×*/÷])\s*([\d.]+)', q)
    if m:
        a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
        ops = {'+': ('+', a+b), '-': ('-', a-b), '×': ('×', a*b), '*': ('×', a*b),
               '/': ('÷', a/b if b else None), '÷': ('÷', a/b if b else None)}
        if op in ops and ops[op][1] is not None:
            sym, result = ops[op]
            return f"## 计算：{a} {sym} {b}\n\n算式：{a} {sym} {b} = **{result:.6g}**\n\n算得又快又准，继续保持！"
        elif b == 0:
            return "**提示**：除数不能为 0 哦，请检查一下题目。"

    # 面积周长
    m = re.search(r'(正方形|长方形|矩形|三角形|圆形|圆).*?(边长|长|宽|半径|底|高|直径)\s*=?\s*(\d+).*?(\d+)?', q)
    if m:
        shape = m.group(1)
        v1 = float(m.group(3))
        v2 = float(m.group(4)) if m.group(4) else None
        if shape == '正方形':
            return f"## 正方形\n边长 = {v1}\n\n- 面积 = {v1}² = **{v1*v1}**\n- 周长 = 4 × {v1} = **{4*v1}**\n\n正方形是特殊的长方形，你掌握了吗？"
        if shape in ('长方形', '矩形') and v2:
            return f"## 长方形\n长={v1}, 宽={v2}\n\n- 面积 = {v1}×{v2} = **{v1*v2}**\n- 周长 = 2×({v1}+{v2}) = **{2*(v1+v2)}**\n\n很好，公式用得很熟练！"
        if shape in ('圆形', '圆'):
            r = v1
            return f"## 圆\n半径 r = {r}\n\n- 周长 C = 2πr ≈ 2×3.14×{r} = **{2*3.14159*r:.2f}**\n- 面积 S = πr² ≈ 3.14×{r}² = **{3.14159*r*r:.2f}**\n\n圆的公式记住了吗？C=2πr, S=πr²"

    return None


SYSTEM_PROMPT = """你是 deepedu.school 的 AI 辅导老师 DeepTutor。
面向 K-12 学生，请使用中文分步骤讲解。
- 数学题必须给出完整解题步骤和验证
- 英语题给出单词释义和例句
- 回答末尾用一句话鼓励学生
- 答对时表扬，答错时温和引导"""


async def call_siliconflow(messages: list[dict]) -> str:
    if not SILICONFLOW_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(
                "https://api.siliconflow.cn/v1/chat/completions",
                headers={"Authorization": f"Bearer {SILICONFLOW_KEY}"},
                json={"model": SILICONFLOW_MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 1024},
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return ""


async def call_local_engine(messages: list[dict]) -> str:
    if not LOCAL_ENGINE_URL:
        return ""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{LOCAL_ENGINE_URL}/chat", json={"messages": messages})
            if resp.status_code == 200:
                return resp.json().get("answer", "")
    except Exception:
        pass
    return ""


# ── Routes ──
@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/knowledge")
def get_knowledge_nodes(subject: str = "", grade: str = ""):
    nodes = KNOWLEDGE_NODES
    if subject:
        nodes = [n for n in nodes if n["subject"] == subject]
    if grade:
        nodes = [n for n in nodes if n["grade"] == grade]
    return {"nodes": nodes, "total": len(nodes)}

@app.get("/api/knowledge/{node_id}")
def get_knowledge_node(node_id: str):
    for n in KNOWLEDGE_NODES:
        if n["id"] == node_id:
            return n
    raise HTTPException(404, "知识点未找到")

@app.post("/api/chat")
async def chat(req: ChatRequest):
    msg = req.message.strip()
    local_answer = solve_math_local(msg)

    if local_answer and req.skill_type == "math":
        return {"answer": local_answer, "source": "local"}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if req.history:
        messages += req.history
    messages.append({"role": "user", "content": msg})

    # Try SiliconFlow first
    answer = await call_siliconflow(messages)
    if answer:
        return {"answer": answer, "source": "siliconflow"}

    # Try local engine
    answer = await call_local_engine(messages)
    if answer:
        return {"answer": answer, "source": "local_engine"}

    # Fallback
    if local_answer:
        return {"answer": local_answer, "source": "local"}
    return {
        "answer": (
            f"**DeepTutor**：我来帮你分析这个问题。\n\n"
            f"你问的是「{msg[:50]}...」\n\n"
            f"目前 AI 引擎暂未连接，但我可以帮你梳理思路：\n"
            f"1. 先明确题目中的已知条件\n"
            f"2. 找出需要求解的未知量\n"
            f"3. 选择合适的公式或方法\n\n"
            f"试试换个说法描述你的问题，或者选择具体的数学题型（方程、鸡兔同笼、面积等）。"
        ),
        "source": "fallback"
    }

@app.post("/api/bkt/update")
def bkt_update(req: BKTRequest):
    p = bkt.update(req.node_id, req.correct)
    return {"node_id": req.node_id, "p_known": round(p, 4), "mastered": p > 0.85}

@app.get("/api/bkt/state")
def bkt_state():
    return {"states": {k: round(v, 4) for k, v in bkt.states.items()}}

@app.get("/api/courses/english")
def english_courses(level: int = 0):
    courses = [
        {"level": 1, "title": "字母与发音", "content": "26 个英文字母的大小写及基本发音。A a /eɪ/ apple, B b /biː/ book, C c /siː/ cat...", "tips": "每天跟读 5 分钟"},
        {"level": 2, "title": "基础词汇积累", "content": "颜色、数字、家庭成员、身体部位等 200 核心词汇。red 红色、blue 蓝色、one 一、mother 妈妈...", "tips": "用闪卡记忆法"},
        {"level": 3, "title": "简单句型", "content": "I am... / This is... / Can you...? 等基础句型。I am a student. This is my book.", "tips": "每天造 5 个句子"},
        {"level": 4, "title": "语法入门", "content": "一般现在时、现在进行时、be 动词用法。He goes to school. She is reading.", "tips": "注意第三人称单数"},
        {"level": 5, "title": "阅读与理解", "content": "200 词以内的短文阅读，回答问题。培养找关键词和推测能力。", "tips": "先读问题再读文章"},
        {"level": 6, "title": "写作基础", "content": "50-100 词段落写作：自我介绍、日记、简单描述。注意时态一致。", "tips": "先列提纲再写作"},
        {"level": 7, "title": "综合提升", "content": "听力训练+口语表达+150 词以上写作。推荐 Echo Loop 五步法：盲听→精听→跟读→复述→间隔复习。", "tips": "每天 30 分钟沉浸式练习"},
    ]
    if level > 0:
        courses = [c for c in courses if c["level"] == level]
    return {"courses": courses}

@app.get("/api/search")
def search(query: str = ""):
    if not query:
        return {"results": KNOWLEDGE_NODES[:10]}
    q = query.lower()
    results = [n for n in KNOWLEDGE_NODES if q in n["title"].lower() or q in n["subject"].lower()]
    return {"query": query, "results": results, "total": len(results)}

# ── Vercel handler ──
handler = Mangum(app)
