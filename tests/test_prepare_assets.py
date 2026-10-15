"""Explicit local image selection and filesystem boundary tests."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

from PIL import Image
import pytest


SPEC = importlib.util.spec_from_file_location("moodcut_prepare_assets", Path(__file__).resolve().parents[1] / "scripts/prepare_assets.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


@pytest.fixture
def selection(tmp_path):
    path = tmp_path / "assets/raw/team/a.png"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (8, 12), "blue").save(path)
    return {"schema_version": "1.0", "assets": [{"asset_id": "a", "character_id": "a",
        "path": "assets/raw/team/a.png", "source_url": None, "revision": None,
        "rights_note": "Generated solid-color unit-test image", "allowed_crops": ["full"]}]}


def test_manifest_records_real_hash_dimensions_and_explicit_rights(tmp_path, selection):
    before = deepcopy(selection)
    result = tool.prepare_assets(selection, project_root=tmp_path)
    asset = result["assets"][0]
    assert (asset["width"], asset["height"]) == (8, 12)
    assert asset["sha256"] == hashlib.sha256((tmp_path / asset["path"]).read_bytes()).hexdigest()
    assert asset["source_url"] is None and asset["allowed_crops"] == ["full"]
    assert selection == before


def test_source_revision_and_unknown_rights_preserved_without_download(tmp_path, selection):
    selected = selection["assets"][0]
    selected.update(source_url="https://example.test/source/image.png",
                    revision="1234567890abcdef" * 2 + "12345678",
                    rights_note="Third-party license unconfirmed; local research reference only")
    asset = tool.prepare_assets(selection, project_root=tmp_path)["assets"][0]
    for field in ("source_url", "revision", "rights_note"):
        assert asset[field] == selected[field]


@pytest.mark.parametrize("path", ["../escape.png", "C:/escape.png", "/escape.png", "assets/a.png", "assets/raw/../../escape.png", "assets\\raw\\a.png"])
def test_unsafe_or_non_raw_paths_rejected(tmp_path, selection, path):
    selection["assets"][0]["path"] = path
    with pytest.raises(ValueError):
        tool.prepare_assets(selection, project_root=tmp_path)


@pytest.mark.parametrize("field,value", [("sha256", "0" * 64), ("allowed_crops", []),
    ("rights_note", ""), ("source_url", "https://example.test/image.png")])
def test_hash_and_explicit_metadata_required(tmp_path, selection, field, value):
    selection["assets"][0][field] = value
    with pytest.raises(ValueError):
        tool.prepare_assets(selection, project_root=tmp_path)


def test_corrupt_image_and_duplicate_ids_fail(tmp_path, selection):
    selection["assets"].append(deepcopy(selection["assets"][0]))
    with pytest.raises(ValueError, match="duplicate asset_id"):
        tool.prepare_assets(selection, project_root=tmp_path)
    selection["assets"].pop()
    (tmp_path / selection["assets"][0]["path"]).write_bytes(b"not an image")
    with pytest.raises(ValueError, match="invalid image"):
        tool.prepare_assets(selection, project_root=tmp_path)


def test_cli_never_overwrites_existing_manifest(tmp_path, selection):
    selected = tmp_path / "selection.json"
    selected.write_text(json.dumps(selection), encoding="utf-8")
    args = ["--selection", str(selected), "--output", "assets/manifest.json", "--project-root", str(tmp_path)]
    assert tool.main(args) == 0
    manifest = tmp_path / "assets/manifest.json"
    original = manifest.read_bytes()
    assert tool.main(args) == 1
    assert manifest.read_bytes() == original
    assert tool.main([*args, "--check"]) == 0
    assert manifest.read_bytes() == original
    changed = json.loads(original)
    changed["assets"][0]["width"] += 1
    manifest.write_text(json.dumps(changed), encoding="utf-8")
    assert tool.main([*args, "--check"]) == 1
    assert json.loads(manifest.read_text(encoding="utf-8")) == changed
