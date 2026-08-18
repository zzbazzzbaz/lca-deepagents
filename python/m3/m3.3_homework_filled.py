# python/m3/m3.3_homework_filled.py
"""m3.3_homework.py 的参考副本，已将 TODO 1 和 TODO 2 填写完成，以便你能端到端运行它，
看看“完成”是什么样子。这只是众多可行答案中的一种，所以你的答案可能不同。
尽情探索吧！"""

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

from models import model

store = InMemoryStore()
memory_path = "/memories/AGENTS.md"
store_memory_path = "/AGENTS.md"

CONTEXT_A = {"workspace_id": "homework", "user_id": "u_you"}
CONTEXT_B = {"workspace_id": "homework", "user_id": "u_teammate"}


def namespace_from_context(context):
    return ("memory", context["workspace_id"], context["user_id"])


def memory_namespace(runtime):
    return namespace_from_context(runtime.context)


# TODO 1 已填写
def build_seed_memory_a() -> str:
    return """\
# 室内绿植笔记

## 浇水
- 琴叶榕每 10 天浇一次水，不固定在某个星期几；先检查土壤表层一英寸。
- 窗台上的多肉只在土壤完全干透时才浇水，大约每 2-3 周一次。

## 光照
- 绿萝和虎尾兰耐阴，养在走廊里。
- 其他植物都需要朝南的窗户。
"""


def build_seed_memory_b() -> str:
    return """\
# 香草园笔记

## 浇水
- 罗勒和薄荷喜欢持续湿润的土壤；夏天每天检查。
- 迷迭香耐旱；只有在表层两英寸变干时才浇水。

## 光照
- 这三种香草都养在厨房窗台上，那里能晒到上午的阳光。
"""


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


# TODO 2 已填写
RECALL_QUESTION = "琴叶榕应该多久浇一次水，绿萝养在哪里？"
REMEMBER_MESSAGE = (
    "记住：我刚给琴叶榕换了盆，所以接下来的 3 周先不要给它浇水，"
    "让根系稳定下来。请更新你的记忆。"
)
LEAK_CHECK_QUESTION = "琴叶榕应该多久浇一次水，绿萝养在哪里？"

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
