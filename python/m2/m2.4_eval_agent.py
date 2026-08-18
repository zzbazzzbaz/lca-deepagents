from deepagents import create_deep_agent
from langchain_quickjs import CodeInterpreterMiddleware

from models import model

agent = create_deep_agent(
    model=model,
    middleware=[CodeInterpreterMiddleware()],
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "使用 eval 工具计算并返回前 15 个斐波那契数。",
            }
        ]
    }
)

print(result["messages"][-1].content)
