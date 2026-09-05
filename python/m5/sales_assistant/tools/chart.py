# python/m5/tools/chart.py
"""根据结构化数据渲染图表——无需执行代码。

这是一个固定用途的工具，而不是代码执行沙箱（sandbox）：模型提供
标题和两个平行的列表（绝不是代码），因此从一开始就没有需要
加固的执行面。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from langchain_core.tools import tool

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


@tool
def render_pie_chart(title: str, labels: list[str], values: list[float], filename: str) -> str:
    """渲染带标签的饼图并保存为 outputs/ 目录下的 PNG 文件。

    参数：
        title: 图表标题。
        labels: 每个扇区一个标签（例如流派名称）。
        values: 每个标签一个数值（例如收入），长度与 labels 相同。
        filename: 输出文件名，例如 "territory_chart.png"。任何目录
            部分都会被剥离——文件始终保存到 outputs/ 目录中。
    """
    if len(labels) != len(values):
        return "错误：labels 和 values 的长度必须相同。"

    # 剥离任何目录部分，这样构造的文件名就无法写到 outputs/ 之外。
    safe_name = Path(filename).name
    if not safe_name:
        return "错误：文件名不能为空。"

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.0f%%")
    ax.set_title(title)

    OUTPUTS_DIR.mkdir(exist_ok=True)
    path = OUTPUTS_DIR / safe_name
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)

    return f"已保存到 outputs/{safe_name}"