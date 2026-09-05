"""停止本课运行中的沙箱。

由 start.sh 在关闭时运行，这样学生关闭 langgraph dev 后能立即停止沙箱计算的
计费，而不是等 idle_ttl_seconds 结束。只处理名为 "thread-*"（agent.py 中本项目
的命名约定）且当前为 "ready" 状态的沙箱——绝不会碰工作区中的其他沙箱。
"""

from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values
from langsmith.sandbox import SandboxClient

# 显式从 python/.env 加载密钥，而不是依赖外部 shell 环境——它可能持有无关的
# LANGSMITH_API_KEY（例如来自外层 shell/会话），会静默地指向错误的工作区——
# 在构建本课时已经被这个问题坑过一次。
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def main() -> None:
    api_key = dotenv_values(ENV_PATH).get("LANGSMITH_API_KEY")
    client = SandboxClient(api_key=api_key)
    targets = [
        sb
        for sb in client.list_sandboxes()
        if sb.name.startswith("thread-") and getattr(sb, "status", None) == "ready"
    ]
    for sb in targets:
        try:
            client.stop_sandbox(sb.name)
            print(f"已停止沙箱 {sb.name}")
        except Exception as exc:
            print(f"无法停止沙箱 {sb.name}：{exc}")


if __name__ == "__main__":
    main()
