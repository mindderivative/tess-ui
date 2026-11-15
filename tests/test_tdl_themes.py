"""A theme in TDL (`src/tess_ui/spec/tdl_theme.py`) loads to the mapping `check_theme` and `Theme` take, and every error of a theme points into the `.tdl`
file (the shape is in `design/tdl-views.md`)."""

from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front end needs tess_dl (Python 3.14)")

from tess_ui.spec.cascade import check_theme  # noqa: E402
from tess_ui.spec.nodes import LoadError, PMap  # noqa: E402
from tess_ui.spec.tdl_theme import THEME_KEYS, load_marked_theme_tdl, load_theme_tdl  # noqa: E402
from tess_ui.spec.themes import load_theme  # noqa: E402

ROOT = Path(__file__).parent.parent
REAL = [ROOT / "src" / "tess_ui" / "spec" / "default_theme.tdl", *sorted(ROOT.joinpath("examples").rglob("*_Theme.tdl"))]


HEAD = '---\nTDL: 0.2\nName: T\nTesserae: "0.6"\n---\n'


def load(body, head=HEAD):
    return load_theme_tdl(head + body, "T_Theme.tdl")


def fails(body, head=HEAD):
    with pytest.raises(LoadError) as exc:
        load(body, head)
    return exc.value


def test_a_syntax_error_is_at_its_line_and_column():
    err = fails('Theme {\n  Seed: "#0B6B58"\n  Colors { Primary red }\n}\n')
    assert err.file == "T_Theme.tdl" and err.line == 8
    assert "T_Theme.tdl:8:" in str(err) and "^" in err.render()


def test_a_key_that_is_not_title_case_says_what_to_write():
    err = fails("Theme {\n  Colors {\n    on_primary: red\n  }\n}\n")
    assert (err.line, err.column) == (8, 4) and "write 'On_Primary'" in err.hint


def test_a_key_a_theme_does_not_have_is_named_with_its_position_and_a_suggestion():
    err = fails("Theme {\n  Seed: red\n  Colours { Primary: red }\n}\n")
    assert (err.line, err.column) == (8, 2)
    assert "unknown field `colours`, expected one of `seed`, `dark`, `colors`, `styles`, `components`, `typography`" in err.message
    assert "did you mean 'colors'" in err.hint


def test_the_root_must_be_theme():
    err = fails("Colors { Primary: red }\n")
    assert (err.line, err.column) == (6, 0) and "Theme block" in err.message and "Theme {" in err.hint


def test_a_duplicate_key_and_a_wrapper_are_errors():
    assert "already used" in fails("Theme {\n  Seed: red\n  Seed: blue\n}\n").message
    err = fails("Theme {\n  If <| true |> { Colors { A: red } }\n}\n")
    assert "wraps a node" in err.message and err.line == 7


def test_the_metadata_is_checked_as_in_a_view():
    err = fails("Theme { Seed: red }\n", HEAD.replace('"0.6"', '"0.9"'))
    assert "0.9" in err.message and err.line == 4
    assert "no metadata key" in fails("Theme { }\n", HEAD.replace('Tesserae: "0.6"', 'Title: T\nTesserae: "0.6"')).message


def test_a_stray_property_in_components_is_read_as_the_key_and_a_wrapper_is_refused():
    assert load("Theme { Components { Card: 8 } }\n")["components"] == {"card": 8}
    assert "wraps a node" in fails("Theme { Components { For x In <| y |> Key <| x |> { Card { } } } }\n").message


def test_positions_are_on_every_level():
    data = load_marked_theme_tdl(HEAD + 'Theme {\n  Seed: "#0B6B58"\n  Colors {\n    Primary: red\n  }\n}\n', "T.tdl")
    assert isinstance(data, PMap) and data.at == (6, 0)
    assert data.key_at["seed"] == (7, 2) and data.val_at["seed"] == (7, 9)  # a quoted value is positioned after its quote, as in YAML
    assert data["colors"].key_at["primary"] == (9, 4) and data.key_at["colors"] == (8, 2)


# -- (g) what the converter refuses --------------------------------------------------------------------------------------------


# -- (h) the file loader ------------------------------------------------------------------------------------------------------


# -- (i) the command ----------------------------------------------------------------------------------------------------------


# -- the themes that exist -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", REAL, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_every_real_theme_loads_and_checks(path):
    theme = load_theme_tdl(path.read_text(encoding="utf-8"), path.name)
    check_theme(theme, path.name)
    assert not set(theme) - set(THEME_KEYS)
    assert load_theme(path) == theme


# -- every key the loader takes -------------------------------------------------------------------------------------------------

EVERYTHING = """Theme {
  Seed: "#0B6B58"
  Dark: true
  Colors { Primary: "#112233", On_Primary: white, Surface: "#FFFFFF80", Tertiary: primary }
  Typography {
    Display_Large { Font_Family: Inter, Font_Weight: 700, Font_Size: 57, Line_Height: 64, Tracking: -0.25 }
    Body_Large { Font_Family: "Segoe UI Variable", Font_Size: 17 }
    Label_Small { Tracking: 0.5 }
  }
  Components { Card { Corner_Radius: 12 } }
}
"""


def test_a_theme_with_every_key_loads_to_the_mapping_check_theme_takes():
    theme = load(EVERYTHING)
    assert theme == {
        "seed": "#0B6B58", "dark": True,
        "colors": {"primary": "#112233", "on_primary": "white", "surface": "#FFFFFF80", "tertiary": "primary"},
        "typography": {"display_large": {"font_family": "Inter", "font_weight": 700, "font_size": 57, "line_height": 64, "tracking": -0.25},
                       "body_large": {"font_family": "Segoe UI Variable", "font_size": 17}, "label_small": {"tracking": 0.5}},
        "components": {"card": {"corner_radius": 12}},
    }
    check_theme(theme)


def test_an_empty_theme_is_an_empty_mapping_and_values_keep_their_types():
    assert load("Theme { }\n") == {}
    theme = load("Theme { Dark: false, Seed: \"#112233\", Typography { Body_Large { Font_Size: 17, Tracking: 0.5 } } }\n")
    assert theme["dark"] is False and theme["typography"]["body_large"] == {"font_size": 17, "tracking": 0.5}


def test_a_component_with_fields_and_variants_is_one_block_and_comes_back_as_two_keys():
    theme = load("Theme { Components { Card { Corner_Radius: 12, Elevated { Elevation: 1 } } } }\n")
    assert theme["components"] == {"card": {"corner_radius": 12}, "card.elevated": {"elevation": 1}}


def test_variants_without_a_component_of_their_own_are_just_the_variants():
    theme = load("Theme { Components { Card { Elevated { Elevation: 1 }, Outlined { Border_Width: 1 } } } }\n")
    assert theme["components"] == {"card.elevated": {"elevation": 1}, "card.outlined": {"border_width": 1}}
