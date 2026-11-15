"""The TDL front end for themes: a theme written in TDL, read into the mapping `spec/themes.py` hands `check_theme` and `Theme`.

Piece 5 of `design/tdl-switch-plan.md`; the shape is in `design/tdl-views.md` ("What piece 5 decided"). A theme file is

```
---
TDL: 0.2
Name: Brand
Tesserae: "0.6"
---
Theme {
  Seed: "#0B6B58"
  Colors { Tertiary: "#C2410C" }
  Typography { Body_Large { Font_Family: Inter, Font_Size: 17 } }
  Components { Card { Elevated { Corner_Radius: 8, Elevation: level_2 } } }
}
```

and reads as `{seed: "#0B6B58", colors: {tertiary: ...}, typography: {...}, components: {"card.elevated": {...}}}`: the dict
`check_theme` and `Theme` take, as a plain dict; `load_marked_theme_tdl` returns the same data as `PMap`s that know where each key and value is, for an error that points into the file.

Two things are not a plain `Title_Case` map: a component's variant is written as a block inside the component (`Card { Elevated { ... } }` is the key
`card.elevated`, because a `.` cannot be in a TDL key), and a theme's own `Styles` list (the older rule shape) is a list of `Item` blocks, as every list
of maps is in a view.
"""

from __future__ import annotations

from typing import Any

import tess_dl

from tess_ui.spec.cascade import _THEME_FIELDS
from tess_ui.spec.nodes import PMap, _near
from tess_ui.spec.tdl import _BOM, _Front, _parse_document

__all__ = ["ROOT", "THEME_KEYS", "load_marked_theme_tdl", "load_theme_tdl", "plain"]

#: The head of the root block of a theme file.
ROOT = "Theme"
#: The keys a theme has (the ones `check_theme` accepts), in the order the docs show them.
THEME_KEYS = _THEME_FIELDS


class _ThemeFront(_Front):
    def components(self, block: tess_dl.Block) -> PMap:
        """`Components { Card { Corner_Radius: 12, Elevated { Elevation: 1 } } }` is `{card: {corner_radius: 12}, "card.elevated": {elevation: 1}}`.

        A block holds the fields of the component (properties) and its variants (blocks, each read the same way); a component of fields only is the key
        itself, one of variants only is just its variants. A property directly in `Components` is the key as written (`Card: 8`),, so the theme loader says
        what is wrong with it."""
        out = self.new_map(self.pos(block))
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                kind = "an If" if isinstance(entry, tess_dl.If) else "a For"
                raise self.fail(entry, f"{kind} wraps a node, and a theme has none", "remove it")
            if isinstance(entry, tess_dl.Property):
                value, value_at = self.value(entry.value)
                key = self.key(entry.key, entry.key_origin)
                self.put(out, key, value, self.pos(entry.key_origin), value_at)
            else:
                self.component(entry, self.key(entry.type, entry), out)
        return out

    def component(self, block: tess_dl.Block, name: str, out: PMap) -> None:
        fields = self.new_map(self.pos(block))
        variants: list[tess_dl.Block] = []
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                kind = "an If" if isinstance(entry, tess_dl.If) else "a For"
                raise self.fail(entry, f"{kind} wraps a node, and a theme has none", "remove it")
            if isinstance(entry, tess_dl.Property):
                key = self.key(entry.key, entry.key_origin)
                value, value_at = self.value(entry.value)
                self.put(fields, key, value, self.pos(entry.key_origin), value_at)
            else:
                variants.append(entry)
        if fields or not variants:
            self.put(out, name, fields, self.pos(block), self.pos(block))
        for variant in variants:
            self.component(variant, f"{name}.{self.key(variant.type, variant)}", out)

    def theme(self, document: tess_dl.Document) -> PMap:
        root = document.root
        if not isinstance(root, tess_dl.Block) or root.type != ROOT:
            head = root.type if isinstance(root, tess_dl.Block) else type(root).__name__
            raise self.fail(root, f"a theme file is one Theme block, got '{head}'", f"write {ROOT} {{ Seed: \"#6750A4\" }}")
        out = self.new_map(self.pos(root))
        for entry in root.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                kind = "an If" if isinstance(entry, tess_dl.If) else "a For"
                raise self.fail(entry, f"{kind} wraps a node, and a theme has none", "remove it")
            if isinstance(entry, tess_dl.Property):
                key = self.key(entry.key, entry.key_origin)
                key_at = self.pos(entry.key_origin)
                value, value_at = self.value(entry.value)
            else:
                key = self.key(entry.type, entry)
                key_at = value_at = self.pos(entry)
                value = self.components(entry) if key == "components" else self.block_value(entry)
            if key not in THEME_KEYS:
                expected = ", ".join(f"`{name}`" for name in THEME_KEYS)
                raise self.fail(key_at, f"unknown field `{key}`, expected one of {expected}", _near(key, THEME_KEYS))
            self.put(out, key, value, key_at, value_at)
        return out


def load_marked_theme_tdl(text: str, file: str = "<theme>") -> PMap:
    """Reads the TDL theme in `text` into a `PMap` (with `at`, `key_at` and `val_at` at every level). A syntax error, a key that is not `Title_Case`, a key
    a theme does not have or a root that is not `Theme { }` is a `LoadError` at its line and column in the file."""
    text = text.removeprefix(_BOM)
    document = _parse_document(text, file)
    front = _ThemeFront(text, file, None)
    front.metadata(document)
    return front.theme(document)


def plain(data: Any) -> Any:
    """`data` with every `PMap` a `dict` and every `PSeq` a `list`: plain values."""
    if isinstance(data, dict):
        return {k: plain(v) for k, v in data.items()}
    if isinstance(data, list):
        return [plain(v) for v in data]
    return data


def load_theme_tdl(text: str, file: str = "<theme>") -> dict[str, Any]:
    """The plain mapping a TDL theme loads to (before `check_theme`): see the module docstring."""
    return plain(load_marked_theme_tdl(text, file))  # type: ignore[no-any-return]
