# python/m4/m4.2_homework.py
"""M4.2 作业：为每个子代理分配自己的隔离草稿文件夹。

核心思想
实验中的文体研究者子代理各自把原始检索笔记写入被分配到的
/research/<文体>/ 文件夹，通过 FilesystemPermission 作用域把它们隔离在
编辑者的上下文之外：研究者可以写入 /research/** 下，而编辑者不能。

这份作业要求你为一个由你自行选择的领域（例如旅行规划、家庭装修）
构建一支由 2 种子代理组成的小团队，每种子代理在 /scratch/<名称>/ 下
拥有自己私有的、受权限作用域限制的文件夹，在作答前先把原始笔记存放进去。
下面的框架已经帮你接好了草稿文件夹、权限以及"先写再答"的指令；
你只需要决定你的两个子代理是谁。

需要你填写的内容
  TODO 1：对于 SUBAGENT_SPECS 中的两个条目，分别填写 "name"、
    "description"（主代理应在何时调用它）和 "role_prompt"
    （这个子代理是谁、它的职责是什么）。其余一切——草稿文件夹、权限、
    作答前保存原始笔记的指令——都已经帮你处理好了。
  TODO 2：编写主代理的系统提示词，告诉它任务的哪一部分该调用哪个子代理，
    以及一个应该触发它把任务委派给两个子代理的用户请求。

运行方式
  cd python
  uv run ./m4/m4.2_homework.py
"""

from deepagents import FilesystemPermission, create_deep_agent

from models import model, strong_model

SCRATCH_ROOT = "/scratch"


def scratch_path(subagent_name: str) -> str:
    return f"{SCRATCH_ROOT}/{subagent_name}/notes.md"


def scratch_permissions(subagent_name: str) -> list:
    """把子代理限定为只能写入它自己的草稿文件夹——和实验里用于
    research_permissions/editor_permissions 的"首个匹配生效、先允许后拒绝"
    模式相同。"""
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


# ════════════════════════════════════════════════════════════════════════
# TODO 1：填写你的两个子代理。
#
# 对于每个条目："name" 是主代理调用它时使用的名称，使用 kebab-case
# （例如 "flight-finder"）。"description" 用于主代理决定该调用哪一个。
# "role_prompt" 是这个子代理自己的职责描述——不要在这里提到草稿文件
# 或 write_file，那些会由程序自动加上。
# ════════════════════════════════════════════════════════════════════════

SUBAGENT_SPECS = [
    {
        "name": "TODO-1-name-1",
        "description": "TODO 1：主代理应在何时把任务委派给这个子代理？",
        "role_prompt": "TODO 1：这个子代理是谁，它的职责是什么？",
    },
    {
        "name": "TODO-1-name-2",
        "description": "TODO 1：主代理应在何时把任务委派给这个子代理？",
        "role_prompt": "TODO 1：这个子代理是谁，它的职责是什么？",
    },
]


# ════════════════════════════════════════════════════════════════════════
# TODO 2：编写主代理的系统提示词和一条触发请求。
#
# MAIN_PROMPT 应该按名称向主代理介绍每个子代理以及何时调用它
# （模仿实验中 EDITOR_PROMPT 是如何点名 genre-researcher 并解释其职责的）。
# USER_REQUEST 应该是一个能让主代理把任务委派给你的两个子代理的任务。
# ════════════════════════════════════════════════════════════════════════

MAIN_PROMPT = """TODO 2：请用你自己的主代理系统提示词替换这一句。"""
USER_REQUEST = "TODO 2：请用一条应能触发向两个子代理委派任务的请求替换这一句。"

for _spec in SUBAGENT_SPECS:
    if _spec["name"].startswith("TODO-1"):
        raise NotImplementedError("TODO 1：请查看上面的注释块")
if MAIN_PROMPT.startswith("TODO 2") or USER_REQUEST.startswith("TODO 2"):
    raise NotImplementedError("TODO 2：请查看上面的注释块")

_team = build_subagents(SUBAGENT_SPECS)

# 主代理也绝不能写入任何一个子代理的草稿文件夹。
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
