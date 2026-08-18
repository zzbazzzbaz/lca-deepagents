import json
import sqlite3
import uuid
from pathlib import Path

from deepagents import create_deep_agent
from langchain.tools import tool
from langchain_quickjs import CodeInterpreterMiddleware

from models import model

DB_PATH = Path(__file__).resolve().parent / "chinook.db"

TASK = (
    "我们销量最高的艺术家是谁，他们最畅销的专辑是哪张，"
    "那张专辑中被购买次数最多的曲目是哪首，"
    "以及有多少位不同的客户购买过该曲目？"
    "每个答案都依赖于上一个查询的结果。"
)

SYSTEM = (
    "你是 Chinook 数字音乐商店的销售分析师。"
    "使用 query_chinook 工具查询数据库。"
    "关键表：Artist(ArtistId, Name), Album(AlbumId, Title, ArtistId), "
    "Track(TrackId, Name, AlbumId), "
    "InvoiceLine(InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity)。"
    "收入为 InvoiceLine.UnitPrice * InvoiceLine.Quantity。"
)


@tool
def query_chinook(sql: str) -> str:
    """对 Chinook 数据库执行只读 SQL 查询。返回一个 JSON 编码的字符串。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        return json.dumps(rows)
    finally:
        conn.close()


# --- 带解释器的代理 ---
# 向系统提示词中添加额外信息，以引导代理使用解释器，并给出一些使用提示。

agent_with = create_deep_agent(
    model=model,
    tools=[query_chinook],
    middleware=[CodeInterpreterMiddleware(ptc=["query_chinook"])],
    system_prompt=(
        SYSTEM
        + " eval 工具支持编程式工具调用（Programmatic Tool Calling，PTC）：运行在 "
        " eval() 内部的 JavaScript 可以通过 tools.queryChinook() 调用 query_chinook。"
        " 对于每个答案都依赖前一个结果的依赖式查询，请优先使用单个 eval() 调用，"
        " 在 JavaScript 中串联所有查询——中间值保存在变量中，不会返回给模型。"
    ),
)

result_with = agent_with.invoke(
    {"messages": [{"role": "user", "content": TASK}]},
    config={"configurable": {"thread_id": str(uuid.uuid4())}},
)

print("=== 带解释器 ===")
print(result_with["messages"][-1].content)

# --- 不带解释器的代理 ---

agent_without = create_deep_agent(
    model=model,
    tools=[query_chinook],
    system_prompt=SYSTEM,
)

result_without = agent_without.invoke(
    {"messages": [{"role": "user", "content": TASK}]},
    config={"configurable": {"thread_id": str(uuid.uuid4())}},
)

print("\n=== 不带解释器 ===")
print(result_without["messages"][-1].content)
