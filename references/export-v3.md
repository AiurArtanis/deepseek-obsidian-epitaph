# DeepSeek 导出结构 v3

此页记录转换器实际读取的字段，不是所有 DeepSeek 历史或未来导出版本的兼容保证。

```text
export/
├─ manifest.json
├─ chat_session_index.json
├─ user.json
└─ chat_sessions/
   ├─ <session-id>.json
   └─ <session-id>_files/<file-id>_<name>
```

- `manifest.json`：`export_format_version: 3`。
- 索引是数组：`id`、`title`、`pinned`、`message_count`、`inserted_at`、`updated_at`。
- 会话：索引中的基础字段，加上 `current_message_id`、`messages`。
- 消息：`id`、`parent_id`、`role`、`status`、`inserted_at`、`fragments`。`thinking_enabled`、`search_enabled` 等原始字段保存在源 JSON。
- 附件：`FILE.files[]` 中的 `id`、`file_name`、`file_size`、`export_path`、`is_image`，以及可选宽高等元数据。

附件时间不决定会话的归档目录。空 `export_path` 代表没有可复制的文件内容；不能从 AI 回答反推原附件已恢复。

| 片段类型 | 处理 |
|---|---|
| REQUEST / RESPONSE / TEMPLATE_RESPONSE | 问答正文 |
| THINK | 折叠思考片段 |
| FILE | 本地附件或明确缺失提示 |
| TOOL_SEARCH | 查询、结果链接和摘要 |
| TOOL_OPEN | 历史网页链接和摘要 |
| TOOL_FIND | 历史查找模式 |
| CONTENT_RISK / TIP | 折叠平台提示 |

状态按导出原值显示。合成测试覆盖 FINISHED、TIMEOUT、INCOMPLETE、CONTENT_FILTER。

## 合成数据扩展

本仓库的 `manifest.json` 另含 `synthetic: true` 和 `fixture_set: epitaph-six-v1`；每个会话含 `synthetic: true`。这些是测试标记，**不是 DeepSeek 官方字段**。

旧 build_demo.py 只检查固定六个合成 ID；新 convert.py 支持普通 DeepSeek v3 导出，不要求这些测试标记。合成资料链接使用 `example.com`，文字、图片和源码均由本项目构造。`user.json` 也为虚构记录，用于验证账号数据不会进入演示笔记库。
