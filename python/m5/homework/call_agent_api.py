# python/m5/homework/call_agent_api.py
"""M5.2 作业，第二部分：通过 Agent Server API 与已部署的代理对话。

核心思想
到目前为止，你只能通过 Studio 的聊天面板访问已部署的代理。这个脚本像任何其他客户端
那样访问它：通过本课讲解的同一个 Agent Server API（Threads、Runs），使用 LangGraph
SDK 而不是浏览器。下面的脚手架会为你创建线程并启动运行；你只需提供要问的问题。

运行前
  在第一个终端中，保持以下命令运行：
    cd python/m5/homework
    uv run langgraph dev
  然后在第二个终端中：
    cd python
    uv run ./m5/homework/call_agent_api.py

你需要填写的内容
  TODO 3：写一个 QUESTION（问题），让代理（来自 agent.py）调用你为 TODO 1 写的工具。
"""

import asyncio

from langgraph_sdk import get_client

API_URL = "http://127.0.0.1:2024"
ASSISTANT_ID = "agent"  # 与 langgraph.json 的 "graphs" 中的 "agent" 键对应

# TODO 3：把它替换成一个应该触发你的工具的问题。
QUESTION = "TODO 3：把它替换成一个用于你的已部署代理的问题。"


def _last_ai_text(messages: list) -> str:
    for msg in reversed(messages):
        if msg.get("type") == "ai":
            return msg.get("content", "")
    return ""


async def main() -> None:
    client = get_client(url=API_URL)

    # 通过 API 创建一个线程——即课程 "Threads" 一节描述的同一个 POST /threads 端点。
    thread = await client.threads.create()
    print(f"已通过 POST /threads 创建线程 {thread['thread_id']}")

    # 启动一次运行并等待它完成——POST /threads/{id}/runs/wait。
    result = await client.runs.wait(
        thread["thread_id"],
        ASSISTANT_ID,
        input={"messages": [{"role": "user", "content": QUESTION}]},
    )
    print("\n--- 代理回复（通过 HTTP 接收，而非 agent.invoke()） ---")
    print(_last_ai_text(result["messages"]))


if QUESTION.startswith("TODO 3"):
    raise NotImplementedError("TODO 3：见上方注释块")

asyncio.run(main())