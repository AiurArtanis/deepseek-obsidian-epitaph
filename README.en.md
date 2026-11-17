<p align="center"><a href="README.md">简体中文</a> · <strong>English</strong></p>

![A blue DeepSeek whale hugging a purple Obsidian crystal on a hard drive, with archived chats growing into linked notes](assets/pics/deepseek-obsidian-hug.png)

# DeepSeek Obsidian Epitaph

**A home for old conversations. A head start for your future knowledge base.**

> Bro, Uncle Liang may be short on GPUs. Your hard drive still has room.

Chat windows close. Sidebars grow. That answer you *know* you saw is usually another eight scrolls away.

The conversations aren't gone. The tokens we burned (not my money, anyway) now live on as Markdown, attachments, and footnotes. A different format. The same questionable late-night questions.

This skill turns AI chat exports into readable Obsidian conversation notes. DeepSeek v3 works directly; other sources need a format adapter first. It keeps the dialogue, branches, formulas, code, and attachments together. **An archive today. Source material for your knowledge base tomorrow.**

## 🐋 From “server busy” to “browse locally”

The same conversation about German high-speed rail, before and after archiving.

<details>
<summary><strong>① Still in DeepSeek: expand the original interface</strong></summary>

The author supplied this screenshot, with reasoning and search records expanded in the original chat.

![Before: the German rail conversation in DeepSeek, showing expanded reasoning, historical searches, and a table](assets/pics/screenshot.png)

</details>

**② Settled into Obsidian: right-aligned questions, a whale for DeepSeek, and collapsible reasoning and search records.**

![After: the same conversation rendered in Obsidian, showing role bubbles, folded reasoning, a table, and native message footnotes with backlinks](assets/pics/obsidian-german-rail.png)

The result was captured directly from Obsidian's native Electron rendering. These two real screenshots are included at the author's request. All runnable fixtures and the bundled demo vault remain synthetic.

**What works now?** Real DeepSeek v3 exports, from representative samples to the complete archive. You review a demo vault first; the rest moves in after approval. Other AI exports follow the same process after their fields have been studied and adapted, with their own `chat-ai-xx` styling and icon. No suitable icon? Sparkles are happy to cover the shift.

**One job: convert chats into notes.** No NAS deployment, sync service, or surprise “knowledge extraction.” The name says epitaph; the job is keeping your conversations alive.

## 🌱 An archive with a second career

An archive answers “what did we actually discuss?” It preserves messages, timestamps, historical branches, statuses, and the attachments that exist in the export.

A knowledge base answers “what can I do with this later?” Add tags, link useful passages to topic notes, verify conclusions, and turn them into your own methods, project records, or study notes. The resulting Markdown is also available to tools you choose to use later.

```text
AI export → Demo vault → Your approval → Complete archive → Your review and connections → Knowledge base
```

The project stocks the shelves. You decide what becomes knowledge. **Your drive can remember it for you. Learning it is still your department.**

## 📦 What gets a room in the archive?

| In the old chat | In the vault |
|---|---|
| Questions and answers | Role-based bubbles, read as a conversation |
| Reasoning and historical searches | Folded until you need them |
| Retries, old branches, timeouts | Original statuses preserved; even failed attempts get a seat |
| Tables, formulas, images | Converted for Obsidian reading |
| Long code and HTML | Collapsible source plus separate files; never auto-executed |
| Missing attachments | Clearly marked, never conjured out of thin air |
| Dates, source, conversation IDs | Note properties for organization and queries |
| Original conversations | gzip copies for tracing back to the source |

One conversation per note, filed by creation date:

```text
YYYY-MM/YYYY-MM-DD/【HHMMSS】 Conversation title.md
```

`【HHMMSS】` is the creation time. Native message footnotes provide return links. Basic reading uses Obsidian Markdown, callouts, and CSS; no community plugin required.

## 🚚 Tour the demo before moving everything in

Requires **Python 3.13+**, standard library only. Keep the export and output directories separate. From the repository root:

```sh
python scripts/convert.py inspect --source input/deepseek-export --report output/structure.json
python scripts/convert.py demo --source input/deepseek-export --dest output/review-vault
```

Open `output/review-vault` in Obsidian. Check the conversations, folders, branches, and attachments. **After approving the demo**, run:

```sh
python scripts/convert.py full --source input/deepseek-export --dest output/chat-vault --reviewed-demo output/review-vault --approved
python scripts/verify_vault.py --source input/deepseek-export --vault output/chat-vault --report output/verification.json
```

`--approved` records approval you already gave; it is not permission for an agent to skip you. Changes to the export, style, timezone, or converter require a new demo. The new entry point writes only to empty directories, so your edited notes keep their furniture.

Prefer a test drive without your private conversations?

```sh
python scripts/build_demo.py --dest output/synthetic-demo
```

Or open [examples/demo-vault](examples/demo-vault/00-首页.md). Its six synthetic scenarios contain **25 messages, 33 fragments, two images, and one missing-attachment record**. These are test actors, not someone's private chats drafted into service.

### Give an agent the house rules

[SKILL.md](SKILL.md) is the entry point. Keep the relative layout of `scripts/`, `assets/`, `references/`, and fixtures. Ask an agent that supports local skills:

> Use deepseek-obsidian-epitaph to inspect my AI chat export. Study the message content, IDs, timestamps, and attachments, then create an Obsidian demo for me to review. After I approve it, convert the complete export and verify integrity.

For unsupported exports, follow the [adapter guide](references/other-providers.md): study the schema, preserve the originals, implement the mapping and provider style, then review a demo. Native parsers for ChatGPT, Claude, and other services are not bundled as ready-made features.

<details>
<summary><strong>For anyone who likes looking under the hood</strong></summary>

```sh
python -m unittest discover -s tests -v
python scripts/check_public_content.py
```

The tests cover archive completeness, code preservation, resource links, reproducibility, and overwrite protection. The public-content check regenerates the synthetic input and example vault and verifies the current version file hashes.

Actual test and native Obsidian checks are recorded in [verification results](references/verification-results.json). Data integrity, sampled visual checks, and the real showcase screenshots each have their own scope.

Optional Obsidian integration checks and environment limits are documented in [verification](references/verification.md). Further technical references are currently in Chinese:

- [Capability scope](references/frozen-scope.md)
- [DeepSeek v3 input structure](references/export-v3.md)
- [Vault format and maintenance](references/vault-format.md)
- [Changelog](CHANGELOG.md) · [Visual sources and production notes](references/visual-assets.md)

</details>

## A few honest footnotes

NAS deployment, incremental sync, automatic summaries, and knowledge extraction are outside the scope. Unsupported AI exports require schema research and an adapter first. Archiving preserves historical answers; it does not fact-check them.

Please report bugs with synthetic minimal reproductions, not private chats or attachments. The open-source license is still undecided; see [LICENSE](LICENSE). The repository remains private while it is being refined; open-source release comes later.

**The GPUs can catch up later. Save the memories now.**
