# python/m2/m2.2_agent.py
from pathlib import Path

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from models import model

reference_dir = Path(__file__).parent / "reference"
reference_dir.mkdir(exist_ok=True)
(reference_dir / "chinook-sales.md").write_text("""\
# Chinook 销售参考资料

你是 Chinook 数字音乐商店的销售代表。

职责：
- 查询客户账户和购买历史
- 根据流派和艺术家偏好推荐音乐
- 回答关于艺术家、专辑、曲目和发票的问题
""")

agent = create_deep_agent(
    model=model,
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/reference/": FilesystemBackend(
                root_dir=str(reference_dir),
                virtual_mode=True,
            ),
        },
    ),
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/reference/**"],
            mode="deny",
        ),
    ],
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": (
                    "读取 /reference/chinook-sales.md，然后向其中添加这条备注："
                    "'当前促销活动：本月月底前所有爵士乐专辑八折优惠。'"
                ),
            }
        ]
    },
    config={"configurable": {"thread_id": "lab-m2.2"}},
)

print(result["messages"][-1].content)
