# python/m5/sales_assistant_sandbox/async_research.py
"""为 newsletter-agent 异步子代理装配 AsyncSubAgentMiddleware。"""

from deepagents.middleware.async_subagents import AsyncSubAgentMiddleware


def build_async_research_middleware() -> AsyncSubAgentMiddleware:
    """将 `AsyncSubAgentMiddleware` 接入共同部署的 newsletter-agent 图，直接使用
    原版 `start_async_task` 工具而不做修改——newsletter-agent 不需要传入任何父线程
    上下文，所以启动调用中无需额外添加任何内容。"""
    return AsyncSubAgentMiddleware(
        async_subagents=[
            {
                "name": "newsletter-agent",
                "description": (
                    "在后台调研本周推荐的音乐类型并组装带样式的 HTML 新闻通讯。"
                    "每次新闻通讯请求只启动它一次，然后继续工作；稍后用 "
                    "`check_async_task`/`list_async_tasks` 再回来看它，"
                    "获取完成后的 HTML。"
                ),
                "graph_id": "newsletter-agent",
            }
        ]
    )
