"""Regression checks of archival behavior, without an Obsidian dependency."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_demo import Builder, build, main_path
from make_synthetic_export import FIXTURE, SAMPLES, make_export


def inventory(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.dest = self.root / "source", self.root / "vault"
        shutil.copytree(FIXTURE, self.source)

    def session(self, number):
        path = self.source / "chat_sessions" / (SAMPLES[number - 1][0] + ".json")
        return path, json.loads(path.read_bytes())

    def write_session(self, number, data):
        path, _ = self.session(number)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def mapping(self):
        return json.loads((self.dest / "_维护/会话映射.json").read_bytes())["sessions"]

    def test_complete_archive_and_source_unchanged(self):
        before = inventory(self.source)
        result = build(self.source, self.dest)
        self.assertEqual((result["sessions"], result["messages"], result["fragments"]), (6, 25, 33))
        self.assertEqual(inventory(self.source), before)
        for row in self.mapping():
            source = (self.source / "chat_sessions" / (row["id"] + ".json")).read_bytes()
            self.assertEqual(gzip.decompress((self.dest / row["raw"]).read_bytes()), source)
            note = (self.dest / row["path"]).read_text(encoding="utf-8")
            expected = {str(mid) for mid in row["main_ids"] + row["alternate_ids"]}
            definitions = re.findall(r"^\[\^msg-(\d+)\]:", note, re.M)
            self.assertEqual(set(definitions), expected)
            self.assertEqual(len(definitions), len(expected))
            self.assertNotRegex(note, r"(?m)^\^msg-")
            for a in row["attachments"]:
                if a["state"] == "copied":
                    self.assertEqual((self.dest / a["path"]).read_bytes(), (self.source / a["export_path"]).read_bytes())
        self.assertFalse((self.dest / "user.json").exists())

    def test_main_branch_and_retry_coverage(self):
        _, session = self.session(5)
        main, history = main_path(session)
        self.assertEqual([m["id"] for m in main], [1, 11, 12, 13])
        self.assertEqual([m["id"] for m in history], list(range(2, 11)))
        build(self.source, self.dest)
        row = self.mapping()[4]
        note = (self.dest / row["path"]).read_text(encoding="utf-8")
        self.assertIn("INCOMPLETE", note)
        self.assertIn("历史分支与重试", note)

    def test_think_depends_on_fragment_not_flag(self):
        build(self.source, self.dest)
        rows = self.mapping()
        self.assertIn("[!chat-think]", (self.dest / rows[0]["path"]).read_text(encoding="utf-8"))
        self.assertNotIn("[!chat-think]", (self.dest / rows[1]["path"]).read_text(encoding="utf-8"))

    def test_math_conversion_preserves_code(self):
        build(self.source, self.dest)
        note = (self.dest / self.mapping()[1]["path"]).read_text(encoding="utf-8")
        self.assertIn("$A=wh$", note)
        self.assertIn("$$", note)
        self.assertIn(r"`\(keep\)`", note)
        self.assertIn(r"formula = r'\[literal\]'", note)

    def test_resources_missing_file_and_code_roundtrip(self):
        build(self.source, self.dest)
        row = self.mapping()[5]
        note = (self.dest / row["path"]).read_text(encoding="utf-8")
        self.assertIn("原附件未包含在导出中", note)
        self.assertNotIn("base64,", note)
        code = next((self.dest / "_附件" / row["id"] / "代码").glob("*.css"))
        target = re.search(r'url\("([^\"]+)"\)', code.read_text(encoding="utf-8"))[1]
        self.assertTrue((code.parent / target).resolve().is_file())
        html_row = self.mapping()[3]
        html_file = next((self.dest / "_附件" / html_row["id"] / "代码").glob("*.html"))
        _, original = self.session(4)
        expected = original["messages"][1]["fragments"][0]["content"].removeprefix("```html\n").removesuffix("```")
        self.assertEqual(html_file.read_text(encoding="utf-8"), expected)

    def test_rebuild_is_byte_identical(self):
        build(self.source, self.dest)
        first = inventory(self.dest)
        build(self.source, self.dest)
        self.assertEqual(first, inventory(self.dest))

    def test_manual_edit_stops_all_writes(self):
        build(self.source, self.dest)
        note = self.dest / self.mapping()[-1]["path"]
        note.write_bytes(note.read_bytes() + "\n手写记录\n".encode())
        before = inventory(self.dest)
        with self.assertRaisesRegex(RuntimeError, "preserving"):
            build(self.source, self.dest)
        self.assertEqual(inventory(self.dest), before)

    def test_existing_unowned_file_preserved(self):
        self.dest.mkdir()
        (self.dest / "00-首页.md").write_text("我的首页", encoding="utf-8")
        before = inventory(self.dest)
        with self.assertRaisesRegex(RuntimeError, "preserving"):
            build(self.source, self.dest)
        self.assertEqual(inventory(self.dest), before)

    def test_existing_app_settings_preserved(self):
        build(self.source, self.dest)
        app = self.dest / ".obsidian/app.json"
        value = {"showInlineTitle": True, "customSetting": "keep"}
        app.write_text(json.dumps(value), encoding="utf-8")
        build(self.source, self.dest)
        self.assertEqual(json.loads(app.read_bytes()), value)

    def test_unknown_fragment_fails_before_writing(self):
        _, d = self.session(1)
        d["messages"][0]["fragments"][0]["type"] = "FUTURE_FRAGMENT"
        self.write_session(1, d)
        with self.assertRaisesRegex(ValueError, "Unhandled fragment"):
            build(self.source, self.dest)
        self.assertFalse(self.dest.exists())

    def test_invalid_main_chain_rejected(self):
        _, d = self.session(1)
        d["messages"][0]["parent_id"] = 2
        self.write_session(1, d)
        with self.assertRaisesRegex(ValueError, "Invalid message chain"):
            build(self.source, self.dest)
        self.assertFalse(self.dest.exists())

    def test_real_export_marker_rejected(self):
        (self.source / "manifest.json").write_text('{"export_format_version":3}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "synthetic"):
            build(self.source, self.dest)

    def test_attachment_escape_rejected(self):
        _, d = self.session(2)
        d["messages"][0]["fragments"][1]["files"][0]["export_path"] = "../outside.png"
        self.write_session(2, d)
        with self.assertRaisesRegex(ValueError, "escapes source"):
            build(self.source, self.dest)

    def test_declared_missing_file_stops(self):
        _, d = self.session(2)
        attachment = d["messages"][0]["fragments"][1]["files"][0]
        (self.source / attachment["export_path"]).unlink()
        with self.assertRaises(FileNotFoundError):
            build(self.source, self.dest)
        self.assertFalse(self.dest.exists())

    def test_source_destination_overlap_rejected(self):
        for target in [self.source, self.source / "vault", self.root]:
            with self.assertRaisesRegex(ValueError, "overlap"):
                build(self.source, target)

    def test_output_collision_rejected(self):
        builder = Builder(self.source, self.dest)
        builder.put("same.md", "first")
        with self.assertRaisesRegex(ValueError, "collision"):
            builder.put("same.md", "second")

    def test_output_traversal_rejected(self):
        builder = Builder(self.source, self.dest)
        builder.put("../outside.md", "do not write")
        with self.assertRaisesRegex(ValueError, "escapes destination"):
            builder.commit()
        self.assertFalse((self.root / "outside.md").exists())

    def test_synthetic_input_is_reproducible(self):
        fresh = self.root / "fresh"
        make_export(fresh)
        self.assertEqual(inventory(fresh), inventory(FIXTURE))


if __name__ == "__main__":
    unittest.main()
