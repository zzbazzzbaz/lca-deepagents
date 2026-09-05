# python/m5/sales_assistant/agent.py
"""Chinook 销售助手。

使用本地的 FilesystemBackend（文件系统后端）、QuickJS 代码解释器进行算术
与数据准备，以及一个专用的图表工具用于渲染。

启动方式：
    ./start.sh
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_quickjs import CodeInterpreterMiddleware
from subagents import build_subagents
from tools.chart import render_pie_chart
from tools.html import markdown_to_html

from models import strong_model

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent

SYSTEM_PROMPT = (
    "你是 Jane Peacock 的销售助手。Jane Peacock 是 Chinook（一家在线音乐发行商）"
    "的销售支持专员（Sales Support Agent）。请遵循你的操作手册（从你的记忆中加载），"
    "并为每个任务使用 /skills/ 下对应的作战手册（playbook）。"
)

MAIL_SERVER = {"transport": "streamable-http", "url": "http://127.0.0.1:5002/mcp"}

_enable_search = bool(os.environ.get("TAVILY_API_KEY"))
if not _enable_search:
    logger.info("未设置 TAVILY_API_KEY —— 新闻稿研究子代理已禁用。")

_backend = FilesystemBackend(root_dir=str(HERE), virtual_mode=True)


async def make_graph():
    client = MultiServerMCPClient({"mock-mail": MAIL_SERVER})
    mail_tools = await client.get_tools()
    return create_deep_agent(
        model=strong_model,
        tools=[markdown_to_html, render_pie_chart] + mail_tools,
        system_prompt=SYSTEM_PROMPT,
        subagents=build_subagents(_backend, enable_search=_enable_search, mail_tools=mail_tools),
        skills=["/skills"],
        memory=["/AGENTS.md"],
        backend=_backend,
        middleware=[CodeInterpreterMiddleware()],
        name="chinook-sales-assistant",
    ).with_config({"recursion_limit": 50})