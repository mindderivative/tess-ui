"""A name finds a TDL file, the loaders read only TDL (a YAML file is refused with where to go from there), only the TDL 0.2 language is accepted, and a
changed `.tdl` is hot-reloaded."""

from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front ends need tess_dl (Python 3.14)")

from loguru import logger  # noqa: E402

from tess_ui import App  # noqa: E402
from tess_ui import project as project_module  # noqa: E402
from tess_ui import shipped  # noqa: E402
from tess_ui.project import (  # noqa: E402
    Project, ProjectError, is_view_file, kind_of_tdl, looks_like_kind, sibling_file, tdl_wrong_kind, view_stem, yaml_refused,
)
from tess_ui.spec.build import shipped_default_theme  # noqa: E402
from tess_ui.spec.nodes import LoadError, parse_view  # noqa: E402
from tess_ui.spec.rules import load_rule_sheet  # noqa: E402
from tess_ui.spec.themes import load_stylesheet, load_theme  # noqa: E402
from tess_ui.spec.watch import ComposedWatcher  # noqa: E402
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


def test_a_name_in_two_places_is_an_error_naming_both(tmp_path):
    put(tmp_path, "Views/Old_View.tdl")
    put(tmp_path, "more/Old_View.tdl")
    with pytest.raises(ProjectError, match=r"Old_View.tdl is in two places, Views.Old_View.tdl and more.Old_View.tdl"):
        Project(tmp_path, search=["more"]).find("view", "Old")


@pytest.mark.parametrize("kind, folder, name", [("view", "Views", "Old_View.yaml"), ("theme", "Themes", "Old_Theme.yaml"),
                                                  ("stylesheet", "Styles", "Old_Stylesheet.yaml")])
def test_a_yaml_file_is_not_found_and_the_message_says_where_to_go(tmp_path, kind, folder, name):
    put(tmp_path, f"{folder}/{name}")
    with pytest.raises(ProjectError) as raised:
        Project(tmp_path).find(kind, "Old")
    text = str(raised.value)
    assert f"found {folder}/{name}: {name}: Tesserae no longer reads YAML files" in text
    assert "tesserae-ui<0.6.1" in text and "docs/migration.md" in text


def test_a_recursive_project_finds_a_tdl_view_anywhere(tmp_path):
    put(tmp_path, "deep/er/Main_View.tdl")
    assert Project(tmp_path, recursive=True).find("view", "Main") == tmp_path / "deep" / "er" / "Main_View.tdl"


def test_a_tdl_file_in_the_wrong_folder_is_found_and_named(tmp_path):
    put(tmp_path, "Themes/Extra_View.tdl")
    with pytest.raises(ProjectError) as raised:
        Project(tmp_path).find("view", "Extra")
    text = str(raised.value)
    assert text.startswith("no view called 'Extra' (Extra_View.tdl) in ")  # the message that was there, first and unchanged
    assert "found Themes/Extra_View.tdl: views are read from Views/ (or add Themes to App(search=[...]))" in text
    put(tmp_path, "Views/Brand_Theme.tdl")
    with pytest.raises(ProjectError, match=r"found Views/Brand_Theme.tdl, a theme, not a view"):
        Project(tmp_path).find("view", "Brand")


def test_names_and_suffix_helpers(tmp_path):
    assert view_stem("a/Main_View.tdl") == "Main" and view_stem(Path("Main_View.yaml")) == "Main_View.yaml" and view_stem("Other.txt") == "Other.txt"
    assert is_view_file("Main_View.tdl") and not is_view_file("Main_View.yaml") and not is_view_file("Main_Theme.tdl")
    assert yaml_refused("a/Main_View.yaml").startswith("Main_View.yaml: Tesserae no longer reads YAML files") and yaml_refused("Main_View.yml") is not None
    assert yaml_refused("Main_View.tdl") is None
    put(tmp_path, "Main_View.tdl")
    assert sibling_file(tmp_path / "Main_View.tdl", "view", "Main") == tmp_path / "Main_View.tdl"
    assert sibling_file(tmp_path / "Main_View.tdl", "view", "Nope") is None


def test_every_loader_refuses_a_yaml_path_with_the_one_message(tmp_path):
    view = put(tmp_path, "Main_View.yaml", "widget: Text\n")
    sheet = put(tmp_path, "Brand_Stylesheet.yaml", "styles: []\n")
    theme = put(tmp_path, "Brand_Theme.yaml", "seed: '#0B6B58'\n")
    with pytest.raises(LoadError, match="Tesserae no longer reads YAML files"):
        parse_view(view.read_text(), str(view))
    with pytest.raises(LoadError, match="Tesserae no longer reads YAML files"):
        load_rule_sheet(sheet)
    for loader, path in ((load_stylesheet, sheet), (load_theme, theme)):
        with pytest.raises(ValueError, match="Tesserae no longer reads YAML files.*tesserae-ui<0.6.1"):
            loader(path)
    app = App(root=tmp_path)
    with pytest.raises(LoadError, match="Tesserae no longer reads YAML files"):
        app.open_view(view)


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


def test_the_hint_names_the_file_to_give():
    assert looks_like_kind("theme", "stylesheet", "Brand_Stylesheet.tdl") == "this looks like a theme: name it Brand_Theme.tdl"
    assert looks_like_kind("view", "theme", "") == "this looks like a view: name it <Name>_View.tdl"
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


def test_the_default_theme_is_the_same_dict_from_either_file(monkeypatch):
    from_tdl = shipped_default_theme()
    monkeypatch.setenv("TESS_UI_SHIPPED", "yaml")
    from_yaml = shipped_default_theme()
    assert from_tdl == from_yaml and from_tdl


# -- side by side: the two paths build the same thing ------------------------------------------------------------------------

_SKIPPED_FIELDS = {"at", "prop_at", "origin", "limits", "decl", "interaction", "text", "file"}


def library_in(monkeypatch, flavour_name):
    monkeypatch.setenv("TESS_UI_SHIPPED", flavour_name)
    return shipped.ViewLibrary()


NAMES = sorted(shipped.shipped_views())


SAMPLE = ["Accordion", "Button", "Card", "Chip", "Dialog", "Menu", "Snackbar", "TextField", "TopAppBar", "TreeNode"]


# -- hot reload ---------------------------------------------------------------------------------------------------------------

TDL_V1, TDL_V2 = V1, V2  # test_hot_reload_composed writes its views in TDL


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
