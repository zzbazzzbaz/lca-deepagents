# python/m4/m4.3_homework_filled.py
"""m4.3_homework.py 的参考副本，其中 TODO 1 和 TODO 2 已被填写完成，
让你可以端到端运行，看看"完成"的样子。这只是众多可行答案之一，
你的答案可能不同。去探索吧！"""

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_quickjs import CodeInterpreterMiddleware

from models import model, strong_model

DATA_DIR = Path(__file__).resolve().parent / "homework_data"
DATA_DIR.mkdir(exist_ok=True)
CORPUS_PATH = DATA_DIR / "my_corpus.txt"


# TODO 1 已填写
def build_corpus() -> str:
    return """\
=== TICKET 1 ===
客户说，每次在 Android 14 上打开设置页面时应用都会崩溃。附有一张错误的截图。

=== TICKET 2 ===
客户在这个计费周期内为月度订阅被重复扣费两次，希望其中一笔扣款能够退款。

=== TICKET 3 ===
客户在取消账户之前，询问如何把数据导出成 CSV 文件。

=== TICKET 4 ===
客户的发票上显示了一笔他们两个月前已降级停用的套餐的费用；他们希望退还差价。

=== TICKET 5 ===
客户反馈，当按日期而不是按相关性筛选时，搜索结果的排序不正确。

=== TICKET 6 ===
客户说优惠码已生效，但他们仍被收取了全额费用，希望退还折扣部分的金额。

=== TICKET 7 ===
客户想知道移动应用是否计划推出深色模式。
"""


CORPUS_PATH.write_text(build_corpus())


# TODO 2 已填写
def build_prompts() -> tuple[str, str]:
    scanner_prompt = """你正在审核一张客服工单，检查是否存在账单投诉：
即任何关于被多收费、被重复扣费、被收取了错误金额，或因收费不正确而要求退款
的表述。

你将被提供给一张工单的标签及其完整文本。

只返回一个 JSON 对象：{"is_billing_complaint": true/false, "summary":
"<一句话，如果为 false 则为空字符串>"}。如果这张工单与账单问题无关，
则返回 is_billing_complaint: false。"""

    main_prompt = """你可以访问位于 /my_corpus.txt 的客服工单日志：
一系列工单，每张以一行严格格式化为 "=== TICKET N ===" 的文本开头。

运行一个工作流：读取该文件，把它切分成各张独立工单，并为每张工单分派一次
section-scanner 子代理调用。永远不要把一个工单的完整文本读进你自己的上下文；
让解释器持有该文件，让每个子代理只持有属于它自己的那张工单。把所有子代理的
发现汇总成一份最终报告，只列出被标记为账单投诉的工单，并附上它们的一句话摘要。"""

    return scanner_prompt, main_prompt


SCANNER_PROMPT, MAIN_PROMPT = build_prompts()

section_scanner = {
    "name": "section-scanner",
    "description": (
        "扫描一张客服工单，找出账单投诉。每次调用只委派一张工单。"
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
