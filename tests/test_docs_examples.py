"""Every view, stylesheet and theme example on a docs page is real: the TDL loads against the shipped views.

A block is read when it is fenced ```tdl (or ```text titled `X.tdl`): see `tests/doc_blocks.py` for the convention (the metadata block is optional, a fragment is
fenced ```text). A block that shows the *old* form on purpose (a migration page) says so with `<!-- old-syntax: ... -->` on the line before its fence.
The generated API and schema pages and the changelog are left out: they quote what was, not what to write now.
"""

import pytest

pytest.importorskip("tess_dl", reason="the docs examples are TDL, which needs tess_dl (Python 3.14)")

import yaml  # noqa: E402  (a development dependency: the check below that no view is shown as YAML any more)

import doc_blocks as docs  # noqa: E402
from tess_ui.shipped import ViewLibrary  # noqa: E402
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet  # noqa: E402
from tess_ui.spec.tdl_theme import plain  # noqa: E402

ALL = list(docs.blocks())
TDL = [pytest.param(b, id=b.id) for b in ALL if b.is_tdl and not b.old and b.included is None]
LIBRARY = ViewLibrary()


def test_the_pages_have_their_examples():
    assert len(TDL) > 100


@pytest.mark.parametrize("block", TDL)
def test_a_tdl_example_loads(block):
    docs.load(block.text)


def test_a_marked_old_syntax_block_is_one_the_loader_refuses():
    """The marker must not hide a block that has become valid or was never old: the old YAML form is what the TDL front end refuses (a view, a stylesheet or a
    theme is read as TDL only). The blocks the pages mark are ```yaml, so they are fed to the front end as they stand."""
    marked = [block for block in ALL if block.old]
    assert marked, "no page carries an old-syntax block any more: delete the marker and this test"
    for block in marked:
        if block.lang in ("yaml", "yml") or block.is_tdl:
            with pytest.raises(Exception):
                docs.load(block.text)


def test_a_block_that_includes_a_file_names_one_that_exists():
    for block in ALL:
        if block.included is not None:
            assert (docs.ROOT / block.included).is_file(), f"{block.id}: {block.included} is not there"


def test_no_page_shows_a_view_or_a_stylesheet_as_yaml():
    """The loaders read TDL only: a ```yaml block that is a view, a stylesheet or a theme is the old form, and says so with the old-syntax marker."""
    shown = []
    for block in ALL:
        if block.lang not in ("yaml", "yml") or block.old:
            continue
        try:
            data = yaml.safe_load(block.text)
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and ("styles" in data or "seed" in data or any(k in data for k in ("widget", "kind", "component", "children"))):
            shown.append(block.id)
    assert not shown, f"write these in TDL (```tdl), or mark them `<!-- old-syntax: ... -->`: {shown}"


def _rule_parts():
    """Every `Part` a docs rule example names for a view Tesserae ships."""
    for block in ALL:
        if not block.is_tdl or block.old or block.included is not None or docs.kind_of(block.text) != "stylesheet":
            continue
        data = plain(load_marked_tdl_stylesheet(docs.document(block.text), "Doc_Stylesheet.tdl"))
        for rule in data.get("styles", []):
            if isinstance(rule, dict) and rule.get("part") and LIBRARY.doc(str(rule.get("widget"))) is not None:
                yield pytest.param(rule["widget"], rule["part"], id=f"{block.id}:{rule['widget']}.{rule['part']}")


@pytest.mark.parametrize("widget, part", list(_rule_parts()))
def test_a_part_a_docs_rule_names_is_a_node_of_the_view(widget, part):
    """A rule whose `Part` names no node of the view matches nothing, and says nothing: so the page shows a rule that does nothing."""
    names = {node.name for node in LIBRARY.doc(widget).root.walk() if node.name}
    assert part in names, f"{widget} has the parts {sorted(names)}"
