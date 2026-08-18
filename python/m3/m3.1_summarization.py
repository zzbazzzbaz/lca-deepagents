"""
python/m3/m3.1_summarization.py

演示内置的 SummarizationMiddleware 如何在上下文窗口填满时压缩对话历史。

默认情况下，触发点是模型真实上下文窗口的 85%（Claude Haiku 4.5 为 20 万 token），
在演示中很难达到。本例将 model.profile["max_input_tokens"] 覆盖为一个小值，
使摘要能在几轮对话后触发。

运行：
    cd python && uv run ./m3/m3.1_summarization.py
"""

import asyncio

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from models import model

# 缩小报告的上下文窗口，使摘要能在约 595 token 处触发
# （700 的 85%），而不是在真实阈值处。必须使用 model 对象，而不是字符串。
model.profile = {**model.profile, "max_input_tokens": 700}

agent = create_deep_agent(
    model=model,
    checkpointer=MemorySaver(),
    system_prompt="你是一位乐于助人的助手。请让每一条回复都保持一句话。",
)

THREAD = {"configurable": {"thread_id": "demo"}}


async def turn(message: str) -> str:
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config=THREAD,
    )
    return result["messages"][-1].content


async def show_state() -> None:
    state = await agent.aget_state(THREAD)
    messages = state.values.get("messages", [])
    event = state.values.get("_summarization_event")
    print(f"  已存储 : {len(messages)} 条消息 (原始历史，绝不裁剪)")
    if event:
        cutoff = event.get("cutoff_index", "?")
        print(f"  模型所见 : summary + messages[{cutoff}:]  [已摘要]")


async def main() -> None:
    turns = [
        "我叫 Alex，我在 Acme 公司工作。",
        "2 + 2 等于多少？",
        "我花了三个月时间构建一个分布式缓存。",
        "法国的首都是哪里？",
        "关于我你还记得什么？",
    ]

    for i, message in enumerate(turns, 1):
        print(f"\n{'─' * 50}")
        print(f"第 {i} 轮  用户:  {message}")
        response = await turn(message)
        print(f"第 {i} 轮  助手: {response}")
        await show_state()


if __name__ == "__main__":
    asyncio.run(main())
