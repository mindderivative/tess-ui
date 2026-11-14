"""Piece 4 of the TDL switch: every shipped `*_Stylesheet.yaml` has its `*_Stylesheet.tdl` beside it, current, loading to the same mapping and to the same rules.

The YAML files are still what tess-ui loads; the `.tdl` files are the converter's output, kept in step until the cutover (piece 10)."""

from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front end needs tess_dl (Python 3.14)")

from tess_ui.expr import Expr  # noqa: E402
from tess_ui.migrate_tdl_sheets import _canon, convert_sheet  # noqa: E402
from tess_ui.spec.nodes import load_marked  # noqa: E402
from tess_ui.spec.rules import load_rule_sheet  # noqa: E402
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet, load_rule_sheet_tdl  # noqa: E402

VIEWS = Path(__file__).parent.parent / "src" / "tess_ui" / "views"
SHIPPED = sorted(VIEWS.glob("*_Stylesheet.yaml"))


def test_every_shipped_stylesheet_has_a_tdl_file_and_no_tdl_file_is_left_without_its_yaml():
    yaml_names = {p.name.removesuffix(".yaml") for p in SHIPPED}
    tdl_names = {p.name.removesuffix(".tdl") for p in VIEWS.glob("*_Stylesheet.tdl")}
    assert len(SHIPPED) == 49
    assert yaml_names == tdl_names


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.name)
def test_the_tdl_file_is_what_the_converter_writes_now_and_loads_to_the_yaml_mapping(path):
    text = path.read_text(encoding="utf-8")
    tdl = path.with_suffix(".tdl")
    written = tdl.read_bytes().decode("utf-8")
    assert written == convert_sheet(text, path.name.removesuffix("_Stylesheet.yaml"), path.name).text, f"{tdl.name} is stale: run `tesserae migrate-tdl --write`"
    assert _canon(load_marked_tdl_stylesheet(written, tdl.name)) == _canon({"styles": load_marked(text)["styles"]}), path.name


def describe(style):
    """A rule's style with each template as the expressions in it (a compiled template has no equality of its own)."""
    return {k: (tuple(p.source if isinstance(p, Expr) else p for p in v.parts) if hasattr(v, "parts") else v) for k, v in style.items()}


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.name)
def test_the_tdl_file_gives_rule_sheet_the_same_rules_with_expressions_that_point_at_their_text(path):
    from_yaml, from_tdl = load_rule_sheet(path), load_rule_sheet_tdl(path.with_suffix(".tdl"))
    key = lambda r: (r.widget, r.selectors, r.classes, r.name, r.part, r.state, r.order, r.specificity, describe(r.style))  # noqa: E731
    assert [key(r) for r in from_tdl.rules] == [key(r) for r in from_yaml.rules]
    for sheet, file in ((from_yaml, path), (from_tdl, path.with_suffix(".tdl"))):
        lines = file.read_text(encoding="utf-8").split("\n")
        for rule in sheet.rules:
            for value in rule.style.values():
                for part in getattr(value, "parts", ()):
                    if isinstance(part, Expr):  # an error inside the expression is drawn at this line and column of the file
                        assert part.origin is not None and lines[part.origin.line - 1][part.origin.column:].startswith(part.source), (file.name, part.source[:30])
