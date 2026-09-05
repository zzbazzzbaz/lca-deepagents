# python/m5/sales_assistant/test_diagnostic.py
"""Chinook 销售助手的分层诊断测试。

按顺序运行所有能力层并打印摘要。先启动两个服务，然后在第二个终端运行：

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

# 加载 langgraph.json 所指向的同一个 .env。
load_dotenv(Path(__file__).parent / "../../.env")

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
    note: str = ""  # 在摘要中为 SKIP 显示


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
    """向既有线程发送一条后续消息，每 5 秒打印一个点。"""
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
    label = "LangGraph 服务器 — 可在端口 2024 访问"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        await client.assistants.search()
        print("完成")
        return Result(label, "PASS")
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL",
                      f"{exc} — ./start.sh 是否在运行？")


async def test_hello(client) -> Result:
    label = "Hello — LLM 连通性"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        reply, _ = await _ask(client, "你好！只用一句话回应一下。")
        if reply:
            print("完成")
            return Result(label, "PASS", textwrap.shorten(reply, 80))
        print("完成")
        return Result(label, "FAIL", "（空回复）")
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))


async def test_agents_md(client) -> Result:
    label = "AGENTS.md — 记忆文件已加载"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        reply, _ = await _ask(
            client,
            "复述你操作手册中的诊断令牌。它出现在文件顶部附近的斜体文本中。",
        )
        passed = "CHINOOK-READY" in reply
        print("完成")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))


async def test_skills_loaded(client) -> Result:
    label = "skills/ — 作战手册可读"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        reply, _ = await _ask(
            client,
            "你有哪些任务作战手册或技能？列出它们的名称。",
        )
        keywords = ["rfq", "quote", "newsletter", "territory"]
        passed = any(kw in reply.lower() for kw in keywords)
        print("完成")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))


async def test_chinook_analyst(client) -> Result:
    label = "chinook-analyst — 数据库查询"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        reply, _ = await _ask(client, "Chinook 数据库中有多少首曲目？")
        passed = "3503" in reply or "3,503" in reply
        print("完成")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))


async def test_code_interpreter(client) -> Result:
    label = "代码解释器 — 精确算术"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        reply, _ = await _ask(
            client,
            "用代码解释器计算：37 首曲目，每首 $0.99。精确总额是多少？",
        )
        passed = "36.63" in reply
        print("完成")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))


async def test_mail_tool_names(client) -> Result:
    label = "inbox-manager — MCP 工具名发现正确"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        from agent import MAIL_SERVER
        from langchain_mcp_adapters.client import MultiServerMCPClient

        mcp_client = MultiServerMCPClient({"mock-mail": MAIL_SERVER})
        tools = await mcp_client.get_tools()
        names = {t.name for t in tools}
        expected = {"mail_list_messages", "mail_read_message", "mail_create_draft"}
        missing = expected - names
        passed = not missing
        detail = f"found: {sorted(names)}" if passed else f"missing: {sorted(missing)}"
        print("完成")
        return Result(label, "PASS" if passed else "FAIL", detail)
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))


async def test_inbox_manager(client) -> Result:
    label = "inbox-manager — 邮件 MCP 工具调用"
    print(f"  运行：{label}…", end=" ", flush=True)
    _reset_inbox()
    try:
        reply, _ = await _ask(client, "我的收件箱里有消息吗？")
        passed = "morgan" in reply.lower() or "message" in reply.lower()
        print("完成")
        return Result(label, "PASS" if passed else "FAIL",
                      textwrap.shorten(reply, 80))
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))


async def test_hitl_interrupt(client) -> Result:
    label = "人在回路 — 草稿触发中断"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        thread = await client.threads.create()
        run = await client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id=_assistant_id,
            input={"messages": [{"role": "user", "content":
                "给 Morgan Vale 的邮件起草一封回复，说明我们会在 24 小时内回复他们。"
                "保存该草稿。"
            }]},
        )
        await client.runs.join(thread["thread_id"], run["run_id"])
        state = await client.threads.get_state(thread["thread_id"])
        tasks = state.get("tasks", [])
        interrupted = any(t.get("interrupts") for t in tasks if isinstance(t, dict))
        print("完成")
        return Result(label, "PASS" if interrupted else "FAIL",
                      "已触发中断" if interrupted else "运行完成，未触发中断")
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))



async def test_sandbox_chart(client) -> Result:
    label = "沙箱图表 — 代理编写并运行 matplotlib，图表落到沙箱 outputs/ 中"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        thread = await client.threads.create()
        _, messages = await _ask_in_thread(
            client, thread["thread_id"],
            "查询 Chinook 数据库，获取按类型统计的总营收（前 5 个类型）。"
            "编写并运行一个 Python 脚本，把饼图保存为 "
            "/outputs/diag_genre_revenue.png。",
        )
        tool_outs = _tool_outputs(messages, "execute")
        from langsmith.sandbox import ResourceNotFoundError, SandboxClient

        sandbox_client = SandboxClient()
        sandbox = await asyncio.to_thread(sandbox_client.get_sandbox, f"thread-{thread['thread_id']}")
        try:
            content = await asyncio.to_thread(sandbox.read, "/outputs/diag_genre_revenue.png")
            passed = len(content) > 0
            detail = f"{len(content):,} 字节"
        except ResourceNotFoundError:
            passed = False
            detail = f"沙箱中缺少文件；execute 返回：{tool_outs}"
        print("完成")
        return Result(label, "PASS" if passed else "FAIL", detail)
    except Exception as exc:
        print("完成")
        return Result(label, "FAIL", str(exc))


async def test_async_genre_research(client) -> Result:
    label = "newsletter-agent（异步）— 后台启动 + 再次询问后保存新闻通讯"
    print(f"  运行：{label}…", end=" ", flush=True)
    try:
        thread = await client.threads.create()
        thread_id = thread["thread_id"]

        # 固定为两个类型，这样测试就不需要先进行一次 chinook-analyst 查找，
        # 并且只触发两次真实的 Tavily 搜索，而不是四次。
        launch_reply, launch_messages = await _ask_in_thread(
            client, thread_id,
            "为正好这两个类型创建本周新闻通讯：Jazz 和 Rock。"
            "不要向 chinook-analyst 询问类型。",
        )

        # 启动回合应当恰好触发一个异步任务（整个新闻通讯作业）并停止，
        # 而不是阻塞等待它完成——要通过 SDK 来检查这一点，而不是靠消息文本推断。
        state = await client.threads.get_state(thread_id)
        tasks = state["values"].get("async_tasks", {})
        launched_non_blocking = len(tasks) == 1
        if not launched_non_blocking:
            print("完成")
            return Result(label, "FAIL",
                          f"启动回合后预期恰好 1 个异步任务，实际得到 {len(tasks)} 个：{textwrap.shorten(launch_reply, 80)}")

        # 现在已经没有完成通知器了——没有任何东西会自己唤醒这个线程，
        # 也没有任何东西调用 `check_async_task`/`list_async_tasks`，
        # 因此留在该线程自身状态中的任务缓存 `status` 字段永远不会被刷新
        #（deepagents 只会作为那些工具的副作用来刷新它——参见
        # `deepagents.middleware.async_subagents` 中的 `_afetch_live_status`）。
        # 改为直接通过 SDK 轮询子代理运行的真实实时状态，然后再显式询问线程
        # 是否就绪，这才会真正触发主代理的检查并保存回合。
        task = next(iter(tasks.values()))
        deadline = asyncio.get_event_loop().time() + 600
        run_status = task["status"]
        while asyncio.get_event_loop().time() < deadline:
            run_state = await client.runs.get(thread_id=task["thread_id"], run_id=task["run_id"])
            run_status = run_state["status"]
            if run_status in ("success", "error", "cancelled", "timeout", "interrupted"):
                break
            print(".", end="", flush=True)
            await asyncio.sleep(5)
        else:
            print("完成")
            return Result(label, "FAIL", f"任务从未达到终态：{run_status}")
        statuses = {task["task_id"]: run_status}

        _, followup_messages = await _ask_in_thread(client, thread_id, "新闻通讯准备好了吗？")

        from langsmith.sandbox import SandboxClient

        sandbox_client = SandboxClient()
        sandbox = await asyncio.to_thread(sandbox_client.get_sandbox, f"thread-{thread_id}")
        listing = await asyncio.to_thread(
            sandbox.run, "find /outputs -maxdepth 1 -type f -name 'newsletter-*.html'"
        )
        newsletter_files = [line for line in listing.stdout.splitlines() if line.strip()]

        passed = bool(newsletter_files)
        detail = f"newsletter: {newsletter_files}, task statuses: {statuses}" if passed else \
            f"follow-up 后没有新闻通讯；任务状态：{statuses}，回复：{textwrap.shorten(_last_ai_text(followup_messages), 80)}"
        print("完成")
        return Result(label, "PASS" if passed else "FAIL", detail)
    except Exception as exc:
        print("完成")
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
    test_sandbox_chart,
    test_async_genre_research,
]


async def main() -> None:
    client = get_client(url=API_URL)

    print(f"\nChinook 销售助手 — 诊断\n{'─' * 42}\n")

    results: list[Result] = []

    for test_fn in TESTS:
        result = await test_fn(client)
        results.append(result)

        # 如果服务器不可达就立即停止——其他所有测试也都会失败。
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
