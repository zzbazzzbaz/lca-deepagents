# python/m2/m2.2_homework.py
"""M2.2 作业：配置你自己的文件系统后端。

核心思路
本实验配置了一套固定的设置：一个 CompositeBackend 将单个参考文件
路由到本地磁盘，并附带一条拒绝所有写入的权限规则。本作业要求你自行
挑选一个小型的基于文件的任务，并按照你喜欢的方式为它配置后端：
StateBackend、FilesystemBackend，或两者混合的 CompositeBackend。
这里没有唯一正确的后端或主题，这正是本作业的意义所在。做这份作业的
两个学生最终可能会得到完全不同的配置。

你要填写的内容
  TODO 1：为一个小型文本文件挑选一个主题（装箱清单、日记、食谱盒、
    会议记录等都可以），用与实验预填充 reference/chinook-sales.md
    相同的方式，为它写入一些初始内容，并为代理配置你喜欢的任意后端。
  TODO 2：编写一条任务消息，让代理读取你的文件，然后以某种方式写入
    或编辑它，并且（可选）添加一条或多条 FilesystemPermission 规则，
    以改变代理对该文件被允许执行的操作。

运行方式
  cd python
  uv run ./m2/m2.2_homework.py
"""

from pathlib import Path

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from models import model


# ════════════════════════════════════════════════════════════════════════
# TODO 1：为你的主题配置一个后端。
#
# 要求：
#   - 挑选一个小型的基于文件的任务：装箱清单、日记、食谱盒、
#     会议记录，任何适合你主题的内容都可以。
#   - 创建带有一些初始内容的种子文件（或多个文件），方式与实验
#     预填充 reference/chinook-sales.md 相同。
#   - 配置你喜欢的任意后端：StateBackend()、FilesystemBackend()，
#     或在它们之间进行路由的 CompositeBackend()。不必与实验的设置一致。
#
# 示例结构（删除这段，写你自己的）：
#   my_dir = Path(__file__).parent / "my_files"
#   my_dir.mkdir(exist_ok=True)
#   (my_dir / "notes.md").write_text("...")
#   backend = FilesystemBackend(root_dir=str(my_dir), virtual_mode=True)
# ════════════════════════════════════════════════════════════════════════
file_dir = Path(__file__).parent / "gqt_files"
file_dir.mkdir(exist_ok=True)
(file_dir / "1.md").write_text("哈哈哈哈，gqt留")
backend = FilesystemBackend(root_dir=file_dir, virtual_mode=True)


# ════════════════════════════════════════════════════════════════════════
# TODO 2：编写任务，并可选地编写一条权限规则。
#
# 编写一条让代理读取你的文件、然后写入或编辑它的用户消息。如果你想演示
# 权限，可以在下面的 permissions 列表中添加一条或多条 FilesystemPermission
# 规则。将列表留空并完全跳过权限也是一种有效的选择。
# ════════════════════════════════════════════════════════════════════════
TASK = (
    "1.md中记录了什么？在里面添加一句“hhh langchain留。如果没有权限写入1.md，新建一个md文档写入并命名为8.md"  # TODO 2：替换为你自己的任务消息
)
permissions: list[FilesystemPermission] = [
    FilesystemPermission(operations=["write"], paths=["/1.md"], mode="deny"),
    FilesystemPermission(operations=["write"], paths=["/*.md"], mode="allow"),
]

if backend is None:
    raise NotImplementedError("TODO 1：见上方注释块")
if TASK is None:
    raise NotImplementedError("TODO 2：见上方注释块")

agent = create_deep_agent(
    model=model,
    backend=backend,
    permissions=permissions,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": TASK}]},
    config={"configurable": {"thread_id": "homework-m2.2"}},
)

print(result["messages"][-1].content)
print("=" * 50)
print((file_dir / "1.md").read_text())
print("=" * 50)
print((file_dir / "8.md").read_text())