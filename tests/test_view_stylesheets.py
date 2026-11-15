"""#274: a view's stylesheet (`<Name>_Stylesheet.tdl`) is read when the view is used by the application, and not otherwise. Shipped ones and a project's own: a
sheet of a view nothing calls costs nothing (it is not even parsed)."""

import os

import pytest

from tess_ui import App, ViewModel
from tess_ui import shipped
from tess_ui.spec.watch import ComposedWatcher


class VM(ViewModel):
    views = "main"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def bump(path):
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))


META = "---\nTDL: 0.2\nName: {}\n---\n"
MAIN_PLAIN = META.format("main") + """Container {
  Name: main
  Style { Width: 300, Height: 200, Background: surface }
  Children {
    Text { Name: t, Text: hi, Typography_Role: body_large, Style { Foreground: on_surface } }
"""
CLOSE = "  }\n}\n"
MAIN_BUTTON = MAIN_PLAIN + "    Button { Name: b, Label: Go }\n" + CLOSE
CALLS_CARD = MAIN_PLAIN + "    Card { Name: c }\n" + CLOSE
STAT_CALL = MAIN_PLAIN + "    Stat { Name: s }\n" + CLOSE
MAIN_PLAIN_VIEW = MAIN_PLAIN + CLOSE
CARD = META.format("Card") + "Container {\n  Params { }\n  Children {\n    Button { Name: b, Label: Go }\n  }\n}\n"
STAT = META.format("Stat") + "Container { Style { Width: 50, Height: 20 } }\n"


def sheet(widget, radius, **selectors):
    rule = ", ".join([f"Widget: {widget}", *[f"{k.title()}: {v}" for k, v in selectors.items()]])
    return META.format("Stat") + f"Styles {{\n  Rule {{ {rule}, Style {{ Corner_Radius: {radius} }} }}\n}}\n"


@pytest.fixture
def loads(monkeypatch):
    """The stylesheets read, by file name."""
    seen = []
    real = shipped.load_rule_sheet
    monkeypatch.setattr(shipped, "load_rule_sheet", lambda path, **kw: seen.append(os.path.basename(str(path))) or real(path, **kw))
    monkeypatch.setattr(shipped, "_SHEETS", {})  # a fresh cache: each test sees what its own app reads
    return seen


def opened(tmp_path, main, files=None, **kwargs):
    write(tmp_path / "Views" / "Main_View.tdl", main)
    for name, text in (files or {}).items():
        write(tmp_path / name, text)
    app = App(root=tmp_path, width=300, height=200, **kwargs)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(600)
    return app, view


def test_a_shipped_stylesheet_is_read_only_for_a_widget_the_app_uses(tmp_path, loads):
    opened(tmp_path, MAIN_PLAIN_VIEW)
    assert "Button_Stylesheet.tdl" not in loads and not [n for n in loads if n != "Text_Stylesheet.tdl"]


def test_the_stylesheet_of_a_widget_that_is_used_is_read(tmp_path, loads):
    opened(tmp_path, MAIN_BUTTON)
    assert "Button_Stylesheet.tdl" in loads and "Card_Stylesheet.tdl" not in loads


def test_a_widget_used_through_a_view_it_calls_counts(tmp_path, loads):
    opened(tmp_path, CALLS_CARD, {"Views/Card_View.tdl": CARD})
    assert "Button_Stylesheet.tdl" in loads


def test_a_widget_used_two_views_down_counts(tmp_path, loads):
    opened(tmp_path, MAIN_PLAIN + "    Outer { Name: o }\n" + CLOSE,
           {"Views/Outer_View.tdl": META.format("Outer") + "Container {\n  Children {\n    Card { Name: c }\n  }\n}\n", "Views/Card_View.tdl": CARD})
    assert "Button_Stylesheet.tdl" in loads


def test_a_view_that_is_in_the_project_but_never_called_adds_nothing(tmp_path, loads):
    broken = META.format("Stat") + "Styles {\n"  # would raise if it were read
    opened(tmp_path, MAIN_PLAIN_VIEW, {"Views/Stat_View.tdl": STAT, "Views/Stat_Stylesheet.tdl": broken})
    assert "Stat_Stylesheet.tdl" not in loads


def test_a_project_stylesheet_beside_a_used_view_applies(tmp_path):
    app, view = opened(tmp_path, STAT_CALL, {"Views/Stat_View.tdl": STAT.replace("Container", "Container"),
                                                                                  "Views/Stat_Stylesheet.tdl": sheet("Stat", 9)})
    assert view.node("root.s").get("corner_radius") == 9.0


def test_a_project_stylesheet_in_the_styles_folder_applies_by_name(tmp_path):
    app, view = opened(tmp_path, STAT_CALL, {"Views/Stat_View.tdl": STAT, "Styles/Stat_Stylesheet.tdl": sheet("Stat", 7)})
    assert view.node("root.s").get("corner_radius") == 7.0


def test_a_used_project_stylesheet_with_a_mistake_is_an_error_naming_the_file(tmp_path):
    with pytest.raises(Exception) as caught:
        opened(tmp_path, STAT_CALL, {"Views/Stat_View.tdl": STAT, "Views/Stat_Stylesheet.tdl": META.format("Stat") + "Styles {\n  Rule { Widget: Stat, Style { Corner_Radiuss: 1 } }\n}\n"})
    assert "Stat_Stylesheet.tdl" in str(caught.value)


def test_the_apps_stylesheet_beats_a_views(tmp_path):
    app, view = opened(tmp_path, STAT_CALL, {"Views/Stat_View.tdl": STAT, "Views/Stat_Stylesheet.tdl": sheet("Stat", 9)},
                       stylesheet_spec={"styles": [{"widget": "Stat", "style": {"corner_radius": 3}}]})
    assert view.node("root.s").get("corner_radius") == 3.0


def test_a_project_view_that_replaces_a_shipped_one_has_its_own_sheet_and_not_the_shipped(tmp_path, loads):
    app, view = opened(tmp_path, MAIN_BUTTON, {"Views/Button_View.tdl": META.format("Button") + "Container {\n  Params { Label { Type: str } }\n  Style { Width: 60, Height: 30 }\n}\n",
                                               "Views/Button_Stylesheet.tdl": sheet("Button", 5)})
    assert view.node("root.b").get("corner_radius") == 5.0
    assert loads.count("Button_Stylesheet.tdl") == 1  # the project's one, and not also the shipped
    assert not [r for sheet in shipped._SHEETS.values() if sheet is not None for r in sheet.rules if r.widget == "Button"]  # the shipped sheet was never read


def test_the_apps_own_stylesheet_is_not_read_again_as_a_views(tmp_path, loads):
    """`Styles/Main_Stylesheet.tdl` given as `App(stylesheet="Main")` is the app's, though a view called `main` is there too."""
    write(tmp_path / "Styles" / "Stat_Stylesheet.tdl", sheet("Stat", 4))
    app, view = opened(tmp_path, STAT_CALL, {"Views/Stat_View.tdl": STAT}, stylesheet="Stat")
    assert loads.count("Stat_Stylesheet.tdl") == 0 and view.node("root.s").get("corner_radius") == 4.0  # the app read it, the library did not


def test_a_view_the_file_starts_to_call_gets_its_sheet_on_reload(tmp_path):
    app, view = opened(tmp_path, MAIN_PLAIN_VIEW, {"Views/Stat_View.tdl": STAT, "Views/Stat_Stylesheet.tdl": sheet("Stat", 9)})
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    assert (tmp_path / "Views" / "Stat_Stylesheet.tdl").resolve() not in watcher.files
    main = tmp_path / "Views" / "Main_View.tdl"
    main.write_text(STAT_CALL)
    bump(main)
    assert watcher.poll() is True
    view.window.advance(600)
    assert view.node("root.s").get("corner_radius") == 9.0
    assert (tmp_path / "Views" / "Stat_Stylesheet.tdl").resolve() in watcher.files


def test_editing_a_used_stylesheet_reloads_the_view(tmp_path):
    app, view = opened(tmp_path, STAT_CALL, {"Views/Stat_View.tdl": STAT, "Views/Stat_Stylesheet.tdl": sheet("Stat", 9)})
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    path = tmp_path / "Views" / "Stat_Stylesheet.tdl"
    assert path.resolve() in watcher.files
    path.write_text(sheet("Stat", 2))
    bump(path)
    assert watcher.poll() is True
    view.window.advance(600)
    assert view.node("root.s").get("corner_radius") == 2.0


def test_every_shipped_sheet_belongs_to_one_widget(tmp_path):
    """The premise of reading a sheet by the name of the widget that uses it."""
    from tess_ui.spec.tdl_stylesheet import load_tdl_stylesheet_file

    for path in sorted(shipped.SHIPPED.glob("*_Stylesheet.tdl")):
        stem = path.name.removesuffix("_Stylesheet.tdl")
        assert {r.get("widget") for r in load_tdl_stylesheet_file(path)["styles"]} == {stem}, path.name
