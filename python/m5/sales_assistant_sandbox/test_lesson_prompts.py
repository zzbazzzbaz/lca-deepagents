# python/m5/sales_assistant/test_lesson_prompts.py
"""针对 m5.3-the-sales-assistant.md 中三个课程提示词的端到端测试。

在两个服务都启动后运行：
    uv run python test_lesson_prompts.py

或通过 start.sh（它会启动邮件服务器 + langgraph dev），然后在第二个终端：
    uv run python test_lesson_prompts.py
"""

from __future__ import annotations

import asyncio
import textwrap

from langgraph_sdk import get_client

API_URL = "http://127.0.0.1:2024"

PROMPTS = [
    (
        "Territory report",
        "我的客户业务情况如何？给我一份区域报告。",
    ),
    (
        "Weekly newsletter",
        '写一下本周的 "This Week in Music" 新闻通讯。',
    ),
    (
        "Process RFQ",
        "检查收件箱中是否有报价请求并处理它们。",
    ),
]


def _last_ai_text(messages: list) -> str:
    """返回最后一条 AI 消息的文本。"""
    for msg in reversed(messages):
        if msg.get("type") == "ai":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text"]
                return "\n".join(parts)
    return "(未找到 AI 消息)"


async def run_prompt(client, label: str, prompt: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"提示词：{prompt}\n")

    # 在 RFQ 测试前重置邮件存储，确保有一条消息可以处理。
    if label == "Process RFQ":
        import subprocess
        subprocess.run(
            ["uv", "run", "python", "mcp/send_to_inbox.py", "--reset"],
            capture_output=True,
        )
        print("（收件箱已重置）\n")

    thread = await client.threads.create()
    run = await client.runs.create(
        thread_id=thread["thread_id"],
        assistant_id="agent",
        input={"messages": [{"role": "user", "content": prompt}]},
    )

    # 轮询直到完成，并处理中断（例如草稿审批门）。
    interrupt_count = 0
    while True:
        await client.runs.join(thread["thread_id"], run["run_id"])
        state = await client.threads.get_state(thread["thread_id"])

        # 只有当图因中断而暂停时，state["next"] 才非空。
        interrupted = bool(state.get("next"))

        if not interrupted or interrupt_count >= 3:
            break

        # 自动批准中断（对应学生点击"批准"）。
        interrupt_count += 1
        tasks = state.get("tasks", [])
        interrupt_info = [
            i
            for t in tasks
            for i in (t.get("interrupts") or [])
        ]
        print(f"  [中断 #{interrupt_count}] 自动批准："
              f"{str(interrupt_info[0].get('value', ''))[:80] if interrupt_info else '?'}")

        run = await client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id="agent",
            command={"resume": {"decisions": [{"type": "approve"}]}},
        )

    messages = state["values"].get("messages", [])
    reply = _last_ai_text(messages)
    print(textwrap.fill(reply, width=72, subsequent_indent="  ") if reply else "（空）")
    print(f"\n[共 {len(messages)} 条消息，处理了 {interrupt_count} 个中断]")


async def main() -> None:
    client = get_client(url=API_URL)

    # 快速健康检查。
    try:
        await client.assistants.search()
    except Exception as exc:
        print(f"错误：无法访问 {API_URL} 上的 langgraph dev — {exc}")
        print("请先用 ./start.sh 启动它。")
        return

    for label, prompt in PROMPTS:
        await run_prompt(client, label, prompt)

    print(f"\n{'=' * 60}")
    print("  全部三个提示词已完成。")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
