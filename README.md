<p align="center"><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

![蓝色 DeepSeek 鲸鱼拥抱紫色 Obsidian 黑曜石，坐在硬盘上，身旁的聊天记录长出关联笔记](assets/pics/deepseek-obsidian-hug.png)

# DeepSeek 的 Obsidian 墓志铭 ✝️

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

从横空出世的 V3 和 R1，到如今在我眼里渐渐跟不上时代的 V4，DeepSeek 已经很久没有带给我 2025 年初那种“世界突然往前走了一大步”的震撼了。但我还是想留住那些对话：第一次看它把问题拆开时的惊讶，深夜里反复追问的执拗，还有几次以为自己终于想明白了什么的快乐。模型会被新的模型超越，那些时刻却不会因此作废。**我想给它们找个能长久住下来的地方，也给当时那个充满好奇的自己留一份底稿。**

于是，聊天从不断刷新的侧栏，搬进了可以自己保管的文件夹。存在你的硬盘里，也可以存在你的 NAS 里；打开 Obsidian，它们依然是一问一答，带着当时的时间、分支、附件和网页来源。名字是墓志铭，里面埋着的却都是还想继续生长的念头。

## 🌱 聊天归档，也是知识库的原料仓

归档解决“当时到底聊了什么”：保留问答、时间、历史分支、消息状态，以及能找到的原始附件。

知识整理解决“这段话以后怎么用”。当对话拥有稳定的文件、日期、来源和链接，就可以接上新的工具：让 AI Agent 帮你归类，让双链把零散的问题织成 Wiki，让时间线找回一个想法的来路，也让检索问答有机会回答“当时的我为什么这样选”。

这个 Skill 把工作做到完整归档。图中后半段，是你可以借助额外工具、配置与人工复核继续探索的方向。

```mermaid
flowchart TB
    subgraph archive[先把记忆完整留下]
        A[各家 AI 聊天导出] --> B[研究字段与附件<br/>适配来源和样式]
        B --> C[抽样生成 demo 笔记库]
        C --> D{你审核样板}
        D -->|调整格式| C
        D -->|确认| E[全量转换与完整性核对]
        E --> F[Obsidian 对话档案<br/>保存在硬盘或 NAS]
    end

    F --> G[筛选内容与访问范围<br/>保留时间、分支和来源]

    subgraph wiki[知识库 Wiki]
        W1[AI Agent<br/>归类、提取概念、发现重复]
        W2[人工复核<br/>主题笔记与双向链接]
        W3[Obsidian / Wiki 工具<br/>方法库、术语库、项目手册]
        W1 --> W2 --> W3
    end
    subgraph timeline[时间线与关联网络]
        T1[事件提取工具<br/>日期、人物、项目与决策]
        T2[Canvas / 图谱工具<br/>关联时间、主题和分支]
        T3[回看想法的变化<br/>研究脉络与项目复盘]
        T1 --> T2 --> T3
    end
    subgraph avatar[数字分身问答]
        Q1[检索索引 / RAG<br/>按主题与时间查找原文]
        Q2[AI Agent + 语言模型<br/>结合偏好与历史上下文]
        Q3[个人问答助手<br/>带来源回答、标明未知]
        Q1 --> Q2 --> Q3
    end

    G --> W1
    G --> T1
    G --> Q1
    W3 -.->|补充主题关联| Q1
    T3 -.->|补充时间上下文| Q1
    W3 --> H[你修订、补充与再提问]
    T3 --> H
    Q3 --> H
    H --> I[新的笔记与对话]
    I -.->|持续归档| F
```

Wiki 可以回答“我已经弄懂了什么”；时间线与关联网络可以回答“我是怎么走到这个判断的”；数字分身问答可以从你授权的材料里，找到过去的偏好、理由与措辞，并把出处交还给你。你还可以把这些材料交给学习助手出复习题，交给写作助手梳理草稿，或交给项目 Agent 找回被遗忘的决策依据。

**硬盘可以替你记住，工具可以帮你重新发现。至于哪些值得相信、哪些值得留下，仍由你决定。**

## 📦 都给老对话安排了什么

| 旧聊天里的东西 | 在笔记库里的待遇 |
|---|---|
| 问题和回答 | 分角色气泡，继续按对话阅读 |
| 思考与历史检索 | 默认折叠，需要时再展开 |
| 引用与检索网页 | 在对应回答末尾列成可点击列表，按顺序去重 |
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

## 写给仍然好奇的自己

我不知道 AI 最终会把我们带到哪里。我会为一次漂亮的推理兴奋，也会在它一本正经地犯错时停下来；我想靠近它，又不愿把自己的判断轻易交出去。这份好奇里有期待，也有敬畏——对尚未理解的能力，对它可能改变的生活，也对那些我们还没有学会承担的后果。

留下这些对话，是想记住自己曾经怎样提问、怎样被说服，又怎样改变了主意。也许几年后重读，会笑当年的天真，也会发现某个后来很重要的念头，早就藏在一句随口的追问里。

如果这座小小的档案馆有什么愿望，我希望它能让我们在追赶下一次惊叹时，偶尔停下来看看来路。**继续探索，也继续怀疑；愿我们始终保有提问的勇气。**

---

项目仍在私人开发阶段，开源协议待选，见 [LICENSE](LICENSE)。问题反馈请使用合成最小复现，保护聊天与附件中的私人内容。
