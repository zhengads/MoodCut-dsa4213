"""Resolve historical serialized names without changing saved evidence."""

from importlib.resources import files
import json

_ALIASES = json.loads(files("moodcut").joinpath("legacy_names.json").read_text(encoding="utf-8"))


def canonical_name(value):
    """Return a functional name; malformed values remain invalid at the caller."""
    return _ALIASES.get(value, value) if isinstance(value, str) else value
