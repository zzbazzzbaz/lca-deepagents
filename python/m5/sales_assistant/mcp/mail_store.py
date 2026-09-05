# python/m5/mcp/mail_store.py
"""由模拟 Gmail MCP 服务器和 `send_to_inbox` 注入 CLI 共享的迷你 JSON 文件邮箱。

这个存储是故意保持简单的：一个 JSON 文件，包含两个列表 ``inbox`` 和
``drafts``。它的存在让课程中的 Gmail 功能可以在离线状态下工作，
无需 OAuth，同时呈现与真实 Gmail MCP 服务器*相同*的工具面
（``list_messages`` / ``read_message`` / ``create_draft``）。这里没有任何
Gmail 特有的东西——它只是足够演示助手的少量状态。

路径根据本文件的位置解析，因此无论 MCP 子进程从哪个工作目录
启动，存储都能正常工作。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 邮箱文件位于本模块旁边，即模块自己的目录下。
_STORE_PATH = Path(__file__).resolve().parent / "mail_store.json"
_SEEDS_DIR = Path(__file__).resolve().parent / "seeds"


def _empty_store() -> dict[str, list[dict[str, Any]]]:
    return {"inbox": [], "drafts": []}


def load_store() -> dict[str, list[dict[str, Any]]]:
    """读取邮箱，首次使用时从 ``seeds/`` 装载种子数据。

    如果存储文件还不存在，``seeds/`` 中的每个 ``*.json`` 测试数据都会
    载入收件箱，这样全新检出（checkout）的代码就会有一条报价请求
    等待处理。
    """
    if _STORE_PATH.exists():
        with _STORE_PATH.open(encoding="utf-8") as f:
            return json.load(f)

    store = _empty_store()
    for seed in sorted(_SEEDS_DIR.glob("*.json")):
        with seed.open(encoding="utf-8") as f:
            store["inbox"].append(json.load(f))
    save_store(store)
    return store


def save_store(store: dict[str, list[dict[str, Any]]]) -> None:
    """将邮箱持久化到磁盘。"""
    with _STORE_PATH.open("w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def next_id(messages: list[dict[str, Any]], prefix: str) -> str:
    """返回下一个顺序 id，如 ``msg-1`` / ``draft-3``。"""
    n = 1 + sum(1 for m in messages if str(m.get("id", "")).startswith(prefix))
    return f"{prefix}-{n}"