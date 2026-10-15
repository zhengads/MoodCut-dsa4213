"""Local import boundaries; generated examples are software tests only."""

import json

import pytest

from moodcut.importer import build_scene_from_synopsis, import_synopsis


def test_import_preserves_utf8_story_and_character_names(tmp_path):
    path = tmp_path / "synopsis.json"
    path.write_text(json.dumps({"MovieScript": "安娜递给艾莎一封信。", "Character": ["安娜", "艾莎"]}), encoding="utf-8")
    assert import_synopsis(path) == {"story": "安娜递给艾莎一封信。", "character_names": ["安娜", "艾莎"]}


@pytest.mark.parametrize("data", [[], {}, {"MovieScript": " ", "Character": ["A"]},
    {"MovieScript": "Story", "Character": []}, {"MovieScript": "Story", "Character": [3]},
    {"MovieScript": "Story", "Character": ["Anna", " anna "]}])
def test_import_rejects_invalid_fields(tmp_path, data):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        import_synopsis(path)


@pytest.mark.parametrize("text", ['{"MovieScript":"a","MovieScript":"b","Character":["A"]}', '{bad', '{"x":NaN}'])
def test_import_rejects_ambiguous_or_corrupt_json(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        import_synopsis(path)


def test_import_missing_file(tmp_path):
    with pytest.raises(ValueError, match="Cannot read synopsis"):
        import_synopsis(tmp_path / "missing.json")


def test_scene_builder_keeps_explicit_provenance_and_does_not_mutate():
    synopsis = {"story": "A greets B.", "character_names": ["A", "B"]}
    provenance = {"kind": "team_authored_development", "adaptation": "Synthetic unit-test story"}
    characters = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
    scene = build_scene_from_synopsis(synopsis, scene_id="test", tone="affectionate",
        characters=characters, beats=[{"id": "b1", "description": "A greets B"}],
        asset_ids=["a", "b"], provenance=provenance)
    assert scene["provenance"] == provenance
    scene["characters"][0]["name"] = "changed"
    assert characters[0]["name"] == "A"
    with pytest.raises(ValueError, match="exactly two"):
        build_scene_from_synopsis({**synopsis, "character_names": ["A", "B", "C"]},
            scene_id="test", tone="hostile", characters=characters, beats=[],
            asset_ids=[], provenance=provenance)
