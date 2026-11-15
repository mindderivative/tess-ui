"""Piece 6a of the TDL switch: a name finds `.tdl` or `.yaml`, every loader picks its front end by the file suffix, the library loads the shipped `.tdl`
(`TESS_UI_SHIPPED=yaml` forces the YAML), only the TDL 0.2 language is accepted, and a changed `.tdl` is hot-reloaded as a YAML one is."""

import ast
import dataclasses
import re
from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front ends need tess_dl (Python 3.14)")

from loguru import logger  # noqa: E402

from tess_ui import App  # noqa: E402
from tess_ui import project as project_module  # noqa: E402
from tess_ui import shipped  # noqa: E402
from tess_ui.expr import Expr  # noqa: E402
from tess_ui.migrate_tdl import _handler_form  # noqa: E402
from tess_ui.migrate_tdl_sheets import convert_sheet  # noqa: E402
from tess_ui.migrate_tdl_theme import convert_theme  # noqa: E402
from tess_ui.project import (  # noqa: E402
    Project, ProjectError, is_view_file, kind_of_tdl, looks_like_kind, sibling_file, tdl_wrong_kind, view_stem,
)
from tess_ui.spec import flavour, marker  # noqa: E402
from tess_ui.spec.build import shipped_default_theme  # noqa: E402
from tess_ui.spec.nodes import Handler, LoadError, Node, parse_view  # noqa: E402
from tess_ui.spec.rules import load_rule_sheet  # noqa: E402
from tess_ui.spec.themes import load_stylesheet, load_theme  # noqa: E402
from tess_ui.spec.watch import ComposedWatcher  # noqa: E402
from tests.tdl_helper import yaml_to_tdl  # noqa: E402
from tests.test_hot_reload_composed import V1, V2, VM, text_of, write  # noqa: E402

HEAD = '---\nTDL: 0.2\nName: {name}\nTesserae: "0.6"\n---\n'
VIEW = HEAD.format(name="Main") + "Container {\n  Name: main\n  Children {\n    Text { Name: t, Text: hi, Typography_Role: body_large, Style { Foreground: on_surface } }\n  }\n}\n"
SHEET = HEAD.format(name="Brand") + "Styles {\n  Rule { Widget: Text, Style { Gap: 4 } }\n}\n"
THEME = HEAD.format(name="Brand") + 'Theme {\n  Seed: "#0B6B58"\n}\n'


def put(root: Path, relative: str, text: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def notes():
    """What the loaders log at INFO and above, as messages."""
    seen: list[str] = []
    sink = logger.add(lambda message: seen.append(message.record["message"]), level="INFO")
    yield seen
    logger.remove(sink)


# -- discovery and naming ----------------------------------------------------------------------------------------------------


def test_a_name_finds_the_tdl_file_of_a_view_a_theme_and_a_stylesheet(tmp_path):
    put(tmp_path, "Views/Main_View.tdl", VIEW)
    put(tmp_path, "Themes/Brand_Theme.tdl", THEME)
    put(tmp_path, "Styles/Brand_Stylesheet.tdl", SHEET)
    project = Project(tmp_path)
    assert project.find("view", "Main") == tmp_path / "Views" / "Main_View.tdl"
    assert project.find("theme", "Brand") == tmp_path / "Themes" / "Brand_Theme.tdl"
    assert project.find("stylesheet", "Brand") == tmp_path / "Styles" / "Brand_Stylesheet.tdl"


def test_a_name_finds_a_yaml_file_still_and_a_tdl_one_in_another_folder_beside_it_is_a_name_in_two_places(tmp_path):
    put(tmp_path, "Views/Old_View.yaml")
    assert Project(tmp_path).find("view", "Old") == tmp_path / "Views" / "Old_View.yaml"
    put(tmp_path, "more/Old_View.tdl")
    with pytest.raises(ProjectError, match=r"Old_View.yaml is in two places, Views.Old_View.yaml and more.Old_View.tdl"):
        Project(tmp_path, search=["more"]).find("view", "Old")


def test_in_one_folder_the_tdl_wins_and_a_note_says_once_that_the_yaml_twin_is_ignored(tmp_path, notes):
    put(tmp_path, "Views/Main_View.yaml")
    put(tmp_path, "Views/Main_View.tdl")
    project = Project(tmp_path)
    assert project.find("view", "Main").name == "Main_View.tdl"
    assert project.index("view") == {"Main": tmp_path / "Views" / "Main_View.tdl"}
    twin = [n for n in notes if "Main_View.yaml" in n and "ignored" in n]
    assert len(twin) == 1 and "Main_View.tdl" in twin[0]


@pytest.mark.parametrize("kind, folder, tdl, yaml", [("theme", "Themes", "Brand_Theme.tdl", "Brand_Theme.yaml"),
                                                        ("stylesheet", "Styles", "Brand_Stylesheet.tdl", "Brand_Stylesheet.yaml")])
def test_the_tdl_wins_for_themes_and_stylesheets_too(tmp_path, kind, folder, tdl, yaml):
    put(tmp_path, f"{folder}/{yaml}")
    put(tmp_path, f"{folder}/{tdl}")
    assert Project(tmp_path).find(kind, "Brand").name == tdl


def test_a_recursive_project_finds_a_tdl_view_anywhere(tmp_path):
    put(tmp_path, "deep/er/Main_View.tdl")
    assert Project(tmp_path, recursive=True).find("view", "Main") == tmp_path / "deep" / "er" / "Main_View.tdl"


def test_a_tdl_file_in_the_wrong_folder_is_found_and_named_as_a_yaml_one_is(tmp_path):
    put(tmp_path, "Themes/Extra_View.tdl")
    with pytest.raises(ProjectError) as raised:
        Project(tmp_path).find("view", "Extra")
    text = str(raised.value)
    assert text.startswith("no view called 'Extra' (Extra_View.yaml) in ")  # the message that was there, first and unchanged
    assert "found Themes/Extra_View.tdl: views are read from Views/ (or add Themes to App(search=[...]))" in text
    put(tmp_path, "Views/Brand_Theme.tdl")
    with pytest.raises(ProjectError, match=r"found Views/Brand_Theme.tdl, a theme, not a view"):
        Project(tmp_path).find("view", "Brand")


def test_names_and_suffix_helpers_know_both_forms(tmp_path):
    assert view_stem("a/Main_View.tdl") == "Main" and view_stem(Path("Main_View.yaml")) == "Main" and view_stem("Other.txt") == "Other.txt"
    assert is_view_file("Main_View.tdl") and is_view_file("Main_View.yaml") and not is_view_file("Main_Theme.tdl")
    assert project_module.suffixes("view") == ("_View.tdl", "_View.yaml") and project_module.suffixes("component") == ("_Component.yaml",)
    put(tmp_path, "Main_View.yaml")
    assert sibling_file(tmp_path / "Main_View.yaml", "view", "Main") == tmp_path / "Main_View.yaml"
    put(tmp_path, "Main_View.tdl")
    assert sibling_file(tmp_path / "Main_View.yaml", "view", "Main") == tmp_path / "Main_View.tdl"
    assert sibling_file(tmp_path / "Main_View.yaml", "view", "Nope") is None


def test_a_tdl_view_beside_its_tdl_stylesheet_finds_it(tmp_path):
    put(tmp_path, "Views/Main_View.tdl", VIEW)
    sheet = put(tmp_path, "Views/Main_Stylesheet.tdl", SHEET)
    library = shipped.ViewLibrary(Project(tmp_path).index("view"), Project(tmp_path).index("stylesheet"))
    assert library.project_sheet("Main") == sheet


# -- kind detection by the root block --------------------------------------------------------------------------------------


@pytest.mark.parametrize("body, kind", [("Styles {\n}\n", "stylesheet"), ("Theme {\n}\n", "theme"), ("Container {\n}\n", "view"), ("# c\nStyles { }\n", "stylesheet")])
def test_the_root_word_of_a_tdl_file_is_its_kind(body, kind):
    assert kind_of_tdl(HEAD.format(name="A") + body) == kind
    assert kind_of_tdl(body) == kind  # a file with no metadata block says it too (the front end refuses it for that)
    assert kind_of_tdl("") is None and kind_of_tdl("# only a comment\n") is None


def test_the_hint_names_the_file_to_give_in_the_files_own_language():
    assert looks_like_kind("theme", "stylesheet", "Brand_Stylesheet.tdl") == "this looks like a theme: name it Brand_Theme.tdl"
    assert looks_like_kind("theme", "stylesheet", "Brand_Stylesheet.yaml") == "this looks like a theme: name it Brand_Theme.yaml"
    assert looks_like_kind("view", "theme", "") == "this looks like a view: name it <Name>_View.yaml"
    assert looks_like_kind("view", "view", "A_View.tdl") is None and looks_like_kind(None, "view") is None
    text = HEAD.format(name="A") + "Theme { }\n"
    hint, line, column = tdl_wrong_kind(text, "view", "A_View.tdl")
    assert hint == "this looks like a theme: name it A_Theme.tdl" and (line, column) == (6, 0)


def test_a_tdl_file_read_as_the_wrong_kind_is_refused_with_the_name_to_give_it(tmp_path):
    theme = put(tmp_path, "Brand_Stylesheet.tdl", THEME)
    sheet = put(tmp_path, "Brand_Theme.tdl", SHEET)
    with pytest.raises(LoadError, match="this looks like a theme: name it Brand_Theme.tdl") as caught:
        load_rule_sheet(theme)
    assert caught.value.line == 6
    with pytest.raises(ValueError, match="this looks like a theme: name it Brand_Theme.tdl"):
        load_stylesheet(theme)
    with pytest.raises(ValueError, match="this looks like a stylesheet: name it Brand_Stylesheet.tdl"):
        load_theme(sheet)
    with pytest.raises(LoadError, match="this looks like a stylesheet: name it Brand_Stylesheet.tdl"):
        parse_view(SHEET, "Brand_View.tdl")
    with pytest.raises(LoadError, match="this looks like a theme: name it A_Theme.tdl"):
        parse_view(THEME, "A_View.tdl")


def test_a_loader_refuses_a_file_whose_name_says_it_is_another_kind(tmp_path):
    with pytest.raises(ValueError, match="loaded as a theme, but its name says it's a stylesheet"):
        load_theme(put(tmp_path, "Brand_Stylesheet.tdl", SHEET))
    with pytest.raises(ValueError, match="loaded as a stylesheet, but its name says it's a theme"):
        load_stylesheet(put(tmp_path, "Brand_Theme.tdl", THEME))


# -- the loaders read by suffix --------------------------------------------------------------------------------------------


def test_every_loader_reads_a_tdl_file_to_what_its_yaml_twin_gives(tmp_path):
    yaml_sheet = "tesserae: 0.6\nstyles:\n  - {widget: Text, style: {gap: 4, foreground: '{{ \"primary\" }}'}}\n"
    yaml_theme = "tesserae: 0.6\nseed: '#0B6B58'\ncolors: {tertiary: '#C2410C'}\n"
    sheet_tdl = convert_sheet(yaml_sheet, "Brand", "Brand_Stylesheet.yaml").text
    theme_tdl = convert_theme(yaml_theme, "Brand", "Brand_Theme.yaml").text
    files = {name: put(tmp_path, name, text) for name, text in {"Brand_Stylesheet.yaml": yaml_sheet, "Brand_Stylesheet.tdl": sheet_tdl,
                                                                  "Brand_Theme.yaml": yaml_theme, "Brand_Theme.tdl": theme_tdl}.items()}
    assert load_stylesheet(files["Brand_Stylesheet.tdl"]) == load_stylesheet(files["Brand_Stylesheet.yaml"])
    assert load_theme(files["Brand_Theme.tdl"]) == load_theme(files["Brand_Theme.yaml"])
    assert canon(load_rule_sheet(files["Brand_Stylesheet.tdl"]).rules) == canon(load_rule_sheet(files["Brand_Stylesheet.yaml"]).rules)


def test_the_app_takes_a_tdl_stylesheet_and_theme(tmp_path):
    put(tmp_path, "Styles/Brand_Stylesheet.tdl", SHEET)
    theme = put(tmp_path, "Themes/Brand_Theme.tdl", THEME)
    app = App(root=tmp_path, stylesheet=tmp_path / "Styles" / "Brand_Stylesheet.tdl", custom_theme=theme)
    assert app._stylesheet_spec == {"styles": [{"widget": "Text", "style": {"gap": 4}}]}
    assert app._custom_theme_spec == {"seed": "#0B6B58"}


def test_an_app_opens_a_tdl_view_by_name_and_names_it_by_its_file(tmp_path):
    put(tmp_path, "Views/Main_View.tdl", VIEW)
    app = App(root=tmp_path)
    opened = app.open_view("Main")
    assert opened.source == (tmp_path / "Views" / "Main_View.tdl").resolve()
    assert "main" in app._opened and opened.node("root.t").get("text") == "hi"


def test_a_tdl_file_without_the_series_is_noted_once_and_one_for_a_newer_series_says_to_upgrade(tmp_path, notes):
    bare = put(tmp_path, "Brand_Theme.tdl", "---\nTDL: 0.2\nName: Brand\n---\nTheme { Seed: \"#0B6B58\" }\n")
    load_theme(bare)
    load_theme(bare)
    assert len([n for n in notes if "Brand_Theme.tdl" in n and "Tesserae" in n and "metadata" in n]) == 1
    load_theme(put(tmp_path, "Other_Theme.tdl", THEME))
    assert not [n for n in notes if "Other_Theme.tdl" in n]  # it has the series: nothing to say
    with pytest.raises(LoadError, match="upgrade"):
        parse_view(VIEW.replace('"0.6"', '"9.9"'), "Main_View.tdl")
    with pytest.raises(LoadError, match="migrate-yaml"):
        parse_view(VIEW.replace('"0.6"', '"0.1"'), "Main_View.tdl")


# -- only the new format -----------------------------------------------------------------------------------------------------

OLD = {"view": ("Main_View.tdl", "Text { Text: <| x |> }\n"), "stylesheet": ("A_Stylesheet.tdl", "Styles { Rule { Widget: Text, Style { Gap: <| 1 |> } } }\n"),
       "theme": ("A_Theme.tdl", 'Theme { Seed: "#112233" }\n')}


def read_any(kind, path, text):
    if kind == "view":
        return parse_view(text, str(path))
    return {"stylesheet": lambda: load_stylesheet(path), "theme": lambda: load_theme(path)}[kind]()


@pytest.mark.parametrize("kind", ["view", "stylesheet", "theme"])
def test_a_tdl_file_in_language_0_1_is_refused_at_its_version_with_no_fallback(tmp_path, kind):
    name, body = OLD[kind]
    text = "---\nTDL: 0.1\nName: A\n---\n" + body
    with pytest.raises(ValueError, match=r"written in TDL 0\.1; Tesserae reads TDL 0\.2") as caught:
        read_any(kind, put(tmp_path, name, text), text)
    assert "<| expr |>" in str(caught.value)
    if kind == "stylesheet":
        with pytest.raises(LoadError, match=r"written in TDL 0\.1"):
            load_rule_sheet(tmp_path / name)


@pytest.mark.parametrize("kind", ["view", "stylesheet", "theme"])
@pytest.mark.parametrize("old", ["{{ x }}", '"{{ x }}"', '"a {{ x }} b"'])
def test_the_old_slot_in_a_0_2_file_is_a_load_error_bare_or_quoted(tmp_path, kind, old):
    name, body = OLD[kind]
    body = {"view": f"Text {{ Text: {old} }}\n", "stylesheet": f"Styles {{ Rule {{ Widget: Text, Style {{ Gap: {old} }} }} }}\n",
            "theme": f"Theme {{ Seed: {old} }}\n"}[kind]
    text = HEAD.format(name="A") + body
    with pytest.raises(ValueError, match=r"\{\{ \}\} was the TDL 0.1 form") as caught:
        read_any(kind, put(tmp_path, name, text), text)
    assert "write <| expression |>" in str(caught.value).lower()


def test_a_file_that_does_not_start_with_a_metadata_block_is_refused(tmp_path):
    with pytest.raises(LoadError, match="does not start with a metadata block"):
        parse_view("Text { Text: hi }\n", "A_View.tdl")


# -- the shipped files -------------------------------------------------------------------------------------------------------


def test_the_library_loads_the_shipped_tdl_by_default():
    assert flavour.shipped_flavour() == "tdl"
    views = shipped.shipped_views()
    assert len(views) == 61 and all(p.suffix == ".tdl" for p in views.values())
    assert shipped.shipped_sheet("Button").file.endswith("Button_Stylesheet.tdl")
    assert all(s.file.endswith(".tdl") for s in shipped.shipped_rules()) and len(shipped.shipped_rules()) == 49
    library = shipped.ViewLibrary()
    assert library.doc("Button").file.endswith("Button_View.tdl")
    assert library.paths["Button"].suffix == ".tdl"


def test_the_environment_variable_forces_the_yaml_files(monkeypatch):
    monkeypatch.setenv("TESS_UI_SHIPPED", "yaml")
    assert flavour.shipped_flavour() == "yaml" and flavour.shipped_ext() == ".yaml"
    assert all(p.suffix == ".yaml" for p in shipped.shipped_views().values()) and len(shipped.shipped_views()) == 61
    assert shipped.shipped_sheet("Button").file.endswith("Button_Stylesheet.yaml")
    assert shipped.ViewLibrary().doc("Button").file.endswith("Button_View.yaml")
    monkeypatch.setenv("TESS_UI_SHIPPED", "tdl")
    assert flavour.shipped_flavour() == "tdl"
    monkeypatch.setenv("TESS_UI_SHIPPED", "toml")
    with pytest.raises(ValueError, match="TESS_UI_SHIPPED is `tdl` or `yaml`"):
        flavour.shipped_flavour()


def test_without_tess_dl_the_shipped_yaml_is_what_loads(monkeypatch):
    monkeypatch.setattr(flavour, "tdl_available", lambda: False)
    assert flavour.shipped_flavour() == "yaml"
    assert all(p.suffix == ".yaml" for p in shipped.shipped_views().values())
    with pytest.raises(ValueError, match="needs the tess-dl package"):
        flavour.require_tdl("A_View.tdl")


def test_the_default_theme_is_the_same_dict_from_either_file(monkeypatch):
    from_tdl = shipped_default_theme()
    monkeypatch.setenv("TESS_UI_SHIPPED", "yaml")
    from_yaml = shipped_default_theme()
    assert from_tdl == from_yaml and from_tdl


# -- side by side: the two paths build the same thing ------------------------------------------------------------------------

_SKIPPED_FIELDS = {"at", "prop_at", "origin", "limits", "decl", "interaction", "text", "file"}


def canon(item):
    """A value as plain data to compare: an expression by its tree, a handler by its program, positions and files left out."""
    if isinstance(item, Expr):
        return ("expr", ast.dump(item.tree))
    if isinstance(item, Handler):
        return ("handler", item.action, _handler_form(item.source) if item.statements is not None else None)
    if dataclasses.is_dataclass(item) and not isinstance(item, type):
        return (type(item).__name__, {f.name: canon(getattr(item, f.name)) for f in dataclasses.fields(item) if f.name not in _SKIPPED_FIELDS})
    if isinstance(item, dict):
        return {k: canon(v) for k, v in item.items()}
    if isinstance(item, (list, tuple, set, frozenset)):
        return [canon(v) for v in item]
    if isinstance(item, ast.AST):
        return ast.dump(item)
    return item


def library_in(monkeypatch, flavour_name):
    monkeypatch.setenv("TESS_UI_SHIPPED", flavour_name)
    return shipped.ViewLibrary()


NAMES = sorted(shipped.shipped_views())


@pytest.mark.parametrize("name", NAMES)
def test_every_shipped_view_parses_to_the_same_tree_from_tdl_and_from_yaml(monkeypatch, name):
    from_tdl = library_in(monkeypatch, "tdl").doc(name)
    from_yaml = library_in(monkeypatch, "yaml").doc(name)
    assert from_tdl.file.endswith(".tdl") and from_yaml.file.endswith(".yaml")
    assert canon(from_tdl.root) == canon(from_yaml.root), name
    assert canon(from_tdl.params) == canon(from_yaml.params) and from_tdl.name == from_yaml.name
    assert [n.id for n in from_tdl.root.walk()] == [n.id for n in from_yaml.root.walk()]
    assert all(isinstance(n, Node) for n in from_tdl.root.walk())


def composed(library, name):
    """The lowered spec of a host that calls the shipped view `name` with no arguments, or the error it gives."""
    from tess_ui.spec.compose import Composer
    from tess_ui.spec.lower import lower

    doc = parse_view(f"widget: Container\nchildren:\n  - {{widget: {name}, name: x}}\n", "Host_View.yaml", resolver=library.decl)
    try:
        comp = Composer(library.doc, VM(), rules=library.sheets_of(library.used(doc))[0]).compose(doc)
        return canon(lower(comp.root)), comp.ids()
    except Exception as exc:  # the same view must fail the same way in both
        return type(exc).__name__, re.sub(r"^.*?_View(?:\.tdl|\.yaml)?:\d+:\d+: ", "", str(exc).split("\n")[0])  # the position is the file's own


@pytest.mark.parametrize("name", NAMES)
def test_every_shipped_view_composes_to_the_same_instance_tree_from_tdl_and_from_yaml(monkeypatch, name):
    assert composed(library_in(monkeypatch, "tdl"), name) == composed(library_in(monkeypatch, "yaml"), name), name


SAMPLE = ["Accordion", "Button", "Card", "Chip", "Dialog", "Menu", "Snackbar", "TextField", "TopAppBar", "TreeNode"]


@pytest.mark.parametrize("name", SAMPLE)
def test_a_sample_of_shipped_stylesheets_gives_the_same_rules_from_tdl_and_from_yaml(monkeypatch, name):
    monkeypatch.setenv("TESS_UI_SHIPPED", "tdl")
    from_tdl = shipped.shipped_sheet(name)
    monkeypatch.setenv("TESS_UI_SHIPPED", "yaml")
    from_yaml = shipped.shipped_sheet(name)
    assert from_tdl is not None and from_tdl.file.endswith(".tdl") and from_yaml.file.endswith(".yaml")
    assert len(from_tdl.rules) == len(from_yaml.rules)
    assert canon(from_tdl.rules) == canon(from_yaml.rules), name


def test_every_shipped_stylesheet_gives_the_same_rules_from_tdl_and_from_yaml(monkeypatch):
    monkeypatch.setenv("TESS_UI_SHIPPED", "tdl")
    from_tdl = shipped.shipped_rules()
    monkeypatch.setenv("TESS_UI_SHIPPED", "yaml")
    from_yaml = shipped.shipped_rules()
    assert [canon(s.rules) for s in from_tdl] == [canon(s.rules) for s in from_yaml] and len(from_tdl) == 49


def test_the_default_theme_gives_the_same_dict_from_tdl_and_from_yaml():
    root = Path(__file__).parent.parent / "src" / "tess_ui" / "spec"  # not named *_Theme: it is read as the shipped default is
    from tess_ui.spec.tdl_theme import load_theme_tdl
    import yaml

    tdl_file = root / "default_theme.tdl"
    assert load_theme_tdl(tdl_file.read_text(encoding="utf-8"), str(tdl_file)) == marker.strip(yaml.safe_load((root / "default_theme.yaml").read_text(encoding="utf-8")))


def test_a_named_theme_gives_the_same_dict_from_tdl_and_from_yaml(tmp_path):
    """The examples' themes have no YAML twin now, so the twin is made here: a YAML theme and the converter's TDL of it, loaded by the suffix."""
    from tess_ui.migrate_tdl_theme import convert_theme

    text = 'tesserae: 0.6\nseed: "#0B6B58"\ntypography:\n  headline_medium: {font_weight: 600}\n'
    (tmp_path / "Brand_Theme.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "Brand_Theme.tdl").write_text(convert_theme(text, "Brand", "Brand_Theme.yaml").text, encoding="utf-8")
    assert load_theme(tmp_path / "Brand_Theme.tdl") == load_theme(tmp_path / "Brand_Theme.yaml")


# -- hot reload ---------------------------------------------------------------------------------------------------------------

TDL_V1, TDL_V2 = yaml_to_tdl(V1, "Main"), yaml_to_tdl(V2, "Main")


@pytest.fixture
def opened(tmp_path):
    path = put(tmp_path, "Views/Main_View.tdl", TDL_V1)
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    return app, view, path, watcher, app.bindings.viewmodel_for("main")


def test_a_changed_tdl_view_recomposes_the_window_and_keeps_the_viewmodel(opened):
    app, view, path, watcher, vm = opened
    assert view.source == path.resolve() and path.resolve() in watcher.files
    assert watcher.poll() is False
    vm.bump()
    assert text_of(view, "label") == "Count 1"
    write(path, TDL_V2)
    assert watcher.poll() is True
    view.window.advance(16)
    assert text_of(view, "label") == "Total 1" and text_of(view, "extra") == "new"
    assert app.bindings.viewmodel_for("main") is vm
    view.window.simulate("click", view.node("root.go"))
    assert vm.clicks == 2


def test_a_tdl_mistake_leaves_the_view_as_it_was_and_names_the_line(opened):
    app, view, path, watcher, vm = opened
    write(path, TDL_V1.replace("Text {", "Textt {", 1))
    with pytest.raises(LoadError) as caught:
        watcher.poll()
    assert "Main_View.tdl" in str(caught.value) and caught.value.line > 5
    view.window.advance(16)
    assert text_of(view, "label") == "Count 0"
    write(path, TDL_V1.replace("<| count |>", "{{ count }}"))
    with pytest.raises(ValueError, match=r"TDL 0.1 form"):
        watcher.poll()
    assert text_of(view, "label") == "Count 0"


def test_the_tdl_stylesheet_beside_a_view_is_watched_and_a_change_to_it_applies(tmp_path):
    put(tmp_path, "Views/Main_View.tdl", HEAD.format(name="Main") + "Container {\n  Name: main\n  Children {\n    Stat { Name: s }\n  }\n}\n")
    put(tmp_path, "Views/Stat_View.tdl", HEAD.format(name="Stat") + "Container {\n  Style { Width: 50, Height: 20 }\n}\n")
    sheet = put(tmp_path, "Views/Stat_Stylesheet.tdl", HEAD.format(name="Stat") + "Styles {\n  Rule { Widget: Stat, Style { Corner_Radius: 3 } }\n}\n")
    app = App(root=tmp_path)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    assert view.node("root.s").get("corner_radius") == 3.0
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0],
                              sheet_files=lambda library, used: library.sheets_of(used)[1])
    assert sheet.resolve() in watcher.files
    write(sheet, sheet.read_text().replace("Corner_Radius: 3", "Corner_Radius: 9"))
    assert watcher.poll() is True
    view.window.advance(16)
    assert view.node("root.s").get("corner_radius") == 9.0


def test_the_theme_files_an_app_watches_reload_through_the_tdl_loader(tmp_path):
    theme = put(tmp_path, "Themes/Brand_Theme.tdl", THEME)
    app = App(root=tmp_path, custom_theme=theme)
    assert app._read_theme_files()[1] == {"seed": "#0B6B58"}
    write(theme, THEME.replace("#0B6B58", "#C2410C"))
    assert app._read_theme_files()[1] == {"seed": "#C2410C"}
    write(theme, THEME.replace('"#0B6B58"', "{{ x }}"))
    with pytest.raises(ValueError, match="TDL 0.1 form"):
        app._read_theme_files()


# -- the templates --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("flags", [[], ["--window"], ["--window", "--custom-title-bar"]])
def test_a_new_project_writes_tdl_views_that_load(tmp_path, flags):
    from tess_ui import cli

    assert cli.main(["new", "fresh", *flags, "--no-venv", "--dir", str(tmp_path)]) == 0
    views = sorted((tmp_path / "fresh" / "Views").iterdir())
    assert views and all(p.name.endswith("_View.tdl") for p in views), views
    library = shipped.ViewLibrary(Project(tmp_path / "fresh").index("view"))
    for path in views:
        doc = library.parse(path)
        assert doc.file.endswith(".tdl") and doc.root is not None


def test_add_screen_writes_a_tdl_view_and_the_window_one_a_node_line_that_reads(tmp_path, capsys):
    from tess_ui import cli

    assert cli.main(["new", "fresh", "--no-venv", "--dir", str(tmp_path)]) == 0
    assert cli.main(["add", "screen", "My Screen".replace(" ", ""), "--dir", str(tmp_path / "fresh")]) == 0
    screen = tmp_path / "fresh" / "Views" / "MyScreen_View.tdl"
    assert screen.is_file() and shipped.ViewLibrary().parse(screen).root.name == "MyScreen"
    assert 'app.open_view("MyScreen")' in (tmp_path / "fresh" / "app.py").read_text()
    assert cli.main(["new", "win", "--window", "--no-venv", "--dir", str(tmp_path)]) == 0
    assert cli.main(["add", "screen", "Extra", "--dir", str(tmp_path / "win")]) == 0
    out = capsys.readouterr().out
    assert 'Extra { Name: extra, Route: "extra", Style { Flex: fill } }' in out and (tmp_path / "win" / "Views" / "Extra_View.tdl").is_file()


def test_the_template_files_are_tdl_and_no_yaml_template_is_left():
    folder = Path(project_module.__file__).parent / "templates"
    assert sorted(p.name for p in folder.glob("*_View.*")) == ["Main_View.tdl.tmpl", "Screen_View.tdl.tmpl", "WindowMain_View.tdl.tmpl",
                                                                  "WindowScreen_View.tdl.tmpl", "Window_View.tdl.tmpl"]
