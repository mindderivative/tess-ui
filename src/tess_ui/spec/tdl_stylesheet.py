"""The TDL front end for stylesheets: a `*_Stylesheet.tdl` read into the mapping with positions that `nodes.load_marked` makes of a `*_Stylesheet.yaml`.

Piece 4 of `design/tdl-switch-plan.md`, the shape in `design/tdl-views.md` ("What piece 4 decided"). `load_marked_tdl_stylesheet(text, file)` returns the `PMap`
`{styles: [rule, ...]}` that `RuleSheet.of` takes as it takes the YAML one, with the same position maps (`at`, `key_at`, `val_at`, `item_at`), so every
error a stylesheet can have keeps its wording and now points into the `.tdl` file. The file is:

```
---
TDL: 0.2
Name: Button
Tesserae: "0.6"
---
Styles {
  Rule { Widget: Button, Size: xs, Style { Height: 32, Gap: 4 } }
  Rule {
    Widget: Button
    Part: label
    Style { Foreground: <| 'primary' if selected else 'surface' |> }
  }
}
```

- the root block is `Styles`; it holds `Rule` blocks, in order (order breaks ties between rules of the same specificity);
- a rule's keys are `Title_Case` properties (`Widget`, `Variant`, `Size`, `Shape`, `State`, `Part`, `Name`, `Classes: [a, b]`) and one `Style { }` block;
- a style field is a property (`Height: 40`); a field that holds a map is a block (`Padding { Left: 12, Right: 12 }`); a value is read as the views read it
  (`true`, `false`, `null`, numbers, `50%`, words, quoted text, a slot `<| expr |>` is the string `{{ expr }}`, text around a slot is a template);
- nothing is a node here: no `If`, `For`, `Children` or `Handlers`; a block that holds nothing but `Item` blocks is a list of maps, as in a view.

The lexical work (keys, values, slots, positions, the metadata block) is `spec/tdl.py`'s; this module only knows where a rule and a style are.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any

import tess_dl

from tess_ui.spec.nodes import LoadError, PMap, PSeq, _near
from tess_ui.spec.rules import RuleSheet
from tess_ui.spec.tdl import _BOM, _Front, _parse_document

__all__ = ["load_marked_tdl_stylesheet", "load_rule_sheet_tdl", "load_tdl_stylesheet_file"]


def _wrapper_kind(entry: Any) -> str:
    return "an If" if isinstance(entry, tess_dl.If) else "a For"


class _SheetFront(_Front):
    def sheet(self, root: tess_dl.Block) -> PMap:
        """`{styles: [...]}` for the `Styles` block `root`."""
        if root.type != "Styles":
            raise self.fail(root, f"a stylesheet is one Styles block of Rule blocks, not '{root.type}'",
                            _near(root.type, ("Styles",)) or "write Styles { Rule { Widget: Button, Style { Height: 40 } } }")
        top = self.new_map(self.pos(root))
        self.put(top, "styles", self.rules(root), self.pos(root), self.pos(root))
        return top

    def rules(self, block: tess_dl.Block) -> PSeq:
        seq = PSeq()
        seq.at, seq.item_at = self.pos(block), []
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                raise self.fail(entry, f"{_wrapper_kind(entry)} has no place in a stylesheet: Styles holds Rule blocks")
            if isinstance(entry, tess_dl.Property):
                raise self.fail(entry, f"Styles holds Rule blocks, and '{entry.key}:' is a property",
                                "write Rule { Widget: Button, Style { Height: 40 } }")
            if entry.type != "Rule":
                raise self.fail(entry, f"Styles holds Rule blocks, got '{entry.type}'", _near(entry.type, ("Rule",)))
            rule = self.rule(entry)
            seq.append(rule)
            seq.item_at.append(rule.at)
        return seq

    def rule(self, block: tess_dl.Block) -> PMap:
        m = self.new_map(self.pos(block))
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                raise self.fail(entry, f"{_wrapper_kind(entry)} has no place in a rule")
            if isinstance(entry, tess_dl.Property):
                key = self.key(entry.key, entry.key_origin)
                value, value_at = self.value(entry.value)
                self.put(m, key, value, self.pos(entry.key_origin), value_at)
            else:
                self.put(m, self.key(entry.type, entry), self.map_value(entry), self.pos(entry), self.pos(entry))
        return m

    def map_value(self, block: tess_dl.Block) -> Any:
        """A block of a rule: a map (the `Style`, a field that holds a map); a list of maps when it holds nothing but `Item` blocks."""
        entries = [e for e in block.entries if not isinstance(e, tess_dl.Comment)]
        items = [e for e in entries if isinstance(e, tess_dl.Block) and e.type == "Item"]
        if entries and len(items) == len(entries):
            seq = PSeq()
            seq.at, seq.item_at = self.pos(block), []
            for item in items:
                seq.append(self.mapping(item))
                seq.item_at.append(self.pos(item))
            return seq
        return self.mapping(block)

    def mapping(self, block: tess_dl.Block) -> PMap:
        m = self.new_map(self.pos(block))
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                raise self.fail(entry, f"{_wrapper_kind(entry)} has no place in a stylesheet, and '{block.type}' holds a map")
            if isinstance(entry, tess_dl.Property):
                key = self.key(entry.key, entry.key_origin)
                value, value_at = self.value(entry.value)
                self.put(m, key, value, self.pos(entry.key_origin), value_at)
            else:
                self.put(m, self.key(entry.type, entry), self.map_value(entry), self.pos(entry), self.pos(entry))
        return m


def load_marked_tdl_stylesheet(text: str, file: str = "<stylesheet>") -> PMap:
    """Reads the TDL stylesheet in `text` into the mapping with positions that `nodes.load_marked` makes of YAML, for `RuleSheet.of`.
    A syntax error, a key that is not `Title_Case` or a block that is not where a stylesheet has it is a `LoadError` at its line and column in the file;
    a mistake in what a rule says (a widget without that property, a state that does not exist) is `RuleSheet.of`'s, with its wording."""
    text = text.removeprefix(_BOM)
    document = _parse_document(text, file)
    front = _SheetFront(text, file, None)
    front.metadata(document)
    return front.sheet(document.root)


def load_tdl_stylesheet_file(path: str | Path) -> PMap:
    """`load_marked_tdl_stylesheet` for a file: UTF-8 (a byte order mark and CRLF lines are fine); errors name the file by its name."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LoadError(f"the file is not UTF-8: {exc.reason}", file=path.name) from None
    return load_marked_tdl_stylesheet(text, path.name)


def load_rule_sheet_tdl(path: Any, parts_of: Callable[[str], Collection[str] | None] | None = None) -> RuleSheet:
    """`rules.load_rule_sheet` for a `*_Stylesheet.tdl` file: the prepared `RuleSheet`; `parts_of` as for `RuleSheet.of`."""
    file = Path(path)
    try:
        text = file.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LoadError(f"the file is not UTF-8: {exc.reason}", file=str(file)) from None
    return RuleSheet.of(load_marked_tdl_stylesheet(text, str(file)), str(file), text.removeprefix(_BOM), parts_of)
