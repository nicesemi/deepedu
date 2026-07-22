---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: d028bd878b182ec2195aba4761d44321_bcfb768485e711f1b66e525400e6dd8f
    ReservedCode1: DWetbL9IkUcy4lCo5yQikqsXIIWbhXxJKjOjcHp2kqU7db9oGIF6NeNVKqvZxnwAq2T4bjCkj0rpO/N9YjXonXDhmD3x+I1pS6CBeCO4IghlGNzMqyXm41m8B5m3noXkktYBIdLFZmX5hMjUzjtsnFOrxXshsPo0XKGQrKSLSAt8XBVNUD6MUmmHDhw=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: d028bd878b182ec2195aba4761d44321_bcfb768485e711f1b66e525400e6dd8f
    ReservedCode2: DWetbL9IkUcy4lCo5yQikqsXIIWbhXxJKjOjcHp2kqU7db9oGIF6NeNVKqvZxnwAq2T4bjCkj0rpO/N9YjXonXDhmD3x+I1pS6CBeCO4IghlGNzMqyXm41m8B5m3noXkktYBIdLFZmX5hMjUzjtsnFOrxXshsPo0XKGQrKSLSAt8XBVNUD6MUmmHDhw=
---

# deepedu.school — 家庭教育 AI 平台

项目架构：**Vercel Serverless（网页 + API）+ 本地 Mac 算力一体机（Ollama）**。

```
deepedu-platform/
├── vercel.json              # Vercel 部署配置
├── .env.example             # 环境变量模板
├── frontend/                # 纯静态前端 → Vercel
│   ├── index.html           # 网页版（含 TV 模拟器）
│   └── tv.html              # TV 版（独立下载）
├── backend/api/             # Python Serverless API → Vercel
│   └── index.py             # FastAPI + Mangum
├── local-engine/            # 本地算力一体机 → Mac
│   ├── main.py              # FastAPI + Ollama 推理
│   └── start.command        # 一键启动脚本
└── supabase/
    └── schema.sql           # 数据库表结构
```

## 部署步骤

### 1. Vercel 部署（网页 + API）

```bash
cd ~/Desktop/deepedu-platform
npm i -g vercel
vercel login
vercel --prod
```

在 Vercel 控制台设置环境变量：
- `SILICONFLOW_API_KEY`
- `SILICONFLOW_MODEL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

### 2. 本地算力一体机

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型
ollama pull qwen2.5:7b

# 启动引擎
cd ~/Desktop/deepedu-platform/local-engine
python3 main.py

# 或双击 start.command
```

### 3. Supabase 数据库

在 Supabase SQL Editor 中执行 `supabase/schema.sql`。

### 4. （可选）暴露本地引擎到公网

```bash
brew install ngrok
ngrok config add-authtoken <your-token>
ngrok http 8765
```

将 ngrok 生成的 URL 设为 Vercel 环境变量 `LOCAL_ENGINE_URL`。

## 技术栈

| 层级 | 技术 | 部署位置 |
|------|------|----------|
| 前端 | 纯 HTML/CSS/JS（SPA） | Vercel CDN |
| API | FastAPI + Mangum | Vercel Serverless |
| AI 推理 | SiliconFlow API / Ollama | 云端 + 本地 Mac |
| 知识追踪 | BKT（贝叶斯） | 本地引擎 |
| 数据库 | Supabase (PostgreSQL) | Supabase Cloud |
| TV 版 | 独立 HTML（10 英尺 UI） | 下载到本地 |

## 定价模型

- **免费**：10 万 Token/月，覆盖基础辅导
- **进阶 ¥29/月**：100 万 Token，全学科
- **一体机 ¥2,999 买断**：本地 Ollama 无限推理，限时赠送 1 年进阶
*（内容由AI生成，仅供参考）*
