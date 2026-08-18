# python/m1/Practice/judge_card_practice.py
"""M1 练习：构建一个"评审官"人格来给你打分并渲染一张卡片。

核心思路
你用方向键完成一份 8 题的性格测试问卷。一个具有特定人格（毒舌海盗 /
千年木乃伊 / 毒舌评论家 等）的智能体会统计你的答案，为你匹配一个真实的
LangChain 产品，并在终端里用 ASCII 艺术渲染出一张可分享的结果卡片。

已提供的部分
参见 judge_card_helpers.py（与 models.py 思路相同：共享的初始化代码，你
import 即可，做练习时不需要阅读它）：
  - run_quiz()：方向键问卷本身（QUIZ_QUESTIONS，8 题）。
  - PRODUCT_MATCHES：特质轴 -> 真实 LangChain 产品的查找表。
  - render_card()：渲染并将完成的结果卡片保存为 ASCII 艺术。你不应该
    需要改动它，但可以随意重新设计样式（如果你想让你的角色拥有自己的
    吉祥物，可以看那里的 PERSONA_STYLES）。
  - post_card()：一个"发布"工具，在我们模拟的 X 平台上渲染一条模拟帖子。
    所有内容都不会离开你的终端。
  - run_judge()：invoke / 中断-恢复循环。你在"人机协作"课程里已经写过
    一次，不需要再写一遍。
  - TOOL_SEQUENCE：所有角色共用的工具调用步骤，被拼接在每个角色的
    字符串后面，这样你只需要写角色的口吻。

________________________________________________________________________    

你需要填写的内容（对应第 1 模块的课程概念）
  TODO 1（课程 1.4，系统提示词：人格）：三个评审官已经写好（海盗船长、
    千年木乃伊、毒舌评论家）；请写第四个属于你自己的角色 "your_persona"：
    这张卡片会被发布出去。
  TODO 2（课程 1.5，工具：自定义工具）：实现 score_and_match() 的函数体：
    把问卷统计成特质得分，并匹配一个 LangChain 产品。
  TODO 3（课程 1.6，MCP：让智能体连接外部服务）：进阶目标，用一条来自
    真实 MCP 的、关于你所匹配产品的事实来支撑裁决，而不是
    PLACEHOLDER_FACT。
  TODO 4（课程 1.7，消息、线程与检查点：线程）：把你第二个角色的键加入
    JUDGES_TO_RUN，让它运行在独立的线程中。
  TODO 5（课程 1.8，人机协作：决策类型）：设置 interrupt_on，让 post_card
    在发布到模拟的 X 平台前需要你的批准。
  TODO 6（课程 1.3，模型，可选）：试试用 strong_model 代替 model，并对比
    喜剧节奏。

________________________________________________________________________    

把它变成你自己的
问卷的特质轴（混沌/有序、谨慎/大胆、单独/协作）是固定的，但你的角色口吻
不是。请给你的评审官一个与三个示例完全不同的性格。


运行
  cd python && uv run python m1/Practice/judge_card_practice.py

════════════════════════════════════════════════════════════════════════
  分享它：有了一张你喜欢的卡片？截图它，在 X 或 LinkedIn 上 @LangChain
  并把你的作品展示给我们！
════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from langchain_core.tools import tool

from judge_card_helpers import (
    OUTPUT_DIR,
    PRODUCT_MATCHES,
    TOOL_SEQUENCE,
    TRAIT_AXES,
    post_card,
    render_card,
    run_judge,
    run_quiz,
)
from models import model


# ════════════════════════════════════════════════════════════════════════
# TODO 1（课程 1.4，系统提示词：人格）
# 下面已经写好三个评审官。
# 选任何一个，脚本都能直接运行。
# 必做项：在下面写出"your_persona"，完全是你自己的口吻。

# 每次都做同样的工作（给三个特质打分、匹配产品、交出一条裁决），但
# 用完全不同的口吻。
# 可以把它写得真的毒舌/狠狠吐槽你（如果你想的话）。
# ════════════════════════════════════════════════════════════════════════

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

    # TODO 1：在这里命名并写出你自己的角色。保持同样的工作
    # （给三个特质打分、匹配产品、交出一条裁决）。
    # 给它一个完全属于你自己的名字和口吻。
    "your_persona": """TODO 1：用你自己的评审官人格替换这里。给你自己取一个
名字和一种独特的口吻（参考上面三个评审官的样子），然后在下面所有用到
judge_name 的地方以那个名字自称。""" + TOOL_SEQUENCE,
}


# ════════════════════════════════════════════════════════════════════════
# TODO 2（课程 1.5，工具：自定义工具）
# 统计部分（给每个答案打分，然后夹到 0-100）已经替你写好了。
# 读注释看看它是怎么工作的。

# 你的工作从"TODO 在这里"注释开始：
# 把算好的分数列表变成匹配的产品。
# ════════════════════════════════════════════════════════════════════════

@tool
def score_and_match(answers: list[tuple[int, int, int]]) -> dict:
    """把问卷答案统计成三个 0-100 的特质得分，并挑选一个匹配的
    LangChain 产品。最先调用它，并传入你拿到的那份精确的 answers 列表。"""
    # 3 个特质得分（混沌/有序、谨慎/大胆、单独/协作）各自从 50 分的中性
    # 起点开始。
    scores = [50, 50, 50]
    # answers 是一组 (delta_1, delta_2, delta_3) 元组，每题一个。
    # 把每个 delta 加到对应的得分上。
    for delta_tuple in answers:
        for i in range(3):
            scores[i] += delta_tuple[i]
    # 长时间选择同一答案可能把某个得分推出 0-100 的范围，所以把每个得分
    # 都夹回这个区间。
    scores = [max(0, min(100, score)) for score in scores]

    # TODO 在这里：scores 已经算完了。用它来挑选匹配的产品。
    # 1. 把 axis_index 设为 scores 中哪个下标（0、1 或 2）对应的得分偏离
    #    50 最远，即 abs(score - 50) 最大。
    #    提示：这是"寻找最大值的下标"问题。Python 的 max() 接受一个 key=
    #    函数，如果你想按值本身以外的条件搜索，例如
    #    max(range(len(scores)), key=lambda i: ...)
    # 2. TRAIT_AXES[axis_index] 是一对 (左标签, 右标签)，例如
    #    ("混沌", "有序")。把 direction 设为 scores[axis_index] 偏向的那一
    #    侧的标签：如果 scores[axis_index] >= 50 用右标签，否则用左标签。
    # 3. 把 product 设为 PRODUCT_MATCHES[direction.lower()]，例如
    #    PRODUCT_MATCHES["混沌"] -> "Fleet"。
    # 4. 返回 {"trait_scores": scores, "product": product}。
    raise NotImplementedError("TODO 2：见上面的注释")


# ════════════════════════════════════════════════════════════════════════
# TODO 3（课程 1.6，MCP：让智能体连接外部服务）
# 这是一个进阶目标。
# score_and_match（TODO 2）已经纯粹通过固定的 PRODUCT_MATCHES 查找决定了
# 你匹配到哪个产品；MCP 在这里没有发言权。

# 这个工具唯一的工作就是用一条真实、鲜活的事实来描述那个已经被选定的
# 产品，而不是靠猜测。

# 请完全照搬 m1.6_agent_mcp.py 的做法：
#   1. 用 MultiServerMCPClient 连接 https://docs.langchain.com/mcp。
#   2. 把它的工具过滤到只剩 "search_docs_by_lang_chain"。
#   3. 用那一个工具搭建一个迷你智能体，让它用一句简短、有事实依据的话
#      （不超过 25 个单词）描述 `product`。
#   4. 返回那句话，去掉多余空白。

# 这个工具本身必须保持同步，所以把 MCP/智能体调用放进一个独立的
# `async def` 辅助函数（与 m1.6 里 `async def main(): ...` 的形状相同），
# 并在 fetch_product_fact 内部用 asyncio.run(...) 调用它。

# 任何失败（没有网络、工具出错）时，回退到 PLACEHOLDER_FACT，让这个练习
# 无论如何都能跑起来。
# ════════════════════════════════════════════════════════════════════════

# 这里不需要登录、API key 或账号：docs.langchain.com/mcp 是一个公共服务器，
# 而且这个调用只描述你在 TODO 2 中已经拿到的产品。

# PLACEHOLDER_FACT 存在纯粹是为了让脚本在文档服务器暂时不可达时仍能跑完，
# 跟任何认证步骤无关。
PLACEHOLDER_FACT = "尚未连接真实数据：请用一条来自真实 MCP 的事实替换这里"


@tool
def fetch_product_fact(product: str) -> str:
    """查找一句有依据、有事实根据的话，介绍你匹配到的 LangChain 产品。
    在 score_and_match 之后紧接着调用它，并传入它返回的产品名。"""
    raise NotImplementedError("TODO 3：见上面的注释块")


# ════════════════════════════════════════════════════════════════════════
# TODO 4（课程 1.7，消息、线程与检查点：线程）
# 在这里再加一个角色键（试试上面已经写好的 "ancient_mummy" 或
# "savage_critic"），让它运行在独立的线程里。

# 你会拿到多张卡片来对比，它们都在评判同一份问卷答案。
# ════════════════════════════════════════════════════════════════════════

JUDGES_TO_RUN = ["your_persona"]  # TODO 4：例如 ["your_persona", "ancient_mummy"]


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
            model=model,  # TODO 6（课程 1.3，模型，可选）：从 models import strong_model 并在这里试用
            interrupt_on=None,  # TODO 5（课程 1.8，人机协作：决策类型）：给 post_card 加上门禁，例如 {"post_card": True}
        )
    print(f"\n卡片已保存到 {OUTPUT_DIR}/")