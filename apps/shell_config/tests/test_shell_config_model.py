"""The document model: one `tess_dl` edit per change, only that entry's lines change, undo and redo restore the bytes, the selection stays on the same block."""

import difflib
from pathlib import Path

import pytest

from tess_shell_config.model import DocumentModel, EditError
from tess_shell_config.structure import nodes_for, path_of, value_of
from tess_shell_config.tdl import child_entries

CONFIG = Path(__file__).parent / "fixtures" / "config"
MAIN = (CONFIG / "Shells" / "Main_Shell.tdl").read_bytes()

# paths into Main_Shell.tdl: root > Monitor > (Name, Index, Bar, Popup)
MONITOR = (0,)


def model(raw: bytes = MAIN) -> DocumentModel:
    return DocumentModel.from_bytes(raw, "Main_Shell.tdl")


def changed_lines(before: str, after: str) -> tuple[list[str], list[str]]:
    """(lines only in the old text, lines only in the new), the diff of one edit."""
    old, new = before.splitlines(), after.splitlines()
    removed, added = [], []
    for line in difflib.ndiff(old, new):
        if line.startswith("- "):
            removed.append(line[2:])
        elif line.startswith("+ "):
            added.append(line[2:])
    return removed, added


def find(m: DocumentModel, type_: str, name: str | None = None):
    """The index path of the first block of that type (and Name) anywhere in the tree."""
    for path in _paths(m):
        node = m.node_at(path)
        if getattr(node, "type", None) == type_ and (name is None or node.name == name):
            return path
    raise AssertionError(f"no {type_} {name}")


# -- a document -------------------------------------------------------------------------------------------------------------------

def test_a_file_that_parses_has_a_tree_and_the_root_selected():
    m = model()
    assert m.valid and m.errors == () and m.selection == () and m.selected.type == "Shell" and not m.dirty
    assert not m.can_undo and not m.can_redo


def test_a_file_with_syntax_errors_has_no_tree_and_says_where():
    m = model((CONFIG / "Shells" / "Broken_Shell.tdl").read_bytes())
    assert not m.valid and m.document is None and m.selection is None and m.errors
    assert m.errors[0].code and m.errors[0].line >= 1 and m.errors[0].message
    with pytest.raises(EditError, match="syntax errors"):
        m.set_value((), "A", "1")
    with pytest.raises(EditError, match="syntax errors"):
        m.add_block((), "Text { }")


# -- one edit, only that entry's lines -------------------------------------------------------------------------------------------

def test_setting_an_existing_value_changes_only_its_line():
    m = model()
    bar = find(m, "Bar", "Top_Bar")
    before = m.text
    m.set_value(bar, "Height", "40")
    removed, added = changed_lines(before, m.text)
    assert removed == ["            Height: 32"] and added == ["            Height: 40"]
    assert m.selection == bar and m.selected.name == "Top_Bar" and m.dirty


def test_setting_a_new_value_adds_one_line_and_keeps_the_comments_and_blank_lines():
    m = model()
    monitor = MONITOR
    before = m.text
    m.set_value(monitor, "Description", '"Left screen"')
    removed, added = changed_lines(before, m.text)
    assert removed == [] and len(added) == 1 and added[0].strip() == 'Description: "Left screen"'
    assert "Index: 0     # the first monitor" in m.text and "# One monitor with a bar and a panel." in m.text


def test_a_value_with_an_end_of_line_comment_keeps_its_comment_when_set():
    m = model()
    before = m.text
    m.set_value(MONITOR, "Index", "1")
    removed, added = changed_lines(before, m.text)
    assert removed == ["        Index: 0     # the first monitor"] and added == ["        Index: 1     # the first monitor"]


def test_clearing_a_value_removes_that_line_and_nothing_else():
    m = model()
    before = m.text
    m.clear_value(MONITOR, "Index")
    removed, added = changed_lines(before, m.text)
    assert removed == ["        Index: 0     # the first monitor"] and added == []
    assert m.selection == MONITOR
    with pytest.raises(EditError):
        m.clear_value(MONITOR, "Index")  # it is gone now


def test_clearing_one_of_two_values_on_a_line_keeps_the_other():
    logging = DocumentModel.from_bytes((CONFIG / "settings.tdl").read_bytes(), "settings.tdl")
    path = find(logging, "Logging")
    logging.clear_value(path, "Retention")
    assert "Logging { Level: INFO }" in logging.text


def test_adding_a_block_adds_its_lines_only_and_returns_its_path():
    m = model()
    bar = find(m, "Bar", "Top_Bar")
    children = find(m, "Children")
    before = m.text
    new = m.add_block(children, "Spacer {\n    Width: EXPAND\n}", 0)
    removed, added = changed_lines(before, m.text)
    assert removed == [] and [a.strip() for a in added] == ["Spacer {", "Width: EXPAND", "}"]
    assert m.document.at(new).type == "Spacer" and new[: len(children)] == children
    assert m.document.at(bar).name == "Top_Bar", "the bar is still where it was"
    assert m.selection == (), "the selection stays where it was; select=True is how a caller selects the new block"
    m.undo()
    assert m.add_block(children, "Spacer { }", select=True) and m.selected.type == "Spacer"


def test_adding_an_inline_block_to_an_inline_parent_stays_on_that_line():
    m = DocumentModel("---\nTDL: 0.1\nName: X\n---\nShell { }\n")
    new = m.add_block((), "Monitor { Name: Primary }")
    assert new == (0,) and m.document.at(new).type == "Monitor"
    assert "Monitor" in m.text and m.text.count("\n") == 5


def test_a_new_block_that_is_not_valid_is_refused_with_the_reason_and_the_file_is_unchanged():
    m = model()
    before = m.text
    with pytest.raises(EditError) as raised:
        m.add_block(MONITOR, "Text {")
    assert str(raised.value) and m.text == before and not m.dirty and not m.can_undo
    with pytest.raises(EditError):
        m.add_block(MONITOR, "If {{ x }} { Text { } }")  # an If is not a block to add


def test_removing_a_block_takes_its_lines_and_its_end_of_line_comment_and_selects_the_parent():
    m = model()
    popup = find(m, "Popup")
    m.select(popup)
    before = m.text
    parent = m.remove_block(popup)
    removed, added = changed_lines(before, m.text)
    assert added == [] and removed[0].strip() == "Popup {" and removed[-1].strip() == "}"
    assert "# the popup the clock opens" in m.text, "a comment line above it stays"
    assert parent == popup[:-1] == m.selection


def test_removing_a_block_with_an_end_of_line_comment():
    m = model()
    text = find(m, "Text", None)
    before = m.text
    m.remove_block(text)
    removed, added = changed_lines(before, m.text)
    assert added == [] and len(removed) == 1 and "inline block with end-of-line comment" in removed[0]


def test_an_if_and_a_for_can_be_removed():
    m = model()
    for kind in ("If", "For"):
        path = next(p for p in _paths(m) if type(m.node_at(p)).__name__ == kind)
        before = m.text
        m.remove_block(path)
        assert {"If": "If {{", "For": "For item"}[kind] not in m.text
        assert m.text != before
    assert m.valid


def _paths(m):
    def walk(node, path):
        yield path
        for i, entry in enumerate(child_entries(node)):
            if type(entry).__name__ in ("Block", "If", "For"):
                yield from walk(entry, (*path, i))

    return list(walk(m.document.root, ()))


def test_the_root_cannot_be_removed_or_moved():
    m = model()
    with pytest.raises(EditError, match="root"):
        m.remove_block(())
    with pytest.raises(EditError, match="root"):
        m.move_block(())


def test_moving_a_block_within_its_parent_changes_only_the_order():
    m = model()
    bar, popup = find(m, "Bar", "Top_Bar"), find(m, "Popup")
    assert bar[-1] < popup[-1]
    before = m.text
    new = m.move_block(popup, index=bar[-1])
    assert new == (*bar[:-1], bar[-1]) and m.document.at(new).type == "Popup" and m.document.at((*bar[:-1], bar[-1] + 1)).name == "Top_Bar"
    assert sorted(m.text.splitlines()) == sorted(before.splitlines()), "the same lines, in another order"
    assert m.text != before


def test_moving_a_block_to_another_parent_moves_it_whole():
    m = model()
    popup = find(m, "Popup")
    children = find(m, "Children")
    before = m.text
    new = m.move_block(popup, children, 0)
    assert m.document.at(new).type == "Popup" and m.document.at(new).name == "Calendar_Popup" and new[: len(children)] == children and len(new) > len(popup)
    assert m.document.at(new).name == "Calendar_Popup"
    assert "# the popup the clock opens" in m.text
    assert sorted(line.strip() for line in before.splitlines() if line.strip()) == sorted(line.strip() for line in m.text.splitlines() if line.strip())


def test_moving_a_block_into_itself_or_an_if_into_another_parent_is_refused():
    m = model()
    bar = find(m, "Bar", "Top_Bar")
    children = find(m, "Children")
    with pytest.raises(EditError, match="into itself"):
        m.move_block(bar, children)
    an_if = next(p for p in _paths(m) if type(m.node_at(p)).__name__ == "If")
    with pytest.raises(EditError, match="inside its own block"):
        m.move_block(an_if, MONITOR)
    with pytest.raises(EditError):
        m.move_block(find(m, "Popup"), index=99)


def test_blocks_inside_an_if_can_be_set_but_not_removed_by_the_structure_edits():
    m = model()
    battery = find(m, "Battery")
    m.set_value(battery, "Visible", "true")
    assert m.selected.type == "Battery" and "Visible: true" in m.text
    with pytest.raises(EditError, match="inside an If or For"):
        m.remove_block(battery)


def test_metadata_is_set_and_cleared():
    m = model()
    m.set_metadata("UID", "abc")
    assert "UID: abc" in m.text
    m.clear_metadata("UID")
    assert m.text == MAIN.decode()


def test_format_runs_only_when_asked_and_is_one_undo_step():
    raw = b"---\nTDL: 0.1\nName: X\n---\nShell {   A: 1,   B: 2 }\n"
    m = DocumentModel.from_bytes(raw)
    assert m.text == raw.decode()
    m.format_file()
    assert m.text != raw.decode() and "A: 1\n" in m.text
    m.undo()
    assert m.data == raw


# -- history -----------------------------------------------------------------------------------------------------------------------

def test_undo_after_each_kind_of_edit_restores_the_earlier_bytes_and_redo_the_later_ones():
    bar = find(model(), "Bar", "Top_Bar")
    popup = find(model(), "Popup")
    children = find(model(), "Children")
    edits = [
        ("set", lambda m: m.set_value(bar, "Height", "40")),
        ("add value", lambda m: m.set_value(bar, "Opacity", "50%")),
        ("clear", lambda m: m.clear_value(MONITOR, "Index")),
        ("add block", lambda m: m.add_block(children, "Spacer { }", 0)),
        ("remove", lambda m: m.remove_block(popup)),
        ("move within", lambda m: m.move_block(popup, index=0)),
        ("move across", lambda m: m.move_block(popup, children, 0)),
        ("metadata", lambda m: m.set_metadata("UID", "u")),
        ("format", lambda m: m.format_file()),
    ]
    for label, edit in edits:
        m = model()
        before = m.data
        edit(m)
        after = m.data
        assert after != before, label
        assert m.can_undo and not m.can_redo
        assert m.undo() and m.data == before and not m.dirty, label
        assert m.can_redo and not m.can_undo
        assert m.redo() and m.data == after, label


def test_many_edits_undo_one_at_a_time_back_to_the_original_and_redo_forward():
    m = model()
    bar = find(m, "Bar", "Top_Bar")
    states = [m.data]
    for value in ("33", "34", "35", "36"):
        m.set_value(bar, "Height", value)
        states.append(m.data)
    for expected in reversed(states[:-1]):
        assert m.undo() and m.data == expected
    assert not m.undo() and m.data == MAIN
    for expected in states[1:]:
        assert m.redo() and m.data == expected
    assert not m.redo()


def test_a_new_edit_after_an_undo_drops_the_redo_states():
    m = model()
    bar = find(m, "Bar", "Top_Bar")
    m.set_value(bar, "Height", "40")
    m.undo()
    m.set_value(bar, "Height", "50")
    assert not m.can_redo and "Height: 50" in m.text


def test_the_selection_stays_on_the_same_block_after_every_kind_of_edit_and_on_undo():
    m = model()
    bar = find(m, "Bar", "Top_Bar")
    m.select(bar)
    m.set_value(bar, "Height", "40")
    assert m.selection == bar and m.selected.name == "Top_Bar"
    m.set_value(bar, "Opacity", "50%")
    assert m.selection == bar
    m.clear_value(bar, "Opacity")
    assert m.selection == bar
    m.set_metadata("UID", "u")
    assert m.selection == bar and m.selected.name == "Top_Bar"
    m.undo()
    assert m.selection == bar and m.selected.name == "Top_Bar"
    m.format_file()
    assert m.selection == bar and m.selected.name == "Top_Bar", "format changes no entry, so the index path is the same"
    m.undo()
    assert m.selected.name == "Top_Bar"


def test_the_selection_follows_its_block_when_an_add_remove_or_move_shifts_its_index():
    """Each edit changes the index path of other blocks; the selection is the same block afterwards (found again by its new path), and undo and redo restore the selection each state had."""
    for pick, edit in [
        ("Popup", lambda m: m.add_block(MONITOR, "Spacer { }", 0)),                              # added before it
        ("Popup", lambda m: m.remove_block(find(m, "Bar", "Top_Bar"))),                            # an earlier sibling leaves
        ("Popup", lambda m: m.move_block(find(m, "Bar", "Top_Bar"), index=len(m.node_at(MONITOR).entries) - 1)),  # an earlier sibling moves past it
        ("Bar", lambda m: m.move_block(find(m, "Popup"), index=0)),                                # a later sibling moves before it
        ("Popup", lambda m: m.move_block(find(m, "Bar", "Top_Bar"), (), 0)),                       # an earlier sibling moves up a level
        ("Battery", lambda m: m.add_block(find(m, "Children"), "Spacer { }", 0)),                  # added before its ancestor's entry
        ("Popup", lambda m: m.move_block(find(m, "Popup"), index=0)),                              # the selected block itself moves
        ("Popup", lambda m: m.move_block(find(m, "Popup"), find(m, "Children"), 0)),               # and across parents
    ]:
        m = model()
        path = find(m, pick, "Calendar_Popup" if pick == "Popup" else None)
        m.select(path)
        node_before = m.text[m.selected.start:m.selected.end]
        edit(m)
        assert m.selected is not None
        assert m.text[m.selected.start:m.selected.end].split() == node_before.split(), (pick, m.selection)
        text_after = m.data
        m.undo()
        assert m.selection == path and m.selected.type == pick
        m.redo()
        assert m.data == text_after and m.text[m.selected.start:m.selected.end].split() == node_before.split()


def test_removing_a_block_that_holds_the_selection_selects_its_parent():
    m = model()
    bar = find(m, "Bar", "Top_Bar")
    battery = find(m, "Battery")
    m.select(battery)
    m.remove_block(bar)
    assert m.selection == MONITOR


def test_select_true_selects_the_added_or_moved_block():
    m = model()
    popup = find(m, "Popup")
    new = m.move_block(popup, index=0, select=True)
    assert m.selection == new and m.selected.name == "Calendar_Popup"


def test_selecting_a_node_that_is_not_there_is_refused_and_selection_can_be_cleared_to_none():
    m = model()
    with pytest.raises(EditError):
        m.select((99,))
    m.select(None)
    assert m.selection is None and m.selected is None


def test_removing_the_selected_block_selects_its_parent():
    m = model()
    popup = find(m, "Popup")
    m.select(popup)
    m.remove_block(popup)
    assert m.selection == popup[:-1] and m.selected.type == "Monitor"


# -- the text view -----------------------------------------------------------------------------------------------------------------

def test_the_text_view_edits_the_text_and_the_tree_follows_when_it_parses():
    m = model()
    bar = find(m, "Bar", "Top_Bar")
    m.select(bar)
    m.set_text(m.text.replace("Height: 32", "Height: 48"))
    assert m.valid and m.selection == bar and "Height: 48" in m.text
    m.set_text(m.text.replace("Height: 48", "Height: 48 {"))  # now it does not parse
    assert not m.valid and m.errors and m.selection is None and m.document is None
    m.set_text(m.text.replace("Height: 48 {", "Height: 49"))
    assert m.valid and m.selection == () and "Height: 49" in m.text


def test_typing_in_the_text_view_is_one_undo_step():
    m = model()
    original = m.data
    text = m.text
    for i in range(1, 6):
        text = text + "# " + "x" * i + "\n"
        m.set_text(text)
    assert m.undo() and m.data == original and not m.can_undo
    assert m.redo() and m.text == text


def test_text_edits_and_structure_edits_are_separate_steps():
    m = model()
    m.set_text(m.text + "\n# note\n")
    m.set_value((), "A", "1")
    m.set_text(m.text + "# more\n")
    assert m.undo() and "# more" not in m.text and "A: 1" in m.text
    assert m.undo() and "A: 1" not in m.text and "# note" in m.text
    assert m.undo() and m.data == MAIN


def test_a_text_edit_that_changes_nothing_is_not_a_step():
    m = model()
    m.set_text(m.text)
    assert not m.can_undo


def test_a_file_that_is_not_utf8_cannot_be_edited_in_the_text_view():
    m = DocumentModel.from_bytes(b"---\nTDL: 0.1\nName: X\n---\nShell { A: \xff }\n")
    with pytest.raises(EditError, match="not UTF-8"):
        m.set_text("---\nTDL: 0.1\nName: X\n---\nShell { }\n")


def test_adopting_the_disk_after_a_change_starts_the_history_over():
    m = model()
    m.set_value(MONITOR, "Index", "2")
    new = MAIN.replace(b"Height: 32", b"Height: 99")
    m.adopt_disk(new)
    assert m.data == new and not m.dirty and not m.can_undo and m.selection == ()


def test_the_structure_tree_follows_the_document_and_a_path_round_trips():
    m = model()
    rows = nodes_for(m.document)
    assert rows[0]["value"] == "r" and rows[0]["label"] == "Shell"
    path = find(m, "Bar", "Top_Bar")
    assert path_of(value_of(path)) == path and path_of(value_of(path, else_branch=True)) == path
    assert nodes_for(None) == []
