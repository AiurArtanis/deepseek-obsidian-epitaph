# 未支持来源：研究、适配、审核

提供同一流程，不声称“任意 JSON 一键转换”。当前没有内置 ChatGPT、Claude 等平台的原生解析器。

## 研究真实结构

`convert.py inspect` 可探查目录、JSON 或 ZIP，输出字段形状而非正文值。HTML、数据库或分段文件需选择相应只读解析器。解压检查成员路径与大小，不覆盖源文件、不执行脚本。

| 语义 | 需要确认 |
|---|---|
| 会话 | ID/标题映射、归档状态 |
| 消息 | role、正文/多模态分块、Markdown/HTML、系统/工具角色 |
| 顺序 | parent/children/current node，或明确的线性顺序 |
| 时间 | 秒/毫秒/字符串、时区、缺失值 |
| 附件 | ID、名称、类型、路径、实体、远程/缺失标记 |
| 其他 | 实际思考、搜索引用、工具结果、失败状态 |

将字段映射、样例覆盖、缺失信息和推断写成适配说明。没有来源证据时不要猜当前分支或补当前时间。

## 规范化契约

针对该导出编写独立适配器，输出 export-v3.md 描述的中间结构，再复用 convert.py。只改变存储表达，不重写对话。

- 会话 ID 为稳定的路径安全字符串，消息 ID 为稳定整数；保留原 ID 与映射。
- 当前渲染器接收 USER/ASSISTANT。若实际有 SYSTEM/TOOL 等独立角色，扩展渲染与核验，不静默冒充助手或删除。
- 每条消息保留 parent、status、带时区时间及全部片段。线性来源可按原顺序建 parent，并说明没有分支信息。
- 附件保留原字节，相对路径在中间目录内；原导出缺失则为 null，不把网络 URL 伪装成本地文件。
- manifest 的 normalization 记录适配器、字段映射与限制；original_exports 列出适配前文件相对路径。转换器将其逐字节压缩归档。

```json
{
  "export_format_version": 3,
  "normalization": {
    "adapter": "example-ai-export-v1",
    "field_mapping": {"body": "fragments[].content", "message_uuid": "original_id"},
    "limitations": []
  },
  "original_exports": ["original/conversations.json"]
}
```

## 来源样式

`chat-ai-<实际来源 slug>` 配来源名称、标题色及图标，其余目录、用户框、分支与脚注保持一致。优先合适 emoji 或确认存在的 Lucide icon；没有合适选择时用 lucide-sparkles。示例值不是某家 AI 的官方品牌色。

```json
{"name":"Example AI","slug":"example-ai","accent":"#7058a3","icon":"lucide-sparkles"}
```

也可用 emoji 字段替代 icon。先生成样板：

```sh
python scripts/convert.py demo --source work/normalized-export --profile work/provider.json --dest output/provider-review
```

用户认可后，用相同 profile、时区和 reviewed-demo 转 full。新适配器至少用合成例验证 ID、分支、时间、附件和源文件还原；明确未覆盖字段。真实用户导出不得加入仓库测试或提交远端。
