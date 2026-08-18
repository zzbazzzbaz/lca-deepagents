# python/m4/m4.3_run_manuscript.py
"""运行手稿代理，然后用已知的、植入在 data/epic_corpus_key.json 中的破坏
内容对它找出的结果进行自查——这是一种即时、精确的方式，用来确认工作流
按卷分派是否真的覆盖了所有内容。

这个检查只是为了让你在学习实验的过程中获得反馈，不是提交的评分：
密钥与语料一起公开放在那里。
"""

import json
from pathlib import Path

from m4_3_manuscript_agent import agent

DATA_DIR = Path(__file__).resolve().parent / "data"

result = agent.invoke(
    {
        "messages": [{
            "role": "user",
            "content": "运行一个工作流，找出手稿中每一个被破坏的句子。",
        }]
    },
    config={"recursion_limit": 200},
)

report = result["messages"][-1].content
print(report)

seeded = json.loads((DATA_DIR / "epic_corpus_key.json").read_text())
seeded_sentences = {entry["sentence"] for entry in seeded}
found_sentences = {s for s in seeded_sentences if s in report}

missed = seeded_sentences - found_sentences
print(f"\n自查：报告中有 {len(found_sentences)}/{len(seeded_sentences)} 处植入的破坏内容。")
if missed:
    print("遗漏的句子：")
    for s in sorted(missed):
        print(f"  - {s}")