"""Build six entirely invented DeepSeek v3 fixtures; no network or private input."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "synthetic-v3"
SAMPLES = [
    ("00000001-0000-4000-8000-000000000000", "表格、思考、搜索与网页查找"),
    ("00000002-0000-4000-8000-000000000000", "同名图片、行内与块级公式"),
    ("00000003-0000-4000-8000-000000000000", "原始 HTML 与围栏代码"),
    ("00000004-0000-4000-8000-000000000000", "多轮修改与长代码"),
    ("00000005-0000-4000-8000-000000000000", "重试分支、超时与未完成消息"),
    ("00000006-0000-4000-8000-000000000000", "缺失附件、内嵌资源与平台提示"),
]


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def png(rgb):
    """An original 96x64 color chart made directly from pixels."""
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    rows = b"".join(b"\0" + bytes(rgb if (y // 8) % 2 else (240, 245, 255)) * 96 for y in range(64))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 96, 64, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def make_export(destination: Path):
    files = {}
    index = []
    sessions = []
    for number, (sid, _) in enumerate(SAMPLES, 1):
        start = dt.datetime(2026, number, 1, 2, 3, 4, tzinfo=dt.timezone.utc)

        def stamp(seconds=0):
            return (start + dt.timedelta(seconds=seconds)).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        def frag(kind, content="", **extra):
            return {"type": kind, "content": content, **extra}

        def msg(mid, parent, role, fragments, status="FINISHED", thinking=False):
            return {"id": mid, "parent_id": parent, "role": role, "status": status,
                    "thinking_enabled": thinking, "search_enabled": number == 1,
                    "accumulated_token_usage": 0, "inserted_at": stamp(mid), "fragments": fragments}

        if number == 1:
            title = "合成样例：纸船与风车的材料比较"
            messages = [
                msg(1, None, "USER", [frag("REQUEST", "请用表格比较纸船与风车两种课堂手工作品需要的材料、制作步骤和展示方式，并保留引用记录。")]),
                msg(2, 1, "ASSISTANT", [
                    frag("THINK", "这是人工编写的思考片段，用于检验折叠展示。", elapsed_secs=1.5),
                    frag("TOOL_SEARCH", queries=["合成手工材料表"], status="FINISHED", stage_id=1,
                         results=[{"url": "https://example.com/craft", "title": "合成资料页", "site_name": "示例站点", "snippet": "虚构材料说明，不是实际检索结果。"}]),
                    frag("TOOL_OPEN", url="https://example.com/craft", title="合成资料页", snippet="纸张与木棒。", status="FINISHED"),
                    frag("TOOL_FIND", pattern="材料", status="FINISHED"),
                    frag("RESPONSE", "# 材料比较\n\n| 作品 | 材料 | 展示 |\n|---|---|---|\n| 纸船 | 彩纸 | 水盆 |\n| 风车 | 纸、木棒 | 窗边 |\n\n- 先准备材料。\n- 再完成折叠。\n\n> 所有内容均为演示数据。\n\n第一行<br>第二行。")], thinking=True),
            ]
        elif number == 2:
            title = "合成样例：两张色卡与简单面积公式"
            attachments = []
            for i, color in enumerate([(57, 100, 254), (30, 160, 120)], 1):
                fid = f"1000000{i}-0000-4000-8000-000000000000"
                path = f"chat_sessions/{sid}_files/{fid}_色卡.png"
                image = png(color)
                files[path] = image
                attachments.append({"id": fid, "file_name": "色卡.png", "file_size": len(image), "token_usage": 0,
                                    "inserted_at": stamp(), "export_path": path, "is_image": True, "width": 96, "height": 64})
            messages = [
                msg(1, None, "USER", [frag("REQUEST", r"比较这两张合成色卡，并展示矩形面积公式 \(A=wh\)。"), frag("FILE", files=attachments)]),
                msg(2, 1, "ASSISTANT", [frag("RESPONSE", "两张图均为脚本生成的条纹色卡。\n\n行内公式 \\(A=wh\\)。\n\n\\[\nA=6\\times4=24\n\\]\n\n内联代码 `\\(keep\\)` 保持原样。\n\n```python\nformula = r'\\[literal\\]'\n```" )], thinking=True),
            ]
        elif number == 3:
            title = "合成样例：HTML 卡片源码"
            messages = [
                msg(1, None, "USER", [frag("REQUEST", "<section class=\"demo\">\n  <h2>合成卡片</h2>\n  <p>只供源码展示。</p>\n</section>\n\n请解释这段 HTML。")]),
                msg(2, 1, "ASSISTANT", [frag("RESPONSE", "这是一个静态卡片。\n\n```html\n<!doctype html>\n<html lang=\"zh-CN\">\n<head><meta charset=\"utf-8\"><title>合成卡片</title></head>\n<body><section><h2>合成卡片</h2><p>示例文本</p></section></body>\n</html>\n```" )]),
            ]
        elif number == 4:
            title = "合成样例：分两轮调整展示列表"
            long_html = "<!doctype html>\n<html><body><ul>\n" + "\n".join(f"<li>合成条目 {i:02d}</li>" for i in range(1, 81)) + "\n</ul></body></html>\n"
            messages = [
                msg(1, None, "USER", [frag("REQUEST", "请生成包含八十个合成条目的静态列表页面，用来测试长代码折叠和独立源码附件的阅读方式。")]),
                msg(2, 1, "ASSISTANT", [frag("RESPONSE", "```html\n" + long_html + "```" )]),
                msg(3, 2, "USER", [frag("REQUEST", "请再提供一段可读的列表样式。")]),
                msg(4, 3, "ASSISTANT", [frag("RESPONSE", "```css\nul { padding: 1rem; }\nli { margin-block: .5rem; }\n```" )]),
            ]
        elif number == 5:
            title = "合成样例：保留重试及历史分支"
            messages = [msg(1, None, "USER", [frag("REQUEST", "请为虚构的纸艺活动提供三个简短名称。")])]
            messages += [msg(i, 1, "ASSISTANT", [frag("RESPONSE", f"第 {i - 1} 次合成尝试仅保存了这句片段。")], "TIMEOUT") for i in range(2, 11)]
            messages += [
                msg(11, 1, "ASSISTANT", [frag("RESPONSE", "1. 折纸时光\n2. 纸间漫游\n3. 彩纸工坊")]),
                msg(12, 11, "USER", [frag("REQUEST", "请为第二个名称补一句活动简介。")]),
                msg(13, 12, "ASSISTANT", [frag("RESPONSE", "纸间漫游：用折叠和想象……")], "INCOMPLETE"),
            ]
        else:
            title = "合成样例：缺失文件与内嵌图案"
            svg = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><circle cx="8" cy="8" r="6" fill="#3964fe"/></svg>'
            uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode("ascii")
            css = ".demo { background-image: url(\"" + uri + "\"); }\n" + "\n".join(f".item-{i:02d} {{ margin: {i}px; }}" for i in range(1, 76))
            missing = {"id": "20000001-0000-4000-8000-000000000000", "file_name": "合成缺失样式.css", "file_size": 1234,
                       "token_usage": 0, "inserted_at": stamp(), "export_path": None, "is_image": False}
            messages = [
                msg(1, None, "USER", [frag("REQUEST", "请检查这个演示附件；原导出故意不包含文件实体。"), frag("FILE", files=[missing])]),
                msg(2, 1, "ASSISTANT", [frag("TEMPLATE_RESPONSE", "以下为合成模板回复，无法恢复缺失附件。\n\n```css\n" + css + "\n```"),
                                          frag("CONTENT_RISK", "合成平台状态提示，仅测试呈现。"), frag("TIP", "合成提示：此处没有真实用户资料。")], "CONTENT_FILTER"),
            ]
        session = {"id": sid, "title": title, "pinned": number == 1, "current_message_id": messages[-1]["id"],
                   "inserted_at": stamp(), "updated_at": stamp(len(messages) + 1), "messages": messages, "synthetic": True}
        sessions.append(session)
        files[f"chat_sessions/{sid}.json"] = json_bytes(session)
        index.append({**{k: session[k] for k in ["id", "title", "pinned", "inserted_at", "updated_at"]}, "message_count": len(messages)})
    files["manifest.json"] = json_bytes({"export_format_version": 3, "synthetic": True, "fixture_set": "epitaph-six-v1"})
    files["chat_session_index.json"] = json_bytes(index)
    files["user.json"] = json_bytes({"display_name": "Synthetic fixture account", "synthetic": True})
    # Preflight the entire destination; never replace unrelated existing input.
    for name, data in files.items():
        target = destination / name
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError("Fixture path escapes destination")
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError(f"Existing fixture differs; use a fresh directory: {target}")
    for name, data in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return {"sessions": len(sessions), "messages": sum(len(s["messages"]) for s in sessions),
            "fragments": sum(len(m["fragments"]) for s in sessions for m in s["messages"]), "files": len(files)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=FIXTURE)
    print(json.dumps(make_export(parser.parse_args().dest), ensure_ascii=False))
