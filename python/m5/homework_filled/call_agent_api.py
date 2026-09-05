# python/m5/homework_filled/call_agent_api.py
"""参考版本：通过 Agent Server API 与已部署的追风者（storm-chaser）代理对话，
而不是使用 Studio 的聊天面板。这只是一个可能的答案，你的答案可能不同。尽情探索！"""

import asyncio

from langgraph_sdk import get_client

API_URL = "http://127.0.0.1:2024"
ASSISTANT_ID = "agent"  # 与 langgraph.json 的 "graphs" 中的 "agent" 键对应

# TODO 3 已填写
QUESTION = "有史以来记录到的最高风速是多少？"


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


asyncio.run(main())