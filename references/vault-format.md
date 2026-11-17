# 笔记库格式 · 1.0.0

下列规则适用于样板与全量库。仓库自带演示使用合成数据；真实转换输出留在用户指定目录。

## 文件组织

```text
chat-vault/
├─ 00-首页.md
├─ 01-对话索引.md
├─ 02-格式与维护说明.md
├─ 03-完整性核对报告.md
├─ 04-缺失附件清单.md
├─ YYYY-MM/YYYY-MM-DD/【HHMMSS】 对话标题.md
├─ _附件/<会话ID>/
│  ├─ <短文件ID>_<文件名>.png
│  ├─ 代码/m2-f1-code1.html
│  └─ 内嵌资源/<内容哈希>.svg
├─ _原始数据/<会话ID>.json.gz
├─ _维护/
│  ├─ 会话映射.json
│  ├─ 生成清单.json
│  ├─ 片段处理记录.json
│  ├─ 资源映射.json
│  ├─ 全量结构统计.json
│  ├─ 样板审核.json
│  └─ 完整性核验.json
└─ .obsidian/snippets/ai-chat-history.css
```

创建日期按 `--timezone-offset` 转换（默认 UTC+08:00），决定文件夹。`【HHMMSS】` 表示创建时分秒。文件标题清理 Windows 非法字符，并截断到 52 个字符；原始完整标题仍保留在属性中。相同目标路径发生内容冲突时停止。

## 笔记属性

| 属性 | 用途 |
|---|---|
| `title`, `aliases` | 原始完整标题 |
| `source` | 实际 AI 来源名称，用于筛选 |
| `conversation_id`, `conversation_id_short` | 完整 ID 与前 8 位 |
| `created`, `updated` | 带时区的日期时间；初始配置标记为原生 datetime |
| `pinned`, `current_message_id` | 置顶状态与当前分支末节点 |
| `message_count`, `main_message_count`, `alternate_message_count`, `round_count` | 消息及轮次计数 |
| `attachment_count`, `missing_attachment_count` | 附件记录计数 |
| `raw_source` | 指向库内原始会话压缩包的内部链接 |
| `content_verified` | 初始为 false，不代表历史内容已核实 |
| `cssclasses`, `tags` | 新入口使用 ai-chat-history 样式及 <来源>/history 标签；旧合成入口保留 deepseek-chat |

不生成 `created_utc`、`updated_utc`、`source_sha256`、`format_version`、`sample_focus`、`archive_note`、`timezone`、`type` 属性。UTC 时间留在原始 JSON；校验哈希和转换版本放在维护文件中。

## 消息与阅读

从 `current_message_id` 沿 `parent_id` 回溯再反转，得到主线。每条用户消息开启新一轮；其余消息放在“历史分支与重试”中独立折叠。异常状态显式显示。

- 轮次标题为“第 XX 轮 · 问题摘要”，含前缀最多 40 个字符，超长以 `…` 结尾。完整问题保留在正文。
- `chat-user`：文本整体右对齐，背景 `#edf3fe`；代码字符方向保持 LTR。
- DeepSeek：`chat-ai-deepseek`、🐋、`#3964fe`；其他来源使用 `chat-ai-<slug>` 与该来源配置，无合适图标时用 `lucide-sparkles`。
- `chat-think`、`chat-search`、`chat-code`：思考、历史检索与长代码默认折叠。
- 消息标题引用 `[^msg-1]`，文末定义 `[^msg-1]: 消息信息`；脚注保存时间、ID、状态、父消息和所属分支。父消息也可通过脚注引用访问。
- 不生成旧的独立 `^msg-1` 块标识。

辅助片段分类展示会改变阅读顺序，维护记录和原始 JSON 保留原片段信息；不存在 THINK 时不凭 `thinking_enabled` 补写。

## 富文本与资源

普通 Markdown 表格、列表、引用保留；一、二级标题降为三级。正文中的 `\(...\)`、`\[...\]` 转为 Obsidian 数学分隔符，跳过代码围栏和内联代码。正文 `<br>` 转为换行。

代码保留语言和内容；达到 70 行的代码、完整 HTML 页面折叠并另存源码。已识别的无围栏 HTML 成对块加代码围栏；这不是通用 HTML 清洗器。归档脚本不执行 HTML/JavaScript，也不提供网页运行预览。

内嵌图像提取到独立文件；代码内替换为相对于该会话 `代码` 文件夹的资源路径。不完整或示例编码另存压缩字符串并标注；复杂混合 HTML/Markdown 仍需样板验证。笔记正文不保留编码图像数据，原始 JSON 可还原转换前内容。

实际附件按会话分目录保存，同名文件由短附件 ID 区分。`export_path` 为空时显示缺失提示；路径存在但文件丢失时停止并报错。远程链接保留，不下载远程资源。

## 审核、重建和追溯

原始会话以 gzip 保存，可逐字节还原；账号级 `user.json` 不复制进库。生成清单记录文件哈希。新 convert.py 只写空目录，full 必须引用相同输入、样式、时区和转换规则的已审核 demo；不自动改写既有笔记。旧 build_demo.py 保留按清单保护的合成重建方式。

相同输入与配置在新的空目录生成确定性内容。初始 Obsidian 设置只在文件不存在时创建，保留之后的用户配置。脚本不自动清理过时产物，也不进行原子目录替换、双向同步或属性合并。

新入口另含 03-完整性核对报告.md、04-缺失附件清单.md、消息/正文转换记录、样板审核绑定和独立完整性核验。未引用源文件在全量阶段压缩保存；规范化适配器的 original_exports 保留适配前原文件。维护数据不会塞入笔记属性。
