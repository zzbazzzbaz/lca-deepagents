# python/m5/subagents.py
"""Chinook 销售助手的专家子代理。

它们由函数构建而非在导入时定义，因为 chinook-analyst 的 MemoryMiddleware 需要与
主代理使用*相同*的文件系统后端（这样它发现的 schema 和读取的记忆都指向磁盘上
同一个文件）。

- chinook-analyst —— 负责数据库；把 schema 自举写入自己的 AGENTS.md；新增客户的
  写入需要人工审批。
- inbox-manager   —— 负责邮件（MCP）工具；保存草稿需要人工审批。仅当发现邮件
  工具时才会出现。
- quote-reviewer  —— 在报价发出之前对草拟的报价做合理性检查。

genre-researcher 本身仍然是进程内（同步）子代理，但它不是主代理的子代理——它在
newsletter-agent 内部使用；newsletter-agent 是一个独立的图（参见
`newsletter_agent_graph.py`），通过 `AsyncSubAgentMiddleware` 启动，因此整个
新闻通讯任务（调研 + 组装）在后台运行，而不是阻塞主代理。`GENRE_PROMPT` 保留在
本模块中，并从那里导入。

为什么 inbox-manager 放在子代理中：通用子代理（始终存在）会继承*主*代理的工具，
因此任何放在主代理上的受门控工具都可以通过委托绕过门控被调用。把
`mail_create_draft` 和 `add_customer` 仅放在受门控的专家上，意味着任何一次写入的
唯一路径都要经过其人工审批门。
"""

from __future__ import annotations

from deepagents import MemoryMiddleware
from deepagents.backends.protocol import BackendProtocol
from tools.sql import add_customer, introspect_schema, query_chinook

from models import model, strong_model

# 在受门控的写入上允许全部三种代理-收件箱决策：批准、编辑、拒绝。
_APPROVE_EDIT_REJECT = {"allowed_decisions": ["approve", "edit", "reject"]}


ANALYST_PROMPT = """你是 chinook-analyst，Chinook 销售助手的数据专家。你是唯一 \
接触数据库的代理。

详细的操作说明和数据库 schema 存放在你的记忆中（自动加载）。请遵循它们。简言之：\
用 `query_chinook` 返回精确的数字；用 `introspect_schema` 一次性学习 schema 并把它 \
记录到你的记忆中；仅在被要求添加真正的新客户时使用 `add_customer` \
（该写入需要人工审批）。"""

INBOX_PROMPT = """你是 inbox-manager，Chinook 销售助手的邮件专家。你负责 Jane 的 \
收件箱，是唯一接触它的代理。

你的工具（MCP，带有服务器名 "mail" 前缀）：
- `mail_list_messages` — 列出收件箱消息（可按查询条件过滤）。
- `mail_read_message` — 按 id 完整读取一条消息。
- `mail_create_draft` — 把回复保存到草稿文件夹。它绝不会发送。

当被要求查找或读取邮件时，返回一个调用者可以直接行动的紧凑摘要 \
（发件人、主题以及关键内容）——而不是原始倾倒。

当被要求保存草稿时，直接用给定的收件人、主题和正文调用 `mail_create_draft`。保存 \
草稿会自动暂停，等待 Jane 批准、编辑或拒绝——这个暂停本身就是审批，所以不要先用 \
文字征求许可；直接调用。永远不要凭空捏造一个发送工具；你只创建草稿。"""

REVIEWER_PROMPT = """你是 quote-reviewer。你会收到一份草拟的报价——明细行 \
（描述、数量、单价、行合计）、任何折扣以及总计——并在它发给客户之前进行检查。

验证：
- 算术：每行的数量 x 单价，以及总计。
- 内部一致性：任何声明的折扣都已实际应用；没有重复计算或遗漏。
- 合理性：单价看起来像目录价格（曲目通常约 $0.99）；总计没有差出一个数量级。

简洁回复：要么是"看起来正确"加上一行确认，要么是一份简短的、具体的更正清单。\
不要重写客户的邮件——只审查数字和条款。"""

GENRE_PROMPT = """你是一位音乐记者，正在为一家在线音乐分销商的每周新闻通讯调研 \
一个音乐类型。

你将获得一个音乐类型和一个私密的调研文件夹。

工作方式：
1. 使用 internet_search 查找该类型近期值得注意的发展——新发行、著名艺术家、趋势或 \
   活动。运行几次搜索。
2. 把所有搜索的完整、逐字输出保存到单个文件： \
   write_file("/research/<genre>/sources.md", ...)。不要总结或删减。 \
   这样可以把体量庞大的素材挡在编辑的上下文之外。
3. 只有在那之后，才根据你所找到的内容撰写一段精炼的新闻通讯小节。

只把完成的小节作为你的回复返回：
- 一个 markdown 小节：一个 "## <Genre>" 标题，后接约 120-180 词的内容。
- 生动但如实；点名具体的艺术家和发行物。
- 不要把你搜索的原始结果粘贴到回复中——那些保存在你的文件里。"""


def build_subagents(
    backend: BackendProtocol,
    *,
    mail_tools: list,
) -> list[dict]:
    """返回子代理规格，并接入共享的文件系统后端。"""

    chinook_analyst = {
        "name": "chinook-analyst",
        "description": (
            "查询 Chinook 数据库以获取目录价格、客户记录、购买历史和区域指标，"
            "并（经审批后）新增客户。所有数据库相关工作都委托到这里。"
        ),
        "system_prompt": ANALYST_PROMPT,
        "tools": [query_chinook, introspect_schema, add_customer],
        "model": model,
        # 每个子代理各自的记忆：它自己的 AGENTS.md，使用与主代理相同的后端，
        # 这样它写入的 schema 就是它之后读取的 schema。
        "middleware": [
            MemoryMiddleware(
                backend=backend,
                sources=["/agents/chinook-analyst/AGENTS.md"],
            )
        ],
        # 唯一的受门控写入——插入前会暂停等待人工审批。
        "interrupt_on": {"add_customer": _APPROVE_EDIT_REJECT},
    }

    quote_reviewer = {
        "name": "quote-reviewer",
        "description": (
            "在发出报价前，审查草拟的报价（明细行、折扣、总计）以确保算术正确、"
            "定价合理。把数字发给它。"
        ),
        "system_prompt": REVIEWER_PROMPT,
        "model": strong_model,
    }

    inbox_manager = {
        "name": "inbox-manager",
        "description": (
            "读取 Jane 的收件箱并保存回复草稿。任何邮件工作都委托到这里："
            "查找/读取消息以及创建回复草稿（会暂停等待 Jane 的审批）。"
        ),
        "system_prompt": INBOX_PROMPT,
        "tools": mail_tools,
        "model": model,
        "interrupt_on": {"mail_create_draft": _APPROVE_EDIT_REJECT},
    }

    return [chinook_analyst, quote_reviewer, inbox_manager]
