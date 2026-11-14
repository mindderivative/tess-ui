"""The `If` and `For` rows of the form: condition, list, key and variable are edited through `tess_dl`'s own edits, and only the bytes of the part change.

The nodes are found by `node.index_path` (a comment at the end of an `If ... {` line is the first entry of the body, so counting by hand is wrong). An `If` with an `Else` is tested too:
the edit of the condition leaves the Else body byte for byte.
"""

import pytest

from tess_shell_config.form import Form
from tess_shell_config.model import DocumentModel, EditError
from tess_shell_config.tdl import walk

from test_shell_config_form import changed

DOC = """---
TDL: 0.1
Name: Flow
---
Shell {
  Monitor {
    Name: Main   # keep this
    Children {
      If {{ battery.low }} {   # the comment is the first entry of the body
        Text { Text: "low" }
      } Else {
        # nothing here
        Text { Text: "fine" }
      }
      For tile In {{ tiles }} Key {{ tile.id }} {
        Text { Text: {{ tile.title }} }
      }
    }
  }
}
"""


class Rig:
    def __init__(self, tmp_path, schema, text=DOC):
        self.model = DocumentModel(text, None, relative="Flow_Shell.tdl")
        self.form = Form(schema)

    def node(self, kind):
        return next(n for n in walk(self.model.document.root) if type(n).__name__ == kind)

    def build(self, kind):
        self.model.select(self.node(kind).index_path)
        return self.form.build(self.model)

    def commit(self, kind, part, text):
        self.build(kind)
        before = self.model.text
        outcome = self.form.commit(f"f:{part}|", {"text": text})
        return outcome, changed(before, self.model.text)


@pytest.fixture
def rig(tmp_path, schema):
    return Rig(tmp_path, schema)


def test_an_if_shows_its_condition_and_a_for_its_variable_list_and_key(rig):
    view = rig.build("If")
    assert view.title == "If" and [r.label for r in view.rows] == ["Condition"]
    assert view.cell("Condition").text == "{{ battery.low }}"
    view = rig.build("For")
    assert [r.label for r in view.rows] == ["Variable", "In", "Key"]
    assert [view.cell(n).text for n in ("Variable", "In", "Key")] == ["tile", "{{ tiles }}", "{{ tile.id }}"]
    assert any("does not rename" in n for n in view.notes)


def test_the_condition_is_written_in_place_and_the_else_body_stays_byte_for_byte(rig):
    before = rig.model.text
    outcome, diff = rig.commit("If", "condition", "{{ battery.level < 20 }}")
    assert outcome.changed and diff == ["-      If {{ battery.low }} {   # the comment is the first entry of the body", "+      If {{ battery.level < 20 }} {   # the comment is the first entry of the body"]
    assert before.split("} Else {")[1] == rig.model.text.split("} Else {")[1]  # the Else body and everything after it
    assert rig.model.node_at(rig.node("If").index_path).condition.text == " battery.level < 20 "
    assert rig.model.can_undo and (rig.model.undo(), rig.model.text)[1] == before


@pytest.mark.parametrize(("part", "text", "old", "new"), [
    ("items", "{{ tiles | sort }}", "In {{ tiles }}", "In {{ tiles | sort }}"),
    ("key", "{{ tile.name }}", "Key {{ tile.id }}", "Key {{ tile.name }}"),
    ("variable", "t", "For tile In", "For t In"),
])
def test_for_parts_change_only_their_own_bytes(rig, part, text, old, new):
    before = rig.model.text
    outcome, diff = rig.commit("For", part, text)
    assert outcome.changed and rig.model.text == before.replace(old, new)
    assert len(diff) == 2
    # the rename leaves the uses alone, as the warning says
    if part == "variable":
        assert "{{ tile.id }}" in rig.model.text and "{{ tile.title }}" in rig.model.text


def test_the_selection_and_the_other_rows_survive_an_edit(rig):
    rig.build("For")
    path = rig.model.selection
    rig.form.commit("f:items|", {"text": "{{ more }}"})
    assert rig.model.selection == path and rig.form.view.cell("In").text == "{{ more }}"


@pytest.mark.parametrize(("kind", "part", "text", "words"), [
    ("If", "condition", "battery.low", "{{"),          # not a slot
    ("If", "condition", "{{ unclosed", ""),             # a syntax error in the slot
    ("For", "items", "{{ a }} {{ b }}", ""),            # not exactly one slot
    ("For", "variable", "2fast", "valid name"),
    ("For", "variable", "Key", "reserved"),
])
def test_text_tess_dl_refuses_is_shown_as_the_refusal_and_the_file_is_unchanged(rig, kind, part, text, words):
    outcome, diff = rig.commit(kind, part, text)
    assert not outcome.changed and not outcome.ok and diff == []
    assert outcome.message and words in outcome.message
    assert rig.form.view.cell(rig.form.FLOW_LABELS[part]).error == outcome.message


def test_a_part_cannot_be_cleared_and_the_model_names_a_part_a_node_does_not_have(rig):
    rig.build("For")
    outcome = rig.form.commit("f:variable|", {"text": ""})
    assert not outcome.ok and "without its variable" in outcome.message
    with pytest.raises(EditError, match="no condition"):
        rig.model.set_flow(rig.node("For").index_path, "condition", "{{ x }}")


def test_a_comment_at_the_end_of_the_head_line_does_not_move_the_path(rig):
    """The `If` of this file starts its body with a comment: its entries are counted from the comment, and `index_path` is what finds the node."""
    node = rig.node("If")
    assert type(node.body[0]).__name__ == "Comment"
    assert rig.model.node_at(node.index_path) is not None
    rig.model.set_flow(node.index_path, "condition", "{{ x }}")
    assert type(rig.node("If").body[0]).__name__ == "Comment" and rig.node("If").index_path == node.index_path
