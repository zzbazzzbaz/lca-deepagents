# python/m5/sales_assistant/mcp/mock_mail_server.py
"""一个本地、离线的模拟邮件 MCP 服务器。

通过 HTTP（streamable-http 传输）在端口 5002 上暴露三个工具：

    mail_list_messages(query)            -> 收件箱邮件的摘要
    mail_read_message(message_id)        -> 单条消息的完整正文
    mail_create_draft(to, subject, body) -> 把回复保存到草稿文件夹

状态是一个由 mail_store.py 管理的小型 JSON 文件。由 start.sh 在
langgraph dev 之前启动，这样 make_graph() 可以在启动时发现这些工具。
"""

from __future__ import annotations

from mail_store import load_store, next_id, save_store
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mock-mail", host="127.0.0.1", port=5002)


@mcp.tool()
def mail_list_messages(query: str = "") -> list[dict]:
    """列出收件箱中的消息。

    返回每条消息的摘要（id、发件人、主题、日期、片段）——
    而不是完整正文。用 read_message 打开某条。可选的 ``query`` 是
    不区分大小写的子串，与主题和发件人匹配，主要用来模拟
    Gmail 的搜索框；留空则列出全部。
    """
    store = load_store()
    q = query.strip().lower()
    out = []
    for m in store["inbox"]:
        haystack = f"{m.get('subject', '')} {m.get('from', '')}".lower()
        if q and q not in haystack:
            continue
        body = m.get("body", "")
        out.append(
            {
                "id": m.get("id"),
                "from": m.get("from"),
                "subject": m.get("subject"),
                "date": m.get("date"),
                "snippet": body[:140] + ("…" if len(body) > 140 else ""),
            }
        )
    return out


@mcp.tool()
def mail_read_message(message_id: str) -> dict:
    """按 id 返回完整消息（发件人、主题、日期、完整正文）。"""
    store = load_store()
    for m in store["inbox"]:
        if m.get("id") == message_id:
            return m
    return {"error": f"没有 id 为 {message_id!r} 的消息。"}


@mcp.tool()
def mail_create_draft(to: str, subject: str, body: str) -> dict:
    """把回复保存到草稿文件夹。不会发送。

    与真实 Gmail 的"创建草稿"调用一致：消息被暂存，供人工稍后
    查看和发送。在本课程中，该工具之前会运行人工审批
    （human-in-the-loop）门控，因此草稿只有在明确批准后才会写入。
    """
    store = load_store()
    draft = {
        "id": next_id(store["drafts"], "draft"),
        "to": to,
        "subject": subject,
        "body": body,
    }
    store["drafts"].append(draft)
    save_store(store)
    return {"status": "draft_saved", "draft_id": draft["id"], "to": to, "subject": subject}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")