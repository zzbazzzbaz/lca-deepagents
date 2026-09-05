# python/m5/tools/search.py
"""为 genre-researcher 子代理（每周新闻通讯）提供的网页搜索工具。

对 Tavily 的薄封装，与第 4 模块实验的精神一致。仅属于调研子代理。需要环境中存在
TAVILY_API_KEY；如果缺失，该工具根本不会注册（参见 subagents.py），因此助手其余
部分仍然可以运行。
"""

from __future__ import annotations

import os
import time

from langchain_core.tools import tool
from requests.exceptions import ConnectionError as RequestsConnectionError
from tavily import TavilyClient

_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 2


@tool
def internet_search(query: str, max_results: int = 8) -> dict:
    """搜索网页以获取近期新闻。用它来调研某个音乐类型中有什么新东西——
    新发行、著名艺术家、趋势和活动。"""
    # 每次调用都新建一个客户端，而不是共享模块级单例——newsletter-agent 的类型调研
    # 会在同一回合内并发触发多个这样的调用（LangGraph 的 ToolNode 在并行线程中汇集
    # 工具调用），而共享 TavilyClient 的连接池会被分发到远端已经关闭的池化 keep-alive
    # 套接字，表现为 ConnectionResetError。重试可以覆盖任何剩余的一次性重置。
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    last_error: RequestsConnectionError | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return client.search(query, max_results=max_results, topic="news")
        except RequestsConnectionError as e:
            last_error = e
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_RETRY_DELAY_SECONDS)
    raise last_error
