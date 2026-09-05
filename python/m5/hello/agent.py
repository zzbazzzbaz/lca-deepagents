# python/m5/hello/agent.py
"""一个极简的深度代理（deep agent），以图（graph）的形式暴露给 `langgraph dev`。

整个代理就是：一个模型，除此之外什么都没有。本实验的重点是*部署*，
而不是代理本身——所以我们把代理做到最小，让 `langgraph dev` 通过 HTTP 提供服务。
"""

from deepagents import create_deep_agent

from models import model

# `langgraph.json` 指向这个模块级变量："./agent.py:graph"。
graph = create_deep_agent(model=model)