# python/m5/sales_assistant_sandbox/newsletter_agent_graph.py
"""newsletter-agent：一个独立的图，作为异步子代理启动。

它在 langgraph.json 中注册为独立的条目，这样主代理的 `AsyncSubAgentMiddleware`
可以通过 LangGraph SDK 启动它并立即返回，而不是阻塞在进程内子代理调用上。

与早期的设计不同（参见 git 历史：genre_researcher_graph.py），这个图自己完成整个
新闻通讯任务——调研每一个类型并组装完成后的 HTML——而不是作为主代理必须回收的
四个并行异步启动之一。在内部，它通过普通的、同步的方式（`task` 工具，与主代理其他
专家使用的机制相同）委托给 genre-researcher 子代理：这些调用在这个图自己的单次运行内、
进程内并行发生，因此跨线程没有任何需要回收的东西。

这里没有完成通知中间件（参见 git 历史：completion_notifier.py）——主代理以普通方式
得知该任务完成：在下一次被问到时检查 `check_async_task`/`list_async_tasks`，而不是
被一次跨线程的运行唤醒。正是这一点使得这个图可以是一个普通的静态对象，而不是
按运行生成的异步工厂。

存储：一个由本次运行自己的 thread_id 做命名空间的 `StoreBackend`，通过命名空间
lambda 内的 `get_config()` 惰性解析——只在真实运行期间后端真正执行存储操作时才被
调用，而不是在构建图时调用，因此构建这个图不需要 factory/`config` 参数。每次
`start_async_task` 调用都会在这里创建一个全新的线程，所以该 thread_id 已经是一个
唯一、无冲突的命名空间——无需跨图转发 ID。省略 `store=` 会在运行时解析为
`get_store()`，也就是主图使用的同一个 store 实例（两个图共享一次部署）。
genre-researcher 子代理继承这同一个后端（子代理继承其父代理的后端，除非它们自己
设置），因此它的 `/research/<genre>/sources.md` 转储也会落到本次运行自己的
命名空间中。
"""

from __future__ import annotations

import os

from deepagents import create_deep_agent
from deepagents.backends.store import StoreBackend
from langgraph.config import get_config
from subagents import GENRE_PROMPT
from tools.html import markdown_to_html

from models import model, strong_model

# langgraph 平台总会导入此模块（它是 langgraph.json 中注册的图），无论主代理
# 是否为其暴露启动工具——所以导入 tools.search（在导入时用 TAVILY_API_KEY 实例化
# Tavily 客户端）在这里也必须保持条件导入，与 agent.py 自身的 `_enable_search`
# 守卫保持一致，尽管这里已经没有工厂函数体可以推迟导入。
_enable_search = bool(os.environ.get("TAVILY_API_KEY"))
if _enable_search:
    from tools.search import internet_search

    _genre_researcher_tools = [internet_search]
else:
    _genre_researcher_tools = []

NEWSLETTER_AGENT_PROMPT = """你负责组装 Chinook 的每周客户新闻通讯 "This Week in \
Music"。你在后台运行——销售助手已经告诉 Jane 你正在工作，并且一完成就会把最终结果 \
交给她。

你会获得一个要覆盖的音乐类型列表。对于每个类型，委托给 genre-researcher 子代理——\
每个类型调用一次，全部在同一回合内完成，这样调研就会并行进行——并收集它返回的小节。

一旦每个 genre-researcher 调用都已返回：
1. 用成功的小节组装成一份 Markdown 文档：一个 "# This Week in Music" 标题、一句 \
   引言，然后按给定顺序排列每个类型的小节。如果某个类型的调研失败了，跳过它并加 \
   一行简短说明指出哪个（些）类型本周未能完成——不要留下看起来未完成的新闻通讯，\
   也不要默默隐瞒有内容缺失这一事实。如果所有类型都失败了，就完全不要产出新闻通讯\
   ——只回复一句朴素的句子说明本周每个类型的调研都失败了，然后就此打住。
2. 对组装好的 Markdown 调用 `markdown_to_html`。

回复时只带工具返回的 HTML——前后都不要有别的，也不要任何评论。你的回复会逐字直接 \
写入一个文件；你在 HTML 周围添加的任何多余句子最终也会落到那个文件里。"""

_genre_researcher = {
    "name": "genre-researcher",
    "description": (
        "调研一个音乐类型，并围绕其中有什么新东西撰写一段新闻通讯小节。"
        "每个类型调用一次，并行进行。"
    ),
    "system_prompt": GENRE_PROMPT,
    "tools": _genre_researcher_tools,
    "model": model,
}

_backend = StoreBackend(
    namespace=lambda rt: (get_config()["configurable"]["thread_id"], "research")
)

graph = create_deep_agent(
    model=strong_model,
    tools=[markdown_to_html],
    system_prompt=NEWSLETTER_AGENT_PROMPT,
    subagents=[_genre_researcher],
    backend=_backend,
    name="newsletter-agent",
)
