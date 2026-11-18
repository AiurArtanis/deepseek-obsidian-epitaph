# README 图片与编排

## 视觉方向

受众是想找回旧对话、并将其整理为个人知识素材的用户。README 先表达用途和语气，再给真实前后对照，最后提供最短运行命令及能力限制。

- 主色：DeepSeek 蓝 `#3964fe`；辅助色：Obsidian 紫；封面使用暖白背景。
- 母题：鲸鱼、黑曜石、硬盘、从聊天长出的笔记连接。
- 语言：轻松、自嘲，技术范围保持准确。中英文分别写成自然文案，保持相同能力声明。
- 截图独立展示，不挤进封面或窄小并排卡片；原始界面可折叠展开，成品图直接可见。

本轮查阅了 [oil-oil/beautify-github-readme 的技能](https://github.com/oil-oil/beautify-github-readme/blob/cee51546f17542d547973e5292ae2e70855424d9/skills/beautify-github-readme/SKILL.md)，使用其中的“用途 → 证据 → 机制 → 首次使用”顺序、项目自身视觉语言和 GitHub 宽窄屏检查方法。也考察了 [beautify-github-profile](https://github.com/rzashakeri/beautify-github-profile)；其定位偏个人主页素材索引，本轮选择前者作为 README 工作流。仅查阅和使用方法，未安装新的全局 Skill 或复制第三方素材。

## 展示图片

| 文件 | 来源与用途 |
|---|---|
| `assets/pics/deepseek-obsidian-hug.png` | 内置 imagegen 生成的封面；2026-11-17 按用户标注修补紫色玩偶脸颊污点，保留原来的拥抱动作、腮红和构图。 |
| `assets/pics/screenshot.png` | 用户主动添加并明确要求用于 README 的 DeepSeek 原始界面截图，保留原字节。 |
| `assets/pics/obsidian-german-rail.png` | 用户指定的德国高铁对话，使用当前模板生成单会话样板后的 Obsidian 原生截图，包含回答末尾的 10 个网页来源与消息脚注。 |
| `deepseek-memory-integral.png` / `obsidian-memory-integral.png` | 用户提供的网页原图与 Obsidian 阅读视图，均截至示例表 45 岁、0.980。 |
| `deepseek-o3.png` / `obsidian-o3.png` | 用户提供的网页原图与 Obsidian 阅读视图，均展开 17 秒思考过程，显示完整回答。 |

真实截图的使用范围仅为上述三组对照图；测试 fixtures、演示笔记库和可恢复的原始 JSON 仍全部为合成数据。README 不包含这些对话的 Markdown、JSON 或附件副本。

## Obsidian 截图方式

先确认目标样板库和笔记。通过 Obsidian CLI 的 `eval` 调用 Electron `webContents.capturePage()`，直接保存 PNG；不使用桌面自动化，也不重新排版成模拟聊天截图。初次制作时 `dev:screenshot` 返回异常，因此沿用已验证的原生截图方式。

截图时临时收起两侧栏、隐藏无关操作区域，并调整窗口尺寸和阅读留白；原笔记文本、属性、代码和样式文件不改写。结束后恢复原视图、窗口、缩放和后台节流。最终图片只呈现指定笔记的内容，包含表格和原生脚注。

## 生成封面

原始封面使用内置 `image_gen` 生成，提示词见 [cover-prompt.txt](cover-prompt.txt)。2026-11-17 使用内置工具的编辑模式，以原封面为编辑目标，仅修补紫色玩偶左侧脸颊的小污点；修图要求见 [cover-edit-prompt.txt](cover-edit-prompt.txt)。原封面在仓库外留有备份，仓库引用修补后的 PNG。

已检查：蓝鲸与紫色晶体有明确拥抱动作；硬盘与关联笔记清晰；文字为 `DEEPSEEK × OBSIDIAN`；封面无界面、凭据或私人信息。

文件尺寸、SHA-256 和核验记录见 [visual-assets.json](visual-assets.json)。正文与图片均留在仓库内，不依赖远程图片服务。

## README 渲染检查

2026-11-17 的三图版本中，中文与英文均通过 GitHub Markdown API 生成真实 GFM HTML，再在 Ego Lite 中用本地 GitHub 风格 CSS 检查 980/360 像素宽度及浅/深色。流程图先由 Obsidian 原生 Markdown 渲染器解析，导出的 SVG 用于本地预览；GitHub 上的 Mermaid 展示另行核对。三张图片均正常加载且带替代文本，页面无横向溢出，原图折叠区可展开。截图已人工查看；本地检查不等同于逐屏审核 GitHub 网站本身的主题 CSS。

## 归档流程图

中英文 README 使用从 [同一份 HTML](../assets/diagrams/chat-archive.html) 导出的 PNG。直接打开源文件查看中文，地址后加 `?lang=en` 查看英文。按 960 或 360 CSS 像素宽度排版，截取 `main` 的完整高度，以两倍分辨率导出到 `assets/pics/chat-archive-{zh,en}[-mobile].png`。小屏版把用途改为纵向排列，书页、时间轴和气泡图标均绘制在 HTML 内。
