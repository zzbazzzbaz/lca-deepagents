---
name: territory-report
description: "为销售代表的销售区域生成报告——Jane 客户盘子的收入、头部客户、头部流派和趋势——并配图表。当被要求提供区域报告、销售摘要、业绩数字，或询问"我的盘子经营得如何"时使用。"
---

# 区域报告

一项指标任务。数字来自数据库；图表由这些数字渲染。

## 1. 收集指标

请 **chinook-analyst** 提供 Jane 的客户盘子（`SupportRepId = 3`）数据：

- 总收入与发票数量。
- 按收入排名的头部客户（含金额）。
- 按流派统计的收入（针对 Jane 的客户）。
- 任何明显的趋势（例如按年份的收入，如果有用的话）。

获取精确的数字；如果需要合并结果，用**代码解释器**做算术。

## 2. 撰写报告

- 用代码解释器获取今天的日期（Python：`import datetime; datetime.date.today().isoformat()`）。
- 用 `write_file` 将一份清晰的 Markdown 报告写入 `/outputs/territory_report-<date>.md`：
  头条总额、头部客户列表，以及按流派收入的表格。

## 3. 图表

调用 `render_pie_chart`，传入按流派收入的标签和数值，保存为
`territory_chart.png`。在报告中引用该图片。

## 完成

告诉 Jane 报告和图表保存在哪里，并给出头条收入数字。