"""What the real checker (tess-shell a3083ca) refused of what the application wrote, and the application now writes the other way; each case has its own test here, against the recorded schema, so it runs everywhere.
`test_shell_config_real_check.py` runs the same through the real `tesserae-shell check` where that is installed."""

from tess_shell_config import fileops
from tess_shell_config.blocks import HOLDER, add_child, children_of, has_layout, holder_of, is_layout, is_surface, module_layout, new_block_text, required_keys
from tess_shell_config.folder import FileType
from tess_shell_config.form import Form
from tess_shell_config.model import DocumentModel, block_names
from tess_shell_config.tdl import walk
from tess_shell_config.widgets import ListWidget


def shell_model(schema, *way):
    model = DocumentModel("---\nTDL: 0.1\nName: T\n---\nShell { }\n")
    path = ()
    for step in way:
        path = add_child(model, schema, path, step)
    return model, path


def test_blocks_of_a_surface_or_container_go_into_its_children_block_made_with_the_first(schema):
    assert [holder_of(schema, t) for t in ("Monitor", "Bar", "Panel", "Box", "Shell", "Module", "Style", "Stylesheet", "Theme")] == [HOLDER] * 4 + [""] * 5
    model, path = shell_model(schema, "Monitor", "Bar")
    assert [n.type for n in walk(model.document.root)][:4] == ["Shell", "Monitor", "Children", "Bar"]
    assert model.document.at(path).type == "Bar" and model.document.at(path[:-1]).type == "Children"
    add_child(model, schema, path[:-2], "Panel")  # the second goes into the Children that is there
    children = [n for n in walk(model.document.root) if getattr(n, "type", "") == "Children"]
    assert len(children) == 1 and [e.type for e in children[0].entries] == ["Bar", "Panel"]


def test_a_children_block_offers_what_its_parent_holds_not_the_parents_own_parts(schema):
    assert [c.type for c in children_of(schema, HOLDER, "Monitor")] == ["Bar", "Panel", "Popup", "Frame"]
    layout = [c.type for c in children_of(schema, HOLDER, "Module")]
    assert "Box" in layout and "Params" not in layout and "Style" not in layout and HOLDER not in layout
    assert children_of(schema, HOLDER) == []


def test_a_new_module_has_its_one_layout_block_and_offers_no_second(schema):
    layout = module_layout(schema)
    text = fileops.minimal_text(FileType.MODULE, "M", layout)
    model = DocumentModel(text)
    assert layout == "Box" and f"{layout} {{ }}" in text and has_layout(schema, model.document.root) and is_layout(schema, "Module", "Text") and not is_layout(schema, "Module", "Params")
    assert not has_layout(schema, DocumentModel(fileops.minimal_text(FileType.MODULE, "M")).document.root)
    assert fileops.minimal_text(FileType.SHELL, "S", layout).count("Box") == 0, "only a module gets a layout"


def test_a_block_with_alternative_required_keys_gets_one_of_each_set_and_not_a_file_where_a_name_will_do(schema):
    assert [k.name for k in required_keys(schema, "Panel")] == ["Name", "Width", "Height"]
    assert [k.name for k in required_keys(schema, "SVG")] == ["Icon"], "of Source (a file that may not be there) and Icon, the one that names no file"
    assert [k.name for k in required_keys(schema, "Bitmap")] == ["Source"]


def test_a_new_rule_selects_a_class_nothing_has_yet_and_a_type_default_in_a_style_has_no_required_keys(schema):
    assert '".new_rule"' in new_block_text(schema, "Rule", set())
    model = DocumentModel("---\nTDL: 0.1\nName: T\n---\nStyle { }\n")
    path = add_child(model, schema, (), "SVG")
    assert model.document.at(path).entries == (), "the keys that make an SVG are not style keys"


def test_a_surfaces_style_keys_and_shadows_are_written_in_its_style_block_and_a_drawn_blocks_on_it(schema):
    assert is_surface(schema, "Bar") and is_surface(schema, "Frame") and not is_surface(schema, "Box") and not is_surface(schema, "Rule")
    model, bar = shell_model(schema, "Monitor", "Bar")
    model.select(bar)
    form = Form(schema)
    form.build(model)
    assert form.commit("k:Background|", form.cell("k:Background|").widget.sample_edit()).ok and "Style { Background:" in model.text
    assert form.commit("k:Shadows|", form.cell("k:Shadows|").widget.sample_edit()).ok and "Shadows {" in model.text.split("Style {")[1]
    form.build(model)
    assert form.reset("k:Background|").changed and form.reset("k:Shadows|").changed and "Background" not in model.text and "Shadows" not in model.text
    box_model, box = shell_model(schema, "Monitor", "Bar", "Box")
    box_model.select(box)
    form = Form(schema)
    form.build(box_model)
    assert form.commit("k:Background|", form.cell("k:Background|").widget.sample_edit()).ok and "Style" not in box_model.text.split("Box")[-1]


def test_a_key_a_module_sets_is_read_only_in_a_shell_file_and_writable_in_a_module_file(schema):
    model, box = shell_model(schema, "Monitor", "Bar", "Box")
    model.select(box)
    form = Form(schema)
    form.build(model)
    assert form.cell("k:Value|").readonly and "set by a module" in form.view.row("Value").markers
    module = DocumentModel(fileops.minimal_text(FileType.MODULE, "M", "Box"))
    module.select(next(n.index_path for n in walk(module.document.root) if getattr(n, "type", "") == "Box"))
    form = Form(schema)
    form.build(module)
    assert not form.cell("k:Value|").readonly


def test_a_list_of_key_names_is_written_as_words_and_a_tooltip_sample_is_not_empty(schema):
    model, box = shell_model(schema, "Monitor", "Bar", "Box")
    model.select(box)
    form = Form(schema)
    form.build(model)
    transition = form.cell("k:Transition|").widget
    assert isinstance(transition, ListWidget) and transition.write({"items": ["Width", "Opacity"]}) == "[Width, Opacity]"
    assert form.cell("k:Tooltip|").widget.sample_edit()["text"] not in ("", '""')


def test_a_block_moves_into_a_surface_that_has_no_children_block_yet_in_one_edit(schema):
    model, bar = shell_model(schema, "Monitor", "Bar")
    popup = add_child(model, schema, bar[:-3], "Popup")
    add_child(model, schema, bar, "Text")
    text = next(n.index_path for n in walk(model.document.root) if getattr(n, "type", "") == "Text")
    steps = len(model._history)
    moved = model.move_block(tuple(text), popup, None, wrap_in=HOLDER)
    assert len(model._history) == steps + 1, "one edit, one undo step"
    assert model.document.at(moved).type == "Text" and model.document.at(moved[:-1]).type == HOLDER and model.document.at(moved[:-2]).type == "Popup"
    assert model.undo() and "Popup {" in model.text and model.text.count("Text") == 1
