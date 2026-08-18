# python/m2/m2.2_homework_filled.py
"""m2.2_homework.py 的参考版本，TODO 1 和 2 均已填写，你可以端到端运行
它并查看“完成”的样子。这只是其中一种可能的答案，你的答案可能会不同。
尽情探索吧！"""

from pathlib import Path

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend

from models import model

recipe_dir = Path(__file__).parent / "recipe_box"
recipe_dir.mkdir(exist_ok=True)
(recipe_dir / "grandmas_apple_pie.md").write_text("""\
# 奶奶的苹果派

配料：6 个苹果、1 杯糖、2 汤匙肉桂粉、双层派皮。
在 375 华氏度下烘烤 45 分钟。
""")

# TODO 1 已填写
backend = FilesystemBackend(root_dir=str(recipe_dir), virtual_mode=True)

# TODO 2 已填写
TASK = (
    "读取 /grandmas_apple_pie.md，然后创建一个名为 "
    "/weeknight_pasta.md 的新文件，其中写一道你自己的简单意大利面食谱。最后，"
    "尝试在 /grandmas_apple_pie.md 中添加一条备注：“已测试，味道很棒”。"
)
permissions = [
    FilesystemPermission(
        operations=["write"],
        paths=["/grandmas_apple_pie.md"],
        mode="deny",
    ),
]

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
