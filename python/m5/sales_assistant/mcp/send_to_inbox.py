# python/m5/sales_assistant/mcp/send_to_inbox.py
"""向模拟邮箱投放一条消息——"客户刚给你发了邮件"的离线替身。

不带参数运行会从 ``seeds/`` 加载随附的 RFQ 测试数据；或者
传入 --from / --subject / --body 注入自定义消息。无论哪种方式，
新消息都会进入收件箱，助手可以用 list_messages 找到它。

示例：
    uv run python mcp/send_to_inbox.py
    uv run python mcp/send_to_inbox.py --reset
    uv run python mcp/send_to_inbox.py --from "a@b.example" \
        --subject "Quote please" --body "Can I get 12 Jazz tracks?"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mail_store import _SEEDS_DIR, _empty_store, load_store, next_id, save_store


def main() -> None:
    parser = argparse.ArgumentParser(description="向模拟收件箱注入一条消息。")
    parser.add_argument("--from", dest="sender", help="发件人地址。")
    parser.add_argument("--subject", help="消息主题。")
    parser.add_argument("--body", help="消息正文。")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清空邮箱（收件箱 + 草稿）并从 seeds/ 重新装载种子数据。",
    )
    args = parser.parse_args()

    if args.reset:
        store = _empty_store()
        for seed in sorted(_SEEDS_DIR.glob("*.json")):
            store["inbox"].append(json.loads(Path(seed).read_text(encoding="utf-8")))
        save_store(store)
        print(f"邮箱已重置。收件箱现有 {len(store['inbox'])} 条消息。")
        return

    store = load_store()
    if args.sender or args.subject or args.body:
        msg = {
            "id": next_id(store["inbox"], "msg"),
            "from": args.sender or "unknown@example.com",
            "subject": args.subject or "（无主题）",
            "date": "2026-06-14T12:00:00Z",
            "body": args.body or "",
        }
        store["inbox"].append(msg)
        save_store(store)
        print(f"已注入 {msg['id']}，来自 {msg['from']!r}。")
    else:
        # 没有自定义字段：确保种子测试数据存在。
        load_store()  # 首次使用时装载种子数据
        store = load_store()
        print(f"收件箱有 {len(store['inbox'])} 条消息。使用 --reset 重新装载种子数据。")


if __name__ == "__main__":
    main()