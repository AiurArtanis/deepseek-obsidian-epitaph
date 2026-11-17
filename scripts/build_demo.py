"""DeepSeek v3 synthetic demo renderer. Offline, standard library only.

Frozen processing scope: 0.3.0-demo; exactly six bundled synthetic conversations.
"""
from __future__ import annotations

import argparse

import base64

import collections

import datetime as dt

import gzip

import hashlib

import html

import json

import pathlib

import re

import sys

from urllib.parse import quote

VERSION = "0.3.0-demo"

TZ = dt.timezone(dt.timedelta(hours=8))

ROUND_TITLE_MAX_CHARS = 40

DATA_URI = re.compile(r"data:([\w.+-]+/[\w.+-]+);base64,([A-Za-z0-9+/=]+)")

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"

def local(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)

def safe_name(s: str, limit=52) -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f\[\]#^]', "_", s)
    return re.sub(r"\s+", " ", s).strip(" .")[:limit].rstrip(" .") or "未命名"

def label(s: str) -> str:
    return re.sub(r"[\[\]|\r\n]", " ", str(s))

def wiki(path: str, text: str | None = None) -> str:
    target = path[:-3] if path.endswith(".md") else path
    return "[[" + target + ("|" + label(text) if text else "") + "]]"

def callout(kind: str, title: str, body: str, folded=False) -> str:
    first = f"> [!{kind}]{'-' if folded else ''} {title}"
    return first + "\n" + "\n".join("> " + line if line else ">" for line in body.split("\n"))

def fenced(s: str, lang="text") -> str:
    n = max([len(m.group()) for m in re.finditer(r"`+", s)] + [2]) + 1
    delim = "`" * n
    return f"{delim}{lang}\n{s.rstrip(chr(10))}\n{delim}"

def text_chunks(s: str):
    """Split fenced code from prose; protect every fenced body from Markdown changes."""
    lines = s.replace("\r\n", "\n").splitlines(keepends=True)
    plain = []; i = 0
    while i < len(lines):
        start = re.match(r"^ {0,3}(`{3,}|~{3,})([^\n]*)", lines[i])
        if not start:
            plain.append(lines[i]); i += 1; continue
        if plain:
            yield "prose", "", "".join(plain); plain = []
        marker, lang = start.groups(); i += 1; body = []
        while i < len(lines) and not re.match(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$", lines[i]):
            body.append(lines[i]); i += 1
        if i < len(lines): i += 1
        yield "code", lang.strip(), "".join(body)
    if plain: yield "prose", "", "".join(plain)

def main_path(session):
    byid = {m["id"]: m for m in session["messages"]}
    cur = session["current_message_id"]; chain = []; seen = set()
    while cur is not None:
        if cur in seen or cur not in byid:
            raise ValueError(f"Invalid message chain: {session['id']} / {cur}")
        seen.add(cur); chain.append(byid[cur]); cur = byid[cur]["parent_id"]
    return list(reversed(chain)), [m for m in session["messages"] if m["id"] not in seen]

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSS = (ROOT / "assets/snippets/deepseek-chat.css").read_text(encoding="utf-8")
from make_synthetic_export import SAMPLES, FIXTURE


class Builder:
    def __init__(self, source: pathlib.Path, dest: pathlib.Path):
        self.source = source; self.dest = dest; self.outputs = {}; self.records = []
        self.fragment_audit = []; self.assets = []; self.transforms = collections.Counter()
        self.provider_name = "DeepSeek"
        self.provider_slug = "deepseek"
        self.cssclass = "deepseek-chat"

    def put(self, path: str, content: str | bytes):
        data = content.encode("utf-8") if isinstance(content, str) else content
        if path in self.outputs and self.outputs[path] != data:
            raise ValueError(f"Output collision: {path}")
        self.outputs[path] = data

    def externalize(self, text: str, sid: str):
        def sub(match):
            mime, encoded = match.groups(); binary = base64.b64decode(encoded, validate=True)
            ext = {"image/svg+xml": ".svg", "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime, ".bin")
            path = f"_附件/{sid}/内嵌资源/{sha(binary)[:20]}{ext}"
            self.put(path, binary)
            self.transforms["embedded_data_uris"] += 1
            self.assets.append({"kind": "embedded", "path": path, "mime": mime, "sha256": sha(binary)})
            # Generated source code is saved in the sibling 代码 folder.
            return "../内嵌资源/" + path.rsplit("/", 1)[-1]
        return DATA_URI.sub(sub, text)

    def prose(self, s: str) -> str:
        # Inline code stays byte-identical (except separately externalized data URIs).
        pieces = re.split(r"(`+[^`\n]*`+)", s)
        for i in range(0, len(pieces), 2):
            p = pieces[i]
            p, n = re.subn(r"\\\[(.*?)\\\]", lambda m: "\n\n$$\n" + m[1].strip() + "\n$$\n\n", p, flags=re.S)
            self.transforms["display_math"] += n
            p, n = re.subn(r"\\\((.*?)\\\)", lambda m: "$" + m[1].strip() + "$", p, flags=re.S)
            self.transforms["inline_math"] += n
            # Preserve heading text, place source headings beneath round headings.
            p = re.sub(r"^(#{1,2})(\s+)", r"###\2", p, flags=re.M)
            # Markdown quotations and all ordinary tables/lists are unchanged.
            p = re.sub(r"<br\s*/?>", "  \n", p, flags=re.I)
            # HTML code outside fences: do not let Obsidian swallow it or execute it.
            raw = re.compile(r"(?ms)^([ \t]*<([A-Za-z][\w:-]*)\b[^\n]*.*?</\2\s*>[ \t]*)(?=\n|$)")
            def protect(m):
                self.transforms["raw_html_blocks"] += 1
                return "\n" + fenced(m[1], "html") + "\n"
            p = raw.sub(protect, p)
            pieces[i] = p
        return "".join(pieces)

    def markdown(self, s: str, sid: str, mid: int, fi: int) -> str:
        changed = self.externalize(s, sid); sections = []; code_no = 0
        for kind, lang, body in text_chunks(changed):
            if kind == "prose":
                sections.append(self.prose(body)); continue
            code_no += 1
            code = fenced(body, lang)
            if len(body.splitlines()) >= 70 or (lang.lower() == "html" and "<html" in body.lower()):
                ext = {"html": "html", "css": "css", "javascript": "js", "js": "js", "python": "py", "powershell": "ps1", "json": "json"}.get(lang.lower(), "txt")
                path = f"_附件/{sid}/代码/m{mid}-f{fi}-code{code_no}.{ext}"
                self.put(path, body)
                self.assets.append({"kind": "generated-code", "path": path, "sha256": sha(body.encode())})
                link = wiki(path, f"独立 {ext.upper()} 文件")
                body_text = f"{link}\n\n{code}"
                sections.append(callout("chat-code", f"{lang.upper() or '代码'} · {len(body.splitlines())} 行 · 点击展开", body_text, True))
                self.transforms["folded_code_blocks"] += 1
            else: sections.append(code)
        if changed != s:
            sections.insert(0, callout("info", "内嵌资源已外置", "代码中的内嵌图像已转为独立附件，路径相对于本会话的 `代码` 文件夹。原始内容仍保存在压缩源数据中。"))
        return "\n\n".join(sections).strip()

    def attachment(self, a: dict, sid: str, mid: int) -> tuple[str, dict]:
        export = a.get("export_path")
        entry = {"id": a["id"], "name": a["file_name"], "message_id": mid, "export_path": export}
        if not export:
            entry["state"] = "not-exported"
            return callout("warning", "原附件未包含在导出中", f"**{label(a['file_name'])}** · 原大小 {a['file_size']:,} 字节\n\n导出只保留名称、文件 ID 等元数据；`export_path` 为空。这里没有该附件的内容，也不能从对话中的代码推定已恢复原文件。\n\n附件 ID：`{a['id']}`"), entry
        src = (self.source / export).resolve()
        if not src.is_relative_to(self.source.resolve()): raise ValueError("Attachment path escapes source")
        if not src.is_file(): raise FileNotFoundError(src)
        suffix = src.suffix.lower(); name = safe_name(pathlib.Path(a['file_name']).stem, 42)
        path = f"_附件/{sid}/{a['id'][:8]}_{name}{suffix}"
        data = src.read_bytes(); self.put(path, data)
        entry.update(state="copied", path=path, sha256=sha(data))
        if a.get("is_image"):
            return f"**附件：{label(a['file_name'])}**\n\n![[{path}]]", entry
        return wiki(path, a["file_name"]), entry

    def search(self, frags: list) -> str:
        blocks = []
        for fi, f in frags:
            t = f["type"]
            line = f"**片段 {fi} · {t}** · 状态 `{f.get('status', '未记录')}`"
            if "stage_id" in f: line += f" · 阶段 {f['stage_id']}"
            if t == "TOOL_SEARCH":
                line += "\n\n查询：" + "；".join(f.get("queries", []))
                for r in f.get("results", []):
                    url = r.get("url", ""); title = html.escape(label(r.get("title") or url))
                    target = quote(url, safe="/:?=&%#@+~!$;,*-._")
                    line += f"\n\n- [{title}](<{target}>)"
                    if r.get("site_name"): line += " · " + label(r["site_name"])
                    if r.get("published_at"): line += " · " + r["published_at"]
                    if r.get("snippet"): line += "\n  " + r["snippet"].replace("\n", "\n  ")
            elif t == "TOOL_OPEN":
                line += f"\n\n[{html.escape(label(f.get('title') or f.get('url', '网页')))}](<{quote(f.get('url',''), safe='/:?=&%#@+~!$;,*-._')}>)\n\n" + f.get("snippet", "")
            else: line += "\n\n查找：" + fenced(f.get("pattern", ""))
            blocks.append(line)
        return "\n\n---\n\n".join(blocks)

    def message(self, m: dict, session: dict, attachments: list, historical=False) -> str:
        sid = session["id"]; mid = m["id"]; user = m["role"] == "USER"
        body = []; thinks = []; searches = []; notices = []
        for fi, f in enumerate(m["fragments"], 1):
            t = f["type"]
            self.fragment_audit.append({"session_id": sid, "message_id": mid, "fragment": fi, "type": t, "source_sha256": sha(jdump(f).encode()), "handling": "attachment" if t == "FILE" else "folded" if t in {"THINK", "TOOL_SEARCH", "TOOL_OPEN", "TOOL_FIND", "CONTENT_RISK", "TIP"} else "body"})
            if t == "FILE":
                for a in f["files"]:
                    rendered, entry = self.attachment(a, sid, mid); body.append(rendered); attachments.append(entry)
            elif t == "THINK":
                duration = f" · {f['elapsed_secs']:.1f} 秒" if f.get("elapsed_secs") is not None else ""
                thinks.append(f"**片段 {fi}{duration}**\n\n" + self.markdown(f.get("content", ""), sid, mid, fi))
            elif t in {"TOOL_SEARCH", "TOOL_OPEN", "TOOL_FIND"}: searches.append((fi, f))
            elif t in {"CONTENT_RISK", "TIP"}: notices.append(f.get("content", ""))
            elif t in {"REQUEST", "RESPONSE", "TEMPLATE_RESPONSE"}: body.append(self.markdown(f.get("content", ""), sid, mid, fi))
            else: raise ValueError(f"Unhandled fragment type {t}")
        if m["status"] != "FINISHED":
            body.insert(0, callout("warning", "原导出状态：" + m["status"], "以下是导出实际保存的消息。该状态不表示已得到完整回答。"))
        extra = []
        if historical:
            parent = f"父消息 m{m['parent_id']}[^msg-{m['parent_id']}]" if m['parent_id'] is not None else "根消息"
            extra.append("历史分支 · " + parent)
        if thinks: extra.append(callout("chat-think", f"思考过程 · {len(thinks)} 个片段", "\n\n---\n\n".join(thinks), True))
        if searches: extra.append(callout("chat-search", f"当时的检索记录 · {len(searches)} 个片段", self.search(searches), True))
        if notices: body.append(callout("info", "原平台提示", "\n\n".join(notices), True))
        title = f"{'我' if user else self.provider_name} · {local(m['inserted_at']):%Y-%m-%d %H:%M:%S} · m{mid}"
        if historical: title += " · " + m['status']
        title += f"[^msg-{mid}]"
        return callout("chat-user" if user else "chat-ai-" + self.provider_slug, title, "\n\n".join(extra + body), historical)

    def session(self, sid: str, purpose: str):
        source_path = self.source / "chat_sessions" / f"{sid}.json"
        data = source_path.read_bytes(); d = json.loads(data); created = local(d["inserted_at"])
        d['title'] = d.get('title') or '未命名对话'
        path = f"{created:%Y-%m}/{created:%Y-%m-%d}/【{created:%H%M%S}】 {safe_name(d['title'])}.md"
        raw = f"_原始数据/{sid}.json.gz"; self.put(raw, gzip.compress(data, mtime=0))
        main, alternatives = main_path(d); attachments = []; rounds = 0; main_text = []
        for m in main:
            if m["role"] == "USER":
                rounds += 1
                request = next((f.get("content", "") for f in m["fragments"] if f["type"] == "REQUEST"), "附件提问")
                summary_request = re.sub(r"(?s)^\s*<([A-Za-z][\w:-]*)\b.*?</\1\s*>", "", request).strip() or request
                excerpt = re.sub(r"[`*_<>#\[\]]", "", summary_request).replace("\n", " ")
                excerpt = re.sub(r"\s+", " ", excerpt).strip()
                prefix = f"第 {rounds:02d} 轮 · "
                available = ROUND_TITLE_MAX_CHARS - len(prefix)
                if len(excerpt) > available:
                    excerpt = excerpt[:available - 1].rstrip() + "…"
                main_text.append(f"## {prefix}{excerpt}\n")
            main_text.append(self.message(m, d, attachments))
        if alternatives:
            history = []
            for m in alternatives:
                history.append(self.message(m, d, attachments, historical=True))
            main_text.append("## 历史分支与重试\n\n" + callout("chat-history", f"{len(alternatives)} 条非当前主线消息 · 完整保留", "每条历史消息独立折叠，展开后可查看父消息脚注；脚注中的回跳箭头可返回对应消息。这些记录没有插入上方的主线问答。") + "\n\n" + "\n\n".join(history))
        footnotes = []
        main_ids = {m['id'] for m in main}
        for m in main + alternatives:
            speaker = '我' if m['role'] == 'USER' else self.provider_name
            parent = f"m{m['parent_id']}" if m['parent_id'] is not None else '无（会话起点）'
            branch = '当前主线' if m['id'] in main_ids else '历史分支'
            footnotes.append(f"[^msg-{m['id']}]: {speaker} · 消息 ID `m{m['id']}` · {local(m['inserted_at']):%Y-%m-%d %H:%M:%S} · 状态 `{m['status']}` · 父消息：{parent} · {branch}。")
        main_text.append("## 消息脚注\n\n" + "\n\n".join(footnotes))
        fm = {
            "title": d["title"], "aliases": [d["title"]], "source": self.provider_name,
            "conversation_id": sid, "conversation_id_short": sid[:8],
            "created": created.isoformat(timespec="milliseconds"), "updated": local(d["updated_at"]).isoformat(timespec="milliseconds"),
            "pinned": d["pinned"], "current_message_id": d["current_message_id"], "message_count": len(d["messages"]),
            "main_message_count": len(main), "alternate_message_count": len(alternatives), "round_count": rounds,
            "attachment_count": len(attachments), "missing_attachment_count": sum(a["state"] != "copied" for a in attachments),
            "raw_source": wiki(raw), "content_verified": False,
            "cssclasses": [self.cssclass], "tags": [self.provider_slug + "/history"],
        }
        frontmatter = "---\n" + "\n".join(k + ": " + json.dumps(v, ensure_ascii=False) for k, v in fm.items()) + "\n---\n\n"
        intro = f"# {d['title']}\n\n{wiki('00-首页.md', '首页')} · {wiki('01-对话索引.md', '对话索引')}\n\n"
        intro += f"创建于 {created:%Y-%m-%d %H:%M} · {rounds} 轮主线 · 共 {len(d['messages'])} 条消息"
        if alternatives: intro += f" · {len(alternatives)} 条历史分支"
        note = frontmatter + intro + "\n\n" + "\n\n".join(main_text) + "\n"
        self.put(path, note)
        self.records.append({"id": sid, "title": d["title"], "path": path, "created": fm["created"], "updated": fm["updated"], "purpose": purpose, "raw": raw, "source_sha256": sha(data), "messages": len(d["messages"]), "main_ids": [m["id"] for m in main], "alternate_ids": [m["id"] for m in alternatives], "attachments": attachments})

    def analyze(self):
        index = json.loads((self.source / "chat_session_index.json").read_bytes())
        indexed = {d["id"]: d for d in index}; counters = collections.Counter(); missing = []; mismatches = []; filesizes = []; image_paths = set()
        statuses = collections.Counter(); types = collections.Counter(); months = collections.Counter(); source_files = {}
        for p in sorted(self.source.rglob("*")):
            if p.is_file(): source_files[p.relative_to(self.source).as_posix()] = sha(p.read_bytes())
        self.source_inventory = source_files
        sessions = sorted((self.source / "chat_sessions").glob("*.json"))
        if {p.stem for p in sessions} != set(indexed): raise ValueError("Index/session ID mismatch")
        for p in sessions:
            d = json.loads(p.read_bytes()); main, other = main_path(d)
            byid = {m["id"] for m in d["messages"]}
            if len(byid) != len(d["messages"]): raise ValueError("Duplicate message ID")
            for m in d["messages"]:
                if m["parent_id"] is not None and m["parent_id"] not in byid: raise ValueError("Missing parent")
            if any(d[k] != indexed[d['id']][k] for k in ["id", "title", "pinned", "inserted_at", "updated_at"]) or indexed[d['id']]["message_count"] != len(d["messages"]): mismatches.append(d["id"])
            parents = collections.Counter(m["parent_id"] for m in d["messages"])
            counters["branch_sessions"] += any(n > 1 for n in parents.values())
            counters["non_current_messages"] += len(other); counters["messages"] += len(d["messages"])
            months[local(d["inserted_at"]).strftime("%Y-%m")] += 1
            for m in d["messages"]:
                statuses[m["status"]] += 1
                for f in m["fragments"]:
                    types[f["type"]] += 1
                    if f["type"] == "FILE":
                        for a in f["files"]:
                            counters["attachment_references"] += 1
                            ep = a.get("export_path")
                            if ep and (self.source / ep).is_file():
                                counters["existing_attachments"] += 1; image_paths.add(ep)
                                if (self.source / ep).stat().st_size != a["file_size"]: filesizes.append(a["id"])
                            else: missing.append({"session_id": d["id"], "title": d["title"], "message_id": m["id"], "file_id": a["id"], "file_name": a["file_name"], "file_size": a["file_size"], "export_path": ep})
        return {"export_format_version": json.loads((self.source/'manifest.json').read_bytes())["export_format_version"], "sessions": len(sessions), **counters, "missing_attachments": len(missing), "missing_attachment_records": missing, "status_counts": dict(statuses), "fragment_counts": dict(types), "months": dict(sorted(months.items())), "index_mismatches": mismatches, "attachment_size_mismatches": filesizes, "source_files": len(source_files), "source_total_bytes": sum(p.stat().st_size for p in self.source.rglob('*') if p.is_file()), "earliest_utc": min(x["inserted_at"] for x in index), "latest_utc": max(x["inserted_at"] for x in index)}

    def verify(self):
        failures = []; checks = []
        for r in self.records:
            d = json.loads((self.source / 'chat_sessions' / (r['id'] + '.json')).read_bytes())
            if set(r['main_ids'] + r['alternate_ids']) != {m['id'] for m in d['messages']}: failures.append("message coverage")
            audited = [x for x in self.fragment_audit if x['session_id'] == r['id']]
            if len(audited) != sum(len(m['fragments']) for m in d['messages']): failures.append("fragment coverage")
            if sha(gzip.decompress(self.outputs[r['raw']])) != r['source_sha256']: failures.append("raw roundtrip")
            note = self.outputs[r['path']].decode()
            for mid in r['main_ids'] + r['alternate_ids']:
                if note.count(f"\n[^msg-{mid}]: ") != 1: failures.append(f"message footnote definition {mid}")
                if not re.search(rf"m{mid}(?: · [A-Z_]+)?\[\^msg-{mid}\]", note): failures.append(f"message footnote reference {mid}")
            if re.search(r"^\^msg-\d+$", note, re.M): failures.append("obsolete block anchor")
            for a in r['attachments']:
                if a['state'] == 'copied' and sha(self.outputs[a['path']]) != a['sha256']: failures.append("attachment hash")
        # Only generated wiki links: all imported text in these samples was checked for authored wikilinks.
        for p, data in self.outputs.items():
            if not p.endswith('.md'): continue
            text = data.decode()
            if DATA_URI.search(text): failures.append("inline encoded data in " + p)
            for target in re.findall(r"!?\[\[([^\]\n]+)\]\]", text):
                target = target.replace('\\|','|').split('|')[0]
                if target.startswith('#'): continue
                target = target.split('#')[0]
                if target not in self.outputs and target + '.md' not in self.outputs: failures.append("unresolved " + target)
        if failures: raise ValueError(failures)
        return {"passed": True, "sessions": len(self.records), "messages": sum(r['messages'] for r in self.records), "fragments": len(self.fragment_audit), "checks": ["all messages represented once", "all fragments accounted for", "raw GZIP roundtrip and SHA256", "attachment SHA256", "generated internal links resolve", "no inline encoded image data in Markdown"], "visual_verification": "not-run; use scripts/check_obsidian.py on an explicitly opened demo vault"}

    def commit(self):
        manifest_path = self.dest / "_维护" / "生成清单.json"
        if not manifest_path.resolve().is_relative_to(self.dest.resolve()):
            raise ValueError("Manifest escapes destination")
        old = json.loads(manifest_path.read_bytes()).get("files", {}) if manifest_path.exists() else {}
        # Preflight every output before writing; never silently overwrite user's edits.
        for name, data in self.outputs.items():
            path = self.dest / name
            if not path.resolve().is_relative_to(self.dest.resolve()): raise ValueError("Output escapes destination")
            if path.exists() and path.read_bytes() != data and sha(path.read_bytes()) != old.get(name):
                raise RuntimeError(f"File changed or not owned by generator; preserving it: {path}")
        for name, data in self.outputs.items():
            path = self.dest / name; path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_bytes() != data: path.write_bytes(data)
        hashes = {name: digest for name, digest in old.items() if name in INITIAL_CONFIGS}
        hashes.update({name: sha(data) for name, data in sorted(self.outputs.items())})
        manifest = {"version": VERSION, "scope": "synthetic-demo-only", "files": dict(sorted(hashes.items()))}
        manifest_path.write_text(jdump(manifest), encoding="utf-8", newline="\n")


INITIAL_CONFIGS = {
    ".obsidian/app.json": {"defaultViewMode": "preview", "showInlineTitle": False, "propertiesInDocument": "hidden", "readableLineLength": True, "attachmentFolderPath": "_附件", "showUnsupportedFiles": True, "promptDelete": True, "alwaysUpdateLinks": True},
    ".obsidian/appearance.json": {"enabledCssSnippets": ["deepseek-chat"], "baseFontSize": 16},
    ".obsidian/community-plugins.json": [],
    ".obsidian/types.json": {"types": {"created": "datetime", "updated": "datetime"}},
    ".obsidian/core-plugins.json": ["file-explorer", "global-search", "switcher", "backlink", "outgoing-link", "tag-pane", "properties", "page-preview", "outline", "file-recovery"],
}


def build_docs(builder, report):
    rows = []
    for i, record in enumerate(builder.records, 1):
        link = wiki(record["path"], record["title"]).replace("|", "\\|")
        rows.append(f"| {i} | {link} | {record['purpose']} |")
    home = """---
title: DeepSeek 的 Obsidian 墓志铭 · 合成演示库
cssclasses: [deepseek-chat]
tags: [demo/synthetic]
---

# DeepSeek 对话归档演示

六段对话、图片和代码均由本项目人工构造或程序生成，不包含真实聊天记录。

| 样板 | 对话 | 覆盖场景 |
|---|---|---|
""" + "\n".join(rows) + """

## 阅读方式

- 浅蓝色、右对齐的气泡是用户；🐋 和蓝色标题表示 DeepSeek。
- 思考、历史检索、长代码和历史分支可以展开阅读。
- 消息编号使用原生脚注，点击后可以通过回跳箭头返回。
- 图片直接嵌入，公式和表格使用 Markdown；HTML 保留为源码。
- 时间、会话 ID、计数和标签保存在笔记属性中。

[[01-对话索引|按时间浏览]] · [[02-格式与维护说明|格式说明]]
"""
    builder.put("00-首页.md", home)
    index = "# 对话索引\n\n[[00-首页|首页]]\n\n所有条目均为合成对话。\n"
    for record in sorted(builder.records, key=lambda row: row["created"], reverse=True):
        index += f"\n- {record['created'][:10]} · {wiki(record['path'], record['title'])} · {record['messages']} 条消息\n"
    builder.put("01-对话索引.md", index)
    builder.put("02-格式与维护说明.md", (ROOT / "references/vault-format.md").read_text(encoding="utf-8"))
    builder.put("_维护/全量结构统计.json", jdump(report))
    builder.put("_维护/会话映射.json", jdump({"schema_version": VERSION, "scope": "six-synthetic-sessions", "sessions": builder.records}))
    builder.put("_维护/片段处理记录.json", jdump(builder.fragment_audit))
    builder.put("_维护/资源映射.json", jdump(builder.assets))


def build(source: pathlib.Path, dest: pathlib.Path):
    source, dest = source.resolve(), dest.resolve()
    if str(dest).startswith("\\\\"):
        raise ValueError("Demo command does not write to UNC/NAS destinations")
    if source.is_relative_to(dest) or dest.is_relative_to(source):
        raise ValueError("Source and destination must not overlap")
    marker = json.loads((source / "manifest.json").read_bytes())
    if marker.get("export_format_version") != 3:
        raise ValueError("Unsupported export version")
    if marker.get("synthetic") is not True or marker.get("fixture_set") != "epitaph-six-v1":
        raise ValueError("This release accepts only the six synthetic fixtures")
    index = json.loads((source / "chat_session_index.json").read_bytes())
    if len(index) != len(SAMPLES) or {r["id"] for r in index} != {sid for sid, _ in SAMPLES}:
        raise ValueError("Expected the six synthetic fixture IDs")
    for path in source.rglob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError("Source must not contain links outside the fixture directory")
    for sid, _ in SAMPLES:
        session = json.loads((source / "chat_sessions" / f"{sid}.json").read_bytes())
        if session.get("synthetic") is not True or session.get("id") != sid:
            raise ValueError("Expected synthetic conversation")
        for message in session["messages"]:
            if message["role"] not in {"USER", "ASSISTANT"}:
                raise ValueError("Unsupported message role")
            for fragment in message["fragments"]:
                for attachment in fragment.get("files", []):
                    export = attachment.get("export_path")
                    if export and not (source / export).resolve().is_relative_to(source):
                        raise ValueError("Attachment path escapes source")
    builder = Builder(source, dest)
    report = builder.analyze()
    if report["index_mismatches"] or report["attachment_size_mismatches"]:
        raise ValueError("Source index or attachment metadata mismatch")
    for sid, purpose in SAMPLES:
        builder.session(sid, purpose)
    builder.put(".obsidian/snippets/deepseek-chat.css", CSS)
    for name, value in INITIAL_CONFIGS.items():
        if not (dest / name).exists():
            builder.put(name, jdump(value))
    build_docs(builder, report)
    result = builder.verify()
    current = {p.relative_to(source).as_posix(): sha(p.read_bytes()) for p in source.rglob("*") if p.is_file()}
    if current != builder.source_inventory:
        raise RuntimeError("Source changed during conversion")
    result["source_files_unchanged"] = len(current)
    builder.put("_维护/自动核验.json", jdump(result))
    builder.commit()
    return {"sessions": len(builder.records), "messages": result["messages"], "fragments": result["fragments"],
            "files_written_or_verified": len(builder.outputs), "transforms": dict(builder.transforms), "verification": "passed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=FIXTURE, help="Synthetic export directory; defaults to bundled fixtures")
    parser.add_argument("--dest", type=pathlib.Path, required=True, help="Separate local output vault")
    args = parser.parse_args()
    print(jdump(build(args.source, args.dest)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
