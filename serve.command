#!/bin/bash
# deepedu.school — 本地开发服务器
# 双击启动，浏览器打开 http://localhost:8080

cd "$(dirname "$0")/frontend"

echo "========================================"
echo "  deepedu.school 本地开发服务器"
echo "========================================"
echo ""
echo "  访问地址: http://localhost:8080"
echo "  TV 版:    http://localhost:8080/tv.html"
echo "  桌面版:   http://localhost:8080/index.html"
echo ""
echo "  推理引擎优先级:"
echo "    1. 本地 Ollama（需先启动 local-engine/start.command）"
echo "    2. DeepTutor WebSocket（直连 Railway）"
echo "    3. Vercel API（当前域名已失效）"
echo ""
echo "  按 Ctrl+C 停止服务器"
echo ""

python3 -m http.server 8080
