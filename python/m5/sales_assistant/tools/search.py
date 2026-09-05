# python/m5/tools/search.py
"""供 genre-researcher 子代理（周报）使用的网络搜索工具。

对 Tavily 的轻量封装，与第 4 模块实验的精神相同。只属于
研究子代理。需要环境中有 TAVILY_API_KEY；如果没有，
该工具就不会被注册（见 subagents.py），因此助手的其余
部分仍然可以运行。
"""

from __future__ import annotations

import os

from langchain_core.tools import tool
from tavily import TavilyClient

_tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


@tool
def internet_search(query: str, max_results: int = 8) -> dict:
    """搜索网络获取近期新闻。用它来研究音乐流派的最新动态——
    新发行、知名艺人、趋势和事件。"""
    return _tavily.search(query, max_results=max_results, topic="news")