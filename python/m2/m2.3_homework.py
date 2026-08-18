# python/m2/m2.3_homework.py
"""M2.3 作业：在你自己的沙箱中证明持久化。

核心思路
实验 1 为单个固定任务（编写并运行一个斐波那契脚本）配置了一个沙箱化的
编码助手。本作业要求你为同一个沙箱挑选你自己的一对任务，一个接一个地运行，
这样你就能看到沙箱的文件系统在两次 invoke() 调用之间得以保留，而不是每次
都重置。TASK_TWO 会读取 TASK_ONE 保存的数据，并将其转换为 matplotlib 图表，
然后你以与实验 2 读取其图表相同的方式，从沙箱中读回该图表。

你要填写的内容
  TODO 1：编写一条系统提示词，描述你想要的编码助手类型（一个角色、
    一组工作规则，任何你喜欢的内容），只要它告诉代理在运行代码之前先
    将代码写入文件（与实验 1 使用的模式相同），并在需要图表时使用
    matplotlib 即可。
  TODO 2：为同一个代理/沙箱编写两条任务消息。TASK_ONE 应让代理生成或
    计算一些数值数据，并将其保存到文件中。TASK_TWO 必须读取该文件
    （不要重新生成数据），并使用 matplotlib 绘制图表，将图片保存到你选择
    的沙箱路径，并明确告诉代理。
  TODO 3：将 CHART_PATH 设置为你在 TASK_TWO 中告诉代理保存图表的那个确切
    沙箱路径，以便之后可以读回该图表。

运行方式
  cd python
  uv run ./m2/m2.3_homework.py
  open m2/homework_chart.png
"""

from pathlib import Path
from uuid import uuid4

from deepagents import create_deep_agent
from deepagents.backends.langsmith import LangSmithSandbox
from langsmith.sandbox import SandboxClient

from models import model

# ════════════════════════════════════════════════════════════════════════
# TODO 1：为你的沙箱化数据/图表助手编写一条系统提示词。
#
# 要求：
#   - 为它设定一个角色（数据分析师、科学家，任何适合你数据的角色）。
#   - 告诉它在运行代码之前先将代码写入文件（与实验 1 使用的模式相同）。
#   - 告诉它在导入任何包之前先用 pip 安装它所需的包（与实验 2 使用的
#     模式相同）——matplotlib 并非预装。
#   - 告诉它在被要求构建图表时使用 matplotlib。
#
# 示例（删除这段，写你自己的）：
#   SYSTEM_PROMPT = (
#       "你是一个数据可视化助手。当被要求运行代码时，先编写脚本到文件，"
#       "然后再执行它。在导入你需要的任何包之前，先用 pip 安装它们。"
#       "当被要求制作图表时，使用 matplotlib 并将其保存为 .png 文件。"
#   )
# ════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = None  # TODO 1：替换为你自己的系统提示词


# ════════════════════════════════════════════════════════════════════════
# TODO 2：编写两个共享沙箱状态的任务。
#
# TASK_ONE：让代理生成或计算一些数值数据（虚构的或计算得出的），并将其
#   保存到一个文件中。
# TASK_TWO：一个 SEPARATE（独立的）请求，稍后发送给同一个代理，它读取
#   TASK_ONE 的文件（不重新生成数据），并使用 matplotlib 绘制图表，将图片
#   保存到你选择并明确说明的路径（例如“将图表保存到 /chart.png”），以便
#   TODO 3 可以读回它。不要让 TASK_TWO 自己重新生成数据，那样即使没有持久化
#   沙箱也能工作，也就无法证明任何东西。
#
# 示例（删除这段，写你自己的）：
#   TASK_ONE = (
#       "为一个虚构的城市生成 12 个月的虚构月降雨量总和（以毫米为单位），"
#       "将其保存到 rainfall.json，并打印出来。"
#   )
#   TASK_TWO = (
#       "读取 rainfall.json（不要重新生成这些数字），创建一张月降雨量的"
#       "柱状图。将其保存到 /chart.png。"
#   )
# ════════════════════════════════════════════════════════════════════════

TASK_ONE = None  # TODO 2：替换为你的第一个任务消息
TASK_TWO = None  # TODO 2：替换为对 TASK_ONE 的文件绘制图表的第二个任务


# ════════════════════════════════════════════════════════════════════════
# TODO 3：将 CHART_PATH 指向 TASK_TWO 保存图表的位置。
#
# 这必须与你告诉代理在 TASK_TWO 中使用的确切沙箱路径一致。它用于下面从
# 沙箱中读回图表并保存到本地，方式与实验 2 读回 /genre_revenue.png 相同。
# ════════════════════════════════════════════════════════════════════════

CHART_PATH = None  # TODO 3：替换为 TASK_TWO 中使用的沙箱路径

if SYSTEM_PROMPT is None:
    raise NotImplementedError("TODO 1：见上方注释块")
if TASK_ONE is None or TASK_TWO is None:
    raise NotImplementedError("TODO 2：见上方注释块")
if CHART_PATH is None:
    raise NotImplementedError("TODO 3：见上方注释块")

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
