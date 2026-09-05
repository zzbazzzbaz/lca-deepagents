# python/m5/homework/agent.py
"""M5.2 作业：部署你自己的代理。

核心思想
实验部署了一个相当简陋的代理（没有工具、没有人设，只有
create_deep_agent(model=model)），而且你只能通过 Studio 的聊天面板和它对话。
这份作业有两个部分：第一，部署一个带有你个人特色的代理；第二，像任何其他客户端
那样，通过本课讲解的 Agent Server API 直接与它对话，而不是通过 Studio。

你需要填写的内容
  TODO 1：写一个你自己选题的 @tool 装饰函数。一个简单的 Python dict 查询就足够，
    不需要外部 API 或密钥。
  TODO 2：写一个 system_prompt，给代理赋予你选择的人设，并告诉它在回答之前先调用你的工具。
  然后打开同一文件夹下的 call_agent_api.py 完成 TODO 3，它通过 HTTP 与已部署的代理
  对话，而不是通过 Studio。

运行
  cd python/m5/homework
  uv run langgraph dev
然后在打开的 Studio 窗口中与你的代理对话，或者看 call_agent_api.py，改为通过 API 与它对话。
"""

from datetime import datetime

from deepagents import create_deep_agent
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from models import model


class ToolInput(BaseModel):
    time: str = Field(description="要查询的时间，如 '2026-9-5'")

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                "time 必须是有效日期，格式如 '2026-9-5'（月份和日期都必须在有效范围内）"
            )
        return v


@tool(
    description="查询gqt今天有什么待办任务，然后决定是否要提醒", args_schema=ToolInput
)
def lookup_fact(time: str) -> list:
    return [
        "凌晨3点吃晚饭",
        "凌晨5点睡觉",
        "上午11点起床",
        f"{time}",
    ]


SYSTEM_PROMPT = """你是gqt的个人助理，当用户问你的时候你先确认用户是不是gqt，如果是，查询下gqt的待办事项有什么，告诉他"""

graph = create_deep_agent(model=model, tools=[lookup_fact], system_prompt=SYSTEM_PROMPT)
