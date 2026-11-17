"""Shared full-export renderer, distilled from the approved archive workflow."""
from __future__ import annotations
import base64
import binascii
import gzip
import html
import re
from urllib.parse import quote
import build_demo as r

class ArchiveBuilder(r.Builder):
    def __init__(self, source, dest):
        super().__init__(source, dest)
        self.case_paths = {}
        self.rendered_parts = []
        self.exceptions = []
        self.message_records = []

    def put(self, path, content):
        folded = path.casefold()
        if folded in self.case_paths and self.case_paths[folded] != path:
            raise ValueError("Case-insensitive filename collision: " + path)
        self.case_paths[folded] = path
        super().put(path, content)

    def externalize(self, text, sid):
        def replace(match):
            mime, encoded = match.groups()
            try:
                binary = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError):
                # These are truncated/example strings in the source, not recoverable images.
                digest = r.sha(match[0].encode())
                path = f"_附件/{sid}/内嵌资源/{digest[:20]}.uri.txt.gz"
                self.put(path, gzip.compress(match[0].encode(), mtime=0))
                self.assets.append({"kind": "invalid-embedded-source", "path": path, "mime": mime,
                                    "source_sha256": digest, "sha256": r.sha(self.outputs[path])})
                self.exceptions.append({"kind": "invalid-data-uri", "session_id": sid,
                                        "mime": mime, "source_sha256": digest, "archive": path})
                self.transforms["invalid_embedded_examples"] += 1
                return "[不完整的内嵌图像编码；原字符串见压缩源数据]"
            ext = {"image/svg+xml": ".svg", "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime, ".bin")
            path = f"_附件/{sid}/内嵌资源/{r.sha(binary)[:20]}{ext}"
            self.put(path, binary)
            self.assets.append({"kind": "embedded", "path": path, "mime": mime, "sha256": r.sha(binary)})
            self.transforms["embedded_data_uris"] += 1
            return "../内嵌资源/" + path.rsplit("/", 1)[-1]
        return r.DATA_URI.sub(replace, text)

    def literal_source_links(self, rendered):
        # Authored Obsidian examples are historical text, not links to this vault.
        parts = re.split(r"(`+[^`\n]*`+)", rendered)
        for i in range(0, len(parts), 2):
            parts[i], n = re.subn(r"(?<!\\)\[\[([^\]\n]+)\]\]",
                                  lambda m: r"\[\[" + m[1] + r"\]\]", parts[i])
            self.transforms["literal_source_wikilinks"] += n
            def local_link(match):
                target = match[2].strip().strip('<>')
                if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('//'):
                    return match[0]
                self.transforms['literal_source_relative_links'] += 1
                return match[0].replace('[', r'\[').replace(']', r'\]')
            parts[i] = re.sub(r'(?<!\\)\[([^\]\n]+)\]\((<[^>\n]*>|[^)\n]*)\)',local_link,parts[i])
        return "".join(parts)

    def prose(self, text):
        return self.literal_source_links(super().prose(text))

    def markdown(self, text, sid, mid, fi):
        result = super().markdown(text or "", sid, mid, fi)
        self.rendered_parts.append({"session_id": sid, "message_id": mid, "fragment": fi,
                                    "rendered_sha256": r.sha(result.encode()), "rendered_chars": len(result),
                                    "text": result})
        return result

    def search(self, fragments):
        blocks = []
        for fi, f in fragments:
            kind = f["type"]
            line = f"**片段 {fi} · {kind}** · 状态 `{f.get('status', '未记录')}`"
            if "stage_id" in f:
                line += f" · 阶段 {f['stage_id']}"
            if kind == "TOOL_SEARCH":
                line += "\n\n查询：" + "；".join(f.get("queries") or [])
                for item in f.get("results") or []:
                    url = item.get("url") or ""
                    title = html.escape(r.label(item.get("title") or url or "未命名结果"))
                    if url:
                        line += f"\n\n- [{title}](<{quote(url, safe='/:?=&%#@+~!$;,*-._')}>)"
                    else:
                        line += f"\n\n- {title}（原导出未记录 URL）"
                    if item.get("site_name"): line += " · " + r.label(item["site_name"])
                    if item.get("published_at"): line += " · " + item["published_at"]
                    if item.get("snippet"): line += "\n  " + self.literal_source_links(item["snippet"]).replace("\n", "\n  ")
            elif kind == "TOOL_OPEN":
                url = f.get("url") or ""
                if url:
                    title = html.escape(r.label(f.get("title") or url))
                    line += f"\n\n[{title}](<{quote(url, safe='/:?=&%#@+~!$;,*-._')}>)\n\n" + self.literal_source_links(f.get("snippet") or "")
                else:
                    line += "\n\n原导出未记录 URL、标题或正文摘要；保留该次打开网页操作及其状态。"
                    self.transforms["null_tool_open_records"] += 1
            else:
                line += "\n\n查找：" + r.fenced(f.get("pattern") or "")
            blocks.append(line)
        return "\n\n---\n\n".join(blocks)

    def message(self, message, session, attachments, historical=False):
        part_start = len(self.rendered_parts)
        result = super().message(message, session, attachments, historical)
        # Independently confirm every converted content fragment occurs inside the message.
        unquoted = "\n".join(re.sub(r"^(?:> ?)+", "", line) for line in result.splitlines())
        for part in self.rendered_parts[part_start:]:
            text = part.pop("text")
            plain = "\n".join(re.sub(r"^(?:> ?)+", "", line) for line in text.splitlines())
            if plain and plain not in unquoted:
                raise ValueError(f"Rendered fragment lost: {session['id']}/m{message['id']}/f{part['fragment']}")
        self.message_records.append({"session_id": session["id"], "message_id": message["id"],
                                     "parent_id": message["parent_id"], "role": message["role"],
                                     "status": message["status"], "historical": historical,
                                     "rendered_sha256": r.sha(result.encode()), "text": result})
        return result

    def session(self, sid, purpose="全量归档"):
        start = len(self.message_records)
        super().session(sid, purpose)
        record = self.records[-1]
        note = self.outputs[record["path"]].decode()
        for message in self.message_records[start:]:
            body = message.pop("text")
            if note.count(body) != 1:
                raise ValueError(f"Rendered message not represented exactly once: {sid}/m{message['message_id']}")

