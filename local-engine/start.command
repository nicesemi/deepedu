#!/bin/bash
# deepedu.school 本地算力一体机 — 一键启动脚本
# 双击 .command 文件或运行此脚本启动

cd "$(dirname "$0")"

echo "========================================"
echo "  deepedu.school 算力一体机引擎"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 未安装，请先安装 Python。"
    exit 1
fi

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo "Ollama 未安装。正在安装..."
    curl -fsSL https://ollama.com/install.sh | sh
    if [ $? -ne 0 ]; then
        echo "ERROR: Ollama 安装失败。请手动访问 https://ollama.com 下载安装。"
        exit 1
    fi
    echo "Ollama 安装完成！"
fi

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "启动 Ollama 服务..."
    ollama serve &
    sleep 3
fi

# Pull model if needed
echo "检查模型..."
MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
if ! ollama list | grep -q "$MODEL"; then
    echo "正在下载模型 $MODEL ..."
    ollama pull "$MODEL"
fi

# Install Python deps
echo "检查 Python 依赖..."
pip3 install -q fastapi uvicorn httpx pydantic 2>/dev/null

# Start engine
echo ""
echo "引擎启动中..."
echo "  本地地址: http://localhost:8765"
echo "  API 文档: http://localhost:8765/docs"
echo ""
python3 main.py
