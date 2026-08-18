# python/m2/m2.4_homework_filled.py
"""m2.4_homework.py 的参考版本，TODO 1 和 2 均已填写，你可以端到端运行
它并查看“完成”的样子。这只是其中一种可能的答案，你的答案可能会不同。
尽情探索吧！"""

import json
import sqlite3
import uuid
from pathlib import Path

from deepagents import create_deep_agent
from langchain.tools import tool
from langchain_quickjs import CodeInterpreterMiddleware

from models import model

DB_PATH = Path(__file__).resolve().parent / "chinook.db"

SYSTEM = (
    "你是 Chinook 数字音乐商店的销售分析师。"
    "使用 query_chinook 工具查询数据库。"
    "关键表：Artist(ArtistId, Name), Album(AlbumId, Title, ArtistId), "
    "Track(TrackId, Name, AlbumId, GenreId), Genre(GenreId, Name), "
    "Customer(CustomerId, FirstName, LastName, Country), "
    "Invoice(InvoiceId, CustomerId), "
    "InvoiceLine(InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity)。"
    "收入为 InvoiceLine.UnitPrice * InvoiceLine.Quantity。"
    "eval 工具支持编程式工具调用（Programmatic Tool Calling，PTC）：运行在 "
    "eval() 内部的 JavaScript 可以通过 tools.queryChinook() 调用 query_chinook。"
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


# TODO 1 已填写
TASK = (
    "哪个国家的客户贡献的总收入最高，并且来自该国家的客户中"
    "单一销量最高的曲目（按收入计算）是什么？每个答案都依赖于前一个答案。"
)


# TODO 2 已填写
def eval_answer(answer_text: str) -> None:
    """独立计算预期的顶级国家和顶级曲目，然后检查两者是否都出现在代理的回答中。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        top_country = conn.execute(
            """
            SELECT Customer.Country, SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity) AS rev
            FROM InvoiceLine
            JOIN Invoice USING(InvoiceId)
            JOIN Customer USING(CustomerId)
            GROUP BY Customer.Country
            ORDER BY rev DESC
            LIMIT 1
            """
        ).fetchone()
        top_track = conn.execute(
            """
            SELECT Track.Name, SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity) AS rev
            FROM InvoiceLine
            JOIN Invoice USING(InvoiceId)
            JOIN Customer USING(CustomerId)
            JOIN Track USING(TrackId)
            WHERE Customer.Country = ?
            GROUP BY Track.TrackId
            ORDER BY rev DESC
            LIMIT 1
            """,
            (top_country["Country"],),
        ).fetchone()
    finally:
        conn.close()

    print("\n--- 评估检查 ---")
    print(f"预期顶级国家：{top_country['Country']}")
    print(f"预期顶级曲目：{top_track['Name']}")

    checks = {
        "mentions expected country": top_country["Country"].lower() in answer_text.lower(),
        "mentions expected track": top_track["Name"].lower() in answer_text.lower(),
    }
    for label, passed in checks.items():
        print(f"  [{'通过' if passed else '未通过'}] {label}")


agent = create_deep_agent(
    model=model,
    tools=[query_chinook],
    middleware=[CodeInterpreterMiddleware(ptc=["query_chinook"])],
    system_prompt=SYSTEM,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": TASK}]},
    config={"configurable": {"thread_id": str(uuid.uuid4())}},
)

answer = result["messages"][-1].content
print(answer)
eval_answer(answer)
