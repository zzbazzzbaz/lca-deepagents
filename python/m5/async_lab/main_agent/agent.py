# python/m5/async_lab/main_agent/agent.py
"""M5.4 实验：主代理，把任务委托给一个独立的、专用的部署。

核心思想
本代理保持轻量：它从课程的 models.py 中获取共享模型，并依赖课程中
其他实验共用的同一套共享环境。它把所有销售分析委托给一个异步子代理
"analyst"，该子代理以*独立的*部署运行在端口 2025 上（见 ../specialized_agent）。
那个部署携带了更重的依赖（pandas），而这个代理永远不需要安装它。

运行
  先启动 ../specialized_agent（见它自己的 docstring），然后：
    cd python/m5/async_lab/main_agent
    uv run langgraph dev
在打开的 Studio 窗口中与它对话。让它同时运行两个分析（例如按地区和按产品），
然后继续聊天，它应该会立刻报告两个 task_id。之后你可以用新的指令更新其中一个
任务，取消另一个任务，并检查剩余任务的状态。
"""

from deepagents import AsyncSubAgent, create_deep_agent
from models import model

subagents = [
    AsyncSubAgent(
        name="analyst",
        description=(
            "按地区或按产品分组运行销售分析，返回每个分组的总营收和销量，"
            "按营收排名——这就是可用的全部数据，所以不要向它索取其他内容"
            "（例如平均客单价、交易笔数或增长指标）。速度慢（这是一个重量级的 "
            "pandas 任务），因此它运行在独立的部署上，而不是在本进程内运行。"
            "如果需要两种分组，就为每种分组启动一个任务。"
        ),
        graph_id="agent",
        url="http://127.0.0.1:2025",
    ),
]

# langgraph.json 指向这个模块级变量："./agent.py:graph"
graph = create_deep_agent(model=model, subagents=subagents)