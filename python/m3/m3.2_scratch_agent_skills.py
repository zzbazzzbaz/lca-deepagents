from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from models import model

m3_dir = Path(__file__).parent
backend = FilesystemBackend(root_dir=str(m3_dir), virtual_mode=True)

agent = create_deep_agent(
    model=model,
    name="Sales_Assistant",
    backend=backend,
    skills=["/skills"],
    system_prompt="你是一名销售助理。",
)

result = agent.invoke({"messages": [{"role": "user", "content": "对这条线索做资格认定：Acme 公司，一家 200 人的物流公司。我和他们的销售副总裁 Sarah Chen 谈过：她是决策人。他们今年为 CRM 预留了 4.5 万美元预算。主要痛点：由于管道可见性差，交易不断从指缝中溜走。他们希望解决方案在第三季度末前上线。"}]})
print(result["messages"][-1].content)
