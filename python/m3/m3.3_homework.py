# python/m3/m3.3_homework.py
"""M3.3 作业：证明用户之间的记忆隔离。

核心思路
本实验把记忆限定在单一的固定 workspace_id/user_id 上，并且始终只在一个上下文下运行
agent，因此用户之间的隔离在课的“记忆的作用域”一节中只是口头描述，
从未在代码中真正展示过。这份作业要求你在两个共享同一个 workspace、但属于不同用户的
不同上下文下运行同一个 agent，分别给它们写入不同的事实，
并确认你在上下文 A 下让 agent 记住的某个细节，绝不会泄漏到 agent 在上下文 B 下
所说的话或所存的内容里。

你要填写的内容
  TODO 1：为你选定的一个领域（不是编码规范）写两条不同的种子记忆，
    一条用于 CONTEXT_A，一条用于 CONTEXT_B。两者应围绕大致相同的主题，
    这样一旦发生泄漏就会非常明显，但具体内容要不同。
  TODO 2：编写三条提示：一个仅凭 A 的种子记忆就能回答的问题；
    一条“记住这个”的消息，在上下文 A 下添加一条新的、独特的事实；
    以及同一个问题在上下文 B 下再次被询问（它应得到 B 自己的答案，或没有答案，
    绝不能是 A 的答案）。

运行
  cd python
  uv run ./m3/m3.3_homework.py
"""

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

from models import model

store = InMemoryStore()
memory_path = "/memories/AGENTS.md"
store_memory_path = "/AGENTS.md"

# 同一个 workspace，两个不同的用户——这正是课上警告的：
# 如果处理不当，可能会在用户之间泄漏私有记忆的作用域模式。
CONTEXT_A = {"workspace_id": "homework", "user_id": "u_you"}
CONTEXT_B = {"workspace_id": "homework", "user_id": "u_teammate"}


def namespace_from_context(context):
    return ("memory", context["workspace_id"], context["user_id"])


def memory_namespace(runtime):
    return namespace_from_context(runtime.context)


# ════════════════════════════════════════════════════════════════════════
# TODO 1：编写两条不同的种子记忆。
#
# 选一个真正属于你的领域（不是代码风格规范）：一份菜谱、一份阅读清单、
# 一份浇水日程、一份训练日志。为 CONTEXT_A（你）写一个版本，
# 为 CONTEXT_B（一位队友）写一个不同的版本，主题大致相同，但具体内容不同。
#
# 示例结构（删除这些并编写你自己的）：
#   def build_seed_memory_a() -> str:
#       return """\
#       # <你的领域> 笔记
#       - <事实 1>
#       """
#   def build_seed_memory_b() -> str:
#       return """\
#       # <你的领域> 笔记（队友的）
#       - <一个不同的事实>
#       """
# ════════════════════════════════════════════════════════════════════════

def build_seed_memory_a() -> str:
    """TODO 1：返回 CONTEXT_A 的初始记忆内容。"""
    raise NotImplementedError("TODO 1：见上方注释块")


def build_seed_memory_b() -> str:
    """TODO 1：返回 CONTEXT_B 的初始记忆内容。"""
    raise NotImplementedError("TODO 1：见上方注释块")


store.put(namespace_from_context(CONTEXT_A), store_memory_path, create_file_data(build_seed_memory_a()))
store.put(namespace_from_context(CONTEXT_B), store_memory_path, create_file_data(build_seed_memory_b()))

agent = create_deep_agent(
    model=model,
    name="Homework_Memory_Agent",
    backend=CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend(namespace=memory_namespace)},
    ),
    store=store,
    memory=[memory_path],
    system_prompt="你是这个项目的一名乐于助人的私人助理。",
)


# ════════════════════════════════════════════════════════════════════════
# TODO 2：编写你的三条提示。
#
# RECALL_QUESTION：可直接由 build_seed_memory_a() 回答，在 CONTEXT_A 下询问。
# REMEMBER_MESSAGE：在 CONTEXT_A 下引入一条两个种子记忆里都没有的、全新的、独特的
#   事实（要具体——一个虚构的数字或名称——这样一旦泄漏到上下文 B 就一目了然）。
# LEAK_CHECK_QUESTION：与 RECALL_QUESTION 相同的问题，但这次在 CONTEXT_B 下再次询问。
#   如果隔离成立，答案应反映 B 自己的种子记忆，而不是 A 的。
# ════════════════════════════════════════════════════════════════════════

RECALL_QUESTION = "TODO 2：用一句仅凭 build_seed_memory_a() 就能回答的问题替换这段文字。"
REMEMBER_MESSAGE = "TODO 2：用一条在上下文 A 下引入一条新的、独特事实的‘记住这个’消息替换这段文字。"
LEAK_CHECK_QUESTION = "TODO 2：用与 RECALL_QUESTION 相同的问题替换这段文字。"

# 1. 上下文 A 从它自己的种子记忆中回忆。
result_a1 = agent.invoke({"messages": [{"role": "user", "content": RECALL_QUESTION}]}, context=CONTEXT_A)
print("--- 上下文 A，问题 1 ---")
print(result_a1["messages"][-1].content)

# 2. 上下文 A 学会一条新的、独特的事实。
result_a2 = agent.invoke({"messages": [{"role": "user", "content": REMEMBER_MESSAGE}]}, context=CONTEXT_A)
print("\n--- 上下文 A，问题 2（记住） ---")
print(result_a2["messages"][-1].content)

# 3. 上下文 B 询问同一个问题。它不应看到来自 A 的任何内容。
result_b = agent.invoke({"messages": [{"role": "user", "content": LEAK_CHECK_QUESTION}]}, context=CONTEXT_B)
print("\n--- 上下文 B，泄漏检查问题 ---")
print(result_b["messages"][-1].content)

memory_a = store.get(namespace_from_context(CONTEXT_A), store_memory_path).value["content"]
memory_b = store.get(namespace_from_context(CONTEXT_B), store_memory_path).value["content"]
print("\n--- 上下文 A 存储的 AGENTS.md ---")
print(memory_a)
print("\n--- 上下文 B 存储的 AGENTS.md ---")
print(memory_b)

if memory_a == memory_b:
    print("\n隔离失败：两个上下文共享了完全相同的存储记忆。")
else:
    print("\n各上下文的存储记忆彼此不同，符合预期。")
