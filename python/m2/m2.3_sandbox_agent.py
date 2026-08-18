from uuid import uuid4

from deepagents import create_deep_agent
from deepagents.backends.langsmith import LangSmithSandbox
from langsmith.sandbox import SandboxClient

from models import model

client = SandboxClient()
ls_sandbox = client.create_sandbox(name=f"lca-deepagents-lab-{uuid4().hex[:8]}")
print(f"沙箱：{ls_sandbox.name}  （id：{ls_sandbox.id}）")
backend = LangSmithSandbox(sandbox=ls_sandbox)

agent = create_deep_agent(
    model=model,
    backend=backend,
    system_prompt=(
        "你是一位编码助手。当被要求运行代码时，先将脚本写入文件，"
        "然后执行它。在最终回答中展示输出结果。"
    ),
)

try:
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "编写一个打印前 15 个斐波那契数的 Python 脚本，"
                        "将其保存为 fib.py，然后运行它。"
                    ),
                }
            ]
        }
    )
    print(result["messages"][-1].content)
finally:
    client.delete_sandbox(ls_sandbox.name)
