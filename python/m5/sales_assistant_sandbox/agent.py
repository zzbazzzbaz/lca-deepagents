# python/m5/sales_assistant_sandbox/agent.py
"""Chinook 销售助手。

整个文件系统——技能、记忆，以及代理写入或运行的一切——都保存在每个线程
（per-thread）的 LangSmith 沙箱中。技能和 AGENTS.md 会在沙箱创建时从本地磁盘
一次性种子化进去。运行时代理没有任何可读或可写的本地文件系统路径，因此不可信的
执行结果没有任何途径可以桥接回本地。

图表没有专门的工具：代理用 write_file 编写 Python 脚本，再用 execute 运行它
（因为后端支持沙箱化命令执行，所以会自动添加），与运行其他任何生成的代码的方式相同。

启动方式：
    ./start.sh
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from pathlib import Path

from async_research import build_async_research_middleware
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.backends.langsmith import LangSmithSandbox
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_quickjs import CodeInterpreterMiddleware
from langgraph_sdk.runtime import ServerRuntime
from subagents import build_subagents
from tools.html import markdown_to_html

from models import strong_model

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent

SYSTEM_PROMPT = (
    "你是 Jane Peacock（Chinook 在线音乐分销商的销售支持专员）的销售助手。请遵循"
    "你的操作手册（从记忆中加载）中的说明，并为每项任务使用 /skills/ 下对应的"
    "作战手册。\n\n"
    "你的整个文件系统——技能、记忆以及你写入的一切——都位于一个隔离的沙箱内，"
    "没有独立的本地文件系统。要生成图表，请用 write_file 编写 Python 脚本，"
    "并用 execute 运行它（例如 `pip install matplotlib && python3 <script>`），"
    "并把图片保存到 /outputs/ 下。"
)

MAIL_SERVER = {"transport": "streamable-http", "url": "http://127.0.0.1:5002/mcp"}

_enable_search = bool(os.environ.get("TAVILY_API_KEY"))
if not _enable_search:
    logger.info("未设置 TAVILY_API_KEY — 新闻通讯研究子代理已禁用。")


def _lookup_or_create(name: str) -> tuple:
    """返回线程级沙箱的 (sandbox, freshly_created)。

    复用就绪的沙箱、重启已停止的沙箱、等待处于过渡状态的沙箱，或创建新沙箱——
    无论结果如何都采用相同的查找模式，因此一个线程后续的回合会落到与第一次
    相同的沙箱中。
    """
    from langsmith.sandbox import SandboxClient

    client = SandboxClient()
    existing = [s for s in client.list_sandboxes() if s.name == name]
    if existing:
        sb = existing[0]
        status = getattr(sb, "status", "ready")
        if status == "ready":
            logger.info("复用沙箱 %s", name)
            return sb, False
        if status == "stopped":
            logger.info("重启已停止的沙箱 %s", name)
            try:
                return client.start_sandbox(name, timeout=15), False
            except Exception as exc:
                raise RuntimeError(
                    "沙箱当前不可用——请稍后再试。"
                ) from exc
        logger.info("等待沙箱 %s（状态：%s）", name, status)
        try:
            return client.wait_for_sandbox(name, timeout=15), False
        except Exception as exc:
            raise RuntimeError(
                "沙箱当前不可用——请稍后再试。"
            ) from exc
    try:
        # idle_ttl_seconds 用于限制学生中途离开会话时的计算成本；delete_after_stop_seconds
        # 进一步限制，因为服务器默认值（约 14 天）远超课堂教学需要已停止沙箱保留的时间。
        sb = client.create_sandbox(
            name=name, idle_ttl_seconds=600, delete_after_stop_seconds=3600
        )
        logger.info("已创建沙箱 %s", name)
        return sb, True
    except Exception:
        # 在列出与创建之间，另一个线程已创建了它——重新查找一下
        existing = [s for s in client.list_sandboxes() if s.name == name]
        if existing:
            logger.info("复用沙箱 %s（竞争恢复）", name)
            return existing[0], False
        raise


def _seed_skills_and_memory(ls_backend: LangSmithSandbox) -> None:
    """把本地的 /skills 和 /AGENTS.md 上传到新沙箱中。"""
    files: list[tuple[str, bytes]] = [("/AGENTS.md", (HERE / "AGENTS.md").read_bytes())]
    for path in (HERE / "skills").rglob("*"):
        if path.is_file():
            files.append((f"/skills/{path.relative_to(HERE / 'skills')}", path.read_bytes()))
    results = ls_backend.upload_files(files)
    for (path, _), result in zip(files, results):
        if result.error:
            logger.warning("向沙箱种子化 %s 失败：%s", path, result.error)


async def _sandbox_backend_for_thread(thread_id: str) -> LangSmithSandbox:
    """查找（或创建）该线程的沙箱；如果沙箱是新建的，则进行种子化。"""
    sandbox, freshly_created = await asyncio.to_thread(_lookup_or_create, f"thread-{thread_id}")
    backend = LangSmithSandbox(sandbox)
    if freshly_created:
        await asyncio.to_thread(_seed_skills_and_memory, backend)
    return backend


# 线程级沙箱模式：
# https://docs.langchain.com/langsmith/graph-rebuild#context-manager-factory
#
# 该工厂接受 ServerRuntime，以便服务器能够指示自己是在处理一次实际运行
# （execution_runtime 非 None），还是在处理内省调用（get_schema、get_graph、
# assistants.read 等）。当 execution_runtime 为 None 时，我们跳过沙箱设置并回退到
# 内存后端——图拓扑相同，但既没有沙箱，也完全没有真实文件系统访问。真实的运行
# 会按 thread_id 查找各自的线程级沙箱。
@contextlib.asynccontextmanager
async def make_graph(config: RunnableConfig, runtime: ServerRuntime):
    if runtime.execution_runtime:
        thread_id = config.get("configurable", {}).get("thread_id")
        backend = await _sandbox_backend_for_thread(thread_id)
    else:
        backend = StateBackend()

    client = MultiServerMCPClient({"mock-mail": MAIL_SERVER})
    mail_tools = await client.get_tools()
    middleware = [CodeInterpreterMiddleware(ptc=["execute", "write_file"])]
    if _enable_search:
        middleware.append(build_async_research_middleware())
    yield create_deep_agent(
        model=strong_model,
        tools=[markdown_to_html] + mail_tools,
        system_prompt=SYSTEM_PROMPT,
        subagents=build_subagents(backend, mail_tools=mail_tools),
        skills=["/skills"],
        memory=["/AGENTS.md"],
        backend=backend,
        middleware=middleware,
        name="chinook-sales-assistant",
    )
