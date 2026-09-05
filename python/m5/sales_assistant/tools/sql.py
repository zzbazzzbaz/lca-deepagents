# python/m5/tools/sql.py
"""供 chinook-analyst 子代理使用的 SQL 工具。

三个工具，内置了数据库的信任边界：

* ``query_chinook``    — 只读 SELECT。连接以 SQLite 只读 URI 模式打开，
  并且语句会被检查为单个 SELECT，因此模型生成的查询永远无法
  修改或删除任何数据。
* ``introspect_schema`` — 返回完整的 DDL，让分析师在首次使用时学习
  （然后记住）schema。
* ``add_customer``     — 唯一的写入路径：参数化的 INSERT，仅写入
  Customer 表，并限定为当前登录的销售代表。该操作受人工审批
  （human-in-the-loop）门控（在构建子代理时配置），因此没有
  明确的同意就不会插入任何行。

模型生成的 SQL 全程被视为不可信输入。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from langchain.tools import tool

# 数据库随代理放在 data/ 下。读取路径使用只读 URI，
# 因此即使一个"有创意"的 SELECT（例如 sqlite PRAGMA 写入）也无法修改文件。
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chinook.db"
_RO_URI = f"file:{DB_PATH}?mode=ro"

# 角色设定：Jane Peacock，销售支持专员。"我的客户" = SupportRepId。
REP_EMPLOYEE_ID = 3

# 只读查询中不允许出现的语句，作为只读连接之上的纵深防御。
_FORBIDDEN = (
    "insert", "update", "delete", "drop", "alter", "create",
    "replace", "truncate", "attach", "detach", "pragma", "vacuum",
)


def _read_only_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_RO_URI, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@tool
def query_chinook(sql: str) -> str:
    """对 Chinook 数据库运行只读 SQL SELECT。

    返回行对象的 JSON 数组。只允许单个 SELECT 语句——
    任何修改数据库的尝试都会被拒绝。用它进行所有查询：
    目录价格、客户的购买历史、区域指标等。
    """
    stripped = sql.strip().rstrip(";").strip()
    lowered = stripped.lower()

    if not lowered.startswith(("select", "with")):
        return json.dumps({"error": "只允许 SELECT 查询。"})
    if ";" in stripped:
        return json.dumps({"error": "只允许单个语句。"})
    if any(f" {word} " in f" {lowered} " for word in _FORBIDDEN):
        return json.dumps({"error": "查询包含被禁止的（写入）关键字。"})

    conn = _read_only_connection()
    try:
        rows = [dict(r) for r in conn.execute(stripped).fetchall()]
        return json.dumps(rows, default=str)
    except sqlite3.Error as exc:
        return json.dumps({"error": f"SQL 错误：{exc}"})
    finally:
        conn.close()


@tool
def introspect_schema() -> str:
    """返回完整的数据库 schema（每张表的 CREATE 语句）。

    调用一次即可学习 schema，然后把它记录到你的记忆中，
    这样你就不必在每次任务时重新发现它。
    """
    conn = _read_only_connection()
    try:
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return "\n\n".join(r["sql"] for r in rows if r["sql"])
    finally:
        conn.close()


@tool
def add_customer(
    first_name: str,
    last_name: str,
    email: str,
    company: str = "",
    city: str = "",
    state: str = "",
    country: str = "",
    phone: str = "",
) -> str:
    """向数据库添加一个新客户，分配给当前销售代表。

    只有在确认客户还不在系统中之后才使用（先按邮箱或姓名搜索）。
    该写入在运行前需要人工批准。成功后返回新的 CustomerId。
    """
    if not email or "@" not in email:
        return json.dumps({"error": "需要有效的邮箱地址。"})

    # 参数化插入，仅针对 Customer 表。其他表不可达，
    # 且销售代表分配由服务端强制指定，不取自模型。
    conn = sqlite3.connect(DB_PATH)
    try:
        # 防止按邮箱重复。
        existing = conn.execute(
            "SELECT CustomerId FROM Customer WHERE lower(Email) = lower(?)", (email,)
        ).fetchone()
        if existing:
            return json.dumps(
                {"error": f"邮箱为 {email} 的客户已存在 "
                          f"（CustomerId {existing[0]}）。"}
            )

        cursor = conn.execute(
            """
            INSERT INTO Customer
                (FirstName, LastName, Company, City, State, Country, Phone,
                 Email, SupportRepId)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                company or None,
                city or None,
                state or None,
                country or None,
                phone or None,
                email,
                REP_EMPLOYEE_ID,
            ),
        )
        conn.commit()
        return json.dumps(
            {"status": "created", "customer_id": cursor.lastrowid,
             "name": f"{first_name} {last_name}", "email": email}
        )
    except sqlite3.Error as exc:
        return json.dumps({"error": f"SQL 错误：{exc}"})
    finally:
        conn.close()