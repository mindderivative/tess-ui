"""User modules: the `Params` of the module files in `Modules/` join the schema's modules, in the Add menu and as the form of a call."""

import shutil

import pytest

from tess_shell_config.blocks import children_of
from tess_shell_config.session import ConfigSession
from tess_shell_config.usermodules import read_module, user_modules

from test_shell_config_window import CONFIG

MODULE = """---
TDL: 0.1
Name: Hello
---

Module {
    Params {
        who { Type: string, Default: "world" }   # whom to greet
        size { Type: number, Default: 12 }
        shout { Type: boolean }
        odd { Type: widget_of_the_future }
        Param { Name: loud, Type: bool, Default: true }
        bare { }
    }

    FlexBox {
        Children { Text { Text: {{ who }} } }
    }
}
"""


def test_a_module_files_params_are_read_with_name_type_and_default():
    module = read_module("Modules/Hello/Hello_Module.tdl", MODULE, "Hello_Module")
    assert module is not None and module.name == "Hello" and module.layout == "FlexBox"
    assert [(p.name, p.type, p.default) for p in module.params] == [
        ("who", "string", '"world"'), ("size", "number", "12"), ("shout", "boolean", None), ("odd", "widget_of_the_future", None), ("loud", "bool", "true"), ("bare", "", None)]


@pytest.mark.parametrize("text", ["not tdl at all", "---\nTDL: 0.1\nName: X\n---\nShell { }\n", "---\nTDL: 0.1\nName: X\n---\nModule { Params { a { Type: string } }\n"])
def test_a_file_that_is_not_a_module_or_does_not_parse_is_not_a_user_module(text, schema):
    assert read_module("Modules/X/X_Module.tdl", text, "X") is None
    assert user_modules([("Modules/X/X_Module.tdl", text, "X")], schema) == {}


def test_a_user_module_is_described_like_a_shipped_one_with_no_doc_lines_for_its_params(schema):
    found = user_modules([("Modules/Hello/Hello_Module.tdl", MODULE, "Hello"), ("Elsewhere/Hello_Module.tdl", MODULE, "Other")], schema)
    assert list(found) == ["Hello"]  # only a file under Modules/
    hello = found["Hello"]
    assert hello.root_block == "FlexBox" and hello.common_keys and "Clock" in schema.modules
    assert {k: (p.type, p.kind, p.doc, p.default) for k, p in hello.params.items()} == {
        "who": ("string", "string", "", '"world"'), "size": ("number", "number", "", "12"), "shout": ("boolean", "bool", "", None),
        "odd": ("widget_of_the_future", "", "", None), "loud": ("bool", "bool", "", "true"), "bare": ("", "", "", None)}
    assert set(hello.common_keys) <= set.intersection(*(set(m.common_keys) for m in schema.modules.values()))


def test_a_shipped_module_is_never_replaced_by_a_user_module_of_its_name(schema):
    text = MODULE.replace("Name: Hello", "Name: Clock")
    assert user_modules([("Modules/Clock/Clock_Module.tdl", text, "Clock")], schema)["Clock"].params["who"].kind == "string"
    merged = schema.with_modules(user_modules([("Modules/Clock/Clock_Module.tdl", text, "Clock")], schema))
    assert merged.modules["Clock"] is schema.modules["Clock"]


def test_the_session_adds_the_users_modules_to_the_schema_and_follows_a_changed_file(tmp_path, schema):
    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    session = ConfigSession(folder, schema, state_dir=tmp_path / "state")
    assert session.shipped_schema is schema and "Hello" in session.schema.modules
    assert "Hello" not in schema.modules  # the shipped schema is not changed
    calls = [c.type for c in children_of(session.schema, "FlexBox")]
    assert "Hello" in calls and all(m in calls for m in schema.modules)  # every shipped module AND the user's
    (folder / "Modules" / "Hello" / "Hello_Module.tdl").write_text(MODULE)
    session.refresh()
    assert list(session.schema.modules["Hello"].params)[:2] == ["who", "size"]
    # unsaved text of an open module file counts
    model = session.open("Modules/Hello/Hello_Module.tdl")
    model.set_text(MODULE.replace("size {", "extent {"))
    session.update_modules()
    assert "extent" in session.schema.modules["Hello"].params and "size" not in session.schema.modules["Hello"].params
    # and a module that is deleted leaves the menu
    session.close("Modules/Hello/Hello_Module.tdl")
    (folder / "Modules" / "Hello" / "Hello_Module.tdl").unlink()
    session.refresh()
    assert "Hello" not in session.schema.modules


SHELL = """---
TDL: 0.1
Name: Calls
---

Shell {
    Monitor {
        Name: Main, Index: default
        Bar {
            Name: Top, Edge: TOP, Width: EXPAND, Height: 32
            Children {
                Hello { who: "you" }
                Clock { }
            }
        }
    }
}
"""


def test_the_form_of_a_call_to_a_user_module_shows_its_params_with_name_and_type_and_no_doc_then_the_common_keys(tmp_path, schema):
    from tess_shell_config.form import Form
    from tess_shell_config.model import DocumentModel

    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    session = ConfigSession(folder, schema, state_dir=tmp_path / "state")
    model = DocumentModel.from_bytes(SHELL.encode())
    hello = next(n for n in __import__("tess_shell_config.tdl", fromlist=["walk"]).walk(model.document.root) if getattr(n, "type", "") == "Hello")
    model.select(tuple(hello.index_path))
    view = Form(session.schema).build(model)
    params = [r for r in view.rows if r.group == "Parameters"]
    assert [r.label for r in params] == ["who"] and params[0].doc == ""
    assert view.cell("who").text == '"you"' and view.cell("who").widget.default == '"world"'
    assert params[0].markers == ["type string"]
    groups = list(view.groups)
    assert groups[0] == "Parameters" and "Common to every module" in groups
    assert view.notes[0].startswith("Your module")
    # a value written in the form is one changed line
    outcome = Form(session.schema)
    outcome.build(model)
    assert outcome.commit("k:who|", {"text": "there"}).changed
    assert 'who: "there"' in model.text
