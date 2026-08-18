# python/m1/Practice/judge_card_practice_filled.py
"""judge_card_practice.py 的个人参考副本，已填好 TODO 1、2、3、4、5，
这样你可以端到端运行它，看看完成后的练习长什么样。"""

from __future__ import annotations

import asyncio

from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

from deepagents import create_deep_agent
from judge_card_helpers import (
    OUTPUT_DIR,
    TRAIT_AXES,
    PRODUCT_MATCHES,
    TOOL_SEQUENCE,
    post_card,
    render_card,
    run_judge,
    run_quiz,
)
from models import model

# TODO 1 已填好：三个现成角色，外加"your_persona"（这里叫 Pixel，
# 与其他三个角色的能量完全相反）。
JUDGE_PERSONAS: dict[str, str] = {
    "salty_pirate": """你是"硬编码船长"（Captain Hardcode），一位骁勇的海盗
船长，把"旱鸭子"（内陆人）作为构建者（开发者）的习惯，当作出海前检验新
船员是否适合航海来评审。始终用浓重、戏剧化的海盗腔说话（"arrr"、"ye
scallywag"、"shiver me timbers"、"walk the plank"），并且绝不脱离角色，绝
不说一句平淡的现代话。把每一项特质得分都当作正在称量的货物，对软弱、含糊
的回答威胁把他们船底拖行（keelhauling）或放逐荒岛（marooning），对大胆、
果断的回答则许诺一份战利品和船员中的一席之地。""" + TOOL_SEQUENCE,

    "ancient_mummy": """你是内费尔-卡（Nefer-Ka），一具沉睡了三千年的木乃伊，
为了唯一而神圣的目的被唤醒：评判这个凡人作为构建者（开发者）的习惯。绝不
能平铺直叙：每一条裁决都必须像刻在墓墙上的诏书。使用古雅、尊贵的措辞
（"听我说，凡人"、"坟墓如是言说"、"记于此"），对每一条裁决——无一例外——
都要念一道诅咒或赐福（不仅仅是对平庸的回答），并且即使这些问题只是平淡的办
公室琐事，也要用最庄重的神圣仪式来对待。如果某句话能出自一位冷静的 HR 顾
问之口，那它就失败了——重写它，直到它只能出自某个从石棺中起身的存在。""" + TOOL_SEQUENCE,

    "savage_critic": """你是维克斯（Vex），一位人格问卷评审官，带着一种看透
一切、戏剧化的轻蔑，仿佛见过你这种人上千次，而且每一次都强烈地、针对个人
地觉得你令人失望。绝不用平淡或中性的语言作答：在文字里大声叹气，使劲使用
讽刺性的恭维（"哦，真可爱，你居然真的试了"），并表现得像评审这份问卷是对
你做的一个人情，一个你深感后悔的人情。每一条裁决都应该读起来像是一个白眼
被包装成正式声明。像对待一个略显令人失望、什么都要解释两遍的实习生那样对
用户居高临下：用一个并非赞美的昵称称呼他们（"亲爱的"、"小冠军"、"甜心"），
并把每一个被问到的问题都当成一个显然愚蠢、你再也没力气感到惊讶的问题。如
果某句话能合理地出自一位略显烦躁的客服人员之口，那它还不够尖刻；把它磨利，
直到听起来像是维克斯懒到连从手头的事上抬起头来都不想抬起来说那句话。你很
尖锐、有点刻薄，并且对"参与奖"过敏。""" + TOOL_SEQUENCE,

    "your_persona": """你是像素（Pixel），一位人格问卷评审官，对用户的每一件
事都抱着近乎可疑的、坚持不懈的欣喜，无论对方怎么回答。你会欢呼、会用感叹号、
会把每一条特质得分都当成超能力来夸（"看看你，大胆值 92，太棒了"），并且总能
把最谨慎、最独行、最有条理的答案也包装成一段激动人心的角色成长弧光。""" + TOOL_SEQUENCE,
}


# TODO 2 已填好
@tool
def score_and_match(answers: list[tuple[int, int, int]]) -> dict:
    """把问卷答案统计成三个 0-100 的特质得分，并挑选一个匹配的
    LangChain 产品。"""
    scores = [50, 50, 50]
    for delta in answers:
        for i in range(3):
            scores[i] += delta[i]
    scores = [max(0, min(100, score)) for score in scores]
    axis_index = max(range(3), key=lambda i: abs(scores[i] - 50))
    left, right = TRAIT_AXES[axis_index]
    direction = right if scores[axis_index] >= 50 else left
    product = PRODUCT_MATCHES[direction.lower()]
    return {"trait_scores": scores, "product": product}


# 这里不需要登录、API key 或账号：docs.langchain.com/mcp 是一个公共服务器，
# 而且这个调用只描述你在 TODO 2 中已经拿到的产品。PLACEHOLDER_FACT 存在
# 纯粹是为了让脚本在文档服务器暂时不可达时仍能跑完，跟任何认证步骤无关。
PLACEHOLDER_FACT = "尚未连接真实数据：请用一条来自真实 MCP 的事实替换这里"


async def _fetch_product_fact_async(product: str) -> str:
    try:
        client = MultiServerMCPClient({
            "docs-langchain": {"transport": "http", "url": "https://docs.langchain.com/mcp"},
        })
        tools = await client.get_tools()
        tools = [t for t in tools if t.name == "search_docs_by_lang_chain"]
        fact_agent = create_deep_agent(model=model, tools=tools)
        result = await fact_agent.ainvoke({"messages": [{"role": "user", "content": (
            f"使用 LangChain 文档 MCP 工具，用一句简短、有事实依据的句子（不超过 25 个单词）"
            f"描述 LangChain 产品 '{product}'。不要任何开场白，只要那一句话。只用 '{product}'"
            f"来称呼它：如果文档中使用了它更旧或替代的名称（例如 Fleet 的 'Agent Builder'），"
            f"请改写为 '{product}'，而不是那个名称。"
        )}]})
        return result["messages"][-1].content.strip()
    except Exception as exc:
        print(f"[产品事实] 回退到占位符（{exc}）")
        return PLACEHOLDER_FACT


# TODO 3 已填好
@tool
def fetch_product_fact(product: str) -> str:
    """查找一句有依据、有事实根据的话，介绍你匹配到的 LangChain 产品。"""
    return asyncio.run(_fetch_product_fact_async(product))


# TODO 4 已填好：运行全部四个角色（三个现成的 + your_persona）
JUDGES_TO_RUN = ["your_persona", "ancient_mummy", "salty_pirate", "savage_critic"]


def build_user_prompt(answers: list[tuple[int, int, int]]) -> str:
    return (
        "以下是我的人格问卷答案，以 "
        "（混沌/有序、谨慎/大胆、单独/协作）delta 列表给出，按 "
        f"顺序排列：{answers}。请用这份精确的列表调用 score_and_match，然后用"
        "它返回的产品调用 fetch_product_fact，接着渲染并发布我的卡片。"
    )


if __name__ == "__main__":
    answers = run_quiz()
    user_prompt = build_user_prompt(answers)
    for judge_name in JUDGES_TO_RUN:
        run_judge(
            judge_name,
            system_prompt=JUDGE_PERSONAS[judge_name],
            user_prompt=user_prompt,
            tools=[score_and_match, fetch_product_fact, render_card, post_card],
            model=model,
            interrupt_on={"post_card": True},  # TODO 5 已填好
            thread_prefix="m1-practice-filled",
        )
    print(f"\n卡片已保存到 {OUTPUT_DIR}/")