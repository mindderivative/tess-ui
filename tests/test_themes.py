"""M29 Phase 4: Tesserae reads theme, stylesheet and font files itself
and hands `tess_re` only dicts (`*_spec=`, tess_re M86) and bytes
(`tess_re.register_font`).

A theme's or stylesheet's effect is observed through `corner_radius`,
which both can set via `styles:` and `Node.get` can read back.
"""

import os
import warnings
from pathlib import Path

import pytest
import tess_re

import tess_ui
import tess_ui.fonts as fonts
from tess_ui.fonts import FontFallbackWarning, available_families
from tess_ui import App, ViewModel
from tess_ui.spec import load_stylesheet, load_theme

SEED = (0x67, 0x50, 0xA4, 0xFF)
RECT_VIEW = '---\nTDL: 0.2\nName: box\n---\nRect { Name: box, Style { Width: 10, Height: 10, Background: "#112233" } }\n'
_FONT = Path("crates") / "engine-render" / "assets" / "fonts" / "Roboto-Regular.ttf"
# A real font file from tess_re's source tree: next to tess_re itself when it's
# installed from a checkout (as on CI), or wherever TESS_RE_SOURCE_DIR points
# when tess_re is an installed wheel (the wheel ships no .ttf files).
ROBOTO = next(
    (p for p in (Path(os.environ["TESS_RE_SOURCE_DIR"]) / _FONT if "TESS_RE_SOURCE_DIR" in os.environ else None,
                 Path(tess_re.__file__).parents[2] / _FONT) if p is not None and p.is_file()),
    Path(tess_re.__file__).parents[2] / _FONT,
)


class BoxViewModel(ViewModel):
    views = "box"


@pytest.fixture(autouse=True)
def _fresh_font_registry(monkeypatch):
    monkeypatch.setattr(fonts, "_registered", set())


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _view(tmp_path: Path, text: str = RECT_VIEW) -> Path:
    return _write(tmp_path / "Views" / "Box_View.tdl", text)


# -- load_theme / load_stylesheet -------------------------------------


def _tdl(body: str, name: str = "X") -> str:
    """A theme, stylesheet or view file's text: the metadata block, then `body`."""
    return f"---\nTDL: 0.2\nName: {name}\n---\n{body}"


def test_an_unknown_key_in_a_theme_file_is_found_when_it_is_read_and_names_the_file(tmp_path: Path):
    path = _write(tmp_path / "Brand_Theme.tdl", _tdl('Theme { Colours { Primary: "#00FF00" } }\n', "Brand"))
    with pytest.raises(ValueError, match=r"Brand_Theme\.tdl:5:9: error: unknown field `colours`, expected one of `seed`"):
        load_theme(path)


def test_load_theme_reads_a_mapping(tmp_path: Path):
    theme = _write(tmp_path / "T_Theme.tdl", _tdl('Theme { Colors { Primary: "#00FF00" }, Dark: true }\n'))
    assert load_theme(theme) == {"colors": {"primary": "#00FF00"}, "dark": True}


def test_an_empty_theme_file_is_an_empty_theme(tmp_path: Path):
    assert load_theme(_write(tmp_path / "T_Theme.tdl", _tdl("Theme { }\n"))) == {}


@pytest.mark.parametrize(
    "body, match",
    [("Styles { }\n", "this looks like a stylesheet: name it bad_Stylesheet.tdl"), ("Theme { Colors {\n", "This block is never closed"),
     ("Theme: 3\n", "This text is not valid here")],
)
def test_bad_theme_files_are_named_in_the_error(tmp_path: Path, body, match):
    theme = _write(tmp_path / "bad_Theme.tdl", _tdl(body))
    with pytest.raises(ValueError, match=rf"bad_Theme\.tdl:.*{match}"):
        load_theme(theme)


def test_load_stylesheet_reads_a_mapping(tmp_path: Path):
    sheet = _write(tmp_path / "S_Stylesheet.tdl", _tdl("Styles { Rule { Widget: Rect, Style { Corner_Radius: 8 } } }\n"))
    assert load_stylesheet(sheet) == {"styles": [{"widget": "Rect", "style": {"corner_radius": 8}}]}


# -- an app and its theme and stylesheet files --------------------------------


def _app(tmp_path: Path, **kwargs) -> tuple[App, object]:
    """An app on `tmp_path` with the view `Box` (one Rect) opened."""
    app = App(root=tmp_path, theme_seed=SEED, **kwargs)
    app.bind(BoxViewModel)
    return app, app.open_view("Box")


def test_an_app_reads_theme_and_stylesheet_files(tmp_path: Path):
    """Tesserae reads both files; the view is built from what they say."""
    _view(tmp_path)
    theme = _write(tmp_path / "Theme_Theme.tdl", _tdl('Theme { Colors { Primary: "#00FF00" } }\n', "Theme"))
    sheet = _write(tmp_path / "Sheet_Stylesheet.tdl", _tdl("Styles { Rule { Widget: Rect, Style { Corner_Radius: 8 } } }\n", "Sheet"))
    app, view = _app(tmp_path, custom_theme=theme, stylesheet=sheet)
    assert view.node("root").get("corner_radius") == 8.0
    assert app._view_theme()["custom_theme_spec"] == {"colors": {"primary": "#00FF00"}}


def test_a_theme_file_really_applies(tmp_path: Path):
    _view(tmp_path)
    theme = _write(tmp_path / "Theme_Theme.tdl", _tdl("Theme { Styles { Item { Kind: Rect, Style { Corner_Radius: 12 } } } }\n", "Theme"))
    _, view = _app(tmp_path, default_theme=theme)
    assert view.node("root").get("corner_radius") == 12.0


def test_a_spec_dict_still_passes_straight_through(tmp_path: Path):
    _view(tmp_path)
    _, view = _app(tmp_path, stylesheet_spec={"styles": [{"widget": "Rect", "style": {"corner_radius": 5}}]})
    assert view.node("root").get("corner_radius") == 5.0


def test_giving_both_a_theme_file_and_its_spec_is_an_error(tmp_path: Path):
    theme = _write(tmp_path / "Theme_Theme.tdl", _tdl("Theme { }\n", "Theme"))
    with pytest.raises(ValueError, match="custom_theme= or custom_theme_spec=, not both"):
        App(root=tmp_path, custom_theme=theme, custom_theme_spec={})


def test_a_bad_key_in_a_theme_file_names_the_theme_file(tmp_path: Path):
    theme = _write(tmp_path / "Theme_Theme.tdl", _tdl('Theme { Colours { Primary: "#00FF00" } }\n', "Theme"))
    with pytest.raises(ValueError, match=r"Theme_Theme\.tdl:5:9: error: unknown field `colours`"):
        App(root=tmp_path, theme_seed=SEED, custom_theme=theme)


def test_set_theme_specs_takes_a_loaded_theme(tmp_path: Path):
    _view(tmp_path)
    app, view = _app(tmp_path)
    theme = _write(tmp_path / "Round_Theme.tdl", _tdl("Theme { Styles { Item { Kind: Rect, Style { Corner_Radius: 20 } } } }\n", "Round"))
    app.set_theme_specs(None, load_theme(theme))
    assert view.node("root").get("corner_radius") == 20.0


# -- fonts -------------------------------------------------------------


@pytest.mark.skipif(not ROBOTO.is_file(), reason="needs a real font file from tess_re's source tree -- set TESS_RE_SOURCE_DIR (runs on CI)")
def test_register_font_hands_tre_the_bytes_and_returns_families():
    assert tess_ui.register_font(ROBOTO) == ["Roboto"]


def test_register_font_records_a_new_family(tmp_path: Path, monkeypatch):
    font = tmp_path / "Inter.ttf"
    font.write_bytes(b"pretend font bytes")
    received = []
    monkeypatch.setattr(tess_re, "register_font", lambda data: received.append(data) or ["Inter"])

    assert tess_ui.register_font(font) == ["Inter"]
    assert received == [b"pretend font bytes"]
    assert "Inter" in available_families()


def test_register_font_rejects_a_file_with_no_font_faces(tmp_path: Path):
    junk = tmp_path / "junk.ttf"
    junk.write_bytes(b"definitely not a font")
    with pytest.raises(ValueError, match=r"junk\.ttf: .*no font faces"):
        tess_ui.register_font(junk)


def test_register_font_missing_file_raises_oserror(tmp_path: Path):
    with pytest.raises(OSError):
        tess_ui.register_font(tmp_path / "nope.ttf")


def test_a_theme_naming_an_unavailable_font_warns(tmp_path: Path):
    theme = _write(tmp_path / "Inter_Theme.tdl", _tdl("Theme { Typography { Body_Large { Font_Family: Inter } } }\n", "Inter"))
    with pytest.warns(FontFallbackWarning, match=r"Inter_Theme\.tdl: font_family 'Inter' is not bundled or registered"):
        load_theme(theme)


def test_a_bundled_or_registered_font_does_not_warn(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(tess_re, "register_font", lambda data: ["Inter"])
    font = tmp_path / "Inter.ttf"
    font.write_bytes(b"x")
    tess_ui.register_font(font)
    theme = _write(
        tmp_path / "Ok_Theme.tdl",
        _tdl("Theme {\n  Typography {\n    Body_Large { Font_Family: Inter }\n    Label_Large { Font_Family: Roboto }\n  }\n}\n", "Ok"),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", FontFallbackWarning)
        load_theme(theme)
