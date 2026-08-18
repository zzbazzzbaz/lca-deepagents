from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

from models import model

store = InMemoryStore()
memory_path = "/memories/AGENTS.md"
store_memory_path = "/AGENTS.md"
demo_context = {"workspace_id": "acme", "user_id": "u_alex"}


def namespace_from_context(context):
    return (
        "memory",
        context["workspace_id"],
        context["user_id"],
    )


def memory_namespace(runtime):
    return namespace_from_context(runtime.context)


store.put(
    namespace_from_context(demo_context),
    store_memory_path,
    create_file_data("""\
# 项目规范

## 代码风格
- 所有函数都必须有类型注解
- 字符串格式化请使用 f-string
- 最大行长 88 个字符
- 文件操作请使用 `pathlib.Path`，而不是 `os.path`

## 工作流
- 用以下命令运行测试：`uv run pytest`
- CI 流水线会在每次推送到 `main` 时运行
- 尽早打开草稿 PR，这样评审者可以一路跟进
"""),
)

agent = create_deep_agent(
    model=model,
    name="Memory_Agent",
    backend=CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend(namespace=memory_namespace)},
    ),
    store=store,
    memory=[memory_path],
    system_prompt="你是这个项目的一名乐于助人的编程助手。",
)

# 第一次调用：agent 使用记忆内容作答
result = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "在这个项目中，我应该用什么工具来处理文件路径？"}
        ]
    },
    context=demo_context,
)
print("--- 问题 1 ---")
print(result["messages"][-1].content)

# 第二次调用：agent 写入记忆
result2 = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "记住：团队改用 ruff 来做 lint 了。请更新你的记忆。",
            }
        ]
    },
    context=demo_context,
)
print("\n--- 问题 2 ---")
print(result2["messages"][-1].content)

print("\n--- 写入后的 AGENTS.md ---")
stored_memory = store.get(namespace_from_context(demo_context), store_memory_path)
print(stored_memory.value["content"])
