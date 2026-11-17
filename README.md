<p align="center"><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

![蓝色 DeepSeek 鲸鱼拥抱紫色 Obsidian 黑曜石，坐在硬盘上，身旁的聊天记录长出关联笔记](assets/pics/deepseek-obsidian-hug.png)

# DeepSeek 的 Obsidian 墓志铭

**给聊过的天一个家，给未来的知识库留点家底。**

> 哥们，梁叔叔算力是不够了，但是你的硬盘够啊。

聊天窗口会关，侧栏会长，那个“我记得它讲过”的回答，往往藏在第八次滚动之后。

以前的对话不是没了。消耗的 token（反正不是我的钱），只是换成了 Markdown、附件和脚注，以另一种方式继续陪伴你。

这个 Skill 把 AI 聊天导出整理成 Obsidian 对话笔记：DeepSeek v3 可直接转换，其他来源先研究格式再适配。它让问答能接着看，分支有迹可循，公式、代码和附件各有位置。**今天是聊天档案，明天是你知识库的素材源。**

## 🐋 从“服务器繁忙”到“本地随便翻”

同一段「德国最快高铁线路及速度信息」对话，从网页来到 Obsidian。

<details>
<summary><strong>① 还在 DeepSeek 里：展开看原始界面</strong></summary>

这是作者提供的原始截图，思考和搜索记录展开在长长的聊天页面里。

![归档前：DeepSeek 网页中的德国高铁对话，包含展开的思考过程、搜索记录和表格](assets/pics/screenshot.png)

</details>

**② 安顿到 Obsidian：问题靠右，回答带鲸鱼，思考与检索记录收进折叠块。**

![归档后：Obsidian 中的同一段对话，展示角色气泡、折叠思考、表格和可回跳的原生消息脚注](assets/pics/obsidian-german-rail.png)

成品图直接取自 Obsidian 的 Electron 原生渲染。两张真实截图经作者指定用于展示；可运行的测试数据与演示库全部使用合成数据。

**现在能做什么？** DeepSeek v3 支持真实导出的抽样与全量转换。先做 demo 给你看，点头之后再让全量对话入住。其他 AI 也走同一流程，但要先研究它的导出字段、实现适配器，再换上自己的 `chat-ai-xx`、颜色和图标；没有合适图标，就请 spark 救场。

**只负责转笔记。** 不替你部署 NAS、开同步服务，也不偷偷把旧回答炼成“知识”。名字是墓志铭，业务是让记忆继续营业。

## 🌱 聊天归档，也是知识库的原料仓

归档解决“当时到底聊了什么”：保留问答、时间、历史分支、消息状态，以及能找到的原始附件。

知识整理解决“这段话以后怎么用”：你可以给对话加标签，把有用的段落链接到主题笔记，复核结论，再写成自己的方法、项目记录或学习笔记。整理好的 Markdown 也能供后续工具读取。

```text
AI 导出 → 抽样做 demo → 你确认 → 全量对话档案 → 你筛选、复核、关联 → 知识库
```

它负责把材料搬进仓库。装修成第二大脑，还得你来。**硬盘可以替你记住，暂时还不能替你学会。**

## 📦 都给老对话安排了什么

| 旧聊天里的东西 | 在笔记库里的待遇 |
|---|---|
| 问题和回答 | 分角色气泡，继续按对话阅读 |
| 思考与历史检索 | 默认折叠，需要时再展开 |
| 重试、旧分支、超时 | 保留原状态；失败的那几次也有席位 |
| 表格、公式、图片 | 转成适合 Obsidian 阅读的格式 |
| 长代码和 HTML | 折叠源码，另存文件；不自动执行 |
| 缺失附件 | 明确标注，绝不现场脑补一个 |
| 时间、来源、会话 ID | 放进笔记属性，方便标签管理和查询 |
| 原始会话 | gzip 留档，方便回溯转换前的内容 |

目录长这样，找旧账相当顺手：

```text
YYYY-MM/YYYY-MM-DD/【HHMMSS】 对话标题.md
```

`【HHMMSS】` 是创建时分秒。每段对话一篇笔记，消息脚注可点击回跳；基础阅读使用 Obsidian 原生 Markdown、callout 和 CSS，无须社区插件。

## 🚚 先看样板间，再让老聊天搬家

需要 **Python 3.13+**，只用标准库。先取得导出的目录，别把输入和输出放成套娃。在仓库根目录运行：

```sh
python scripts/convert.py inspect --source input/deepseek-export --report output/structure.json
python scripts/convert.py demo --source input/deepseek-export --dest output/review-vault
```

用 Obsidian 打开 `output/review-vault`：看看目录顺不顺手、问答像不像聊天、分支有没有漏、附件有没有安顿好。**样板认可后**，再运行：

```sh
python scripts/convert.py full --source input/deepseek-export --dest output/chat-vault --reviewed-demo output/review-vault --approved
python scripts/verify_vault.py --source input/deepseek-export --vault output/chat-vault --report output/verification.json
```

`--approved` 不是“略过用户”的后门，而是已有审核结果的声明。源文件、样式、时区或转换规则变化，会要求重做样板。新入口只写空目录，已有笔记不用担心被顺手重新装修。

还不想拿真聊天试？先让六位合成网友入住：

```sh
python scripts/build_demo.py --dest output/synthetic-demo
```

也可直接打开 [examples/demo-vault](examples/demo-vault/00-首页.md)。六组样例有 **25 条消息、33 个片段、2 张图片和 1 条缺失附件记录**；它们是测试演员，不是从谁的聊天记录里抓来的临时工。

### 让 Agent 接手

仓库根目录的 [SKILL.md](SKILL.md) 就是技能入口。保留 `scripts/`、`assets/`、`references/` 和 fixtures 的相对位置，让支持本地 Skill 的 Agent 读取它：

> 使用 deepseek-obsidian-epitaph 检查我的 AI 聊天导出。先研究正文、ID、时间和附件，做几个 Obsidian 样板给我看；我确认后，再转全量并核对完整性。

遇到未支持来源，Agent 按 [适配指南](references/other-providers.md) 调查字段、保留原始数据、建立适配与来源样式，再走样板审核。当前没有把 ChatGPT、Claude 等平台的原生解析器包装成现成功能。

<details>
<summary><strong>给爱翻引擎盖的朋友：验证、格式与维护</strong></summary>

```sh
python -m unittest discover -s tests -v
python scripts/check_public_content.py
```

归档测试检查内容完整性、代码保留、资源引用、重建一致性和覆盖保护；公开内容检查重新生成合成输入与演示库，并核对当前版本文件哈希。

测试及 Obsidian 原生检查的执行结果保存在 [验证记录](references/verification-results.json)。结构核验、样板视觉检查与真实展示截图各自说明范围，不互相冒领功劳。

可选的 Obsidian 集成检查及环境限制见[验证说明](references/verification.md)。更多细节：

- [能力范围](references/frozen-scope.md)
- [DeepSeek v3 输入结构](references/export-v3.md)
- [笔记格式与维护规则](references/vault-format.md)
- [变更记录](CHANGELOG.md) · [图片来源与制作说明](references/visual-assets.md)

</details>

## 最后几句实话

不包含 NAS 部署、增量同步、自动摘要或知识提炼；未支持的 AI 导出需先研究和适配。归档会保留历史回答，不替它重新判卷。

报告问题时请提供合成最小复现，不要上传私人聊天或附件。开源协议仍待选定，见 [LICENSE](LICENSE)；仓库目前保持私人开发，打磨后再考虑开源。

**算力有空再续，记忆先落盘。**
