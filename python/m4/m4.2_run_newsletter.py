# python/m4/m4.2_run_newsletter.py
"""运行编辑代理，并把它产出的所有内容保存下来。

关于文件处理的说明：Deep Agents *可以*获得真实的本地磁盘访问权限
（通过 FilesystemBackend），但我们刻意不给。这个代理运行在默认的
StateBackend 上，所以它的写入落在代理状态里，而不是你的机器上。
允许代理写入你的文件系统是一种需要你授予的权限——而且当代理在根据不可信的
网页搜索内容行事时，你不应该授予。作为替代，这段受信任的主机代码在 invoke
之后把文件从代理状态（"files" 通道）中读出来，并把它们镜像到 OUT_DIR：
包括最终成稿的 newsletter，以及每个研究者原始的 /research/<文体>/ 存档，
这样你就能检查被隔离在那里的内容。
"""

from pathlib import Path

from m4_2_newsletter_agent import agent

OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(exist_ok=True)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "请整理好本周的通讯稿。"}]},
    config={"recursion_limit": 50},
)

# 编辑代理的最终回复（协调总结）。
print(result["messages"][-1].content)

# 代理产出的所有内容都存在于代理状态中（不在你的磁盘上——它运行在默认的
# StateBackend）。把全部内容取出来并镜像到 OUT_DIR：包括编辑代理的
# newsletter，以及每个研究者原始的 /research/<文体>/ 存档。
files = result.get("files", {})
if "/output/newsletter.html" not in files:
    raise SystemExit("代理没有写入 /output/newsletter.html")


def _content(fd) -> str:
    # FileData 条目是以 "content" 为键的字典（字符串，或旧的列表形式）。
    body = fd["content"] if isinstance(fd, dict) else fd
    return "\n".join(body) if isinstance(body, list) else body


out_root = OUT_DIR.resolve()
print("\n正在把代理文件写入磁盘：")
for path in sorted(files):
    # 把代理状态中的布局映射到 OUT_DIR：/output/* 落在根目录，
    # /research/<文体>/* 保留其文件夹结构。
    rel = path[len("/output/"):] if path.startswith("/output/") else path.lstrip("/")
    dest = (OUT_DIR / rel).resolve()

    # 文件内容是【不可信的】网页搜索文本，而且路径来自代理——所以先验证
    # 目标路径始终落在 OUT_DIR 之内（拒绝任何 ../ 穿越），再写入，
    # 并且只写纯文本。
    if dest != out_root and out_root not in dest.parents:
        print(f"  已跳过（越出输出目录）：{path}")
        continue

    dest.parent.mkdir(parents=True, exist_ok=True)
    body = _content(files[path])
    dest.write_text(body, encoding="utf-8")
    print(f"  {path}  ->  {dest.relative_to(out_root)}  ({len(body):,} 字符)")

print(f"\n请在浏览器中打开 {OUT_DIR / 'newsletter.html'} 阅读本周的通讯稿。")
