"""M30: `App`'s app-wide theme and per-screen stylesheets.

The theme is set once on `App(...)` and applies to every screen the app
opens (a theme is window-level in `tess_re`); `stylesheet=` on `App(...)`
is every screen's default. Files are read once, by Tesserae; `tess_re` gets
dicts.

Effects are observed through `elevation`/`corner_radius`, which a
theme's or stylesheet's `styles:` can set and `Node.get` reads back.
"""

import warnings
from pathlib import Path

import pytest

from helpers import elevation

import tess_ui.fonts as fonts
from tess_ui import App
from tess_ui.fonts import FontFallbackWarning

SEED = (0x67, 0x50, 0xA4, 0xFF)
HEADER = "---\nTDL: 0.2\nName: {name}\n---\n"


@pytest.fixture(autouse=True)
def _fresh_font_registry(monkeypatch):
    monkeypatch.setattr(fonts, "_registered", set())


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _fields(style) -> str:
    return ", ".join(f"{k.title()}: {v}" for k, v in style.items())


def _theme_rule(**style) -> str:
    """A theme file whose `Styles` list has one rule for every Rect."""
    return HEADER.format(name="brand") + f"Theme {{ Styles {{ Item {{ Kind: Rect, Style {{ {_fields(style)} }} }} }} }}\n"


def _sheet_rule(**style) -> str:
    """A stylesheet file with one rule for every Rect."""
    return HEADER.format(name="default") + f"Styles {{ Rule {{ Widget: Rect, Style {{ {_fields(style)} }} }} }}\n"


def _screens(tmp_path: Path, *names: str) -> None:
    """One `Views/<name>_View.tdl` of a single Rect for each name."""
    for name in names:
        _write(tmp_path / "Views" / f"{name}_View.tdl", HEADER.format(name=name) + 'Rect { Style { Width: 10, Height: 10, Background: "#112233" } }\n')


def _look(view):
    node = view.node("root")
    return elevation(node), node.get("corner_radius")


def test_an_app_wide_theme_reaches_every_opened_screen(tmp_path: Path):
    theme = _write(tmp_path / "brand_Theme.tdl", _theme_rule(elevation=3))
    _screens(tmp_path, "Home", "Settings")
    app = App(root=tmp_path, theme_seed=SEED, custom_theme=theme)
    a, b = app.open_view("Home"), app.open_view("Settings")
    assert _look(a)[0] == _look(b)[0] == 3.0


def test_a_default_theme_file_applies_too(tmp_path: Path):
    base = _write(tmp_path / "base_Theme.tdl", _theme_rule(corner_radius=6))
    _screens(tmp_path, "Home")
    app = App(root=tmp_path, theme_seed=SEED, default_theme=base)
    assert _look(app.open_view("Home"))[1] == 6.0


def test_the_default_stylesheet_applies_to_every_screen(tmp_path: Path):
    default = _write(tmp_path / "default_Stylesheet.tdl", _sheet_rule(corner_radius=8))
    _screens(tmp_path, "Home", "Settings")
    app = App(root=tmp_path, theme_seed=SEED, stylesheet=default)
    assert _look(app.open_view("Home"))[1] == 8.0
    assert _look(app.open_view("Settings"))[1] == 8.0


def test_spec_forms_work_the_same_as_files(tmp_path: Path):
    _screens(tmp_path, "Home")
    app = App(
        root=tmp_path,
        theme_seed=SEED,
        custom_theme_spec={"styles": [{"kind": "Rect", "style": {"elevation": 2}}]},
        stylesheet_spec={"styles": [{"widget": "Rect", "style": {"corner_radius": 4}}]},
    )
    assert _look(app.open_view("Home")) == (2.0, 4.0)


@pytest.mark.parametrize("arg", ["default_theme", "custom_theme", "stylesheet"])
def test_a_file_and_its_spec_together_is_an_error(tmp_path: Path, arg):
    file = _write(tmp_path / "x_Theme.tdl", HEADER.format(name="x") + "Theme { }\n")
    with pytest.raises(ValueError, match=rf"App: pass {arg}= or {arg}_spec=, not both"):
        App(**{arg: file, f"{arg}_spec": {}})


def test_screens_are_built_in_the_apps_window_with_the_theme_and_stylesheet_it_read(tmp_path: Path):
    """M37: `App` builds its screens itself, in its own window, from the theme and stylesheet it read; `tess_re` gets nodes,
    never files or dicts."""
    theme = _write(tmp_path / "brand_Theme.tdl", _theme_rule(elevation=3))
    sheet = _write(tmp_path / "default_Stylesheet.tdl", _sheet_rule(corner_radius=8))
    _screens(tmp_path, "Home")
    app = App(root=tmp_path, theme_seed=SEED, dark=True, custom_theme=theme, stylesheet=sheet)
    view = app.open_view("Home")
    assert view.window is app.show("Home")
    assert _look(view) == (3.0, 8.0)


def test_theme_files_are_read_once_so_a_font_warning_fires_once(tmp_path: Path):
    theme = _write(tmp_path / "inter_Theme.tdl", HEADER.format(name="inter") + "Theme { Typography { Body_Large { Font_Family: Inter } } }\n")
    _screens(tmp_path, "Home", "Settings", "About")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        app = App(root=tmp_path, theme_seed=SEED, custom_theme=theme)
        for name in ("Home", "Settings", "About"):
            app.open_view(name)
    assert sum(issubclass(w.category, FontFallbackWarning) for w in caught) == 1


def test_an_app_with_no_theme_arguments_has_no_theme_rules(tmp_path: Path):
    _screens(tmp_path, "Home")
    app = App(root=tmp_path)
    assert _look(app.open_view("Home")) == (0.0, 0.0)
