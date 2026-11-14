"""Add, remove, move and duplicate (model.py, blocks.py), without a window: each is one `tess_dl` edit that changes only the lines of that entry, is one undo step, and keeps the selection on the same block.

A test compares the file's text before and after line by line, on a file with comments, blank lines, inline blocks and end-of-line comments.
"""

import difflib

import pytest
import tess_dl

from tess_shell_config.blocks import accepts, children_of, new_block_text
from tess_shell_config.model import DocumentModel, EditError, block_names
from tess_shell_config.tdl import walk

DOC = """---
TDL: 0.1
Name: Structure_Test
---

# the root comment
Shell {
    Monitor {
        Name: Main   # the monitor

        # the bar
        Bar {
            Name: Top_Bar
            Edge: TOP

            Box { Name: A }   # first, inline
            Box { Name: B, Width: 3 }

            # between B and C
            Box {
                Name: C
                Height: 2
            }
            If {{ x }} {
                Box { Name: In_If }
            }
        }
        Popup { Name: P }   # a popup
    }
}
"""


def diff(before: str, after: str) -> list[str]:
    return [line[0] + line[2:].rstrip("\n") for line in difflib.ndiff(before.splitlines(True), after.splitlines(True)) if line[0] in "+-"]


class Rig:
    def __init__(self, tmp_path, text=DOC):
        self.path = tmp_path / "S.tdl"
        self.path.write_text(text)
        self.model = DocumentModel.from_bytes(self.path.read_bytes(), self.path, relative="S.tdl")

    def at(self, type_name, name=None):
        """The index path of the node called so in the current tree."""
        for node in walk(self.model.document.root):
            if getattr(node, "type", type(node).__name__) == type_name and (name is None or getattr(node, "name", None) == name):
                return node.index_path
        raise AssertionError(f"no {type_name} {name}")

    def label_at(self, path):
        node = self.model.node_at(path)
        return getattr(node, "name", None) or type(node).__name__


@pytest.fixture
def rig(tmp_path):
    return Rig(tmp_path)


# -- each kind of edit changes only its own lines ------------------------------------------------------------------------------------------

def test_adding_a_block_writes_only_its_lines_after_the_last_entry(rig):
    m = rig.model
    before = m.text
    m.select(rig.at("Bar"))
    new = m.add_block(rig.at("Bar"), "Box { Name: New }")
    assert diff(before, m.text) == ["+            Box { Name: New }"]
    assert m.node_at(new).name == "New" and m.selected.name == "Top_Bar", "the selection stays on the block that was selected"


def test_adding_a_block_at_an_index_before_the_selected_one_moves_the_selection_with_its_block(rig):
    m = rig.model
    m.select(rig.at("Box", "C"))
    before = m.text
    bar = rig.at("Bar")
    m.add_block(bar, "Box { Name: First }", 0)
    assert diff(before, m.text) == ["+            Box { Name: First }"]
    assert m.selected.name == "C", "an insert above it shifts its path; the selection follows the block"


def test_removing_a_block_takes_its_lines_and_its_end_of_line_comment_and_no_other(rig):
    m = rig.model
    before = m.text
    removed = rig.at("Box", "A")
    m.remove_block(removed)
    assert diff(before, m.text) == ["-            Box { Name: A }   # first, inline"]
    m.undo()
    m.remove_block(rig.at("Box", "C"))
    assert diff(before, m.text) == ["-            Box {", "-                Name: C", "-                Height: 2", "-            }"]
    assert "# between B and C" in m.text, "the comment above it stays"


def test_removing_the_selected_block_selects_its_parent_and_removing_another_keeps_the_selection(rig):
    m = rig.model
    m.select(rig.at("Box", "B"))
    m.remove_block(rig.at("Box", "A"))
    assert m.selected.name == "B"
    m.remove_block(rig.at("Box", "B"))
    assert m.selected.name == "Top_Bar"


def test_moving_a_block_up_or_down_changes_only_its_own_lines(rig):
    m = rig.model
    before = m.text
    b = rig.at("Box", "B")
    m.select(b)
    m.move_block(b, None, m.neighbour(b, -1))
    assert diff(before, m.text) == ["+            Box { Name: B, Width: 3 }", "-            Box { Name: B, Width: 3 }"], "only the moved block's own line is written again"
    assert [n.name for n in m.node_at(rig.at("Bar")).entries if hasattr(n, "name") and n.type == "Box"][:2] == ["B", "A"]
    assert m.selected.name == "B", "the selection follows the block that moved"


def test_moving_a_block_into_another_block_removes_it_there_and_adds_it_there(rig):
    m = rig.model
    before = m.text
    a = rig.at("Box", "A")
    m.select(a)
    moved = m.move_block(a, rig.at("Popup"))
    assert diff(before, m.text) == ["-            Box { Name: A }   # first, inline", "-        Popup { Name: P }   # a popup", "+        Popup { Name: P, Box { Name: A } }   # a popup"], "a block written on one line gets an inline insert"
    assert m.node_at(moved).name == "A" and m.node_at(moved[:-1]).type == "Popup" and m.selected.name == "A"
    with pytest.raises(EditError, match="into itself"):
        m.move_block(rig.at("Bar"), rig.at("Box", "C"))


def test_duplicating_a_block_copies_its_text_after_it_and_gives_a_name_no_other_block_has(rig):
    m = rig.model
    before = m.text
    m.select(rig.at("Box", "B"))
    copy = m.duplicate_block(rig.at("Box", "B"))
    assert diff(before, m.text) == ["+            Box { Name: B_Copy, Width: 3 }"]
    assert m.node_at(copy).name == "B_Copy" and m.selected.name == "B", "the selection stays on the original"
    again = m.duplicate_block(rig.at("Box", "B"))
    assert m.node_at(again).name == "B_Copy_2"
    names = [n.name for n in walk(m.document.root) if getattr(n, "name", None)]
    assert len(names) == len(set(names)), "names stay unique"


def test_duplicating_a_multi_line_block_and_one_with_no_name(rig):
    m = rig.model
    before = m.text
    m.duplicate_block(rig.at("Box", "C"))
    assert diff(before, m.text) == ["+            Box {", "+                Name: C_Copy", "+                Height: 2", "+            }"]
    plain = Rig(rig.path.parent, DOC.replace("Box { Name: A }   # first, inline", "Box { Width: 1 }"))
    before = plain.model.text
    plain.model.duplicate_block(plain.at("Box"))
    assert diff(before, plain.model.text) == ["+            Box { Width: 1 }"]


def test_a_quoted_name_is_copied_quoted(tmp_path):
    r = Rig(tmp_path, DOC.replace("Name: B,", 'Name: "B b",'))
    copy = r.model.duplicate_block(r.at("Box", "B b"))
    assert r.model.node_at(copy).name == "B b_Copy" and 'Name: "B b_Copy"' in r.model.text


# -- undo and redo, and the selection --------------------------------------------------------------------------------------------------

EDITS = {
    "add": lambda r: r.model.add_block(r.at("Bar"), "Box { Name: New }"),
    "remove": lambda r: r.model.remove_block(r.at("Box", "B")),
    "move up": lambda r: r.model.move_block(r.at("Box", "B"), None, r.model.neighbour(r.at("Box", "B"), -1)),
    "move into": lambda r: r.model.move_block(r.at("Box", "B"), r.at("Popup")),
    "duplicate": lambda r: r.model.duplicate_block(r.at("Box", "B")),
    "value": lambda r: r.model.set_value(r.model.selection, "Height", "9"),  # a form edits the selected block
    "clear": lambda r: r.model.clear_value(r.model.selection, "Name"),
}


@pytest.mark.parametrize("kind", EDITS)
@pytest.mark.parametrize("selected", [("Bar", None), ("Box", "B"), ("Box", "C"), ("Popup", None)])
def test_undo_after_each_kind_of_edit_restores_the_earlier_bytes_and_selection_and_redo_the_later(tmp_path, kind, selected):
    r = Rig(tmp_path)
    m = r.model
    m.select(r.at(*selected))
    name = m.selected.name
    before, selection = m.text, m.selection
    EDITS[kind](r)
    after, after_selection = m.text, m.selection
    assert after != before and m.valid
    if kind in ("value", "clear"):
        assert m.selection == selection, "the selection stays where it was"
    elif kind not in ("remove", "move into"):
        assert m.selected.name == name, "the selection stays on the same block"
    assert m.can_undo and m.undo()
    assert m.text == before and m.selection == selection, "undo brings back the earlier bytes and the selection it had"
    assert m.redo() and m.text == after and m.selection == after_selection, "redo brings back the later ones"
    assert tess_dl.loads(m.text)


def test_an_edit_is_one_undo_step_and_a_run_of_typing_is_one_too(rig):
    m = rig.model
    start = m.text
    m.duplicate_block(rig.at("Box", "B"))
    assert m.undo() and m.text == start and not m.can_undo
    m.redo()
    m.set_text(m.text.replace("Height: 2", "Height: 3"))
    m.set_text(m.text.replace("Height: 3", "Height: 33"))
    assert m.undo() and "Height: 2" in m.text and "B_Copy" in m.text, "the typing run is one step"
    assert m.undo() and m.text == start


def test_the_selection_stays_on_its_block_through_every_edit_in_a_row(rig):
    m = rig.model
    m.select(rig.at("Box", "C"))
    m.add_block(rig.at("Bar"), "Box { Name: N1 }", 0)
    m.duplicate_block(rig.at("Box", "A"))
    m.move_block(rig.at("Box", "N1"), None, m.neighbour(rig.at("Box", "N1"), 1))
    m.remove_block(rig.at("Box", "B"))
    m.set_value(rig.at("Box", "C"), "Width", "1")
    assert m.selected.name == "C"
    undone = 0
    while m.undo():
        undone += 1
        assert m.selected.name == "C", "undo brings back the selection each state had"
    assert undone == 5 and m.text == DOC


# -- inside an If or For, and the root ---------------------------------------------------------------------------------------------------

def test_a_block_inside_an_if_is_refused_with_a_message_and_nothing_changes(rig):
    m = rig.model
    before, undo_state = m.text, m.can_undo
    inside = rig.at("Box", "In_If")
    for action in (lambda: m.remove_block(inside), lambda: m.duplicate_block(inside), lambda: m.move_block(inside, None, 0)):
        with pytest.raises(EditError):
            action()
    assert m.text == before and m.can_undo == undo_state


def test_a_block_can_be_added_into_a_block_that_is_inside_an_if_and_an_if_can_be_moved_among_its_siblings(rig):
    m = rig.model
    before = m.text
    m.add_block(rig.at("Box", "In_If"), "Box { Name: Deep }")
    assert diff(before, m.text) == ["-                Box { Name: In_If }", "+                Box { Name: In_If, Box { Name: Deep } }"]
    if_path = rig.at("If")
    m.move_block(if_path, None, m.neighbour(if_path, -1))
    assert tess_dl.loads(m.text) and rig.at("If")[-1] < if_path[-1] and m.text.index("If {{ x }}") < m.text.index("Name: C")


def test_the_root_block_cannot_be_removed_moved_or_duplicated(rig):
    for action in (lambda: rig.model.remove_block(()), lambda: rig.model.move_block(()), lambda: rig.model.duplicate_block(())):
        with pytest.raises(EditError, match="root"):
            action()


def test_a_file_with_syntax_errors_refuses_every_structure_edit(tmp_path):
    r = Rig(tmp_path, DOC.replace("Name: P }", "Name: P"))
    assert not r.model.valid
    with pytest.raises(EditError, match="syntax errors"):
        r.model.duplicate_block((0,))


# -- the new block, from the schema ----------------------------------------------------------------------------------------------------

def test_a_new_block_has_its_required_keys_only_and_a_name_no_block_has(schema):
    assert new_block_text(schema, "Bar", {"bar_1"}) == "Bar {\n  Name: Bar_2\n  Edge: TOP\n  Width: 10\n  Height: 10\n}"
    assert new_block_text(schema, "Box", set()) == "Box { }" and new_block_text(schema, "Clock", set()) == "Clock { }"
    assert new_block_text(schema, "Bitmap", set()).splitlines()[1].strip().startswith("Source:")
    optional = {k.name for k in schema.block("Bar").all_keys().values() if not k.required}
    assert not optional & {line.split(":")[0].strip() for line in new_block_text(schema, "Bar", set()).splitlines()}


def test_the_add_list_is_the_allowed_children_then_the_modules_where_the_block_takes_module_calls(schema):
    bar = children_of(schema, "Bar")
    assert [c.type for c in bar][: len(schema.block("Bar").allowed_children)] == list(schema.block("Bar").allowed_children)
    assert {c.type for c in bar if c.module} == set(schema.modules) and all(accepts(schema, "Bar", c.type) for c in bar)
    assert children_of(schema, "Text") == [] and children_of(schema, "NoSuchBlock") == [] and not accepts(schema, "Text", "Box")
    assert [c.type for c in children_of(schema, "Monitor")] == ["Bar", "Panel", "Popup", "Frame"]


def _scratch(root, head):
    return f"---\nTDL: 0.1\nName: Scratch\n---\n{root} {{ {head} {{ }} }}\n" if head != root else f"---\nTDL: 0.1\nName: Scratch\n---\n{root} {{ }}\n"


def test_adding_each_allowed_child_to_every_block_of_the_schema_gives_a_file_tess_dl_parses_and_undo_brings_it_back(tmp_path, schema):
    """The schema walk: every root block and block that has allowed_children (and every module-calling one), each child written with its required keys."""
    added = 0
    problems = []
    for name, info in {**schema.roots, **schema.blocks}.items():
        head = info.heads[0] if info.heads else name
        offers = children_of(schema, head)
        if not offers:
            continue
        path = tmp_path / "Scratch.tdl"
        path.write_text(_scratch("Shell", head) if name != "Shell" else _scratch("Shell", "Shell"))
        model = DocumentModel.from_bytes(path.read_bytes(), path, relative="Scratch.tdl")
        parent = next(n for n in walk(model.document.root) if getattr(n, "type", None) == head)
        for child in offers:
            before = model.text
            text = new_block_text(schema, child.type, block_names(model.document))
            try:
                new = model.add_block(parent.index_path, text)
                tess_dl.loads(model.text)
            except (EditError, tess_dl.TDLError) as error:
                problems.append(f"{name} + {child.type}: {error}")
                continue
            added += 1
            if model.node_at(new).type != child.type or not (model.undo() and model.text == before and model.redo() and model.undo()):
                problems.append(f"{name} + {child.type}: the new block is not there, or undo did not restore the bytes")
    assert problems == []
    assert added > 100, added
    print(f"{added} (block, allowed child) pairs added, each parsed and undone")
