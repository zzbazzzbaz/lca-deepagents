#!/usr/bin/env bash
# 先启动模拟邮件服务器，然后启动 langgraph dev。
# 在 sales_assistant 目录下运行：./start.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 杀掉上一次运行遗留的邮件服务器。
OLD_PID=$(lsof -ti :5002 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
    echo "端口 5002 已被占用（PID $OLD_PID）——正在结束它 ..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
fi

echo "正在 http://127.0.0.1:5002 上启动模拟邮件服务器 ..."
uv run python "$SCRIPT_DIR/mcp/mock_mail_server.py" &
MAIL_PID=$!

# 在 Ctrl-C、正常退出或 TERM 时杀掉邮件服务器。
cleanup() {
    kill "$MAIL_PID" 2>/dev/null
    wait "$MAIL_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

# 等待服务器接受连接（最多 10 秒）。
for i in $(seq 1 10); do
    if curl -s --max-time 1 http://127.0.0.1:5002/ >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "邮件服务器已就绪（PID $MAIL_PID）。正在启动 langgraph dev ..."
cd "$SCRIPT_DIR"

uv run langgraph dev "$@"