---
name: weekly-newsletter
description: "通过调研分销商的头部音乐类型并组装一个带样式的 HTML 页面，产出每周的 'This Week in Music' 客户新闻通讯。当被要求创建、撰写或发送每周新闻通讯或音乐新闻汇总时使用。"
---

# 每周新闻通讯

一个后台作业。启动它，然后让开——newsletter-agent 会调研每个类型并自己组装
完成后的 HTML。

## 1. 挑选类型

- 如果 Jane 指定了类型，就用那些。否则请 **chinook-analyst** 按营收给出整个
  目录中的前 4 个类型，并推荐那些。

## 2. 在后台启动

- 调用 `start_async_task(subagent_type="newsletter-agent", description=...)`
  **一次**，把类型列表放在 `description` 中（例如 "Research and
  assemble this week's newsletter for these genres: Rock, Latin, Jazz,
  Classical"）。它立即返回一个任务 ID；不会阻塞。
- 告诉 Jane 新闻通讯正在后台制作中，然后**停下**。不要轮询——等她下次询问时
  再检查。
- **不要**自己调研类型或组装新闻通讯——那完全是 newsletter-agent 的工作。

## 3. 当被问到是否就绪时

- 获取 task_id：调用 `list_async_tasks()` 并读取 newsletter-agent 条目的
  `task_id:` 字段。不要依赖对话早先出现的 task_id——它可能已滚出上下文或被
  摘要掉；`list_async_tasks` 从持久状态读取它，而不是从记忆读取。
- 调用 `check_async_task(task_id)`。
- 如果 `status` 还不是终态（`success` 或 `error`），向 Jane 汇报进度并停下——
  等她下次询问时再检查。
- 如果 `status` 是 `error`，告诉 Jane 本周新闻通讯无法制作，然后停下——
  没有可保存的 HTML。
- 如果 `status` 是 `success`，`result` 就是完成后的 HTML，逐字原样——
  这里无需再做 Markdown 转换，newsletter-agent 已经做过了。
  在同一回合内立即继续第 4 步——不要先征求 Jane 的许可。她在第 1 步时
  就已经要求制作新闻通讯了；一个已完成的后台作业不是需要重新确认的新决策。

## 4. 保存（只保存一次）

- 同一个 task_id 可能被询问多次（例如 Jane 在你已经保存之后再次问"好了吗？"）——
  不要保存重复文件。要确定性地检查，而不是依赖对话记忆（它可能被摘要掉）：
  调用 `glob("/outputs/newsletter-*-<task_id, first 8 chars>.html")`。
  如果已经有匹配的文件，告诉 Jane 它已保存在该路径，然后停下。
- 否则，用代码解释器获取时间戳：
  `new Date().toISOString().slice(0, 19).replace(/:/g, '-')` ——这是日期加时间，
  而不仅仅是日期，这样同一天稍后真正的新新闻通讯请求会产生一个新文件，
  而不是覆盖上一个。
- 把第 3 步的 HTML **原样**写入 `write_file`——不做编辑、不加评论——
  保存到 `/outputs/newsletter-<timestamp>-<task_id, first 8 chars>.html`。

## 完成

告诉 Jane 新闻通讯保存到了哪里。如果你刚保存的 HTML 提到某个类型没能入选
（当某个类型的调研失败时 newsletter-agent 自己会注明这一点），用你自己的话
转达这一信息。
