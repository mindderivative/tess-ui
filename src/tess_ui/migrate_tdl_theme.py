"""`tesserae migrate-tdl` for themes: `*_Theme.yaml` (and the shipped `default_theme.yaml`) as `*_Theme.tdl` (piece 5 of `design/tdl-switch-plan.md`).

`convert_theme(text, name)` turns the text of one YAML theme into TDL with the machinery of `migrate_tdl` (comments, blank lines and key order kept, two spaces to a
level, a one-line YAML mapping on one line up to 150 columns) and the shape in `design/tdl-views.md` ("What piece 5 decided"): a root `Theme { }` holding `Seed`,
`Dark`, `Colors { }`, `Typography { }`, `Components { }` and `Styles { }`; a colour is quoted (`"#0B6B58"`); a component key with a dot is a nested block
(`card.elevated` is `Card { Elevated { } }`). Every result is read back with `spec/tdl_theme.py` and compared with the YAML loader's mapping, so a form that has no TDL
form is a `ConvertError` naming the YAML line, never a nearly right file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from tess_ui.migrate_tdl import (
    _KEY, _NO_BLOCK, ConvertError, Converted, FileResult, _canon, _Converter, _Line, _line_of, _where,
)
from tess_ui.spec import marker
from tess_ui.spec.expand import _normalize_scalars
from tess_ui.spec.nodes import LoadError, _near
from tess_ui.spec.tdl import LANGUAGE_VERSION
from tess_ui.spec.tdl_theme import ROOT, THEME_KEYS, load_theme_tdl

__all__ = ["convert_theme", "theme_result", "theme_stem"]

_VARIANT = re.compile(r"^[a-z][a-z0-9_]*$")


def theme_stem(file_name: str) -> str:
    """The `Name` of a theme's TDL file: `Brand_Theme.yaml` is `Brand`, `default_theme.yaml` is `default_theme`."""
    stem = file_name.removesuffix(".yaml")
    return stem.removesuffix("_Theme")


class _Group:
    """The components `card`, `card.elevated`, ... as a tree: a node has the pair of its own key (if the theme has one) and its variants."""

    def __init__(self) -> None:
        self.own: tuple[yaml.Node, yaml.Node] | None = None
        self.variants: dict[str, _Group] = {}


class _ThemeConverter(_Converter):
    def __init__(self, text: str, name: str, file: str) -> None:
        super().__init__(text, name, file, None)

    def components(self, kn: yaml.Node, vn: yaml.Node, indent: int) -> list[_Line]:
        if not isinstance(vn, yaml.MappingNode) or not vn.value:
            return self.map_entry(kn, vn, indent, steps=False)
        groups: dict[str, _Group] = {}
        order: list[str | tuple[yaml.Node, yaml.Node]] = []
        for ckn, cvn in vn.value:
            key = self.key_text(ckn)
            if not isinstance(cvn, yaml.MappingNode):
                if "." in key:
                    raise self.fail(ckn, f"the component '{key}' is not a mapping", "a component's fields are a mapping: corner_radius and elevation")
                order.append((ckn, cvn))
                continue
            parts = key.split(".")
            for part in parts:
                if not _VARIANT.match(part):
                    raise self.fail(ckn, f"the component key '{key}' has a part '{part}' that is not lower snake_case",
                                    "a component is words of lower case letters, digits and underscores, with dots between component and variant")
            if parts[0] not in groups:
                groups[parts[0]] = _Group()
                order.append(parts[0])
            group = groups[parts[0]]
            for part in parts[1:]:
                group = group.variants.setdefault(part, _Group())
            if group.own is not None:
                raise self.fail(ckn, f"the component '{key}' is written twice")
            group.own = (ckn, cvn)
        head = self.key_of(self.key_text(kn), kn, block=True)
        out = [_Line(indent, f"{head} {{", (_line_of(kn),), (_line_of(kn),))]
        for item in order:
            if isinstance(item, str):
                out += self.group(item, groups[item], indent + 2)
            else:
                out += self.map_entry(item[0], item[1], indent + 2, steps=False)
        return [*out, _Line(indent, "}")]

    def group(self, name: str, group: _Group, indent: int) -> list[_Line]:
        head = self.key_of(name, group.own[0] if group.own else self.first(group), block=True)
        if not group.variants:
            assert group.own is not None
            return self.map_block(head, group.own[1], indent, _line_of(group.own[0]))  # type: ignore[arg-type]
        first = _line_of(group.own[0]) if group.own else _line_of(self.first(group))
        out = [_Line(indent, f"{head} {{", (first,), (first,))]
        if group.own is not None:
            assert isinstance(group.own[1], yaml.MappingNode)
            for fkn, fvn in group.own[1].value:
                out += self.map_entry(fkn, fvn, indent + 2, steps=False)
        for variant, sub in group.variants.items():
            out += self.group(variant, sub, indent + 2)
        return [*out, _Line(indent, "}")]

    def first(self, group: _Group) -> yaml.Node:
        """The key node of the first component of `group` that exists (where a position is needed)."""
        if group.own is not None:
            return group.own[0]
        return next(self.first(sub) for sub in group.variants.values())

    def run_theme(self, scanned: marker.Marker, view_name: str) -> Converted:
        meta_line = _line_of(self.root.value[0][0]) if scanned.found and self.root.value else 0
        skip = frozenset({marker.KEY}) if scanned.found else frozenset()
        entries = [(kn, vn) for kn, vn in self.root.value if self.key_text(kn) not in skip]
        body_first = _line_of(entries[0][0]) if entries else _line_of(self.root)
        head = [_Line(0, "---"), _Line(0, f"TDL: {LANGUAGE_VERSION}"), _Line(0, f"Name: {view_name}")]
        if scanned.found and scanned.value:
            head.append(_Line(0, f'Tesserae: "{scanned.value}"', trails=(meta_line,)))
        head.append(_Line(0, "---"))
        if not entries:
            body = [_Line(0, f"{ROOT} {{ }}", (body_first,), (body_first,))]
        else:
            body = [_Line(0, f"{ROOT} {{", (body_first,))]
            for kn, vn in entries:
                key = self.key_text(kn)
                if key not in THEME_KEYS:
                    expected = ", ".join(f"`{field}`" for field in THEME_KEYS)
                    raise self.fail(kn, f"unknown field `{key}`, expected one of {expected}", _near(key, THEME_KEYS))
                body += self.components(kn, vn, 2) if key == "components" else self.map_entry(kn, vn, 2, steps=False)
            body.append(_Line(0, "}"))
        return Converted(self.assemble(head, body, body_first), 0, self.notes)


def _expected(text: str) -> Any:
    return _normalize_scalars(marker.strip(yaml.safe_load(text)))


def convert_theme(text: str, name: str, file: str = "<theme>") -> Converted:
    """The TDL for the YAML theme `text` (`name` is its `Name`: see `theme_stem`). Raises `ConvertError` (with the YAML line and what to write) for a form with
    no TDL form and for any result that does not read back as the same theme. Line ends are the ones the text has."""
    text = text.removeprefix("\ufeff")
    newline = "\r\n" if "\r\n" in text else "\n"
    scanned = marker.scan(text)
    if scanned.problem:
        raise ConvertError(scanned.problem, scanned.line)
    if not _KEY.match(name) or name in _NO_BLOCK:
        raise ConvertError(f"the theme's name {name!r} cannot be a TDL Name", 1, hint="a Name is letters, digits and underscores, starting with a letter: rename the file")
    try:
        data = _expected(text)
    except yaml.YAMLError as exc:
        raise ConvertError(f"invalid YAML: {exc}") from None
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConvertError(f"a theme is a mapping, got {type(data).__name__}", 1, hint="write seed: \"#6750A4\"")
    try:
        converter: _ThemeConverter | None = _ThemeConverter(text, name, file)
    except ConvertError:
        if data:  # an anchor, say: the converter's own refusal
            raise
        converter = None  # nothing but comments (or nothing): there is no mapping to read them from
    if converter is None:
        result = Converted(f"---\nTDL: {LANGUAGE_VERSION}\nName: {name}\n" + (f'Tesserae: "{scanned.value}"\n' if scanned.found and scanned.value else "") + f"---\n{ROOT} {{ }}\n")
    else:
        result = converter.run_theme(scanned, name)
    try:
        got = load_theme_tdl(result.text, file)
    except LoadError as exc:
        raise ConvertError(f"the TDL written does not load: {exc.message} (TDL line {exc.line})", 1,
                           hint="this form has no TDL form the converter knows: " + (exc.hint or "simplify the theme")) from None
    if _canon(got) != _canon(data):
        raise ConvertError("the TDL written does not read back as the same theme: " + _where(_canon(data), _canon(got)), 1,
                           hint="this form has no TDL form the converter knows")
    if newline != "\n":
        result.text = result.text.replace("\n", newline)
    return result


def theme_result(file: Path, root: Path) -> FileResult:
    """What the YAML theme `file` becomes beside it (`<stem>.tdl`), as `migrate_tdl` reports a view; a failure is a `failed` result."""
    new_path = file.with_suffix(".tdl")
    try:
        raw = file.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        return FileResult(file, "failed", error=f"not UTF-8: {exc.reason}", line=1)
    try:
        converted = convert_theme(raw, theme_stem(file.name), file.name)
    except ConvertError as exc:
        return FileResult(file, "failed", error=str(exc), line=exc.line)
    existing = new_path.read_bytes().decode("utf-8", "replace") if new_path.is_file() else None
    result = FileResult(file, "current" if existing == converted.text else "converted", new_path, converted.text, 0, list(converted.notes))
    if existing is not None and existing != converted.text:
        result.notes.append(f"{new_path.name} exists and differs: it is replaced")
    return result
