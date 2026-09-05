---
name: territory-report
description: "构建一份销售代表的区域销售报告——Jane 客户业务的营收、头部客户、头部类型和趋势——并附图表。当被要求提供区域报告、销售摘要、业绩数据，或询问'我的客户业务怎么样了'时使用。"
---

# 区域报告

一个指标类任务。数字来自数据库；图表由它们渲染而成。

## 1. 收集指标

请 **chinook-analyst** 提供 Jane 的客户业务（`SupportRepId = 3`）数据：

- 总营收和发票数量。
- 按营收排名的头部客户（带金额）。
- 按类型的营收（针对 Jane 的客户）。
- 任何明显的趋势（例如按年份的营收，如果有用的话）。

获取精确数字；如果需要合并结果，用**代码解释器**做算术。

## 2. 撰写报告

- 用代码解释器获取时间戳：
  `new Date().toISOString().slice(0, 19).replace(/:/g, '-')` ——这是日期加时间，
  而不仅仅是日期，这样同一天稍后再次请求的报告不会静默覆盖早先的那份。
- 用 `write_file` 把一份清晰的 Markdown 报告写到
  `/outputs/territory_report-<timestamp>.md`：头条总额、头部客户列表，
  以及一张按类型营收的表格。

## 3. 图表

用 `write_file` 编写一个简短的 Python 脚本，用 matplotlib 把按类型营收的数据
绘制成饼图，并保存到 `/outputs/territory_chart-<timestamp>.png`（与第 2 步使用
相同的时间戳），然后用 `execute` 运行它（如果 matplotlib 尚未安装，先安装）。
在报告中引用图片时只使用裸文件名（例如 `![Revenue by Genre](territory_chart-<timestamp>.png)`），
而不要用绝对的 `/outputs/...` 路径——当 Jane 下载报告和图表时，两者会一起落在
同一个本地文件夹中，没有 `outputs` 子目录，因此相对文件名才能真正解析；
绝对路径只对下面聊天回复中的内嵌图片才是正确的。

## 完成

告诉 Jane 报告和图表保存到了哪里，并附上头条营收数字。在回复中把图表本身作为
Markdown 图片内嵌——`![Revenue by Genre](/outputs/territory_chart-<timestamp>.png)`——
使用该精确的绝对路径（第 3 步中相同的时间戳文件名），而不仅仅在文本中提及文件名，
这样它能在聊天中直接渲染，而不是只显示为一个下载链接。
