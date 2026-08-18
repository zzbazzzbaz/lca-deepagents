# python/m2/m2.4_homework.py
"""M2.4 作业：提出你自己的问题，然后为它评分。

核心思路
实验 2 针对 Chinook 数据库提出了一个固定的、依赖式查询的问题，并让解释器
在单个 eval() 调用中把四条 SQL 查询串联在一起。本作业要求你针对该数据库提出
你自己的问题（query_chinook 和少量 JavaScript 能回答的任何问题都可以，简单
的或依赖式的都行），然后，由于本课还涉及评估代理代码生成的内容，请编写一个
你自己快速编写的 eval 检查，判断代理的回答看起来是否正确。这里没有唯一正确的
问题或评估方法，这正是本作业的意义所在。

你要填写的内容
  TODO 1：编写你自己针对 Chinook 数据库的自然语言问题（参见下方 SYSTEM 中
    的表结构提示），让解释器代理使用 eval() 和 query_chinook 来回答。
  TODO 2：编写一个小型 eval_answer(...) 函数，独立检查代理的最终回答
    看起来是否正确。你想怎么做都行：运行你自己的 SQL 查询并比较、检查
    是否包含预期的关键字或数字，或者干脆把两者并排打印出来供你自己判断。
    根据你的问题选择合适程度的严谨性即可。

运行方式
  cd python
  uv run ./m2/m2.4_homework.py
"""

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


# ════════════════════════════════════════════════════════════════════════
# TODO 1：编写你关于 Chinook 数据库的问题。
#
# 挑选任何 query_chinook 工具能回答的内容：按国家/地区统计的顶级客户、
# 哪位艺术家的专辑最多、按年份统计的平均发票总额，任何你好奇的内容。
# 带有几个依赖步骤的问题（如实验 2 那样）很适合使用 PTC，但单个查询的
# 问题也完全可以。
# ════════════════════════════════════════════════════════════════════════

TASK = None  # TODO 1：替换为你自己的问题


# ════════════════════════════════════════════════════════════════════════
# TODO 2：为代理的回答编写一个简单的 eval 检查。
#
# eval_answer(answer_text) 在代理回复后运行。独立地算出你认为的正确
# 答案（运行你自己的 SQL 查询、手工计算，都行），并将其与 answer_text
# 进行比较。打印你认为合理的任何结论；这不必是严格的通过/失败，
# 一段有理有据的打印输出就很好。
# ════════════════════════════════════════════════════════════════════════

def eval_answer(answer_text: str) -> None:
    raise NotImplementedError("TODO 2：见上方注释块")


if TASK is None:
    raise NotImplementedError("TODO 1：见上方注释块")

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
