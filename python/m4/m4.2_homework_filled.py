# python/m4/m4.2_homework_filled.py
"""m4.2_homework.py 的参考副本，其中 TODO 1 和 TODO 2 已被填写完成，
让你可以端到端运行，看看"完成"的样子。这只是众多可行答案之一，
你的答案可能不同。去探索吧！"""

from deepagents import FilesystemPermission, create_deep_agent

from models import model, strong_model

SCRATCH_ROOT = "/scratch"


def scratch_path(subagent_name: str) -> str:
    return f"{SCRATCH_ROOT}/{subagent_name}/notes.md"


def scratch_permissions(subagent_name: str) -> list:
    return [
        FilesystemPermission(operations=["read", "write"], paths=[f"{SCRATCH_ROOT}/{subagent_name}/**"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
    ]


def scratch_instruction(subagent_name: str) -> str:
    return (
        f'在作答之前，请对 "{scratch_path(subagent_name)}" 调用 write_file，'
        "写入你的原始笔记或推理过程。然后只使用整理后的结果给出最终答案——"
        "不要在回复中重复那些原始笔记。"
    )


def build_subagents(specs: list[dict]) -> list[dict]:
    team = []
    for spec in specs:
        name = spec["name"]
        team.append(
            {
                "name": name,
                "description": spec["description"],
                "system_prompt": spec["role_prompt"] + "\n\n" + scratch_instruction(name),
                "permissions": scratch_permissions(name),
            }
        )
    return team


# TODO 1 已填写
SUBAGENT_SPECS = [
    {
        "name": "workout-planner",
        "description": "为给定的目标、时间预算和可用器械设计一次单次训练课程。",
        "role_prompt": (
            "你是一名力量与体能教练。根据客户的训练目标、可用时间和器械，"
            "编写一次训练课程的内容：一个简短的热身、4-6 个带组数/次数的主项动作，"
            "以及一个放松整理。要考虑到给定的时间，让计划切实可行。"
        ),
    },
    {
        "name": "nutrition-advisor",
        "description": "针对给定的健身目标，给出膳食结构和食物替换建议。",
        "role_prompt": (
            "你是一名运动营养顾问。根据客户的训练目标（增肌、耐力、减脂等）"
            "以及他们提到的任何饮食限制，给出一个简单的每日膳食结构"
            "（不是严格的饮食计划）和 2-3 个有助于达成该目标的具体食物替换建议。"
        ),
    },
]


# TODO 2 已填写
MAIN_PROMPT = """你是教练，一个小型健身指导团队的负责人。
对于任何客户请求，使用 task 工具委派给你的专家：
- workout-planner 负责实际的动作安排
- nutrition-advisor 负责饮食和膳食指导

如果请求同时涉及这两个方面，就同时委派给两者。汇总他们的回复，
向客户呈现一个组合起来的、友好的完整计划。"""

USER_REQUEST = (
    "我正在为 8 周后的半程马拉松训练。我每周跑 3 天，想为其中一个不跑步的日子"
    "安排一次力量训练，同时希望得到关于跑步日与休息日应该怎么吃的建议。"
)

for _spec in SUBAGENT_SPECS:
    if _spec["name"].startswith("TODO-1"):
        raise NotImplementedError("TODO 1：请查看上面的注释块")
if MAIN_PROMPT.startswith("TODO 2") or USER_REQUEST.startswith("TODO 2"):
    raise NotImplementedError("TODO 2：请查看上面的注释块")

_team = build_subagents(SUBAGENT_SPECS)

MAIN_PERMISSIONS = [
    FilesystemPermission(operations=["write"], paths=[f"{SCRATCH_ROOT}/**"], mode="deny"),
]

agent = create_deep_agent(
    model=strong_model,
    name="Homework_Team_Agent",
    system_prompt=MAIN_PROMPT,
    subagents=_team,
    permissions=MAIN_PERMISSIONS,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": USER_REQUEST}]},
    config={"recursion_limit": 50},
)
print(result["messages"][-1].content)

files = result.get("files", {})
print("\n--- 草稿文件夹隔离检查 ---")
for spec in SUBAGENT_SPECS:
    path = scratch_path(spec["name"])
    print(f"  {path}: {'找到' if path in files else '未写入（子代理可能未被调用）'}")

scratch_files = [p for p in files if p.startswith(SCRATCH_ROOT + "/")]
expected = {scratch_path(spec["name"]) for spec in SUBAGENT_SPECS}
stray = [p for p in scratch_files if p not in expected]
if stray:
    print(f"  意外的草稿文件（隔离可能失败）：{stray}")
else:
    print("  没有游离的草稿文件——每个子代理都只写入了自己的文件夹。")
