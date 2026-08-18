# python/m4/data/prepare_corpus.py
"""用于第 4.3 模块"被破坏的手稿"实验的一次性准备脚本。

从古腾堡计划下载三部公共领域的散文译本，把它们的 HTML/样板文本剥离成
纯文本，把 60 个卷的标题统一规范化为同一种格式，在不均匀的位置拼接进
一组固定的不合时代"破坏"句子，然后写出：

  epic_corpus.txt  — 合并后的、被破坏的语料，学生们的分派任务对象
  epic_corpus_key.json — 植入的破坏内容以及每个句子所在的卷

来源（在美国均为公共领域；译者早已过世）：
  - 《伊利亚特》，Samuel Butler 译（1898）   — 古腾堡计划 #2199
  - 《奥德赛》，Samuel Butler 译（1900） — 古腾堡计划 #1727
  - 《埃涅阿斯纪》，J. W. Mackail 译（1885）  — 古腾堡计划 #22456

本脚本不属于实验本身——上面两个文件已经提交到本目录中。只有当你想要
重新生成它们时才需要再次运行它（例如要修改植入的破坏内容）。
"""

import json
import re
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent

SOURCES = {
    "ILIAD": {
        "url": "https://www.gutenberg.org/files/2199/2199-h/2199-h.htm",
        "heading": re.compile(r'<h2><a id="chap(\d+)"></a>BOOK ([IVXLC]+)\.</h2>'),
        "count": 24,
    },
    "ODYSSEY": {
        "url": "https://www.gutenberg.org/files/1727/1727-h/1727-h.htm",
        "heading": re.compile(r'<h2><a name="chap(\d+)"></a>\s*BOOK ([IVXLC]+)</h2>'),
        "count": 24,
    },
    "AENEID": {
        "url": "https://www.gutenberg.org/files/22456/22456-h/22456-h.htm",
        "heading": re.compile(r'<h2><a name="BOOK_\w+" id="BOOK_\w+"></a>BOOK \w+</h2>'),
        "count": 12,
    },
}

# 植入的破坏内容：(epic, book_number, sentence, position="middle"/"end")。
# 故意分布不均——几卷里有两处，大多数卷为零处。
CORRUPTIONS = [
    ("ILIAD", 2, "A vending machine hummed faintly beside the Scaean gates."),
    ("ILIAD", 9, "Patroclus adjusted his smartwatch before donning the borrowed armor."),
    ("ILIAD", 9, "Achilles paused to check his bronze pager before returning to the battle line."),
    ("ILIAD", 16, "Somewhere beyond the ships, a food truck sold roasted chestnuts to the Myrmidons."),
    ("ILIAD", 23, "Hector paused to refresh his podcast feed before facing Achilles."),
    ("ODYSSEY", 1, "Telemachus updated his status to 'it's complicated' before the suitors arrived."),
    ("ODYSSEY", 5, "Odysseus checked his phone for a signal before addressing the Cyclops."),
    ("ODYSSEY", 12, "The sirens' song briefly buffered (because the free version has ads) before resuming its melody."),
    ("ODYSSEY", 12, "Circe's swine wore tiny name tags that read 'Hello, my name is.'"),
    ("ODYSSEY", 20, "Penelope scrolled through a catalog of suitors on her tablet."),
    ("AENEID", 2, "Dido kept a small espresso machine in the corner of her palace."),
    ("AENEID", 2, "Aeneas glanced at Google Maps of the Mediterranean before setting sail."),
    ("AENEID", 7, "A traffic light blinked uselessly at the gates of Latium."),
    ("AENEID", 11, "Turnus paused to check the weather forecast before the final duel."),
]

TAG_RE = re.compile(r"<[^>]+>")
PG_MARKER_RE = re.compile(r"\*\*\* (START|END) OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*")
PAGE_MARKER_RE = re.compile(r"\[Pg \d+\]")
BLANK_RUN_RE = re.compile(r"\n{3,}")


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def strip_html(chunk: str) -> str:
    # 在下方的通用标签剥离 *之前*，先在 </p> 边界强制插入真实的段落换行，
    # 因为源 HTML 中的周围空白太不一致，无法在稍后切分段落时依赖它。
    chunk = re.sub(r"</p\s*>", "\n\n", chunk)
    chunk = re.sub(r"<br\s*/?>", "\n", chunk)
    text = TAG_RE.sub(" ", chunk)
    text = PAGE_MARKER_RE.sub("", text)
    import html as html_module
    text = html_module.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = BLANK_RUN_RE.sub("\n\n", text)
    return text.strip()


def split_books(epic: str, raw: str) -> dict:
    """返回一部史诗原始 HTML 的 {卷号: 纯文本}。"""
    start = PG_MARKER_RE.search(raw)
    body = raw[start.end():] if start else raw
    cfg = SOURCES[epic]
    matches = list(cfg["heading"].finditer(body))
    books = {}
    for i, m in enumerate(matches):
        book_num = i + 1  # 标题按卷序出现
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        books[book_num] = strip_html(body[m.end():end])
    if len(books) != cfg["count"]:
        raise RuntimeError(f"{epic}: 预期 {cfg['count']} 卷，实际找到 {len(books)} 卷")
    return books


def splice_corruption(text: str, sentence: str, slot: int, slots_in_book: int) -> str:
    """把 `sentence` 插入到全卷大约 slot/slots_in_book 处的一个段落末尾，
    这样同一卷里的多处破坏会落在不同位置，而不会堆在同一段落里。"""
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    idx = min(len(paragraphs) - 1, max(0, (len(paragraphs) * slot) // (slots_in_book + 1)))
    paragraphs[idx] = paragraphs[idx].rstrip() + " " + sentence
    return "\n\n".join(paragraphs)


def main():
    all_books = {}
    for epic in SOURCES:
        print(f"正在获取 {epic}...")
        raw = fetch(SOURCES[epic]["url"])
        all_books[epic] = split_books(epic, raw)
        print(f"  已提取 {len(all_books[epic])} 卷")

    # 按 (epic, book) 对破坏内容分组，以便在一卷内分配不同的插入槽位。
    slots_used = {}
    key_entries = []
    for epic, book_num, sentence in CORRUPTIONS:
        slot_key = (epic, book_num)
        slots_used[slot_key] = slots_used.get(slot_key, 0) + 1
    slot_counter = {}
    for epic, book_num, sentence in CORRUPTIONS:
        slot_key = (epic, book_num)
        slot_counter[slot_key] = slot_counter.get(slot_key, 0) + 1
        total_slots = slots_used[slot_key]
        all_books[epic][book_num] = splice_corruption(
            all_books[epic][book_num], sentence, slot_counter[slot_key], total_slots
        )
        key_entries.append({"epic": epic, "book": book_num, "sentence": sentence})

    # 按史诗顺序组装合并后的语料：《伊利亚特》《奥德赛》《埃涅阿斯纪》。
    parts = []
    for epic in ("ILIAD", "ODYSSEY", "AENEID"):
        for book_num in sorted(all_books[epic]):
            parts.append(f"=== {epic} BOOK {book_num} ===\n\n{all_books[epic][book_num]}")
    corpus = "\n\n".join(parts) + "\n"

    corpus_path = OUT_DIR / "epic_corpus.txt"
    corpus_path.write_text(corpus, encoding="utf-8")
    key_path = OUT_DIR / "epic_corpus_key.json"
    key_path.write_text(json.dumps(key_entries, indent=2), encoding="utf-8")

    print(f"\n已写入 {corpus_path}（{len(corpus):,} 字符，约 {len(corpus.split()):,} 词）")
    print(f"已写入 {key_path}（{len(key_entries)} 处植入的破坏内容）")


if __name__ == "__main__":
    main()