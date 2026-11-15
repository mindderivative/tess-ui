"""Piece 5 of the TDL switch: a theme in TDL (`src/tess_ui/spec/tdl_theme.py`) loads to the mapping the YAML loader makes, and `tesserae migrate-tdl` writes
`*_Theme.yaml` as `*_Theme.tdl` keeping comments and order, idempotent and read back (`src/tess_ui/migrate_tdl_theme.py`; the shape is in `design/tdl-views.md`)."""

from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front end needs tess_dl (Python 3.14)")

import yaml  # noqa: E402

from tess_ui import cli  # noqa: E402
from tess_ui.migrate_tdl import _canon, migrate_tdl  # noqa: E402
from tess_ui.migrate_tdl_theme import ConvertError, convert_theme, theme_stem  # noqa: E402
from tess_ui.spec import marker  # noqa: E402
from tess_ui.spec.cascade import check_theme  # noqa: E402
from tess_ui.spec.expand import _normalize_scalars  # noqa: E402
from tess_ui.spec.nodes import LoadError, PMap  # noqa: E402
from tess_ui.spec.themes import load_theme  # noqa: E402
from tess_ui.spec.tdl_theme import THEME_KEYS, load_marked_theme_tdl, load_theme_tdl, load_theme_tdl_file  # noqa: E402
from tess_ui.theme import _COMPONENT_FIELDS, _TYPE_FIELDS  # noqa: E402

ROOT = Path(__file__).parent.parent
REAL = sorted(p for p in [*ROOT.joinpath("examples").rglob("*_Theme.yaml"), ROOT / "src" / "tess_ui" / "spec" / "default_theme.yaml"])


def yaml_mapping(text):
    return _normalize_scalars(marker.strip(yaml.safe_load(text)))


def tdl_of(text, name="T"):
    return convert_theme(text, name, f"{name}_Theme.yaml").text


def equal(yaml_text, name="T"):
    """The converted TDL loads to exactly the mapping (types included) the YAML loader makes."""
    written = tdl_of(yaml_text, name)
    got = load_theme_tdl(written, f"{name}_Theme.tdl")
    assert got == yaml_mapping(yaml_text)
    assert _canon(got) == _canon(yaml_mapping(yaml_text)), "types differ (True is not 1, 8 is not 8.0)"  # keys sorted: see the component order test
    return written


def body_of(tdl_text):
    return tdl_text.split("---\n", 2)[2]


# -- (a) the real themes ------------------------------------------------------------------------------------------------------


def test_there_are_real_themes_to_check():
    assert len(REAL) == 9


@pytest.mark.parametrize("path", REAL, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_every_real_theme_converts_and_loads_to_the_yaml_mapping(path):
    text = path.read_text(encoding="utf-8")
    written = equal(text, theme_stem(path.name))
    # the file loader (includes, check_theme, fonts) gives the same dict for both files
    tdl_file = path.parent / (theme_stem(path.name) + ".tdl")
    assert load_theme_tdl_file(tdl_file.with_name(path.with_suffix(".tdl").name)) == load_theme(path)
    assert written == path.with_suffix(".tdl").read_text(encoding="utf-8")


# -- (b) every key the loader takes -------------------------------------------------------------------------------------------

EVERYTHING = """tesserae: 0.6  # the series
# the colour the palette is made from
seed: "#0B6B58"
dark: true
colors:
  primary: "#112233"
  on_primary: white
  surface: "#FFFFFF80"
  tertiary: primary
typography:
  display_large: {font_family: Inter, font_weight: 700, font_size: 57, line_height: 64, tracking: -0.25}
  body_large:
    font_family: "Segoe UI Variable"
    font_size: 17
  label_small: {tracking: 0.5}
components:
  card: {corner_radius: 12}
  card.elevated: {elevation: level_2}
  chip: {corner_radius: small, elevation: 0}
  fab: {elevation: 3}
  fab.small: {corner_radius: 12}
  fab.large: {corner_radius: extra_large}
  navigation_drawer.indicator: {corner_radius: 28}
  badge: {}
  split_button.tightened.pressed: {corner_radius: 4}
styles:
  - kind: Rect
    style: {corner_radius: 0}
  - kind: Container
    classes: [panel, wide]
    style: {background: surface_container_high, padding: 12}
  - id: title
    style: {foreground: primary}
"""


def test_a_theme_with_every_key_loads_equal():
    written = equal(EVERYTHING)
    assert written.startswith('---\nTDL: 0.2\nName: T\nTesserae: "0.6"  # the series\n---\n')
    got = load_theme_tdl(written)
    assert set(got) == set(THEME_KEYS)
    check_theme(got)  # and the loader takes it


def test_every_typography_and_component_field_is_in_the_matrix():
    # the loader's own lists: if a field is added there, this theme must grow with it
    assert set(_TYPE_FIELDS) == {"font_family", "font_weight", "font_size", "line_height", "tracking"}
    assert set(_COMPONENT_FIELDS) == {"corner_radius", "elevation"}
    for field in (*_TYPE_FIELDS, *_COMPONENT_FIELDS):
        assert field in EVERYTHING


@pytest.mark.parametrize("key", THEME_KEYS)
def test_each_theme_key_alone_loads_equal(key):
    one = {
        "seed": 'seed: "#6750A4"\n', "dark": "dark: false\n", "colors": "colors:\n  primary: '#FF0000'\n  secondary: tertiary\n",
        "styles": "styles:\n  - kind: Text\n    style: {foreground: primary}\n",
        "components": "components:\n  dialog: {corner_radius: small}\n  dialog.modal: {elevation: 2}\n",
        "typography": "typography:\n  title_large: {font_size: 22, font_weight: 500}\n",
    }[key]
    written = equal(one)
    assert set(load_theme_tdl(written)) == {key}


def test_an_empty_theme_and_a_theme_of_only_comments_convert():
    assert body_of(equal("tesserae: 0.6\n")) == "Theme { }\n"
    assert tdl_of("").endswith("Theme { }\n")
    text = equal("# just a note\nseed: red\n")
    assert body_of(text).startswith("# just a note\nTheme {")


def test_values_keep_their_types():
    got = load_theme_tdl(tdl_of("seed: '0B6B58'\ndark: false\ncomponents:\n  a: {corner_radius: 8, elevation: 1.5, x: null, y: 'true', z: 'null'}\n"))
    assert got["seed"] == "0B6B58" and got["dark"] is False
    assert got["components"]["a"] == {"corner_radius": 8, "elevation": 1.5, "x": None, "y": "true", "z": "null"}


def test_a_component_with_fields_and_variants_is_one_block_and_comes_back_as_two_keys():
    text = "components:\n  card: {corner_radius: 12}\n  card.elevated: {elevation: 1}\n"
    written = equal(text)
    assert "Card {\n      Corner_Radius: 12\n      Elevated { Elevation: 1 }\n    }" in written.replace("\n  ", "\n    ", 0) or "Elevated { Elevation: 1 }" in written
    assert list(load_theme_tdl(written)["components"]) == ["card", "card.elevated"]


def test_variants_without_a_component_of_their_own_are_just_the_variants():
    written = equal("components:\n  tabs.indicator: {corner_radius: 3}\n  tabs.divider: {elevation: 0}\n")
    assert list(load_theme_tdl(written)["components"]) == ["tabs.indicator", "tabs.divider"]


def test_a_component_written_after_its_variants_is_read_back_in_place_of_the_group():
    written = tdl_of("components:\n  card.elevated: {elevation: 1}\n  card: {corner_radius: 12}\n")
    got = load_theme_tdl(written)["components"]
    assert got == {"card.elevated": {"elevation": 1}, "card": {"corner_radius": 12}}  # the same dict, the group's own key first


# -- (c) colours ---------------------------------------------------------------------------------------------------------------


def test_a_colour_is_written_quoted_and_a_bare_hash_is_an_error():
    written = tdl_of("seed: '#0B6B58'\ncolors: {primary: '#FF000080', secondary: tertiary}\n")
    assert 'Seed: "#0B6B58"' in written
    assert 'Primary: "#FF000080"' in written and "Secondary: tertiary" in written  # a role name needs no quotes
    bare = written.replace('"#0B6B58"', "#0B6B58")
    with pytest.raises(LoadError, match=r"needs quotes") as exc:
        load_theme_tdl(bare, "B_Theme.tdl")
    assert (exc.value.line, exc.value.column) == (6, 8)
    assert 'Quote the colour: "#' in exc.value.hint


# -- (d) comments, order and layout -------------------------------------------------------------------------------------------

COMMENTED = """tesserae: 0.6   # series
# Brand theme: the header comment
# (two lines)

seed: "#0B6B58"   # the seed
dark: false

# the roles to replace
colors:
  tertiary: "#C2410C"   # warm
  # between roles
  secondary: "#112233"

typography:
  headline_medium: {font_weight: 600}  # heavier

components:
  # cards
  card: {corner_radius: 12}   # round
  card.elevated: {elevation: 1}
  dialog: {corner_radius: 28, elevation: 3}
# the end
"""

GOLDEN = """---
TDL: 0.2
Name: Brand
Tesserae: "0.6"  # series
---
# Brand theme: the header comment
# (two lines)

Theme {
  Seed: "#0B6B58"  # the seed
  Dark: false

  # the roles to replace
  Colors {
    Tertiary: "#C2410C"  # warm
    # between roles
    Secondary: "#112233"
  }

  Typography {
    Headline_Medium { Font_Weight: 600 }  # heavier
  }

  Components {
    # cards
    Card {  # round
      Corner_Radius: 12
      Elevated { Elevation: 1 }
    }
    Dialog { Corner_Radius: 28, Elevation: 3 }
  }
}
# the end
"""


def test_comments_blank_lines_order_and_layout_are_kept_golden():
    written = tdl_of(COMMENTED, "Brand")
    assert written == GOLDEN
    assert load_theme_tdl(written) == yaml_mapping(COMMENTED)


def test_every_comment_of_the_yaml_is_in_the_tdl_once():
    written = tdl_of(COMMENTED, "Brand")
    comments = [part.strip() for line in COMMENTED.splitlines() for part in [line.replace('"#', "").partition("#")[2]] if part]
    assert len(comments) == 11
    for comment in comments:
        assert written.count("# " + comment) == 1, comment


def test_crlf_lines_and_a_byte_order_mark_are_fine():
    text = "\ufefftesserae: 0.6\r\nseed: '#0B6B58'\r\n"
    written = convert_theme(text, "T").text
    assert "\r\n" in written and "\n" not in written.replace("\r\n", "")
    assert load_theme_tdl(written)["seed"] == "#0B6B58"


def test_a_long_flow_mapping_is_opened_to_one_entry_a_line():
    fields = ", ".join(f"role_{i}: '#00{i:04d}'" for i in range(14))
    written = equal(f"colors: {{{fields}}}\n")
    assert body_of(written).count("\n") > 10 and all(len(line) <= 150 for line in written.splitlines())


def test_a_file_without_the_marker_has_no_tesserae_line():
    written = equal("seed: red\n")
    assert "Tesserae" not in written


# -- (e) idempotence ----------------------------------------------------------------------------------------------------------


def test_converting_twice_is_the_same_and_the_second_migrate_touches_nothing(tmp_path):
    (tmp_path / "Brand_Theme.yaml").write_bytes(COMMENTED.encode())
    first = migrate_tdl(tmp_path, write=True)
    assert [r.status for r in first.results] == ["converted"]
    target = tmp_path / "Brand_Theme.tdl"
    assert target.read_text(encoding="utf-8") == GOLDEN
    stamp = target.stat().st_mtime_ns
    second = migrate_tdl(tmp_path, write=True)
    assert [r.status for r in second.results] == ["current"]
    assert target.stat().st_mtime_ns == stamp
    assert tdl_of(COMMENTED, "Brand") == tdl_of(COMMENTED, "Brand")


def test_a_stale_tdl_is_replaced_only_with_write(tmp_path):
    (tmp_path / "A_Theme.yaml").write_text("seed: red\n", encoding="utf-8")
    (tmp_path / "A_Theme.tdl").write_text("old", encoding="utf-8")
    report = migrate_tdl(tmp_path)
    assert report.results[0].status == "converted" and "exists and differs" in report.results[0].notes[0]
    assert (tmp_path / "A_Theme.tdl").read_text() == "old"
    migrate_tdl(tmp_path, write=True)
    assert "Seed: red" in (tmp_path / "A_Theme.tdl").read_text()


# -- (f) errors point into the file -------------------------------------------------------------------------------------------

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


@pytest.mark.parametrize("body, match", [
    ("colorz: {a: b}\n", "unknown field"),
    ("seed: &a red\ndark: *a\n", "anchor or alias"),
    ("components:\n  card.Elevated: {elevation: 1}\n", "not lower snake_case"),
    ("components:\n  card.elevated: 8\n", "not a mapping"),
    ("components:\n  card.elevated: {elevation: 1}\n  card.elevated: {elevation: 2}\n", "duplicate|twice"),
    ("typography:\n  Body: {font_size: 1}\n", "not lower snake_case"),
    ("- a\n- b\n", "a theme is a mapping"),
    ("seed: [[1], [2]]\n", "no TDL form|unknown|lists"),
])
def test_what_has_no_tdl_form_is_refused_with_the_yaml_line(body, match):
    with pytest.raises(ConvertError, match=match):
        convert_theme(body, "T")


def test_an_empty_component_with_variants_is_refused_not_dropped():
    with pytest.raises(ConvertError, match="read back"):
        convert_theme("components:\n  card: {}\n  card.elevated: {elevation: 1}\n", "T")


def test_a_theme_name_that_cannot_be_a_tdl_name_is_refused():
    with pytest.raises(ConvertError, match="cannot be a TDL Name"):
        convert_theme("seed: red\n", "my-theme")


def test_a_misplaced_marker_is_refused_with_its_line():
    with pytest.raises(ConvertError) as exc:
        convert_theme("seed: red\ntesserae: 0.6\n", "T")
    assert exc.value.line == 2


# -- (h) the file loader ------------------------------------------------------------------------------------------------------


def test_the_file_loader_expands_a_rule_style_file_checks_the_theme_and_names_the_file(tmp_path):
    (tmp_path / "Card_Style.yaml").write_text("corner_radius: 4\n", encoding="utf-8")
    yaml_file = tmp_path / "A_Theme.yaml"
    yaml_file.write_text("styles:\n  - kind: Rect\n    style: Card_Style.yaml\n", encoding="utf-8")
    migrate_tdl(tmp_path, write=True)
    assert load_theme_tdl_file(tmp_path / "A_Theme.tdl") == load_theme(yaml_file)
    bad = tmp_path / "B_Theme.tdl"
    bad.write_text(HEAD + "Theme { Typography { Body_Large { Font_Colour: red } } }\n", encoding="utf-8")
    load_theme_tdl_file(bad)  # an unknown typography field is Theme's to refuse, not the file loader's (as for YAML)
    wrong = tmp_path / "C_Theme.tdl"
    wrong.write_bytes(b"\xff\xfe")
    with pytest.raises(LoadError, match="not UTF-8"):
        load_theme_tdl_file(wrong)


# -- (i) the command ----------------------------------------------------------------------------------------------------------


def test_the_command_converts_a_theme_beside_its_yaml(tmp_path, capsys):
    (tmp_path / "Brand_Theme.yaml").write_text(COMMENTED, encoding="utf-8")
    (tmp_path / "default_theme.yaml").write_text("seed: red\n", encoding="utf-8")
    assert cli.main(["migrate-tdl", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "would convert" in out and "Brand_Theme.yaml -> Brand_Theme.tdl" in out and "default_theme.yaml -> default_theme.tdl" in out
    assert not list(tmp_path.glob("*.tdl"))
    assert cli.main(["migrate-tdl", str(tmp_path), "--write"]) == 0
    assert (tmp_path / "Brand_Theme.tdl").read_text(encoding="utf-8") == GOLDEN
    assert "Name: default_theme" in (tmp_path / "default_theme.tdl").read_text(encoding="utf-8")
    assert cli.main(["migrate-tdl", str(tmp_path)]) == 0
    assert sum(line.startswith("current") for line in capsys.readouterr().out.splitlines()) == 2
    assert cli.main(["migrate-tdl", str(tmp_path), "--write", "--remove-source"]) == 0
    assert not list(tmp_path.glob("*.yaml")) and len(list(tmp_path.glob("*.tdl"))) == 2


def test_the_command_takes_one_theme_file_and_reports_a_failure_with_exit_1(tmp_path, capsys):
    good = tmp_path / "Good_Theme.yaml"
    good.write_text("seed: red\n", encoding="utf-8")
    bad = tmp_path / "Bad_Theme.yaml"
    bad.write_text("colorz: 1\n", encoding="utf-8")
    assert cli.main(["migrate-tdl", str(good), "--write"]) == 0
    assert (tmp_path / "Good_Theme.tdl").is_file()
    assert cli.main(["migrate-tdl", str(tmp_path), "--write"]) == 1
    out = capsys.readouterr().out
    assert "failed" in out and "Bad_Theme.yaml:1:" in out and "unknown field" in out
    assert not (tmp_path / "Bad_Theme.tdl").exists()


def test_a_view_and_a_theme_in_one_folder_are_both_converted(tmp_path):
    (tmp_path / "Main_View.yaml").write_text("widget: Text\ntext: hi\n", encoding="utf-8")
    (tmp_path / "Brand_Theme.yaml").write_text("seed: red\n", encoding="utf-8")
    report = migrate_tdl(tmp_path, write=True)
    assert sorted(r.status for r in report.results) == ["converted", "converted"]
    assert (tmp_path / "Main_View.tdl").is_file() and (tmp_path / "Brand_Theme.tdl").is_file()
