"""A key whose value is a block of its own (Shadows, Animation, Peek, Inner_Border...): one button adds the block, then opens it in the structure; Reset removes it."""

import difflib

import pytest
from test_shell_config_form_window import FormWindow
from test_shell_config_window import CONFIG  # noqa: F401

from tess_shell_config.form import Form
from tess_shell_config.model import DocumentModel
from tess_shell_config.tdl import walk

DOC = """---
TDL: 0.1
Name: Blocks
---

Shell {
    Monitor {
        Name: Main, Index: default
        Frame {
            Name: Ring
            Inner_Border { Width: 2, Color: "#FFFFFF" }
        }
        Bar {
            Name: Top, Edge: TOP, Width: EXPAND, Height: 32
            Shadows: $elevation.max
        }
        Panel {
            Name: Side, Edge: LEFT, Width: 200, Height: 100
            Shadows { Shadow { X: 0, Y: 4, Blur: 8 } }
        }
    }
}
"""


def select(model, type_name):
    node = next(n for n in walk(model.document.root) if getattr(n, "type", "") == type_name)
    model.select(tuple(node.index_path))


def changed(before, after):
    return [line[0] + line[2:].strip() for line in difflib.ndiff(before.splitlines(), after.splitlines()) if line[0] in "+-"]


@pytest.fixture
def model():
    return DocumentModel.from_bytes(DOC.encode())


def test_a_block_key_gets_a_button_not_a_text_field(model, schema):
    select(model, "Panel")
    view = Form(schema).build(model)
    cell = view.row("Shadows").cells[0].view()
    assert cell["ui"] == "block" and cell["exists"] and cell["label"] == "Open Shadows" and view.row("Shadows").cells[0].present
    absent = view.row("Animation").cells[0].view()
    assert absent["ui"] == "block" and not absent["exists"] and absent["label"] == "Add Animation"
    assert not view.row("Shadows").cells[0].widget.reason


def test_the_button_adds_the_block_with_its_required_keys_in_one_edit_and_reset_removes_it(model, schema):
    select(model, "Panel")
    form = Form(schema)
    form.build(model)
    before = model.text
    assert form.commit("k:Animation|", {"add": True}).changed
    added = changed(before, model.text)
    assert len(added) >= 1 and all(line.startswith("+") for line in added) and any("Animation" in line for line in added)
    assert form.view.row("Animation").cells[0].view()["label"] == "Open Animation"
    assert not form.commit("k:Animation|", {"add": True}).ok  # it is there already
    assert form.reset("k:Animation|").changed and model.text == before
    assert model.undo() and "Animation" in model.text and model.redo() and model.text == before


def test_a_block_named_for_its_key_is_written_with_the_keys_of_the_schemas_spec(model, schema):
    select(model, "Frame")
    form = Form(schema)
    form.build(model)
    assert form.view.row("Inner_Border").cells[0].view()["exists"]
    assert form.commit("k:Outer_Border|", {"add": True}).changed
    assert "Outer_Border {" in model.text and "Border {" not in model.text.replace("Outer_Border {", "").replace("Inner_Border {", "")


def test_a_token_reference_in_a_shadows_key_stays_text_and_is_not_rewritten(model, schema):
    select(model, "Bar")
    form = Form(schema)
    view = form.build(model)
    cell = view.row("Shadows").cells[0]
    assert cell.view()["ui"] == "field" and cell.text == "$elevation.max" and cell.tdl
    before = model.text
    refused = form.commit("k:Shadows|", {"add": True})
    assert not refused.ok and "reset it first" in refused.message and model.text == before  # a value is there: no second Shadows
    assert form.commit("k:Shadows|", {"text": "$elevation.min"}).changed and "Shadows: $elevation.min" in model.text  # typed text is the key's own property
    assert form.reset("k:Shadows|").changed and "Shadows" not in model.text.split("Panel")[0].split("Bar {")[1]


def test_a_block_key_the_shell_refuses_has_no_button(model, schema):
    select(model, "Frame")
    cell = Form(schema).build(model).row("Shadows").cells[0]
    assert cell.readonly and cell.view()["ui"] == "field"


@pytest.fixture
def folder(tmp_path):
    import shutil

    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    (target / "Shells" / "Blocks_Shell.tdl").write_text(DOC)
    return target


def test_in_the_window_the_button_adds_and_opens_the_block_in_the_structure(folder, tmp_path, schema):
    w = FormWindow(folder, tmp_path, schema)
    w.open("Shells/Blocks_Shell.tdl")
    w.select("Panel  Side")
    w.open_all_groups()
    names = {inst.name for inst in w.built.view.handle.composition.walk() if inst.name}
    assert "block_button" in names
    w.vm.form_block("k:Animation|")
    w.settle()
    assert "Animation" in w.session.model.text and w.session.model.selected.type == "Panel"
    labels = [i["label"] for i in w.vm.form_items.get() if i["type"] == "row" and i["id"] == "k:Animation"]
    assert labels == ["Animation"]
    w.vm.form_block("k:Animation|")  # now it is there: the button opens it
    w.settle()
    assert w.session.model.selected.type == "Animation" and w.vm.selected_label.get().startswith("Selected: Animation")
