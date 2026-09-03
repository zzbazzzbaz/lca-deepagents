# python/m3/m3.1_homework.py
"""M3.1 作业：触发链式摘要（Summarization）。

核心思路
在本课中，你看到 SummarizationMiddleware 将演示对话压缩了一次，超过了 85% 的阈值。
但摘要并不会只触发一次就停止：在一段足够长的对话中，它会一而再、再而三地触发，
每次都会在“上一条摘要 + 此后新增内容”的基础上重新做摘要，
而完整的被淘汰历史会不断累积到位于 /conversation_history/{thread_id}.md 的单一后端文件中。

这份作业要求你围绕自己选定的一个主题构建一段足够长的对话，
以便至少触发两次摘要，然后确认两件事：
模型仍然能回忆出你最初那一轮里的某个细节（即便已经过多次压缩），
以及后端的历史记录文件确实累积了多个“Summarized at ...”小节，
而不是丢失了更早的那些。

你要填写的内容
  TODO 1：为你自己选定的一个主题编写你自己的用户消息列表（至少 8 条）。
    在前两轮中的某一轮里放一个重要的细节，然后再围绕该主题聊几轮，
    最后以一条要求 agent 回忆该早期细节的消息收尾。
  TODO 2：调整 model.profile["max_input_tokens"]，让摘要在你的最后一轮之前
    至少触发两次，而不是只触发一次。像本课用 700 那样，通过反复试验来调参。

运行
  cd python
  uv run ./m3/m3.1_homework.py
"""

import asyncio

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from models import model


# ════════════════════════════════════════════════════════════════════════
# TODO 1：编写你自己的多轮场景。
#
# 要求：
#   - 至少 8 条用户消息，全部围绕你选定的一个主题。
#   - 前两轮中的某一轮应陈述一个具体细节（一个数字、一个名称、一个决定）。
#   - 最后一轮应要求 agent 回忆该细节，在此之前围绕同一主题进行几轮不相关的追问。
#
# 示例结构（删除这些并编写你自己的）：
#   return [
#       "我正在计划一次两周的……旅行",
#       "我的总预算是……",
#       ...,
#       ...,
#       ...,
#       "快速回顾：我的总预算是多少？",
#   ]
# ════════════════════════════════════════════════════════════════════════

def build_turns() -> list[str]:
    """TODO 1：返回你自己的用户消息列表（至少 8 条）。"""
    return [
        "我叫gqt，我正在学langchain框架",
        "我学完了langchain框架但我还是发现不能做东西",
        "我又开始学langgraph框架",
        "发现langchain基于langgraph框架",
        "但是langgraph太低层了，我想要构建高层自主智能体",
        "于是我开始学习deepagent框架，但我一直在学习，还没有实际产出。我很沮丧",
        "话说，我叫什么？我之前都学过什么？好像太久了我忘记了，我已经活了两个世纪了",
    ]
    raise NotImplementedError("TODO 1：见上方注释块")


# ════════════════════════════════════════════════════════════════════════
# TODO 2：选择摘要触发阈值。
#
# 把 model.profile["max_input_tokens"] 调低到一个能让 SummarizationMiddleware
# 在 TODO 1 的整段对话中（以该数值的 85% 为触发点）至少触发两次、而非仅一次的值。
# 本课对 5 轮演示用了 700 并只触发一次；你的数值取决于你写了几轮、每轮多长。
# ════════════════════════════════════════════════════════════════════════

MAX_INPUT_TOKENS = 500  # TODO 2：用你选定的整数阈值替换 None

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
