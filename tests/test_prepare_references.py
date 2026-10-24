"""Offline checks for reference preparation, independent of model APIs."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
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

    def test_animation_library_identities_match_selection_and_manifest(self):
        directory = ROOT / "assets/library"
        entries = references.load_manifest(directory / "movieagent-animation.sources.lock.json")
        selection = json.loads((directory / "movieagent-animation.selection.json").read_text(encoding="utf-8"))
        manifest = json.loads((directory / "movieagent-animation.manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 100)
        self.assertEqual(len(manifest["assets"]), 75)
        self.assertEqual(len(selection["characters"]), 25)
        self.assertFalse(selection["public_redistribution_authorized"])
        self.assertFalse(selection["commercial_use_cleared"])
        self.assertEqual(selection["rights_status"], "unconfirmed")
        by_path = {e["path"]: e for e in entries}
        self.assertEqual(len(by_path), len(entries))
        self.assertEqual({c["film"] for c in selection["characters"]},
                         {"FrozenII", "DespicableMe4", "InsideOut2", "NeZha2"})
        for selected, asset in zip(selection["assets"], manifest["assets"]):
            with self.subTest(asset=asset["asset_id"]):
                self.assertEqual({k: asset[k] for k in selected}, selected)
                source = by_path[asset["path"]]
                self.assertEqual(asset["sha256"], source["sha256"])
                self.assertEqual(asset["revision"], source["revision"])
                self.assertEqual(asset["source_url"], source["url"])
                self.assertEqual(asset["allowed_crops"], ["full"])
        for character in selection["characters"]:
            images = [a for a in manifest["assets"] if a["character_id"] == character["character_id"]]
            self.assertEqual(len(images), 3)
            self.assertEqual(len({a["sha256"] for a in images}), 3)
            self.assertIn(character["primary_asset_id"], {a["asset_id"] for a in images})
            self.assertIn(character["caption_path"], by_path)

    def test_animation_download_is_opt_in_and_shared_files_are_checked_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = dict(entry(), group="assets", path="assets/raw/movieagent/test.png")
            target = root / shared["path"]
            target.parent.mkdir(parents=True)
            target.write_bytes(b"reference source\n")
            (root / "references").mkdir()
            base = root / "references/sources.lock.json"
            base.write_text(json.dumps({"schema_version": 1, "files": [shared]}), encoding="utf-8")
            with patch.object(references, "ROOT", root):
                self.assertEqual(references.main(["--assets", "--check"]), 0)
                library = root / "assets/library/movieagent-animation.sources.lock.json"
                library.parent.mkdir(parents=True)
                library.write_text(json.dumps({"schema_version": 1, "files": [shared]}), encoding="utf-8")
                with patch.object(references, "prepare", wraps=references.prepare) as prepare:
                    self.assertEqual(references.main(["--assets", "--animation-assets", "--check"]), 0)
                    self.assertEqual(len(prepare.call_args.args[1]), 1)
                changed = dict(shared, sha256="0" * 64)
                library.write_text(json.dumps({"schema_version": 1, "files": [changed]}), encoding="utf-8")
                with patch.object(references, "prepare") as prepare:
                    self.assertEqual(references.main(["--assets", "--animation-assets", "--check"]), 1)
                    prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
