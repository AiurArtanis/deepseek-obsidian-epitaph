"""Optional live check of an explicitly opened synthetic vault via Obsidian CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


class Reviewer:
    def __init__(self, cli, vault):
        self.cli = cli
        self.vault = vault

    def command(self, *args):
        result = subprocess.run([self.cli, "vault=" + self.vault.name, *args], capture_output=True, encoding="utf-8", timeout=20)
        output = result.stdout.strip()
        if result.returncode or re.search(r"(?m)^Error:", output):
            raise RuntimeError(output or result.stderr)
        return output

    def evaluate(self, code):
        text = self.command("eval", "code=" + code)
        if text.startswith("=> "):
            text = text[3:]
        return json.loads(text)

    def inspect(self, rows):
        actual = self.evaluate("JSON.stringify(app.vault.adapter.getBasePath())")
        if Path(actual).resolve() != self.vault:
            raise RuntimeError("Obsidian selected a different vault; no view changes made")
        previous = self.evaluate("JSON.stringify(app.workspace.activeLeaf.getViewState())")
        throttling = self.evaluate('require("electron").remote.getCurrentWebContents().getBackgroundThrottling()')
        results = []
        try:
            self.evaluate('(()=>{require("electron").remote.getCurrentWebContents().setBackgroundThrottling(false);return true})()')
            for row in rows:
                self.command("open", "path=" + row["path"])
                self.evaluate("(async()=>{const l=app.workspace.activeLeaf,s=l.getViewState();await l.setViewState({...s,state:{...s.state,mode:'preview'}});return true})()")
                deadline = time.monotonic() + 15
                while True:
                    stats = self.evaluate(STATS)
                    ready = (stats.get("file") == row["path"] and stats.get("title") == row["title"]
                             and stats.get("userBubble") and stats.get("footnoteLinks")
                             and all(i["loaded"] for i in stats["images"]))
                    if ready:
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Rendering timed out: " + row["path"])
                    time.sleep(.25)
                expected = {"msg-" + str(i) for i in row["main_ids"] + row["alternate_ids"]}
                checks = {
                    "footnote_definitions": set(stats["footnotes"]) == expected,
                    "footnote_references": set(stats["footnoteRefs"]) == expected,
                    "user_background": stats["userBubble"] == "rgb(237, 243, 254)",
                    "deepseek_title": stats["aiTitleColor"] == "rgb(57, 100, 254)",
                    "whale_icon": "🐋" in (stats["aiIcon"] or ""),
                    "right_alignment": bool(stats["userAlignment"]) and all(a == "right" for a in stats["userAlignment"]),
                    "round_title_limit": all(len(h) <= 40 for h in stats["roundHeadings"]),
                    "math": stats["mathErrors"] == 0,
                    "removed_properties": not stats["removedProperties"],
                }
                failed = [name for name, passed in checks.items() if not passed]
                if failed:
                    raise RuntimeError(row["path"] + ": " + ", ".join(failed))
                results.append({**stats, "checks": checks, "passed": True})
                print(json.dumps({"sample": len(results), "passed": True}), flush=True)
        finally:
            # Restore only the explicit target vault's active view and temporary throttle flag.
            try:
                self.evaluate("(async()=>{await app.workspace.activeLeaf.setViewState(" + json.dumps(previous) + ");return true})()")
            finally:
                self.evaluate('(()=>{require("electron").remote.getCurrentWebContents().setBackgroundThrottling(' + json.dumps(throttling) + ');return true})()')
        return results


STATS = """(()=>{
const f=app.workspace.getActiveFile(),c=f?app.metadataCache.getFileCache(f):null;
const p=app.workspace.activeLeaf.view.containerEl.querySelector('.markdown-preview-view');
if(!p)return JSON.stringify({});
const u=p.querySelector('[data-callout=chat-user]'),a=p.querySelector('[data-callout=chat-ai-deepseek]');
const fm=c?.frontmatter||{};
return JSON.stringify({file:f?.path,title:p.querySelector('h1')?.textContent,
footnotes:(c?.footnotes||[]).map(e=>e.id),footnoteRefs:(c?.footnoteRefs||[]).map(e=>e.id),
footnoteLinks:p.querySelectorAll('.footnote-link').length,
userBubble:u?getComputedStyle(u).backgroundColor:null,
aiTitleColor:a?getComputedStyle(a.querySelector('.callout-title')).color:null,
aiIcon:a?getComputedStyle(a.querySelector('.callout-icon'),'::before').content:null,
userAlignment:u?[...u.querySelectorAll('.callout-title-inner,.callout-content,p,pre,code,li,th,td')].filter(e=>e.textContent.trim()).map(e=>getComputedStyle(e).textAlign):[],
roundHeadings:[...p.querySelectorAll('h2')].filter(e=>e.textContent.startsWith('第 ')).map(e=>e.textContent),
removedProperties:['created_utc','updated_utc','source_sha256','format_version','sample_focus','archive_note','timezone','type'].filter(k=>k in fm),
tables:p.querySelectorAll('table').length,codeBlocks:p.querySelectorAll('pre').length,
math:p.querySelectorAll('.math').length,mathErrors:p.querySelectorAll('mjx-merror,.MathJax_Error').length,
images:[...p.querySelectorAll('img')].map(e=>({loaded:e.complete&&e.naturalWidth>0}))});
})()"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", type=Path, required=True, help="Already registered and opened synthetic vault")
    parser.add_argument("--cli", default=shutil.which("obsidian") or shutil.which("Obsidian.com"))
    parser.add_argument("--report", type=Path, required=True, help="New JSON report path outside the input fixture")
    args = parser.parse_args()
    if not args.cli:
        parser.error("Obsidian CLI not found; enable the CLI in Obsidian or pass --cli")
    vault = args.vault_path.resolve()
    report = args.report.resolve()
    if report.exists():
        parser.error("Report already exists; choose a new output path")
    mapping = json.loads((vault / "_维护/会话映射.json").read_bytes())
    if mapping.get("scope") not in {"six-synthetic-sessions", "demo"}:
        parser.error("The target must be a generated review/demo vault")
    if mapping.get("scope") == "demo":
        profile = json.loads((vault / "_维护/样板审核.json").read_bytes())["binding"]["profile"]
        if profile.get("slug") != "deepseek":
            parser.error("This DeepSeek visual check needs provider-specific assertions for another profile")
    reviewer = Reviewer(args.cli, vault)
    results = reviewer.inspect(mapping["sessions"])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"passed": True, "obsidian": reviewer.command("version"), "samples": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
