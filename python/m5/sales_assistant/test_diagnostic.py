# python/m5/sales_assistant/test_diagnostic.py
"""Chinook 销售助手的分层诊断测试。

按顺序运行所有能力层并打印摘要。先启动两个服务，
然后在第二个终端中运行：

    ./start.sh                          # 终端 1
    uv run python test_diagnostic.py    # 终端 2
"""

from __future__ import annotations

import asyncio
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langgraph_sdk import get_client

# 加载与 langgraph.json 指向的同一个 .env。
load_dotenv(Path(__file__).parent / "../../.env", override=True)

API_URL = "http://127.0.0.1:2024"
Status = Literal["PASS", "FAIL", "SKIP"]


# ---------------------------------------------------------------------------
# 结果容器
# ---------------------------------------------------------------------------

@dataclass
class Result:
    label: str
    status: Status
    detail: str = ""
    note: str = ""  # 摘要中为 SKIP 显示的内容


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _last_ai_text(messages: list) -> str:
    for msg in reversed(messages):
        if msg.get("type") == "ai":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join(
                    b["text"] for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
    return ""


async def _ask(client, prompt: str) -> tuple[str, list]:
    thread = await client.threads.create()
    _, messages = await _ask_in_thread(client, thread["thread_id"], prompt)
    return _last_ai_text(messages), messages


async def _ask_in_thread(client, thread_id: str, prompt: str) -> tuple[str, list]:
    """向现有线程发送后续消息，每 5 秒打印一个点。"""
    run = await client.runs.create(
        thread_id=thread_id,
        assistant_id=_assistant_id,
        input={"messages": [{"role": "user", "content": prompt}]},
    )
    # 手动轮询，以便在等待时打印进度点。
    while True:
        state = await client.runs.get(thread_id, run["run_id"])
        if state["status"] in ("success", "error", "timeout"):
            break
        print(".", end="", flush=True)
        await asyncio.sleep(5)
    state = await client.threads.get_state(thread_id)
    messages = state["values"].get("messages", [])
    return _last_ai_text(messages), messages


def _tool_outputs(messages: list, tool_name: str) -> list[str]:
    return [
        m.get("content", "")
        for m in messages
        if m.get("type") == "tool" and m.get("name") == tool_name
    ]


OUTPUTS_DIR = Path(__file__).parent / "outputs"

_assistant_id: str = "agent"


def _reset_inbox() -> None:
    subprocess.run(
        ["uv", "run", "python", "mcp/send_to_inbox.py", "--reset"],
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

async def test_server_reachable(client) -> Result:
    label = "LangGraph 服务器——端口 2024 可达"
    print(f"  运行中：{label}...", end=" ", flush=True)
    try:
        await client.assistants.search()
        print("done")
        return Result(label, "PASS")
    except Exception as exc:
        print("done")
        return Result(label, "FAIL",
                      f"{exc}——./start.sh 是否在运行？")


async def test_hello(client) -> Result:
    label = "问候——LLM 连通性"
    print(f"  运行中：{label}...", end=" ", flush=True)
    try:
        reply, _ = await _ask(client, "你好！请用一句话打个招呼。")
        if reply:
            print("done")
            return Result(label, "PASS", textwrap.shorten(reply, 80))
        print("done")
        return Result(label, "FAIL", "（空回复）")
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


async def test_agents_md(client) -> Result:
    label = "AGENTS.md——记忆文件已加载"
    print(f"  运行中：{label}...", end=" ", flush=True)
    try:
        reply, _ = await _ask(
            client,
            "复述你的操作手册中的诊断标记。"
            "它以斜体文本出现在文件顶部附近。",
        )
        passed = "CHINOOK-READY" in reply
        print("done")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


async def test_skills_loaded(client) -> Result:
    label = "skills/——作战手册可读取"
    print(f"  运行中：{label}...", end=" ", flush=True)
    try:
        reply, _ = await _ask(
            client,
            "你有哪些任务作战手册（playbook）或技能可用？列出它们的名字。",
        )
        keywords = ["rfq", "quote", "newsletter", "territory"]
        passed = any(kw in reply.lower() for kw in keywords)
        print("done")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


async def test_chinook_analyst(client) -> Result:
    label = "chinook-analyst——数据库查询"
    print(f"  运行中：{label}...", end=" ", flush=True)
    try:
        reply, _ = await _ask(client, "Chinook 数据库里有多少首曲目？")
        passed = "3503" in reply or "3,503" in reply
        print("done")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


async def test_code_interpreter(client) -> Result:
    label = "代码解释器——精确算术"
    print(f"  运行中：{label}...", end=" ", flush=True)
    try:
        reply, _ = await _ask(
            client,
            "用代码解释器计算：37 首曲目，每首 0.99 美元。"
            "精确的总价是多少？",
        )
        passed = "36.63" in reply
        print("done")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


async def test_mail_tool_names(client) -> Result:
    label = "inbox-manager——MCP 工具名发现正确"
    print(f"  运行中：{label}...", end=" ", flush=True)
    try:
        from agent import MAIL_SERVER
        from langchain_mcp_adapters.client import MultiServerMCPClient

        mcp_client = MultiServerMCPClient({"mock-mail": MAIL_SERVER})
        tools = await mcp_client.get_tools()
        names = {t.name for t in tools}
        expected = {"mail_list_messages", "mail_read_message", "mail_create_draft"}
        missing = expected - names
        passed = not missing
        detail = f"已发现：{sorted(names)}" if passed else f"缺失：{sorted(missing)}"
        print("done")
        return Result(label, "PASS" if passed else "FAIL", detail)
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


async def test_inbox_manager(client) -> Result:
    label = "inbox-manager——邮件 MCP 工具调用"
    print(f"  运行中：{label}...", end=" ", flush=True)
    _reset_inbox()
    try:
        reply, _ = await _ask(client, "我的收件箱里有什么消息吗？")
        passed = "morgan" in reply.lower() or "message" in reply.lower()
        print("done")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


async def test_hitl_interrupt(client) -> Result:
    label = "人工审批（human-in-the-loop）——草稿触发中断"
    print(f"  运行中：{label}...", end=" ", flush=True)
    try:
        thread = await client.threads.create()
        run = await client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id=_assistant_id,
            input={"messages": [{"role": "user", "content":
                "起草一封给 Morgan Vale 的邮件的回复，说我们会在 24 小时内"
                "回复他们。保存草稿。"
            }]},
        )
        await client.runs.join(thread["thread_id"], run["run_id"])
        state = await client.threads.get_state(thread["thread_id"])
        tasks = state.get("tasks", [])
        interrupted = any(t.get("interrupts") for t in tasks if isinstance(t, dict))
        print("done")
        return Result(label, "PASS" if interrupted else "FAIL",
                      "已触发中断" if interrupted else "运行完成，无中断")
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


async def test_render_pie_chart(client) -> Result:
    label = "render_pie_chart——流派收入图表落入 outputs/"
    print(f"  运行中：{label}...", end=" ", flush=True)
    target = OUTPUTS_DIR / "diag_genre_revenue.png"
    target.unlink(missing_ok=True)
    try:
        thread = await client.threads.create()
        _, messages = await _ask_in_thread(
            client, thread["thread_id"],
            "查询 Chinook 数据库，按流派统计总收入（前 5 大流派）。"
            "调用 render_pie_chart 将饼图保存为 diag_genre_revenue.png。",
        )
        tool_outs = _tool_outputs(messages, "render_pie_chart")
        passed = target.exists() and target.stat().st_size > 0 and bool(tool_outs)
        detail = (f"{target.stat().st_size:,} 字节" if target.exists()
                  else f"文件缺失；render_pie_chart 返回了：{tool_outs}")
        print("done")
        return Result(label, "PASS" if passed else "FAIL", detail)
    except Exception as exc:
        print("done")
        return Result(label, "FAIL", str(exc))


# ---------------------------------------------------------------------------
# 运行器
# ---------------------------------------------------------------------------

TESTS = [
    test_server_reachable,
    test_hello,
    test_agents_md,
    test_skills_loaded,
    test_chinook_analyst,
    test_code_interpreter,
    test_mail_tool_names,
    test_inbox_manager,
    test_hitl_interrupt,
    test_render_pie_chart,
]


async def main() -> None:
    client = get_client(url=API_URL)

    print(f"\nChinook 销售助手——诊断\n{'─' * 42}\n")

    results: list[Result] = []

    for test_fn in TESTS:
        result = await test_fn(client)
        results.append(result)

        # 如果服务器不可达则立即停止——其他所有测试也都会失败。
        if test_fn is test_server_reachable and result.status == "FAIL":
            print("  （服务器不可达——跳过其余测试）")
            break

    # 摘要
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")

    print(f"\n{'─' * 42}")
    print("摘要\n")
    icons = {"PASS": "✓", "FAIL": "✗", "SKIP": "–"}
    for r in results:
        icon = icons[r.status]
        print(f"  {icon}  {r.label}")
        if r.status == "FAIL" and r.detail:
            print(f"       {textwrap.shorten(r.detail, 72)}")
        if r.status == "SKIP" and r.note:
            print(f"       ({r.note})")

    totals = f"{passed} 通过"
    if failed:
        totals += f"，{failed} 失败"
    if skipped:
        totals += f"，{skipped} 跳过"
    print(f"\n{totals}")
    print(f"{'─' * 42}\n")


if __name__ == "__main__":
    asyncio.run(main())