# python/m3/m3.2_homework_filled.py
"""m3.2_homework.py 的参考副本，已将 TODO 1-3 填写完成，以便你能端到端运行它，
看看“完成”是什么样子。这只是众多可行答案中的一种，所以你的答案可能不同。
尽情探索吧！"""

import tempfile
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from models import model

SKILL_NAME = "plan-a-workout"
REFERENCE_PATH = f"/skills/{SKILL_NAME}/reference.md"


# TODO 1 已填写
def build_skill_md() -> str:
    return """---
name: plan-a-workout
description: 当用户想要针对特定一天或目标制定一份结构化的锻炼计划时使用。
---

# 制定一次锻炼计划

根据用户的目标和可用时间，制定一份单次训练的锻炼计划。

**第 1 步：目标**：如果用户消息里还不明确，就问他们今天要练什么（力量、增肌、
耐力还是柔韧性）。

**第 2 步：限制条件**：确认他们有多少时间、有哪些器材可用（仅自重、哑铃、还是完整健身房）。

**第 3 步：查表取数**：在写组数和次数之前，先读取本技能目录中的 `reference.md`，
以获得针对所陈述目标的确切组数/次数/休息表。不要自行猜测这些数字；
它们随目标不同而变化，而且本技能的评分标准对它们有明确规定。

**第 4 步：热身**：始终包含 5 分钟与目标相符的热身。

**第 5 步：主体部分**：使用 reference.md 中的组数/次数/休息来编写 4-6 个动作，
使其符合所陈述的目标、时间和器材。

**第 6 步：放松**：以 2-3 分钟针对所练肌群的拉伸结束。

## 输出

以编号列表形式呈现计划：热身、主体部分（组数/次数/休息按 reference.md），然后是放松。
让整个计划对用户给出的时间来说是现实可行的。
"""


# TODO 2 已填写
def build_reference_md() -> str:
    return """# 组数 / 次数 / 休息评分标准

使用与用户所陈述目标匹配的那一行。不要偏离这些数字；
它们是为单次 20-30 分钟的训练校准的。

| 目标        | 组数  | 次数    | 组间休息        |
|-------------|------|--------|-----------------|
| 力量        | 4-5  | 4-6     | 90-120 秒       |
| 增肌        | 3-4  | 8-12    | 60-90 秒        |
| 耐力        | 2-3  | 15-20   | 30-45 秒        |
| 柔韧性      | 2-3  | 保持 30-60 秒（非次数） | 15-30 秒 |
"""


_tmp_root = Path(tempfile.mkdtemp(prefix="m3_2_homework_"))
_skill_dir = _tmp_root / "skills" / SKILL_NAME
_skill_dir.mkdir(parents=True, exist_ok=True)
(_skill_dir / "SKILL.md").write_text(build_skill_md())
(_skill_dir / "reference.md").write_text(build_reference_md())

backend = FilesystemBackend(root_dir=str(_tmp_root), virtual_mode=True)
print(f"技能文件已写入: {_skill_dir}")


# TODO 3 已填写
SYSTEM_PROMPT = """你是教练任，一位热情但务实的私人教练。请保持鼓励而实用的语气。"""
USER_QUESTION = "我有 30 分钟，只有一副哑铃。给我一份以力量为主的训练计划。"

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
