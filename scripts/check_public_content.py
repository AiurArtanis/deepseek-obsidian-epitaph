"""Verify synthetic fixture provenance, generated examples and frozen file hashes."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

from build_demo import build
from make_synthetic_export import FIXTURE, SAMPLES, make_export

ROOT = Path(__file__).resolve().parents[1]


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and not any(part in {"__pycache__", ".git"} for part in p.relative_to(root).parts)}


def check():
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        make_export(temp / "source")
        if files(FIXTURE) != files(temp / "source"):
            raise ValueError("Committed fixtures differ from independently generated synthetic data")
        build(temp / "source", temp / "vault")
        if files(ROOT / "examples/demo-vault") != files(temp / "vault"):
            raise ValueError("Committed example vault differs from synthetic regeneration")
    allowed_ids = {sid for sid, _ in SAMPLES} | {f"1000000{i}-0000-4000-8000-000000000000" for i in (1, 2)} | {"20000001-0000-4000-8000-000000000000"}
    count = 0
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(p in {".git", "__pycache__", "output", ".venv"} for p in relative.parts):
            continue
        raw = path.read_bytes()
        if path.suffix == ".gz":
            raw = gzip.decompress(raw)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        count += 1
        ids = set(re.findall(r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b", text, re.I))
        if ids - allowed_ids:
            raise ValueError("Unexpected non-synthetic identifier in " + relative.as_posix())
        if re.search(r"(?i)\b[A-Z]:[\\/](?:Users|tmp|Work|AI|Program Files)[\\/]", text):
            raise ValueError("Machine-specific absolute path in " + relative.as_posix())
        if path.suffix == ".md" and re.search(r"data:[^\s]+;base64,", text):
            raise ValueError("Inline encoded image in Markdown: " + relative.as_posix())
    manifest = json.loads((ROOT / "references/frozen-files.json").read_bytes())
    for name, digest in manifest["files"].items():
        target = ROOT / name
        if not target.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Frozen manifest path escapes repository")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("Frozen file changed: " + name)
    return {"passed": True, "text_files_checked": count, "synthetic_data_reproduced": True,
            "example_vault_reproduced": True, "frozen_files": len(manifest["files"])}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(check(), ensure_ascii=False, indent=2))
