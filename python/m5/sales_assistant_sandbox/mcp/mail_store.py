# python/m5/mcp/mail_store.py
"""一个由模拟 Gmail MCP 服务器和 `send_to_inbox` 注入 CLI 共享的、基于 JSON 文件的
迷你邮箱。

这个存储故意保持简单：一个 JSON 文件，包含 ``inbox`` 和 ``drafts`` 两个列表。
它存在的意义是让课程的 Gmail 功能可以离线工作，无需 OAuth，同时呈现与真实 Gmail
MCP 服务器*相同*的工具表面（``list_messages`` / ``read_message`` /
``create_draft``）。这里没有任何 Gmail 特有的东西——它只是足以演示助手的状态。

路径都从本文件的位置解析，因此无论 MCP 子进程从哪个工作目录启动，存储都能正常工作。
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
    """读取邮箱，首次使用时从 ``seeds/`` 种子化。

    如果存储文件还不存在，``seeds/`` 中的每个 ``*.json`` 固定数据都会被加载到
    收件箱，这样新检出时就会有一条报价请求在等待。
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
    """把邮箱持久化到磁盘。"""
    with _STORE_PATH.open("w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def next_id(messages: list[dict[str, Any]], prefix: str) -> str:
    """返回下一个顺序 id，例如 ``msg-1`` / ``draft-3``。"""
    n = 1 + sum(1 for m in messages if str(m.get("id", "")).startswith(prefix))
    return f"{prefix}-{n}"
