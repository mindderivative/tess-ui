"""`tesserae migrate-tdl` for stylesheets: a `*_Stylesheet.yaml` written as `*_Stylesheet.tdl` (piece 4 of `design/tdl-switch-plan.md`; the shape is in
`design/tdl-views.md`, "What piece 4 decided").

`convert_sheet(text, name)` turns the text of one YAML stylesheet into TDL: the `styles:` list is a root `Styles { }` block holding one `Rule { }` block per rule,
in order; keys are `Title_Case`; a rule's `style:` is a `Style { }` block, a style field that holds a map (`padding: {left: 12}`) a block of its own, a list of
names (`classes: [a, b]`) a TDL list; `{{ expr }}` is `<| expr |>`. It is `migrate_tdl`'s converter with the stylesheet's two levels in place of the view's tree, so it
keeps the comments (above a rule, above a key, at the end of a line, at the top and the end of the file), the blank lines between entries and the order, and
lays a rule out as the YAML had it: a rule written on one line in flow style stays on one line when it fits in 150 columns, a rule in block style is opened one
entry to a line (its `Style` stays on one line when the YAML had it so and it fits).

As for views, nothing is written that does not read back: the result is loaded again through the front end (`spec/tdl_stylesheet.py`) and compared with the YAML
loader's mapping, so a form with no TDL form (an anchor, a value that is not text, a number, yes/no or null, a list of lists, a key that is not lower
snake_case) is a `ConvertError` with the YAML line and what to write, never a nearly right file.
"""

from __future__ import annotations

from typing import Any

import yaml  # type: ignore[import-untyped]

from tess_ui.migrate_tdl import _KEY, _NO_BLOCK, ConvertError, Converted, _comments, _Converter, _line_of, _Line, _where
from tess_ui.project import looks_like
from tess_ui.spec import marker
from tess_ui.spec.nodes import LoadError, PMap, load_marked
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet

__all__ = ["convert_sheet"]


class _SheetConverter(_Converter):
    """`_Converter` for a mapping `{styles: [rule, ...]}`. Nothing in a stylesheet is a handler, so an `on_` key is the plain text it is."""

    def __init__(self, text: str, name: str, file: str) -> None:
        self.text, self.name, self.file, self.resolver = text, name, file, None
        self.loader = yaml.SafeLoader(text)
        root = self.loader.get_single_node()
        if not isinstance(root, yaml.MappingNode):
            raise ConvertError("a stylesheet is a mapping with styles:", 1, hint="write styles: and one '- widget: Button' rule after it")
        self.root = root
        self.check_aliases(root, _line_of(root), set())
        self.comments = _comments(text)
        self.comment_lines = sorted({c.line for c in self.comments if c.text})
        self.steps = 0
        self.loops = []
        self.notes = []

    def handler_text(self, vn: yaml.ScalarNode) -> str | None:
        return None

    def rules(self, kn: yaml.Node, vn: yaml.Node) -> list[_Line]:
        line = _line_of(kn)
        if isinstance(vn, yaml.ScalarNode) and self.construct(vn) is None:  # `styles:` with nothing after it is no rules, as the loader reads it
            return [_Line(0, "Styles { }", (line,), (line,))]
        if not isinstance(vn, yaml.SequenceNode):
            raise self.fail(vn, "'styles:' is a list of rules", "write '- widget: Button' and its style: under it")
        if not vn.value:
            return [_Line(0, "Styles { }", (line,), (line,))]
        out = [_Line(0, "Styles {", (line,), (line,))]
        for item in vn.value:
            if not isinstance(item, yaml.MappingNode):
                raise self.fail(item, "a rule is a mapping", "write - widget: Button, then its style:")
            out += self.map_block("Rule", item, 2, _line_of(item))
        return [*out, _Line(0, "}")]

    def run_sheet(self, scanned: marker.Marker, data: Any) -> Converted:
        skip = frozenset({marker.KEY}) if scanned.found else frozenset()
        meta_line = _line_of(self.root.value[0][0]) if scanned.found and self.root.value else 0
        styles: tuple[yaml.Node, yaml.Node] | None = None
        for kn, vn in self.root.value:
            key = self.key_text(kn)
            if key in skip:
                continue
            if key != "styles":
                raise self.fail(kn, f"a stylesheet has only 'styles:', not '{key}'", looks_like(data, "stylesheet", self.file))
            styles = (kn, vn)
        body_first = _line_of(styles[0]) if styles else _line_of(self.root)
        if not _KEY.match(self.name) or self.name in _NO_BLOCK:
            raise ConvertError(f"the stylesheet's name {self.name!r} cannot be a TDL Name", 1,
                               hint="a Name is letters, digits and underscores, starting with a letter: rename the file")
        head = [_Line(0, "---"), _Line(0, "TDL: 0.1"), _Line(0, f"Name: {self.name}")]
        if scanned.found and scanned.value:
            head.append(_Line(0, f'Tesserae: "{scanned.value}"', trails=(meta_line,)))
        head.append(_Line(0, "---"))
        body = self.rules(*styles) if styles else [_Line(0, "Styles { }", (body_first,), (body_first,))]
        return Converted(self.assemble(head, body, body_first), 0, [], self.notes)


def _canon(item: Any) -> Any:
    """The mapping as comparable plain data: types kept (`True` is not `1`), key order not."""
    if isinstance(item, dict):
        return ("map", tuple(sorted((k, _canon(v)) for k, v in item.items())))
    if isinstance(item, list):
        return ("seq", tuple(_canon(v) for v in item))
    return (type(item).__name__, item)


def convert_sheet(text: str, name: str, file: str = "<stylesheet>") -> Converted:
    """The TDL for the YAML stylesheet `text` (its file name stem is `name`). Raises `ConvertError` (with the YAML line and what to write) for a form with no TDL
    form, and for any result that does not read back as the same stylesheet. Line ends are the ones the text has."""
    text = text.removeprefix("\ufeff")
    newline = "\r\n" if "\r\n" in text else "\n"
    scanned = marker.scan(text)
    if scanned.problem:
        raise ConvertError(scanned.problem, scanned.line)
    try:
        data = load_marked(text, file)
    except LoadError as exc:
        raise ConvertError(exc.message, exc.line, exc.column, exc.hint) from None
    if not isinstance(data, PMap):
        raise ConvertError("a stylesheet is a mapping with styles:", 1, hint="write styles: and one '- widget: Button' rule after it")
    try:
        result = _SheetConverter(text, name, file).run_sheet(scanned, data)
    except yaml.YAMLError as exc:  # unreachable after load_marked; kept so a scanner difference is an error, not a traceback
        raise ConvertError(f"YAML: {exc}") from None
    expected = {"styles": data.get("styles") or []}
    try:
        got = load_marked_tdl_stylesheet(result.text, file)
    except LoadError as exc:
        raise ConvertError(f"the TDL written does not load: {exc.message} (TDL line {exc.line})", 1,
                           hint="this form has no TDL form the converter knows: " + (exc.hint or "simplify the stylesheet")) from None
    if _canon(got) != _canon(expected):
        raise ConvertError("the TDL written does not read back as the same stylesheet: " + _where(_canon(expected), _canon(got)), 1,
                           hint="this form has no TDL form the converter knows")
    if newline != "\n":
        result.text = result.text.replace("\n", newline)
    return result

