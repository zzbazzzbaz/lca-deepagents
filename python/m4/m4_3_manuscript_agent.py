# python/m4/m4_3_manuscript_agent.py
"""第 4 模块 · 第 3 课：动态子代理——"被破坏的手稿"实验。

一些不合时代的句子被拼接进了《伊利亚特》《奥德赛》和《埃涅阿斯纪》的
合并公共领域语料中（data/epic_corpus.txt；构建方式见
data/prepare_corpus.py）。这份语料太大，塞不进一个上下文窗口，所以主代理
被赋予了代码解释器和一个 `book-scanner` 子代理：它编写一个工作流，
读取手稿、按规范化的 "=== EPIC BOOK N ===" 标题切分，
然后为每卷分派一次扫描器调用，并汇总每个扫描器标记出来的内容。

语料永远不会进入模型自己的上下文。只有 `book-scanner` 简短、提炼过的
发现会进入：解释器持有这份 2MB 的文件，模型在任何时刻看到的文本
都不会超过一卷的量（在子代理调用内部）。
"""

from pathlib import Path

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_quickjs import CodeInterpreterMiddleware

from models import model, strong_model

DATA_DIR = Path(__file__).resolve().parent / "data"

# --- 卷册扫描子代理 ----------------------------------------------------------
SCANNER_PROMPT = """你正在校对一部古希腊或古罗马史诗（《伊利亚特》《奥德赛》
或《埃涅阿斯纪》）的一卷，查找一位爱恶作剧的编辑拼接进去的不合时代句子：
任何提到了青铜时代或古典古代不可能存在之物的句子（手机、自动售货机、
手表、意式浓缩咖啡机等等）。

你将被提供这卷书的标签及其完整文本。

只返回一个 JSON 数组，包含你找到的不合时代的句子，从文本中逐字引用
（不要转述，不要引用片段）。如果找不到，返回 `[]`。大多数卷里都没有；
不要强行找出一处。"""

book_scanner = {
    "name": "book-scanner",
    "description": (
        "扫描手稿中的一卷，查找不合时代的句子。"
        "每次调用只委派一卷，并传入该卷的标签和完整文本。"
    ),
    "system_prompt": SCANNER_PROMPT,
    "model": model,  # 更便宜的 Haiku 4.5：这是一个范围狭窄、反复进行的任务
}


# --- 主代理 ------------------------------------------------------------------
MANUSCRIPT_PROMPT = """你可以访问位于 /epic_corpus.txt 的手稿：一份
《伊利亚特》《奥德赛》和《埃涅阿斯纪》的合并公共领域译本。一位爱恶作剧的
编辑在其中拼接了几处不合时代的句子。

这份手稿被分割成 60 卷，每卷以一行严格格式化为 "=== EPIC BOOK N ==="
的文本开头（例如 "=== ILIAD BOOK 9 ==="）。

运行一个工作流：读取手稿，把它切分成 60 卷，并为每卷分派一次
book-scanner 子代理调用，按每个 Promise.all 轮次批量处理 30 卷
（共 2 轮），而不是使用工具指南中展示的较小批次。永远不要把一个卷的
完整文本读进你自己的上下文；让解释器持有该文件，让每个子代理只持有
属于它自己的那一卷。把所有子代理的发现汇总成一份最终报告，
按 "EPIC BOOK N" 分组，列出在该卷中找到的不合时代句子
（没有发现的卷就省略）。"""

# 扫描器只需要对那一个手稿文件的读权限；不需要写权限。
manuscript_permissions = [
    FilesystemPermission(operations=["read"], paths=["/epic_corpus.txt"], mode="allow"),
    FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="deny"),
]

agent = create_deep_agent(
    model=strong_model,
    middleware=[CodeInterpreterMiddleware(ptc=["read_file", "grep"])],
    system_prompt=MANUSCRIPT_PROMPT,
    subagents=[book_scanner],
    backend=FilesystemBackend(root_dir=DATA_DIR, virtual_mode=True),
    permissions=manuscript_permissions,
)