"""Offline checks for reference preparation, independent of model APIs."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare_references", ROOT / "scripts/prepare_references.py")
references = importlib.util.module_from_spec(spec)
spec.loader.exec_module(references)


def entry(data=b"reference source\n"):
    return {"path": "references/upstream/example/source.py", "group": "core",
            "url": "https://raw.githubusercontent.com/example/source/" + "a" * 40 + "/source.py",
            "revision": "a" * 40, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


class ReferencePreparationTests(unittest.TestCase):
    def test_missing_download_is_verified_and_second_run_is_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fetch = Mock(return_value=b"reference source\n")
            self.assertEqual(references.prepare(root, [entry()], fetch=fetch), (0, 1))
            fetch.assert_called_once()
            fetch.reset_mock()
            self.assertEqual(references.prepare(root, [entry()], check=True, fetch=fetch), (1, 0))
            fetch.assert_not_called()

    def test_check_never_downloads_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            fetch = Mock()
            with self.assertRaisesRegex(ValueError, "Missing references"):
                references.prepare(Path(directory), [entry()], check=True, fetch=fetch)
            fetch.assert_not_called()

    def test_bad_download_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "mismatch"):
                references.prepare(root, [entry()], fetch=lambda _: b"tampered source")
            self.assertFalse((root / entry()["path"]).exists())

    def test_local_edits_are_preserved_and_preflight_stops_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / entry()["path"]
            target.parent.mkdir(parents=True)
            target.write_bytes(b"local notes")
            fetch = Mock()
            with self.assertRaises(ValueError):
                references.prepare(root, [entry()], fetch=fetch)
            self.assertEqual(target.read_bytes(), b"local notes")
            fetch.assert_not_called()

    def test_manifest_rejects_escape_and_mutable_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "lock.json"
            for bad in [dict(entry(), path="references/upstream/../../outside.py"),
                        dict(entry(), url="https://raw.githubusercontent.com/example/source/main/source.py"),
                        dict(entry(), path="C:/outside.py")]:
                with self.subTest(bad=bad):
                    manifest.write_text(json.dumps({"schema_version": 1, "files": [bad]}), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        references.load_manifest(manifest)

    def test_committed_manifest_has_pinned_sources_and_expected_groups(self):
        entries = references.load_manifest(ROOT / "references/sources.lock.json")
        self.assertEqual({group: sum(e["group"] == group for e in entries)
                          for group in ("core", "papers", "assets")},
                         {"core": 33, "papers": 2, "assets": 4})


if __name__ == "__main__":
    unittest.main()
