# python/m3/m3.1_homework_filled.py
"""m3.1_homework.py 的参考副本，已将 TODO 1 和 TODO 2 填写完成，
以便你能端到端运行它，看看“完成”是什么样子。这只是众多可行答案中的一种，
所以你的答案可能不同。尽情探索吧！"""

import asyncio

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from models import model


# TODO 1 已填写
def build_turns() -> list[str]:
    return [
        "我正计划四月份去日本旅行两周，从东京出发。",
        "我的总预算是 4000 美元，包含机票。",
        "2 + 2 等于多少？",
        "我想看樱花，并且至少去一个温泉小镇。",
        "意大利的首都是哪里？",
        "中间那周我打算坐火车去京都和大阪。",
        "12 乘以 12 等于多少？",
        "我已经预订了东京-京都-大阪段的 JR 铁路通票。",
        "德国的首都是哪里？",
        "快速回顾：我的总预算是多少，我说过出发的第一个城市是哪里？",
    ]


# TODO 2 已填写
MAX_INPUT_TOKENS = 3000

model.profile = {**model.profile, "max_input_tokens": MAX_INPUT_TOKENS}

agent = create_deep_agent(
    model=model,
    checkpointer=MemorySaver(),
    system_prompt="你是一位乐于助人的助手。请让每一条回复都保持一句话。",
)

THREAD = {"configurable": {"thread_id": "homework"}}
HISTORY_PATH = f"/conversation_history/{THREAD['configurable']['thread_id']}.md"


async def turn(message: str) -> str:
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config=THREAD,
    )
    return result["messages"][-1].content


async def show_state(seen_cutoffs: set) -> bool:
    """打印一轮之后的状态。如果这一轮产生了一个新的摘要事件
    （而不是仍然处于上一个事件之下），则返回 True。"""
    state = await agent.aget_state(THREAD)
    messages = state.values.get("messages", [])
    event = state.values.get("_summarization_event")
    print(f"  已存储 : {len(messages)} 条消息 (原始历史，绝不裁剪)")
    if not event:
        return False
    cutoff = event.get("cutoff_index", "?")
    is_new_event = cutoff not in seen_cutoffs
    seen_cutoffs.add(cutoff)
    tag = "  <-- 新事件" if is_new_event else ""
    print(f"  模型所见 : summary + messages[{cutoff}:]  [已摘要]{tag}")
    return is_new_event


async def main() -> None:
    turns = build_turns()
    seen_cutoffs: set = set()
    event_count = 0
    for i, message in enumerate(turns, 1):
        print(f"\n{'─' * 50}")
        print(f"第 {i} 轮  用户:  {message}")
        response = await turn(message)
        print(f"第 {i} 轮  助手: {response}")
        if await show_state(seen_cutoffs):
            event_count += 1

    print(f"\n摘要在 {len(turns)} 轮对话中触发了 {event_count} 次。")
    if event_count < 2:
        print(
            "这少于 2 次。请调低 MAX_INPUT_TOKENS，或增加更多轮/更多细节，"
            "让它在对话结束前再次触发。"
        )

    state = await agent.aget_state(THREAD)
    history_file = state.values.get("files", {}).get(HISTORY_PATH)
    if history_file:
        content = history_file["content"] if isinstance(history_file, dict) else history_file
        sections = content.count("## Summarized at")
        print(f"\n--- {HISTORY_PATH} ({sections} 个小节) ---")
        print(content)


if __name__ == "__main__":
    asyncio.run(main())
