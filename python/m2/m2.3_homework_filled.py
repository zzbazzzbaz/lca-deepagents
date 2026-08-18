# python/m2/m2.3_homework_filled.py
"""m2.3_homework.py 的参考版本，TODO 1-3 均已填写，你可以端到端运行
它并查看“完成”的样子。这只是其中一种可能的答案，你的答案可能会不同。
尽情探索吧！"""

from pathlib import Path
from uuid import uuid4

from deepagents import create_deep_agent
from deepagents.backends.langsmith import LangSmithSandbox
from langsmith.sandbox import SandboxClient

from models import model

# TODO 1 已填写
SYSTEM_PROMPT = (
    "你是一个数据可视化助手。当被要求运行代码时，先编写脚本到文件，"
    "然后再执行它。在导入你需要的任何包之前，先用 pip 安装它们。"
    "当被要求制作图表时，使用 matplotlib 并将其保存为 .png 文件。"
)

# TODO 2 已填写
TASK_ONE = (
    "为一个虚构的城市生成 12 个月的虚构月降雨量总和（以毫米为单位），"
    "将其保存到 rainfall.json，并打印出来。"
)
TASK_TWO = (
    "读取 rainfall.json（不要重新生成这些数字），创建一张月降雨量的"
    "柱状图。将其保存到 /chart.png。"
)

# TODO 3 已填写
CHART_PATH = "/chart.png"

client = SandboxClient()
ls_sandbox = client.create_sandbox(name=f"lca-deepagents-homework-{uuid4().hex[:8]}")
print(f"沙箱：{ls_sandbox.name}  （id：{ls_sandbox.id}）")
backend = LangSmithSandbox(sandbox=ls_sandbox)

agent = create_deep_agent(
    model=model,
    backend=backend,
    system_prompt=SYSTEM_PROMPT,
)

try:
    result = agent.invoke({"messages": [{"role": "user", "content": TASK_ONE}]})
    print("--- 任务 1 ---")
    print(result["messages"][-1].content)

    result = agent.invoke({"messages": [{"role": "user", "content": TASK_TWO}]})
    print("\n--- 任务 2（同一沙箱，应能看到任务 1 的文件）---")
    print(result["messages"][-1].content)

    chart_bytes = ls_sandbox.read(CHART_PATH)
    out_path = Path(__file__).parent / "homework_chart.png"
    out_path.write_bytes(chart_bytes)
    print(f"图表已保存到 {out_path}")
finally:
    client.delete_sandbox(ls_sandbox.name)
