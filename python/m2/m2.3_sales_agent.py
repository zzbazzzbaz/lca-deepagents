from pathlib import Path
from uuid import uuid4

from deepagents import create_deep_agent
from deepagents.backends.langsmith import LangSmithSandbox
from langsmith.sandbox import SandboxClient

from models import model

DB_PATH = Path(__file__).resolve().parent / "chinook.db"

client = SandboxClient()
ls_sandbox = client.create_sandbox(name=f"lca-deepagents-lab-{uuid4().hex[:8]}")
print(f"沙箱：{ls_sandbox.name}  （id：{ls_sandbox.id}）")

backend = LangSmithSandbox(sandbox=ls_sandbox)

with open(DB_PATH, "rb") as f:
    upload_results = backend.upload_files([("/chinook.db", f.read())])

for upload_result in upload_results:
    if upload_result.error:
        raise RuntimeError(
            f"Failed to upload {upload_result.path}: {upload_result.error}"
        )

agent = create_deep_agent(
    model=model,
    backend=backend,
    system_prompt=(
        "你是一位销售数据分析师，可以访问位于 /chinook.db 的 Chinook 音乐商店数据库。"
        "使用 sqlite3 和 matplotlib 结合图表回答问题。"
        "在导入任何包之前，先用 pip 安装你需要的包。"
        "当被要求生成图表时，编写一个 Python 脚本，执行它，并确认"
        "输出文件已创建。"
    ),
)

try:
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "查询位于 /chinook.db 的 Chinook 数据库，计算各流派的"
                        "总收入。创建一张清晰的环形图，展示每个流派在总销售额"
                        "中所占的份额。将任何单独占总收入不足 3% 的流派合并到"
                        "一个“其他”（Other）扇区中。为每个扇区标注流派名称和百分比。"
                        "使用视觉上区分度高的配色方案，中间留出白色空心圆，"
                        "并确保任何标签之间或标签与标题之间都不重叠。"
                        "为标题留出足够的上方内边距，使其完全可见。"
                        "将图表保存到 /genre_revenue.png。"
                    ),
                }
            ]
        }
    )
    print(result["messages"][-1].content)

    print("=" * 50)

    png_bytes = ls_sandbox.read("/genre_revenue.png")
    out_path = Path(__file__).parent / "genre_revenue.png"
    out_path.write_bytes(png_bytes)
    print(f"图表已保存到 {out_path}")

finally:
    client.delete_sandbox(ls_sandbox.name)
