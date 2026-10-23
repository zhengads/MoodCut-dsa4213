"""Small generated images exercise preservation/failure boundaries, no real portraits."""

from copy import deepcopy
import hashlib
import importlib.util
import io
from pathlib import Path

from PIL import Image, features
import pytest


SPEC = importlib.util.spec_from_file_location("prepare_umbrella_assets",
    Path(__file__).resolve().parents[1] / "scripts/prepare_umbrella_assets.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


@pytest.fixture
def case(tmp_path):
    if not features.check("avif"):
        pytest.skip("AVIF-capable Pillow required for the conversion fixture")
    lock = {"schema_version": 1, "revision": "a" * 40,
            "credit": "Synthetic unit-test image; no external portrait or license evidence",
            "sources": [], "portraits": [], "selection": {"schema_version": "1.0", "assets": []},
            "offline_manifest": {"schema_version": "1.0", "assets": []}}
    for index in range(2):
        original = f"assets/raw/unit/{index}.avif"
        converted = f"assets/raw/unit/{index}.png"
        url = f"https://raw.githubusercontent.com/ambravo/sigils-people/{lock['revision']}/{index}.avif"
        data = io.BytesIO()
        Image.new("RGB", (16, 24), (index * 100, 70, 120)).save(data, format="AVIF",
            xmp=b'<x:xmpmeta xmlns:x="adobe:ns:meta/">synthetic test marking</x:xmpmeta>')
        raw = data.getvalue()
        sha = hashlib.sha256(raw).hexdigest()
        target = tmp_path / original
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        png, pixels, size = tool.encode_png(raw, credit=lock["credit"], source_url=url, source_sha256=sha)
        lock["sources"].append({"path": original, "url": url, "size_bytes": len(raw), "sha256": sha})
        lock["portraits"].append({"original_path": original, "origin_url": url, "original_sha256": sha,
            "converted": {"path": converted, "sha256": hashlib.sha256(png).hexdigest(), "size_bytes": len(png),
                          "decoded_rgb_sha256": pixels, "dimensions": size}})
        selected = {"asset_id": f"p{index}", "character_id": f"c{index}", "path": converted,
                    "source_url": f"https://example.invalid/{index}.png", "revision": lock["revision"],
                    "sha256": hashlib.sha256(png).hexdigest(), "rights_note": lock["credit"],
                    "allowed_crops": ["full"]}
        lock["selection"]["assets"].append(selected)
        lock["offline_manifest"]["assets"].append({**selected, "width": 16, "height": 24})
    return lock


def test_local_conversion_preserves_pixels_xmp_credit_and_check_is_read_only(tmp_path, case, monkeypatch):
    monkeypatch.setattr(tool, "download", lambda _: pytest.fail("No network in default/check modes"))
    before = deepcopy(case)
    assert tool.prepare(case, root=tmp_path)["files_written"] == 2
    for p in case["portraits"]:
        with Image.open(tmp_path / p["original_path"]) as original, Image.open(tmp_path / p["converted"]["path"]) as png:
            assert original.convert("RGB").tobytes() == png.convert("RGB").tobytes()
            assert png.info["Attribution"] == case["credit"]
            assert png.info["Source"] == p["origin_url"]
            assert "synthetic test marking" in png.info["XML:com.adobe.xmp"]
            assert "synthetic person" in png.info["DigitalSourceType"]
    snapshot = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = tool.prepare(case, root=tmp_path, check=True)
    assert result["files_written"] == 0 and not result["execution_enabled"]
    assert all(p.read_bytes() == data for p, data in snapshot.items())
    assert case == before


@pytest.mark.parametrize("which", ["source", "converted"])
def test_tampered_source_or_conversion_is_never_repaired(tmp_path, case, monkeypatch, which):
    tool.prepare(case, root=tmp_path)
    p = case["portraits"][0]
    target = tmp_path / (p["original_path"] if which == "source" else p["converted"]["path"])
    target.write_bytes(b"keep this changed file")
    monkeypatch.setattr(tool, "download", lambda _: pytest.fail("Must not refetch altered files"))
    with pytest.raises(ValueError):
        tool.prepare(case, root=tmp_path, fetch=True)
    assert target.read_bytes() == b"keep this changed file"


def test_missing_source_needs_explicit_fetch(tmp_path, case, monkeypatch):
    path = tmp_path / case["sources"][0]["path"]
    raw = path.read_bytes()
    path.unlink()
    with pytest.raises(ValueError, match="explicit --fetch"):
        tool.prepare(case, root=tmp_path)
    calls = []
    monkeypatch.setattr(tool, "download", lambda entry: calls.append(entry["path"]) or raw)
    assert tool.prepare(case, root=tmp_path, fetch=True)["files_written"] == 3
    assert calls == [case["sources"][0]["path"]] and path.read_bytes() == raw


def test_read_only_check_missing_conversion_writes_nothing(tmp_path, case):
    with pytest.raises(ValueError, match="Converted image missing"):
        tool.prepare(case, root=tmp_path, check=True)
    assert not list(tmp_path.rglob("*.png"))


@pytest.mark.parametrize("field,value", [("decoded_rgb_sha256", "0" * 64), ("sha256", "0" * 64),
                                        ("dimensions", [1, 1]), ("size_bytes", 1)])
def test_conversion_lock_mismatch_stops_before_writes(tmp_path, case, field, value):
    case["portraits"][1]["converted"][field] = value
    with pytest.raises(ValueError, match="Conversion differs"):
        tool.prepare(case, root=tmp_path)
    assert not list(tmp_path.rglob("*.png"))


def test_unpinned_source_url_rejected_before_fetch(tmp_path, case, monkeypatch):
    case["sources"][0]["url"] = "https://example.com/image.avif"
    monkeypatch.setattr(tool, "download", lambda _: pytest.fail("Must reject URL first"))
    with pytest.raises(ValueError, match="outside the pinned"):
        tool.prepare(case, root=tmp_path, fetch=True)


def test_avif_origin_cannot_be_misbound_to_another_file(tmp_path, case):
    case["portraits"][0]["origin_url"] = case["portraits"][1]["origin_url"]
    with pytest.raises(ValueError, match="origin URL/hash differs"):
        tool.prepare(case, root=tmp_path)
    assert not list(tmp_path.rglob("*.png"))
