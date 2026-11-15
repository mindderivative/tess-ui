"""#292: every Tesserae TDL file says in its metadata block which release series it was written for (`Tesserae: "0.6"`, `marker.LINE`), and the loaders check it. In this line it is
optional (a missing key is a note, a wrong one is an error, a file of an older line is refused); it is meant to be required from a later line."""

import tomllib
from pathlib import Path

import pytest
from loguru import logger

from tess_ui.spec import marker
from tess_ui.spec.nodes import LoadError, parse_data
from tess_ui.spec.rules import load_rule_sheet
from tess_ui.spec.tdl import load_marked_tdl
from tess_ui.spec.themes import load_stylesheet, load_theme

ROOT = Path(__file__).resolve().parent.parent
BODY = "Container { Style { Width: 10, Height: 10 } }\n"


def doc(body=BODY, series=None, name="A"):
    """A TDL file's text: the metadata block (with the `Tesserae` line when `series` is given: its text as written) and `body`."""
    tesserae = f"Tesserae: {series}\n" if series is not None else ""
    return f"---\nTDL: 0.2\nName: {name}\n{tesserae}---\n{body}"


def quoted(series):
    return f'"{series}"'


def parse(text, file="A_View.tdl"):
    return parse_data(load_marked_tdl(text, file), text, file)


def test_the_line_is_the_first_two_parts_of_the_package_version():
    """A new line is the user's to start: this fails when the version moves up a line, and then the files and `marker.LINE` move together."""
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert marker.LINE == ".".join(version.split(".")[:2])


@pytest.mark.parametrize("series", [quoted(marker.LINE), marker.LINE, f'"{marker.LINE}"   # the line'])
def test_a_marker_in_the_metadata_is_fine(series):
    assert parse(doc(series=series)).root.widget == "Container"


def test_no_marker_is_not_a_problem_in_this_line():
    assert parse(doc()).root.widget == "Container"


@pytest.mark.parametrize("value", ["", "abc", "0.5.1", "0", "05", "0.5."])
def test_a_value_that_is_not_a_line_says_what_to_write(value):
    with pytest.raises(LoadError) as caught:
        parse(doc(series=quoted(value)))
    assert f"write `Tesserae: {marker.LINE}`" in str(caught.value)


def test_a_newer_line_says_to_upgrade_and_an_older_one_is_refused():
    with pytest.raises(LoadError) as caught:
        parse(doc(series=quoted("0.99")))
    assert "written for Tesserae 0.99" in str(caught.value) and "this is" in str(caught.value) and "upgrade" in str(caught.value)
    with pytest.raises(LoadError) as caught:
        parse(doc(series=quoted("0.4")))
    assert "written for Tesserae 0.4" in str(caught.value)
    with pytest.raises(LoadError) as caught:
        parse(doc(series=quoted("1.0")))
    assert "upgrade" in str(caught.value)


def test_a_property_of_a_node_called_tesserae_is_not_the_marker():
    mapping = load_marked_tdl(doc("Container { Children { Text { Tesserae: \"0.5\" } } }\n"), "A_View.tdl")
    assert mapping["children"][0]["tesserae"] == "0.5"


# -- the loaders

def test_a_view_with_the_marker_loads_as_one_without():
    with_key = load_marked_tdl(doc(series=quoted(marker.LINE)), "A_View.tdl")
    without = load_marked_tdl(doc(), "A_View.tdl")
    assert dict(with_key) == dict(without) and "tesserae" not in with_key and "tesserae" not in with_key.key_at and "tesserae" not in with_key.val_at


def test_the_positions_of_everything_else_are_the_same_with_the_marker():
    """The marker is a line of the metadata block, so an error's line in the body is the file's line."""
    body = "Container {\n  Children {\n    Text { Colour: red }\n  }\n}\n"
    lines = []
    for text in (doc(body, series=quoted(marker.LINE)), doc(body)):
        with pytest.raises(LoadError) as caught:
            parse(text)
        lines.append((caught.value.line, "colour" in str(caught.value)))
    assert lines[0] == (lines[1][0] + 1, True) and lines[1][1], "each file's own line: the marker is a line of its own and shifts the lines after it by one"


def test_a_view_of_another_line_is_a_load_error_at_the_marker():
    with pytest.raises(LoadError) as caught:
        parse(doc(series=quoted("0.99")))
    assert "A_View.tdl:4" in str(caught.value) and "upgrade" in str(caught.value)


def test_a_rule_sheet_file_with_the_marker_loads(tmp_path):
    path = tmp_path / "A_Stylesheet.tdl"
    path.write_text(doc("Styles { Rule { Widget: Text, Style { Opacity: 1 } } }\n", series=quoted(marker.LINE)), encoding="utf-8")
    assert len(load_rule_sheet(path).rules) == 1


def test_a_theme_and_a_stylesheet_file_with_the_marker_load_without_it(tmp_path):
    theme = tmp_path / "A_Theme.tdl"
    theme.write_text(doc('Theme { Seed: "#6750A4" }\n', series=quoted(marker.LINE)), encoding="utf-8")
    assert load_theme(theme) == {"seed": "#6750A4"}
    sheet = tmp_path / "A_Stylesheet.tdl"
    sheet.write_text(doc("Styles { Rule { Widget: Text, Style { Opacity: 1 } } }\n", series=quoted(marker.LINE)), encoding="utf-8")
    assert list(load_stylesheet(sheet)) == ["styles"]


@pytest.mark.parametrize("series, said", [('"abc"', "write `Tesserae:"), ('"0.99"', "upgrade")])
def test_a_theme_file_with_a_wrong_marker_is_an_error_naming_the_file(tmp_path, series, said):
    theme = tmp_path / "A_Theme.tdl"
    theme.write_text(doc('Theme { Seed: "#6750A4" }\n', series=series), encoding="utf-8")
    with pytest.raises(ValueError, match=rf"A_Theme\.tdl.*{said}"):
        load_theme(theme)


def test_the_shipped_default_theme_loads_with_its_marker():
    from tess_ui.spec.build import shipped_default_theme

    path = ROOT / "src" / "tess_ui" / "spec" / "default_theme.tdl"
    assert f'\nTesserae: "{marker.LINE}"\n' in path.read_text(encoding="utf-8")
    assert "tesserae" not in shipped_default_theme() and "styles" in shipped_default_theme()


# -- the note

@pytest.fixture
def notes():
    seen = []
    handle = logger.add(lambda message: seen.append(str(message)), level="INFO", format="{message}")
    marker._noted.clear()
    yield seen
    logger.remove(handle)


def test_a_file_without_the_marker_is_noted_once_and_a_file_with_it_is_not(tmp_path, notes):
    plain = tmp_path / "A_Theme.tdl"
    plain.write_text(doc('Theme { Seed: "#6750A4" }\n'), encoding="utf-8")
    keyed = tmp_path / "B_Theme.tdl"
    keyed.write_text(doc('Theme { Seed: "#6750A4" }\n', series=quoted(marker.LINE)), encoding="utf-8")
    load_theme(plain)
    load_theme(plain)
    load_theme(keyed)
    mine = [n for n in notes if "A_Theme.tdl" in n or "B_Theme.tdl" in n]
    assert len(mine) == 1 and "A_Theme.tdl" in mine[0] and f'Tesserae: \"{marker.LINE}\"' in mine[0] and "metadata" in mine[0]


def test_text_given_straight_to_the_parser_is_not_noted(notes):
    parse(doc())
    assert not [n for n in notes if "A_View.tdl" in n]


def test_the_note_is_for_a_view_read_from_disk_too(tmp_path, notes):
    from tess_ui.shipped import ViewLibrary

    (tmp_path / "Z_View.tdl").write_text(doc(name="Z"), encoding="utf-8")
    ViewLibrary({"Z": tmp_path / "Z_View.tdl"}).doc("Z")
    assert [n for n in notes if "Z_View.tdl" in n and "metadata" in n]


# -- a file of an older line is refused by the loaders

PREVIOUS = f"{marker.LINE.split('.')[0]}.{int(marker.LINE.split('.')[1]) - 1}"  # the line before this one
SHEET = "Styles { Rule { Widget: Text, Style { Opacity: 1 } } }\n"
THEME = 'Theme { Seed: "#6750A4" }\n'
KINDS = [("view", "Views/A_View.tdl", BODY), ("stylesheet", "Styles/A_Stylesheet.tdl", SHEET), ("theme", "Themes/A_Theme.tdl", THEME)]


def load_as(kind, path):
    """Loads `path` the way the app does; an older line is a `ValueError` (a `LoadError` is one) for each of the three."""
    if kind == "view":
        return parse(path.read_text(encoding="utf-8"), path.name)
    return load_rule_sheet(path) if kind == "stylesheet" else load_theme(path)


@pytest.mark.parametrize("line", [PREVIOUS, "0.1"])
@pytest.mark.parametrize("kind, relative, body", KINDS)
def test_a_file_of_an_older_line_is_refused(tmp_path, kind, relative, body, line):
    path = tmp_path / relative
    path.parent.mkdir()
    path.write_text(doc(body, series=quoted(line)), encoding="utf-8")
    with pytest.raises(ValueError, match=f"written for Tesserae {line}"):
        load_as(kind, path)
    path.write_text(doc(body, series=quoted(marker.LINE)), encoding="utf-8")
    load_as(kind, path)  # the same file on this line loads


# -- a dict a user loaded from such a file

def test_a_mapping_loaded_from_a_file_with_the_marker_is_accepted_by_the_checks_and_other_keys_still_are_not():
    from tess_ui.spec.cascade import check_stylesheet, check_theme
    from tess_ui.spec.rules import RuleSheet

    sheet = {"tesserae": marker.LINE, "styles": [{"widget": "Text", "style": {"opacity": 1}}]}
    assert len(RuleSheet.of(sheet).rules) == 1
    check_stylesheet({"tesserae": marker.LINE, "styles": []})
    check_theme({"tesserae": marker.LINE, "seed": "#6750A4"})
    with pytest.raises(LoadError, match="only 'styles:', not 'colour'"):
        RuleSheet.of({"tesserae": marker.LINE, "colour": 1})
    with pytest.raises(ValueError, match="unknown field `colour`"):
        check_theme({"tesserae": marker.LINE, "colour": 1})


# -- everything Tesserae ships or writes carries it
def test_every_tdl_file_tesserae_ships_has_the_marker_in_its_metadata():
    """The shipped views and stylesheets and the default theme."""
    files = sorted([*(ROOT / "src" / "tess_ui" / "views").glob("*.tdl"), ROOT / "src" / "tess_ui" / "spec" / "default_theme.tdl"])
    assert len(files) >= 100, len(files)
    missing = [str(p.relative_to(ROOT)) for p in files if f'\nTesserae: "{marker.LINE}"\n' not in p.read_text(encoding="utf-8").split("\n---\n", 1)[0] + "\n"]
    assert not missing, f"{len(missing)} file(s) lack `Tesserae: \"{marker.LINE}\"` in their metadata: {missing[:5]}"


def test_a_new_app_and_a_new_screen_are_written_with_the_marker(tmp_path):
    """The templates write TDL: the series is the `Tesserae` metadata line, and a project's own files load."""
    from tess_ui import cli

    for flags in ([], ["--window"], ["--window", "--custom-title-bar"]):
        name = "app" + "".join(f.strip("-") for f in flags).replace("window", "w").replace("custom", "c").replace("title-bar", "t")
        assert cli.main(["new", name, "--no-venv", "--dir", str(tmp_path), *flags]) == 0
        written = [p for p in (tmp_path / name).rglob("*_View.tdl")]
        assert written and not list((tmp_path / name).rglob("*_View.yaml")), name
        for path in written:
            text = path.read_text(encoding="utf-8")
            assert text.startswith("---\nTDL: 0.2\n") and f'\nTesserae: "{marker.LINE}"\n' in text, f"{path.relative_to(tmp_path)}: {text[:60]!r}"
    assert cli.main(["add", "screen", "Settings", "--dir", str(tmp_path / "app")]) == 0
    added = (tmp_path / "app" / "Views" / "Settings_View.tdl").read_text(encoding="utf-8")
    assert f'\nTesserae: "{marker.LINE}"\n' in added


def test_an_example_loads_with_no_note_about_the_marker(tmp_path):
    """The shipped views and stylesheets an app reads, and the example's own, have the marker: opening one says nothing about it."""
    import subprocess
    import sys

    done = subprocess.run([sys.executable, "app.py"], cwd=ROOT / "examples" / "counter", capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr[-800:]
    assert "no `Tesserae:" not in done.stderr, done.stderr[-800:]
