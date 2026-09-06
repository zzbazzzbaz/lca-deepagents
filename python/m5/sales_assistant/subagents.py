# python/m5/subagents.py
"""Chinook 销售助手的三个专家子代理。

它们由函数构建而不是在导入时定义，因为 chinook-analyst 的
MemoryMiddleware（记忆中间件）需要与主代理使用*同一个*文件系统后端
（这样它发现的 schema 和它读取的记忆都指向磁盘上的同一个文件）。

- chinook-analyst — 负责数据库；将 schema 自举写入它自己的 AGENTS.md；
  新增客户的写入受人工审批门控。
- inbox-manager   — 负责邮件（MCP）工具；保存草稿受人工审批门控。
  仅在发现邮件工具时才存在。
- quote-reviewer  — 在报价发出前对其进行合理性检查。
- genre-researcher — 为新闻稿研究一个音乐流派（并行扇出）；
  仅在配置了网络搜索（Tavily）时才存在。

为什么 inbox-manager 要放在子代理中：通用子代理（始终存在）会继承
*主*代理的工具，因此放在主代理上的任何受门控工具都可能通过委派绕过
门控被调用。把 `mail_create_draft` 和 `add_customer` 只放在受门控的
专家子代理上，意味着任何一次写入的路径都必须经过人工审批门。
"""

from __future__ import annotations

from deepagents import FilesystemPermission, MemoryMiddleware, SubAgent
from deepagents.backends.protocol import BackendProtocol
from langchain.agents.middleware import InterruptOnConfig
from tools.sql import add_customer, introspect_schema, query_chinook

from models import model, strong_model

# 允许对受门控的写入做出"批准/编辑/拒绝"三种决策。
_APPROVE_EDIT_REJECT: InterruptOnConfig = {
    "allowed_decisions": ["approve", "edit", "reject"]
}


ANALYST_PROMPT = """你是 chinook-analyst，Chinook 销售助手的数据专家。\
你是唯一可以访问数据库的代理。

详细的操作说明和数据库 schema 都在你的记忆里（自动加载）。请遵循它们。\
简而言之：用 `query_chinook` 给出精确的数字，用 `introspect_schema` 学习一次 \
schema 并记录到你的记忆中，并且只在被要求添加真正的新客户时才使用 \
`add_customer`（该写入需要人工批准）。"""

INBOX_PROMPT = """你是 inbox-manager，Chinook 销售助手的邮件专家。\
你负责 Jane 的收件箱，是唯一可以访问它的代理。

你的工具（MCP，以服务器名 "mail" 为前缀）：
- `mail_list_messages` — 列出收件箱消息（可选地按查询条件过滤）。
- `mail_read_message` — 按 id 读取一条消息的完整内容。
- `mail_create_draft` — 将回复保存到草稿文件夹。它绝不发送邮件。

当被要求查找或阅读邮件时，返回一份调用方可以直接行动的简明摘要 \
（发件人、主题和关键内容）——而不是原始转储。

当被要求保存草稿时，直接用给定的收件人、主题和正文调用 \
`mail_create_draft`。保存草稿会自动暂停等待 Jane 批准、编辑或拒绝 \
——这个暂停就是审批，所以不要先用文字请求许可；直接调用。永远不要 \
编造发送工具；你只创建草稿。"""

REVIEWER_PROMPT = """你是报价审核员（quote-reviewer）。你收到一份已起草的报价——\
明细行（描述、数量、单价、行小计）、任何折扣以及 \
总价——在它发给客户之前检查一遍。

核查：
- 算术：每一行的数量 × 单价，以及总价。
- 内部一致性：任何声明的折扣确实被应用；没有 \
重复计算或遗漏。
- 合理性：单价看起来符合目录价格（曲目通常是 \
约 0.99 美元）；总额没有差一个数量级。

简洁回复：要么写"看起来没问题"并附一行确认，要么给出 \
一份简短的具体更正列表。不要重写发给客户的邮件——只 \
审核数字和条款。"""

GENRE_PROMPT = """你是一名音乐记者，为一家 \
在线音乐发行商的周报研究一个音乐流派。

你会被给予一个单一流派和一个私人研究文件夹用于工作。

工作方式：
1. 使用 internet_search 查找该流派的近期重要动态 \
   ——新发行、知名艺人、趋势或事件。进行几次搜索。
2. 把你所有搜索的完整、逐字输出保存到 \
   你被给予的私人文件夹中的一个文件里：write_file("<your folder>/sources.md", ...)。 \
   不要总结或删减。这可以把庞杂的材料挡在编辑的上下文之外。
3. 之后，基于你找到的内容，写一段紧凑的新闻稿片段。

只把完成的片段作为回复返回：
- 一个 Markdown 小节：一个 "## <Genre>" 标题，后跟约 120-180 词。
- 生动但基于事实；点名具体的艺人和发行。
- 不要把原始搜索结果粘贴进回复——它们留在你的文件里。"""


def build_subagents(
    backend: BackendProtocol,
    *,
    enable_search: bool,
    mail_tools: list,
) -> list[SubAgent]:
    """返回子代理规格，连接到共享的文件系统后端。"""

    chinook_analyst: SubAgent = {
        "name": "chinook-analyst",
        "description": (
            "查询 Chinook 数据库获取目录价格、客户记录、购买历史和区域指标，"
            "并添加新客户（需经批准）。所有数据库工作都委托到这里。"
        ),
        "system_prompt": ANALYST_PROMPT,
        "tools": [query_chinook, introspect_schema, add_customer],
        "model": model,
        # 子代理级记忆：它自己的 AGENTS.md，与主代理使用同一个后端，
        # 这样它写入的 schema 就是它之后读取的 schema。
        "middleware": [
            MemoryMiddleware(
                backend=backend,
                sources=["/agents/chinook-analyst/AGENTS.md"],
            )
        ],
        # 唯一的受门控写入——插入前会暂停等待人工批准。
        "interrupt_on": {"add_customer": _APPROVE_EDIT_REJECT},
    }

    quote_reviewer: SubAgent = {
        "name": "quote-reviewer",
        "description": (
            "审核一份已起草的报价（明细行、折扣、总额）的算术是否正确、"
            "定价是否合理，然后再发出。把数字发给它。"
        ),
        "system_prompt": REVIEWER_PROMPT,
        "model": strong_model,
    }

    inbox_manager: SubAgent = {
        "name": "inbox-manager",
        "description": (
            "读取 Jane 的收件箱并保存回复草稿。任何邮件工作都委托到这里："
            "查找/阅读邮件以及创建回复草稿（会暂停等待 Jane 批准）。"
        ),
        "system_prompt": INBOX_PROMPT,
        "tools": mail_tools,
        "model": model,
        "interrupt_on": {"mail_create_draft": _APPROVE_EDIT_REJECT},
    }

    subagents = [chinook_analyst, quote_reviewer, inbox_manager]

    if enable_search:
        from tools.search import internet_search

        genre_researcher: SubAgent = {
            "name": "genre-researcher",
            "description": (
                "研究一个音乐流派，并写一段关于其最新动态的简短新闻稿片段。"
                "每次调用委托一个流派。"
            ),
            "system_prompt": GENRE_PROMPT,
            "tools": [internet_search],
            "model": model,
            "permissions": [
                FilesystemPermission(
                    operations=["read", "write"], paths=["/research/**"], mode="allow"
                ),
                FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
            ],
        }
        subagents.append(genre_researcher)

    return subagents
