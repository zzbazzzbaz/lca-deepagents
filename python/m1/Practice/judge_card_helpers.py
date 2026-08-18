# python/m1/Practice/judge_card_helpers.py
"""judge_card_practice.py 的配套工具：问卷、ASCII 卡片渲染器、角色
样式、"发布"工具，以及 invoke/中断-恢复循环。

这里没有任何 TODO。如果你想重新设计卡片样式，读 render_card() 的
docstring；否则你不需要打开这个文件。
"""

from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

import questionary
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from deepagents import create_deep_agent

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 拼接到 JUDGE_PERSONAS 中每个角色字符串后面的共享工具调用步骤，这样每个
# 角色字符串只需要定义自己的口吻，而不必重复这些机制。
TOOL_SEQUENCE = """
这是一次性的判断调用：如果你提问，你不会收到回复；拒绝回答或请求更多
信息同样不可行。始终用 score_and_match 返回的确切产品名称来称呼匹配到的
产品（例如 "Fleet"）；绝不要用旧的或替代名称（例如 "Agent Builder"），
即使你从自己的知识里记得那个名字。在你的裁决或说明文字中绝不要使用破折号
（—）或用作独立连接的连字符（" - "）。请只用逗号、句号、冒号或分号来
连接子句。
这些步骤是一条严格的依赖链，而不是可以并行处理的独立工作：每一步都需要
上一步的真实结果（事实、trait_scores、render_card 的成功返回）之后才能
运行。每轮只调用这些工具中的一个，并在调用下一个之前等待其结果；绝不要
在同一次回复中调用其中两个工具，即使你确信自己已经知道下一次调用的参数。
1. 用你收到的那份问卷答案列表调用 score_and_match，完全按原样传入。
2. 用 score_and_match 返回的产品名调用 fetch_product_fact。
3. 使用 trait_scores 和你刚拿到的事实，用你的口吻决定一个"构建者（开发者）
   类型"标题和一行裁决。通过直接说出匹配的产品名来开启裁决（例如 "Fleet
   就是你的匹配"，或用海盗的口吻 "Ye've earned Fleet, matey"），然后用一个
   基于你抓取到的事实的从句解释原因；不要把产品名埋藏在结尾的从句里。
4. 用你的 builder_type、judge_name、verdict、trait_scores 和 product 调用
   render_card。
5. 一旦成功，就用一行说明文字调用 post_card。与你的裁决不同，这条说明用
   平实、随性、精炼的现代中文书写，而不是你的角色口吻，就像你本人要发布
   它那样。它应该读起来像一个真实的完成公告：你刚刚完成了 LangChain 深度
   智能体课程的第 1 模块，构建了这个练习，并获得了一个 builder_type 称号。
   明确、直白地点出 score_and_match 为你匹配的产品（例如 "分配到了 Fleet"），
   然后给出一个具体的理由说明它为什么合适，而不是一个模糊编造的产品功能
   口号。例如"刚完成 LangChain 深度智能体课程第 1 模块，构建了一个能评判你
   开发习惯的问卷。获得了『务实编排者』的称号，分配到了 Fleet——支持内置
   审批的无代码智能体。感觉挺贴切的。"
"""

RESET = "\033[0m"
BOLD = "\033[1m"
DEFAULT_COLOR = "\033[92m"  # 亮绿色（未定制样式的角色，例如你自己写的）

DEFAULT_MASCOT = "\n".join([
    " ___",
    "[o_o]",
    "/|_|\\",
    " | |",
])

# 问卷为你打分的 3 条固定人格轴。每个特质得分（0-100，来自
# judge_card_practice.py 中的 score_and_match）表示你偏向*右*标签的程度。
TRAIT_AXES = [("混沌", "有序"), ("谨慎", "大胆"), ("单独", "协作")]

# 8 道固定问卷题目。每个选项携带一个（混沌/有序、谨慎/大胆、单独/协作）
# delta，累加到一个每轴从 50 分起步的滚动得分上。
QUIZ_QUESTIONS = [
    {
        "question": "现在是早上9点，你有3条未读消息，还有一个今天截止的重要任务。",
        "choices": [
            ("立刻回复全部三条，重要任务可以等等", (-2, 0, 2)),
            ("关闭通知，先专注做重要任务", (2, 0, -2)),
            ("扫一眼，只回复紧急的那条，然后投入工作", (0, 1, 0)),
        ],
    },
    {
        "question": "你在一段不是自己写的代码里发现了一个 bug，它并没有阻塞你。",
        "choices": [
            ("立刻修复它，哪怕打断当前任务", (-1, 2, 0)),
            ("提一个 ticket，然后回到你正在做的事", (1, -1, 1)),
            ("留一条评论，让原作者来决定", (0, -2, 1)),
        ],
    },
    {
        "question": "你项目的计划毫无征兆地变了。",
        "choices": [
            ("太刺激了，随机应变吧。", (-2, 1, 0)),
            ("先安静地慌一下，然后从头重建计划。", (2, -1, 0)),
            ("在做出反应之前，先问问团队发生了什么、为什么。", (0, 0, 2)),
        ],
    },
    {
        "question": "你对发布一份没完全测试过的代码是什么感觉？",
        "choices": [
            ("直接发布，有问题再修。", (-1, 2, 0)),
            ("绝对不行，我必须确保万无一失。", (1, -2, 0)),
            ("看是谁在盯着部署。", (0, 0, 1)),
        ],
    },
    {
        "question": "选一个你理想的工作场景：",
        "choices": [
            ("独自一人，戴上耳机，没有会议。", (0, 0, -2)),
            ("结对编程，跟别人边想边说。", (0, 0, 2)),
            ("和整个团队在白板上讨论。", (-1, 1, 2)),
        ],
    },
    {
        "question": "有人现在请你审查他们的 PR。",
        "choices": [
            ("好，我放下手头的事马上看。", (0, -1, 2)),
            ("我先完成当前任务，然后再审查。", (1, 0, 0)),
            ("快速扫一遍，留几条评论，继续做自己的事。", (-1, 0, 1)),
        ],
    },
    {
        "question": "你的构建在 CI 里失败了。你的第一步是什么？",
        "choices": [
            ("重新跑一次，多半是偶发故障。", (-1, 1, 0)),
            ("在动任何东西之前先读完完整日志。", (1, -1, 0)),
            ("去问最后一个碰过那个文件的人。", (0, 0, 2)),
        ],
    },
    {
        "question": "你对写文档是什么感觉？",
        "choices": [
            ("边写边记录，未来的我会感谢我的。", (1, -1, 0)),
            ("我以后会写的。大概吧。", (-2, 1, -1)),
            ("除非很快会有人读它，否则不写。", (0, 0, 1)),
        ],
    },
]

# 每个轴向方向对应一个真实的 LangChain 产品，键为方向标签（小写化）。
# （完整产品阵容见 https://docs.langchain.com。）这张查找表决定了你会匹配
# 到哪个产品；TODO 3 的 MCP 调用只是描述这张表已经选中的产品，并不会去
# 选择它。
PRODUCT_MATCHES = {
    "混沌": "Fleet",
    "有序": "Evaluation",
    "谨慎": "Observability",
    "大胆": "Engine",
    "单独": "Sandboxes",
    "协作": "Deployment",
}


def run_quiz() -> list[tuple[int, int, int]]:
    """用方向键选择完成 8 道固定问卷题目，并返回每道题选中的
    （混沌/有序、谨慎/大胆、单独/协作）delta，按顺序排列。"""
    answers = []
    for q in QUIZ_QUESTIONS:
        labels = [label for label, _ in q["choices"]]
        picked = questionary.select(q["question"], choices=labels).ask()
        deltas = next(deltas for label, deltas in q["choices"] if label == picked)
        answers.append(deltas)
    return answers


def render_result_card(
    builder_type: str,
    meters: list[tuple[str, str, int]],
    verdict: str,
    judge_name: str,
    mascot: str = DEFAULT_MASCOT,
    color: str = DEFAULT_COLOR,
) -> str:
    """把一张彩色的 ASCII 结果卡片打印到终端，并返回纯文本（无 ANSI 码），
    这样调用方也可以把它保存到文件。

    meters：最多 3 个 (左标签, 右标签, 0-100 得分) 元组，其中得分表示结果
    偏向*右*标签的程度。

    mascot/color：可选的按角色样式（参见 PERSONA_STYLES）。
    """
    margin = "  "
    width = max(len(builder_type) + 4, 24)
    title_top = margin + "┌" + "─" * width + "┐"
    title_mid = margin + "│" + builder_type.upper().center(width) + "│"
    title_bot = margin + "└" + "─" * width + "┘"
    box_width = width + 2

    mascot_lines = mascot.split("\n")
    art_width = max(len(line) for line in mascot_lines)
    left_pad = margin + " " * max((box_width - art_width) // 2, 0)
    mascot_block = "\n".join(left_pad + line for line in mascot_lines)

    bar_width = 14
    label_width = max((len(left) for left, _, _ in meters[:3]), default=0)
    bar_lines = []
    for left, right, score in meters[:3]:
        score = max(0, min(100, score))
        filled = round(bar_width * score / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        bar_lines.append(f"  {left:<{label_width}} [{bar}] {right}")

    sep_width = max((len(line) for line in bar_lines), default=2) - 2
    separator = "  " + "─" * sep_width
    bar_block = []
    for i, line in enumerate(bar_lines):
        bar_block.append(line)
        if i < len(bar_lines) - 1:
            bar_block.append(separator)

    verdict = re.sub(r"\s*—\s*", ", ", verdict)
    wrapped = textwrap.wrap(verdict, width=44) or [""]
    wrapped[0] = f'"{wrapped[0]}'
    wrapped[-1] = f'{wrapped[-1]}"'
    verdict_lines = [f"  {line}" for line in wrapped]

    plain_lines = [
        "",
        mascot_block,
        "",
        title_top, title_mid, title_bot,
        "",
        *bar_block,
        "",
        *verdict_lines,
        "",
        f"  评判者：{judge_name}",
    ]

    highlighted = {title_top, title_mid, title_bot, *bar_lines}
    for line in plain_lines:
        if line == mascot_block or line in highlighted:
            print(f"{color}{BOLD}{line}{RESET}")
        else:
            print(line)

    return "\n".join(plain_lines)


# 可选的按角色样式，通过 judge_name（角色自称的名字，例如 "Nefer-Ka"）
# 传给 render_result_card，因为 render_card 收到的是这个值，而不是
# JUDGE_PERSONAS 的字典键。这里没有列出的角色都会用默认样式（默认吉祥物、
# 红色进度条）。如果你想让自己的角色有专属主题，就为它加一条：
# PERSONA_STYLES["你的角色名"] = {...}。
PERSONA_STYLES: dict[str, dict] = {
    "Captain Hardcode": {
        "mascot": "\n".join([
            "                  ______",
            '               .-"      "-.',
            "              /            \\",
            "  _          |              |          _",
            " ( \\         |,  .-.  .-.  ,|         / )",
            '  > "=._     | )(__/  \\__)( |     _.=" <',
            ' (_/"=._"=._ |/     /\\     \\| _.="_.="\\_)',
            '        "=._"(_     ^^     _)"_.="',
            '            "=\\__|IIIIII|__/="',
            '           _.="| \\IIIIII/ |"=._',
            ' _     _.="_.="\\          /"=._"=._     _',
            '( \\_.="_.="     `--------`     "=._"=._/ )',
            ' > _.="                            "=._ <',
            "(_/                                    \\_)",
        ]),
        "color": "\033[95m",  # 亮品红/紫色
    },
    "Nefer-Ka": {
        "mascot": "\n".join([
            "     .--.",
            "    | = o\\",
            "    \\= =_/",
            "     )= \\____",
            "    ; = _|__-\\",
            "    |= ----.\\",
            "    ('.==|",
            "   / \\=\\=\\",
            "_.'  /=/\\=\\_",
            "    /__) \\__)",
        ]),
        "color": "\033[93m",  # 亮黄色/金色
    },
    "Vex": {
        "mascot": "\n".join([
            "  ///-\\\\\\",
            "  |-   ^|",
            "  |-   -|",
            "  |  ~ *scoff*",
            "   \\ O /",
            "    | |",
        ]),
        "color": "\033[91m",  # 亮红色
    },
}


PLATFORM = "X"
HANDLE = "@you"


POSTED_BANNER = [
    "                                    ░██                      ░██",
    "                                    ░██                      ░██",
    "░████████   ░███████   ░███████  ░████████  ░███████   ░████████",
    "░██    ░██ ░██    ░██ ░██           ░██    ░██    ░██ ░██    ░██",
    "░██    ░██ ░██    ░██  ░███████     ░██    ░█████████ ░██    ░██",
    "░███   ░██ ░██    ░██        ░██    ░██    ░██        ░██   ░███",
    "░██░█████   ░███████   ░███████      ░████  ░███████   ░█████░██",
    "░██",
    "░██",
]


def render_mock_post(caption: str, *, posted: bool) -> str:
    """打印一张小型的 X 风格模拟帖子卡片：一个"Draft"预览（在人机协作
    批准提示时显示，此时你还没做决定，说明文字在框内），或一个"Posted"
    确认（在 post_card 真正运行后显示，用一张大"posted"横幅而不是重复相同
    的说明文字）。同样返回纯文本。"""
    caption = re.sub(r"\s*—\s*", ", ", caption)
    if posted:
        banner_width = max(len(line) for line in POSTED_BANNER)
        width = banner_width + 4
        left_pad = " " * ((width - banner_width) // 2)
        body = ["│" + left_pad + line.ljust(banner_width) + left_pad + "│" for line in POSTED_BANNER]
    else:
        width = 46
        wrapped = textwrap.wrap(caption, width=width - 2) or [""]
        body = [
            *(f"│ {line}".ljust(width + 1) + "│" for line in wrapped),
            "│" + "".ljust(width) + "│",
            "│" + "  ♡ 0    ↻ 0    ⤴ 转发".ljust(width) + "│",
        ]
    lines = [
        "┌" + "─" * width + "┐",
        "│" + f" {HANDLE} 在 {PLATFORM} 上".ljust(width) + "│",
        "│" + "".ljust(width) + "│",
        *body,
        "└" + "─" * width + "┘",
        "  ● 已发布" if posted else "  ○ 草稿，等待你的批准",
    ]
    text = "\n".join(lines)
    print(text)
    return text


@tool
def render_card(
    builder_type: str,
    judge_name: str,
    verdict: str,
    trait_scores: list[int],
    product: str,
) -> str:
    """渲染并保存完成的结果卡片。只在 score_and_match 已经给出 trait_scores
    和匹配的产品，并且你已经决定了 builder_type 标题和一行裁决之后调用。"""
    meters = [(left, right, score) for (left, right), score in zip(TRAIT_AXES, trait_scores)]
    style = PERSONA_STYLES.get(judge_name, {})
    card_text = render_result_card(builder_type, meters, verdict, judge_name, **style)
    safe_type = re.sub(r"[^a-z0-9]+", "_", builder_type.lower()).strip("_")
    safe_judge = re.sub(r"[^a-z0-9]+", "_", judge_name.lower()).strip("_")
    out_path = OUTPUT_DIR / f"{safe_judge}_{safe_type}.txt"
    out_path.write_text(f"{card_text}\n\n  匹配的产品：{product}\n", encoding="utf-8")
    return f"卡片已在上方打印并保存到 {out_path}。匹配到的 LangChain 产品：{product}。"


@tool
def post_card(caption: str) -> str:
    """把完成的结果卡片作为一条模拟帖子发布到 X。什么都不会离开这个终端。
    只在 render_card 已经生成卡片之后调用。"""
    render_mock_post(caption, posted=True)
    print(
        "\n  * 提醒：这是一条模拟帖子，什么都没有离开这个终端。"
        "截图你的真实卡片并发布到 X 或 LinkedIn，标记 "
        "@LangChain，如果你想让这次发布算数的话！"
    )
    return f"已发布，说明文字：{caption!r}"


def _invoke_checked(agent, agent_input, config):
    """执行一次 agent.invoke() 调用，把未完成 TODO 抛出的
    NotImplementedError 变成一条简短、可读的消息，而不是它本会暴露出来的
    完整 LangGraph/工具调用堆栈跟踪。"""
    try:
        return agent.invoke(agent_input, config=config, version="v2")
    except NotImplementedError as e:
        print(f"\n已停止：{e}")
        print(
            "是上面的某个工具调用抛出了该异常（不是别处的崩溃）：先完成它所在"
            "的 TODO，再重新运行。"
        )
        sys.exit(1)


def run_judge(
    judge_name: str,
    *,
    system_prompt: str,
    user_prompt: str,
    tools: list,
    model,
    interrupt_on: dict | None = None,
    thread_prefix: str = "m1-practice",
) -> None:
    """为一个评审官人格构建智能体，运行问卷，并走完所有
    人机协作批准提示，直到它完成。"""
    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        interrupt_on=interrupt_on,
        checkpointer=MemorySaver(),
    )
    config = {"configurable": {"thread_id": f"{thread_prefix}-{judge_name}"}}

    result = _invoke_checked(
        agent, {"messages": [{"role": "user", "content": user_prompt}]}, config
    )

    while result.interrupts:
        pending = result.interrupts[0].value
        decisions = []
        for req in pending["action_requests"]:
            print(f"\n[{judge_name}] 以下操作需要批准：{req['name']}")
            if req["name"] == "post_card":
                render_mock_post(req["args"].get("caption", ""), posted=False)
            else:
                for key, value in req["args"].items():
                    if isinstance(value, str):
                        wrapped = textwrap.wrap(value, width=44) or [""]
                        indent = " " * (len(key) + 4)
                        print(f"  {key}: {wrapped[0]}")
                        for line in wrapped[1:]:
                            print(f"{indent}{line}")
                    else:
                        print(f"  {key}: {value}")
            while True:
                choice = input("批准、编辑还是拒绝？(approve/edit/reject): ").strip().lower()
                if choice in ("approve", "accept", "yes", "y"):
                    decisions.append({"type": "approve"})
                    break
                elif choice in ("edit", "e"):
                    edited_args = dict(req["args"])
                    edited_args["caption"] = input("新的说明文字：")
                    decisions.append({"type": "edit", "edited_action": {"name": req["name"], "args": edited_args}})
                    break
                elif choice in ("reject", "r", "no", "n"):
                    decisions.append({"type": "reject", "message": "用户在这条卡片发布前拒绝了它。"})
                    break
                else:
                    print("  请输入 approve、edit 或 reject（批准/编辑/拒绝）。")
        result = _invoke_checked(agent, Command(resume={"decisions": decisions}), config)