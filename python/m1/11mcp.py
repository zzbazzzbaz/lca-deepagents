import asyncio

from deepagents import create_deep_agent
from langchain.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from rich import print as rp

from models import model


async def main():
    client = MultiServerMCPClient(
        {
            "docs-langchain": {
                "transport": "http",
                "url": "https://docs.langchain.com/mcp",
            }
        }
    )
    tools = await client.get_tools()
    rp(tools)
    agent = create_deep_agent(model=model, tools=tools)
    result = await agent.ainvoke(
        HumanMessage(
            "Use the LangChain docs MCP tool to explain what MCP is and how LangChain uses MCP tools.使用中文回答我"
        )
    )

    print(result["messages"][-1].content)


asyncio.run(main())
