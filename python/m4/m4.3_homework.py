# python/m4/m4.3_homework.py
"""M4.3 作业：编写你自己的动态子代理工作流。

核心思想
实验给主代理提供了一份被分割成带标签卷册的 2MB 手稿，并让它编写一个
"工作流"为每卷分派一个"卷册扫描"子代理，这样完整的语料就永远不会
进入主模型自己的上下文。这份作业要求你在一个自选场景上做同样形态的事情：
一份你自己的合成语料，分割成你自己的带标签章节，以及一个扫描每个章节中
除"时代错误"之外某种内容的子代理。

如果你需要，这里提供几个起点：
  - 一个夏洛克·福尔摩斯故事，按章节分割，扫描侦探提到过但从未真正解释的线索。
  - 《蜜蜂总动员》或《怪物史莱克》的剧本，按场景分割，扫描那些与说出台词的
    角色不匹配的台词。
  - 你自制的"被破坏的经典"（像实验那样），但植入的是另一种错误：
    错误的单位、人物名字互换、章节之间的连贯性错误。

需要你填写的内容
  TODO 1：编写你自己的语料——一个被分割成至少 5 个带标签章节的字符串，
    使用一致的标题格式（像实验里的 "=== EPIC BOOK N ==="）。
  TODO 2：编写章节扫描器的系统提示词（它应该在一个章节里标记什么？）
    以及主代理的系统提示词（告诉它运行一个把语料切分、并为每个章节
    分派一次扫描器调用的工作流）。

运行方式
  cd python
  uv run ./m4/m4.3_homework.py

注意
  这里使用和实验相同的代码解释器（langchain_quickjs）。请确保你在
  python/ 下运行过 `uv sync`，让它被安装好。
"""

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_quickjs import CodeInterpreterMiddleware

from models import model, strong_model

DATA_DIR = Path(__file__).resolve().parent / "homework_data"
DATA_DIR.mkdir(exist_ok=True)
CORPUS_PATH = DATA_DIR / "my_corpus.txt"


# ════════════════════════════════════════════════════════════════════════
# TODO 1：编写你自己的语料。
#
# 要求：
#   - 一个包含至少 5 个带标签章节的字符串。
#   - 选择一种一致的标题格式，例如 "=== SECTION N ===" 或
#     "=== TICKET N ==="，并严格保持一致：主代理的提示词（TODO 2）
#     需要描述同一种格式，这样才能按它切分。
#   - 在几个章节中植入一些值得发现的内容（一句离题的话、一个特定关键词，
#     或你的扫描器在 TODO 2 中要找的任何东西），这样工作流才有东西可找。
#
# 示例形状（删除它，写你自己的）：
#   return """\
#   === SECTION 1 ===
#   ...
#
#   === SECTION 2 ===
#   ...
#   """
# ════════════════════════════════════════════════════════════════════════

def build_corpus() -> str:
    """TODO 1：返回你自己的、包含至少 5 个章节的语料字符串。"""
    raise NotImplementedError("TODO 1：请查看上面的注释块")


CORPUS_PATH.write_text(build_corpus())


# ════════════════════════════════════════════════════════════════════════
# TODO 2：编写扫描器和主代理的提示词。
#
# 返回 (scanner_prompt, main_prompt)：
#   - scanner_prompt：交给章节扫描器子代理的、它应该在交给它的一个章节里
#     找什么、以及它应该返回什么。
#   - main_prompt：告诉主代理关于语料文件、TODO 1 中的标题格式，并让它运行
#     一个切分语料、为每个章节分派一次扫描器调用的"工作流"（"workflow"
#     这个词正是触发基于代码的分派机制的关键，参见课程内容）。
# ════════════════════════════════════════════════════════════════════════

def build_prompts() -> tuple[str, str]:
    """TODO 2：返回 (scanner_prompt, main_prompt)。"""
    raise NotImplementedError("TODO 2：请查看上面的注释块")


SCANNER_PROMPT, MAIN_PROMPT = build_prompts()

section_scanner = {
    "name": "section-scanner",
    "description": (
        "扫描语料的一个章节，找出扫描器提示词要求的内容。每次调用只委派一个章节。"
    ),
    "system_prompt": SCANNER_PROMPT,
    "model": model,
}

agent = create_deep_agent(
    model=strong_model,
    middleware=[CodeInterpreterMiddleware()],
    system_prompt=MAIN_PROMPT,
    subagents=[section_scanner],
    backend=FilesystemBackend(root_dir=DATA_DIR, virtual_mode=True),
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "运行一个工作流，扫描 my_corpus.txt 的每个章节，并报告你的发现。",
            }
        ]
    },
    config={"recursion_limit": 100},
)
print(result["messages"][-1].content)
