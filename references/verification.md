# 验证与证据

## 离线数据验证

```sh
python -m unittest discover -s tests -v
python scripts/check_public_content.py
```

测试覆盖合成归档、任意会话与全量范围、样板确认约束、输入/品牌变更、历史分支环、异常记录、规范化来源及 spark 回退、源数据还原、附件损坏检测和覆盖保护。

```sh
python scripts/verify_vault.py --source INPUT --vault OUTPUT --report WORK/verification.json
```

独立核验从落盘结果重新核对消息和片段、主线/分支、父子关系、角色块哈希、脚注、附件字节/大小、原 JSON 还原、源文件不变及生成文件哈希。Obsidian 会改写自身 JSON 配置，配置变化单独记录；正文与 CSS 严格核对。

## Obsidian 原生验证

先运行 obsidian help，确认用户指定的目标库已打开。用官方 CLI 检查当前库路径，不能误选用户的其他库。可以用 Electron 调试，但不需要 Computer Use。

```sh
python scripts/check_obsidian.py --vault-path OUTPUT --report WORK/obsidian.json
```

当前可重复集成检查用于 DeepSeek 的合成样板，验证角色颜色、鲸鱼、右对齐、公式、图片、脚注、属性与标题长度。其他品牌需按 profile 对应颜色和图标检查，不把 DeepSeek 断言套上去。

正式转换还需核对原生 metadataCache：全部笔记、标准脚注、附件链接、轮次标题及 unresolved。复杂长会话按代表性抽查，报告样本数量与未逐屏覆盖的范围。

截图优先 dev:screenshot；命令失效时可通过 CLI eval 调用 Electron 原生 capturePage 并直接写文件，不输出编码图像。仅作用于目标库；临时调整视图、窗口、缩放或后台节流后恢复。多个标签页时将 DOM 查询限定在目标 Markdown leaf。

数据完整性通过不等于视觉验收；截图不证明全量归档无遗漏。环境不可用时保留“未执行”，不要报告通过。

## 仓库数据边界

fixtures 与演示库必须能从合成生成器独立复现。README 两张真实截图的授权范围、来源和哈希单独记录；不得把真实 JSON、笔记、附件、账号资料或机器路径一起提交。更新功能后同步规范、样例、测试、验证记录与文件清单。

跨 Python/zlib 版本时，gzip 允许不同压缩字节表达同一原文：先独立核对两份生成清单中的实际文件 SHA256，再逐字节比较解压内容；其他生成文件仍逐字节比较，文件覆盖及清单结构必须相同。版本清单继续严格核对仓库中已提交文件的原字节。合成 PNG 使用无压缩 DEFLATE，避免压缩器版本改变 fixture 本身。
