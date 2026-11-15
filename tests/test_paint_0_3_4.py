"""M33: Tesserae's own views are right for `tess_re` 0.3.4's paint model.

`tess_re` 0.3.4 (its M95) changed two things a static spec can get wrong,
and neither shows up anywhere but on screen:

- **A color's own alpha renders.** A Text glyph colored `"#FFFFFF00"`
  painted solid white on 0.3.3, where the node's opacity replaced the
  alpha; on 0.3.4 it's invisible.
- **`opacity` is group opacity:** it fades the node's whole subtree. A
  translucent scrim wrapping its panel has to take its translucency
  from its color, or the panel fades with it.

`tess_re` 0.3.4 can't read pixels back from Python, so this checks what
every view, fragment and docs snippet declares: the shipped and example views
(`widget` nodes, read through the TDL front end), the built-in fragments
(`spec/fragments.py`, each with its look applied), and every whole TDL view on a docs page.
"""

import importlib.util
import re
from pathlib import Path

import pytest

import doc_blocks

ROOT = Path(__file__).resolve().parent.parent
HEX = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")
HAS_TDL = importlib.util.find_spec("tess_dl") is not None


def _documents():
    """`(label, parsed data)` for every fragment file, and (with `tess_dl`) every view file and every whole `tdl` block in the docs that is a view."""
    from tess_ui.spec.expand import _apply_sheet, _plain
    from tess_ui.spec.fragments import FRAGMENTS

    for name, entry in FRAGMENTS.items():
        tree = _plain(entry["tree"])
        _apply_sheet(tree, _plain(entry["sheet"]), name)
        yield f"src/tess_ui/spec/fragments.py::{name}", tree
    if not HAS_TDL:  # the views are TDL (Python 3.14): read through the front end
        return
    from tess_ui.spec.tdl import load_tdl_file
    from tess_ui.spec.tdl_theme import plain

    for path in sorted([*ROOT.glob("src/tess_ui/**/*_View.tdl"), *ROOT.glob("examples/**/*_View.tdl")]):
        yield path.relative_to(ROOT).as_posix(), plain(load_tdl_file(path))
    for block in doc_blocks.blocks():
        if block.is_tdl and not block.old and block.included is None and doc_blocks.kind_of(block.text) == "view":
            yield f"docs/{block.id}", _view_data(block.text)


def _view_data(text):
    from tess_ui.shipped import ViewLibrary
    from tess_ui.spec.tdl import load_marked_tdl
    from tess_ui.spec.tdl_theme import plain
    from tess_ui.spec.widgets import WidgetDecl

    library = ViewLibrary()
    return plain(load_marked_tdl(doc_blocks.document(text), "Doc_View.tdl", resolver=lambda name: library.decl(name) or WidgetDecl(name, view=True, container=True)))


def _nodes(data):
    """Every mapping with a `widget:` (the current language) or a `kind:` or `component:` (the fragments') -- a widget node."""
    if isinstance(data, dict):
        if "widget" in data or "kind" in data or "component" in data:
            yield data
        for value in data.values():
            yield from _nodes(value)
    elif isinstance(data, list):
        for item in data:
            yield from _nodes(item)


def _alpha(color: str) -> int:
    digits = color[1:]
    if len(digits) in (4, 8):
        return int(digits[-(len(digits) // 4):] * (2 if len(digits) == 4 else 1), 16)
    return 255


DOCS = list(_documents())


def test_the_scan_covers_views_fragments_and_docs():
    labels = [label for label, _ in DOCS]
    assert sum(label.startswith("src/tess_ui/spec/fragments.py::") for label in labels) >= 50
    if HAS_TDL:
        assert any(label.startswith("examples/") for label in labels)
        assert sum(label.startswith("src/tess_ui/views/") for label in labels) >= 50
        assert any(label.startswith("docs/") for label in labels)


@pytest.mark.parametrize("label,data", DOCS, ids=[label for label, _ in DOCS])
def test_no_glyph_color_is_translucent(label, data):
    for node in _nodes(data):
        style = node.get("style")
        color = style.get("foreground") if isinstance(style, dict) else None  # a `*_Style.yaml` file (M75) isn't read here
        if isinstance(color, str) and HEX.match(color):
            assert _alpha(color) == 255, f"{label}: {node.get('id') or node.get('name')!r} has glyph color {color}, invisible on tre 0.3.4"


@pytest.mark.parametrize("label,data", DOCS, ids=[label for label, _ in DOCS])
def test_no_node_with_children_sets_opacity(label, data):
    """A *constant* opacity on a node with children is the scrim shape that fades its panel with it. An opacity that is an expression (`<| 0.38 if disabled else 1 |>`,
    which the data holds as `{{ }}`) is a fade of the whole node on purpose: a disabled segment, a toolbar that hides; the widened scan (the `widget` nodes of the TDL
    views) found exactly those two in the shipped views."""
    for node in _nodes(data):
        style = node.get("style") if isinstance(node.get("style"), dict) else {}  # (a style file, M75: not read here)
        opacity = style.get("opacity")
        if opacity is not None and node.get("children") and not (isinstance(opacity, str) and "{{" in opacity):
            pytest.fail(f"{label}: {node.get('id') or node.get('name')!r} sets opacity {opacity} and has children, which fade too on tre 0.3.4")
