# python/m5/async_lab/specialized_agent/agent.py
"""M5.4 实验："专用"部署。

核心思想
这是第二个独立的部署，不是共享课程环境下的一个文件夹。它有自己独立的
pyproject.toml 和模型配置，因此 pandas（下面这个分析工具需要它）只在这里
安装，永远不会装进课程中其他实验依赖的共享环境。它的 langgraph.json 也声明了
"dependencies": ["."] 而不是通常的 ["../.."]，正是这一点让隔离成为现实。

运行
  cd python/m5/async_lab/specialized_agent
  uv run langgraph dev --port 2025
让它保持运行，然后在第二个终端启动 ../main_agent。主代理通过 HTTP 在
http://127.0.0.1:2025 访问这个代理，和访问任何其他远程部署完全一样。
"""
import os
import time
from pathlib import Path

import pandas as pd
from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

SALES = pd.DataFrame(
    {
        "region": ["West", "West", "East", "East", "Central", "Central"],
        "product": ["Widget", "Gadget", "Widget", "Gadget", "Widget", "Gadget"],
        "units_sold": [1200, 850, 980, 1400, 630, 720],
        "revenue": [36000, 42500, 29400, 70000, 18900, 36000],
    }
)


@tool
def analyze_sales(group_by: str = "region") -> str:
    """运行完整的销售分析，按 "region" 或 "product" 分组，按营收从高到低排序。

    这是一个缓慢、重量级的分析任务，不适合阻塞主代理自身的模型调用。
    """
    time.sleep(20)  # 用来模拟一个真正缓慢的任务（大型 pandas 管道、模型调用等）
    key = group_by if group_by in ("region", "product") else "region"
    grouped = SALES.groupby(key)[["units_sold", "revenue"]].sum().sort_values("revenue", ascending=False)
    lines = [
        f"{name}: ${int(row['revenue']):,} revenue, {int(row['units_sold']):,} units"
        for name, row in grouped.iterrows()
    ]
    return "\n".join(lines)

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
model = init_chat_model(
    os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),  # noqa: F821
    model_provider="deepseek",
    base_url=os.environ["DEEPSEEK_BASE_URL"],
    api_key=os.environ["DEEPSEEK_API_KEY"],
    timeout=60,
    max_retries=2,
)
# langgraph.json 指向这个模块级变量："./agent.py:graph"
graph = create_deep_agent(model=model, tools=[analyze_sales])