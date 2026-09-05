#!/usr/bin/env bash
# 启动模拟邮件服务器、聊天界面，然后启动 langgraph dev。
# 在 sales_assistant_sandbox 目录下运行：./start.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 结束上一次运行残留的任何邮件服务器或聊天界面进程。
for PORT in 5002 3000 3001; do
    OLD_PID=$(lsof -ti ":$PORT" 2>/dev/null || true)
    if [ -n "$OLD_PID" ]; then
        echo "端口 $PORT 已被占用（PID $OLD_PID）——正在结束它……"
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
done

echo "正在 http://127.0.0.1:5002 上启动模拟邮件服务器……"
uv run python "$SCRIPT_DIR/mcp/mock_mail_server.py" &
MAIL_PID=$!

echo "正在 http://localhost:3000 上启动 agent-chat-ui……"
AGENT_CHAT_UI_DIR="$(cd "$SCRIPT_DIR/../../../agent-chat-ui" && pwd)"
"$AGENT_CHAT_UI_DIR/start.sh" &
UI_PID=$!

# 可选：langchain-ai/deep-agents-ui，用于与 agent-chat-ui 并排试用。
# 不是本课的一部分——仅当这台机器上恰好存在该兄弟仓库时才运行
#（~/Documents/Github/deep-agents-ui）。
# 它不支持异步子代理或真实沙箱文件（参见 m5.5 笔记），
# 因此新闻通讯/异步任务/沙箱文件这些功能不会在这里出现。
DEEP_AGENTS_UI_DIR="$HOME/Documents/Github/deep-agents-ui"
DEEP_AGENTS_UI_PID=""
if [ -d "$DEEP_AGENTS_UI_DIR" ]; then
    echo "正在 http://localhost:3001 上启动 deep-agents-ui……"
    (
        cd "$DEEP_AGENTS_UI_DIR"
        if [ ! -d node_modules ]; then
            echo "正在安装 deep-agents-ui 依赖（yarn install）……"
            yarn install
        fi
        yarn dev --port 3001
    ) &
    DEEP_AGENTS_UI_PID=$!
fi

# 在 Ctrl-C、正常退出或 TERM 时结束邮件服务器、聊天界面，并停止所有运行中的
# 沙箱——这样学生关闭此脚本后，不会一直为沙箱计算付费直到 idle_ttl_seconds 生效。
cleanup() {
    # `set -e` 在 trap 内部同样生效。在真实的 Ctrl-C 场景下，邮件服务器和聊天界面
    # 与本脚本处于同一进程组，通常会在这些行运行之前就因同一个 SIGINT 退出——
    # 因此对已死的 PID 执行 `kill` 会返回非零，如果没有 `|| true`，就会在这里
    # 中止 cleanup()，静默跳过停止沙箱这一步。
    kill "$MAIL_PID" 2>/dev/null || true
    kill "$UI_PID" 2>/dev/null || true
    [ -n "$DEEP_AGENTS_UI_PID" ] && kill "$DEEP_AGENTS_UI_PID" 2>/dev/null || true
    # pnpm/yarn run dev 会把 `next dev` 作为子进程（而非替代进程）派生出来——
    # 仅结束父进程 PID 可能会让它（以及 next-server）变成孤儿进程。
    pkill -f "next dev" 2>/dev/null || true
    wait "$MAIL_PID" "$UI_PID" 2>/dev/null || true
    echo "正在停止所有运行中的沙箱……"
    uv run python "$SCRIPT_DIR/stop_sandboxes.py" || true
}
trap cleanup EXIT INT TERM

# 等待服务器接受连接（最多 10 秒）。
for i in $(seq 1 10); do
    if curl -s --max-time 1 http://127.0.0.1:5002/ >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "邮件服务器已就绪（PID $MAIL_PID），聊天界面正在启动（PID $UI_PID）。正在启动 langgraph dev……"
cd "$SCRIPT_DIR"

# langgraph dev 的本地队列默认只有 1 个工作槽位。每个异步子代理
#（genre-researcher）在其整个运行期间都会占住一个槽位，因此默认配置会让主线程
# 在它们运行期间缺少可用的槽位来处理新消息——参见
# docs.langchain.com/oss/python/deepagents/async-subagents。
uv run langgraph dev --n-jobs-per-worker 10
