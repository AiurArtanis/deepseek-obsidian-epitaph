# DeepSeek 完整转换工作流

本指南提炼自一次实际归档。机器路径、账号、会话正文、真实 ID 和附件未进入仓库；回归数据重新合成。README 的德国高铁前后截图是用户指定的有限例外。

## 调查与抽样

1. 查 manifest 版本，核对索引与会话 ID、标题、创建/更新时间、消息数。
2. 抽查短问答、长对话、修改/重试分支、图片、缺失附件、公式、表格、HTML/CSS 与检索。
3. 识别当前叶节点及 parent 链。旧回答、失败记录、改写前问题均保留。
4. 附件按 export_path 查实体文件并核对大小；空路径生成缺失提示，声明有路径但文件不存在则停止诊断。
5. 创建时间决定归档位置，更新时间为属性；使用用户确认的时区。

```sh
python scripts/convert.py inspect --source input/deepseek-export --report output/structure.json
python scripts/convert.py demo --source input/deepseek-export --dest output/review-vault --timezone-offset +08:00
```

默认最多六篇，按内容特征覆盖选择。可重复传 `--id` 使用实际会话 ID。用户认可后运行：

```sh
python scripts/convert.py full --source input/deepseek-export --dest output/chat-vault --reviewed-demo output/review-vault --approved
python scripts/verify_vault.py --source input/deepseek-export --vault output/chat-vault --report output/verification.json
```

新入口不要求 synthetic 标记或固定数量。旧 build_demo.py 仅保留为六组合成示例生成器。

## 实际数据带来的处理规则

- 空标题显示“未命名对话”，原 JSON 的 null 不改写。
- 空 TOOL_OPEN 保留操作、状态及空结果说明，不生成假 URL。
- TIMEOUT、INCOMPLETE、CONTENT_FILTER 等状态按源值保存。
- 有效图像编码外置；不完整/示例编码显示说明并压缩保留原字符串，不伪造图像。
- 正文、网页摘要中的 wikilink、相对链接示例和误识别为 Markdown 链接的日志按字面显示。
- 所有分支检查父节点和环，不只检查当前主线。
- 原始会话、索引、格式描述可逐字节还原；未被消息引用的源文件在全量阶段单独压缩保留，账号级 user.json 除外。
- 附件复制后核对字节、大小与 SHA256；确认正文片段进入对应角色消息，并逐条核对角色块哈希。

先读取独立核验与缺失清单，再检查 Obsidian 原生索引、脚注、附件解析和代表性阅读视图。环境无法视觉验证时明确记录，不以模拟网页代替原生渲染。交付止于笔记库目录，不包含 NAS 部署、挂载或同步。
