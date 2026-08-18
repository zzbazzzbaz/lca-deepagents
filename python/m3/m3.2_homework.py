# python/m3/m3.2_homework.py
"""M3.2 作业：把参考文件打包进你的技能（Skill）。

核心思路
本实验的两个技能（qualify-lead 和 draft-pitch）各自都是单个扁平的 SKILL.md 文件，
所有内容都内联在其中。但本课还介绍了渐进式披露的第三个阶段：
一个技能可以指向与 SKILL.md 同目录存放的支持性文件（一份参考文档、一个模板、一个脚本），
agent 只在真正需要时才会去读取这些文件，而不是把所有内容都预先塞进系统提示里。
这份作业要求你为自己选定的一个主题或工作流（不是销售）编写一个技能，
该技能要打包第二个文件，其中包含 agent 需要但 SKILL.md 本身并不包含的细节，
然后从 trace 中确认 agent 在作答之前确实对第二个文件调用了 `read_file`，
而不是靠猜。

你要填写的内容
  TODO 1：编写你自己的 SKILL.md 内容。它必须指示 agent 为所需的特定细节
    读取一个 `reference.md` 文件（位于同一技能目录中），并且绝不能把这些细节
    内联重复写出来。frontmatter 中的 `name` 字段必须与下面的 SKILL_NAME 完全一致。
  TODO 2：编写 reference.md 的内容：你的技能指令所指并依赖的那些具体事实、数字或模板。
  TODO 3：编写一个系统提示和一个应能激活你技能的用户问题。

运行
  cd python
  uv run ./m3/m3.2_homework.py
"""

import tempfile
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from models import model

# 这个名称会成为技能的目录名。它必须与下面 build_skill_md() 中 frontmatter 里
# 你写的 `name:` 字段完全一致。
SKILL_NAME = "your-skill-name"
REFERENCE_PATH = f"/skills/{SKILL_NAME}/reference.md"


# ════════════════════════════════════════════════════════════════════════
# TODO 1：编写你自己的 SKILL.md 内容。
#
# 要求：
#   - YAML frontmatter，包含 `name`（必须等于上面的 SKILL_NAME）和
#     `description`（一句具体的话，描述何时使用该技能）。
#   - 步骤要告诉 agent 为完成任务的特定细节去打开 `reference.md`（位于同一技能目录）。
#   - 不要把这些细节写进 SKILL.md 本身；如果 agent 不读 reference.md 也能正确完成
#     任务，那就没有实践渐进式披露。
#
# 示例结构（删除这些并编写你自己的）：
#   return """---
#   name: your-skill-name
#   description: 当用户想要……时使用
#   ---
#
#   # 你的技能标题
#
#   **第 1 步：...**：...
#   **第 2 步：...**：在继续之前，请读取本技能目录中的 reference.md，
#     以获得要使用的准确……。不要自行猜测。
#   """
# ════════════════════════════════════════════════════════════════════════

def build_skill_md() -> str:
    """TODO 1：以字符串形式返回你自己的 SKILL.md 内容。"""
    raise NotImplementedError("TODO 1：见上方注释块")


# ════════════════════════════════════════════════════════════════════════
# TODO 2：编写 reference.md 的内容。
#
# 这部分应包含你的 SKILL.md 所指并依赖的那些具体事实：一份评分标准、一组数字、
# 一个模板、一份检查清单。要具体到：一份不读它而产出的答案，
# 会明显不同于读了它而产出的答案。
# ════════════════════════════════════════════════════════════════════════

def build_reference_md() -> str:
    """TODO 2：返回你的技能 reference.md 的内容。"""
    raise NotImplementedError("TODO 2：见上方注释块")


# 把技能写入一个临时目录，使其能通过 FilesystemBackend 被发现，
# 这正是实验在 python/m3/skills/ 中所用的机制。
_tmp_root = Path(tempfile.mkdtemp(prefix="m3_2_homework_"))
_skill_dir = _tmp_root / "skills" / SKILL_NAME
_skill_dir.mkdir(parents=True, exist_ok=True)
(_skill_dir / "SKILL.md").write_text(build_skill_md())
(_skill_dir / "reference.md").write_text(build_reference_md())

backend = FilesystemBackend(root_dir=str(_tmp_root), virtual_mode=True)
print(f"技能文件已写入: {_skill_dir}")


# ════════════════════════════════════════════════════════════════════════
# TODO 3：编写一个系统提示和一个可触发该技能的问题。
#
# SYSTEM_PROMPT：给 agent 一个你选定的人设（一个名字、一种语气，随你发挥）。
# USER_QUESTION：一个问题，应与你技能 `description` 足够贴近，使 agent 会激活它。
# ════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """TODO 3：用你自己的系统提示替换这段文字。"""
USER_QUESTION = "TODO 3：用一句应能触发你技能的问题替换这段文字。"

agent = create_deep_agent(
    model=model,
    name="Homework_Agent",
    backend=backend,
    skills=["/skills"],
    system_prompt=SYSTEM_PROMPT,
)

result = agent.invoke({"messages": [{"role": "user", "content": USER_QUESTION}]})
print(result["messages"][-1].content)

read_calls = [
    call
    for msg in result["messages"]
    for call in getattr(msg, "tool_calls", [])
    if call["name"] == "read_file"
]
reference_was_read = any(call["args"].get("file_path") == REFERENCE_PATH for call in read_calls)
print(f"\n--- agent 是否读取了 {REFERENCE_PATH}? {reference_was_read} ---")
if not reference_was_read:
    print(
        "没有读取。要么是 SKILL.md 没有清楚地指示它去读，"
        "要么是这个任务不读 reference.md 里的细节也能回答。"
    )
