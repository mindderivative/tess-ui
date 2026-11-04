"""The first line of a Tesserae YAML file: `tesserae: <line>`, the release series the file was written for (#292).

A view, a stylesheet or a theme says which line of Tesserae it is written for, on its first line, so a loader can tell a Tesserae file from any other
YAML and a file for another line from one for this. In this line (`LINE`) the key is **optional**: a file without it loads and is noted once; one with it
is checked, and a file for an older line is refused until `tesserae migrate-yaml` moves it forward (`older_line` finds one, `restamp` moves it). It is
meant to be required from a later line. The value is the first two parts of the package version (`LINE`); it moves only when a new line is
started, and `tests/test_language_marker.py` fails when the version moves without it.

`scan(text)` reads the first line without parsing the YAML. `strip(data)` takes the key out of a parsed mapping, so no loader's own check of keys
(a node's properties, a stylesheet's `styles:`, a theme's fields) ever sees it. `note_if_missing(text, file)` is for the loaders that read a file from
disk; text handed straight to the parser is never noted.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional

from loguru import logger

__all__ = ["KEY", "LINE", "Marker", "SCHEMA", "note_if_missing", "older_line", "restamp", "scan", "strip"]

KEY = "tesserae"
#: The release series this Tesserae reads and writes: the first two parts of its version.
LINE = "0.6"

#: The key as an editor's schema describes it. A YAML parser reads `0.6` as a number, hence both types.
SCHEMA = {"type": ["number", "string"], "description": f"The release series of Tesserae this file was written for ({LINE}). It must be the first line of the file."}

_FIRST = re.compile(r"tesserae[ \t]*:[ \t]*(.*)$")
_FIRST_VALUE = re.compile(r"\A(\ufeff?tesserae[ \t]*:[ \t]*)\d+\.\d+")
_ELSEWHERE = re.compile(r"(?m)^tesserae[ \t]*:")
_VALUE = re.compile(r"(\d+)\.(\d+)")
_noted: set[str] = set()


@dataclass(frozen=True)
class Marker:
    """What the first line says: `found` the key is on line 1, its `value` (the text), and a `problem` (a sentence) with the `line` it is about."""

    found: bool = False
    value: Optional[str] = None
    problem: Optional[str] = None
    line: int = 1


def _tuple(text: str) -> tuple[int, int]:
    found = _VALUE.fullmatch(text)
    assert found
    return int(found[1]), int(found[2])


def scan(text: str) -> Marker:
    """The marker at the top of `text` (a UTF-8 byte order mark and CRLF lines are allowed), or a problem with it. Nothing is parsed."""
    text = text.removeprefix("﻿")
    first, _, rest = text.partition("\n")
    found = _FIRST.match(first.rstrip("\r"))
    if found is None:
        later = _ELSEWHERE.search(text)
        if later is None:
            return Marker()
        line = text.count("\n", 0, later.start()) + 1
        return Marker(problem=f"`tesserae:` must be the first line of the file (it is on line {line}): move `tesserae: {LINE}` to line 1", line=line)
    value = re.split(r"(?:^|\s)#", found[1], maxsplit=1)[0].strip()
    if not _VALUE.fullmatch(value):
        said = f", not `tesserae: {value}`" if value else ""
        return Marker(True, value, f"`tesserae:` names the release series the file was written for: write `tesserae: {LINE}`{said}")
    if _tuple(value) > _tuple(LINE):
        return Marker(True, value, f"written for Tesserae {value}; this is Tesserae {LINE}.x: upgrade Tesserae (`pip install --upgrade tesserae-ui`)")
    if _tuple(value) < _tuple(LINE):
        return Marker(True, value, f"written for Tesserae {value}: run `tesserae migrate-yaml` on the project to bring it to {LINE}")
    return Marker(True, value)


def older_line(text: str) -> Optional[str]:
    """The series the first line of `text` names when it is older than `LINE`, which is what `tesserae migrate-yaml` brings forward; else `None`."""
    scanned = scan(text)
    if scanned.found and scanned.value and _VALUE.fullmatch(scanned.value) and _tuple(scanned.value) < _tuple(LINE):
        return scanned.value
    return None


def restamp(text: str) -> str:
    """`text` with the series on its first line moved to `LINE`. Nothing else changes: a comment after the value, a byte order mark and Windows line
    ends stay as they were."""
    return _FIRST_VALUE.sub(lambda found: found[1] + LINE, text, count=1)


def strip(data: Any) -> Any:
    """`data` without the marker key, when it is a mapping (a `PMap` loses its positions for it as well); anything else as it is."""
    if isinstance(data, dict) and KEY in data:
        data.pop(KEY)
        for positions in (getattr(data, "key_at", None), getattr(data, "val_at", None)):
            if positions is not None:
                positions.pop(KEY, None)
    return data


def note_if_missing(text: str, file: str) -> None:
    """Says once per file that it has no `tesserae: <line>` first line (the key is optional in this line)."""
    if file in _noted or scan(text).found:
        return
    _noted.add(file)
    logger.info(f"{file}: no `tesserae: {LINE}` on its first line; it is optional in the {LINE} line and required from the next: write it as the file's first line")
