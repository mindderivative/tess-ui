"""#292: every Tesserae YAML file starts with `tesserae: <line>` (the release series, `marker.LINE`), and the loaders check it. In this line it is optional
(a missing key is a note, a wrong or misplaced one is an error, a file of an older line is refused until `migrate-yaml` moves it); it is meant to be required from a later line."""

import tomllib
from pathlib import Path

import pytest
from loguru import logger

from tess_ui.spec import marker
from tess_ui.spec.nodes import LoadError, load_marked, parse_view
from tess_ui.spec.rules import load_rule_sheet
from tess_ui.spec.themes import load_stylesheet, load_theme

ROOT = Path(__file__).resolve().parent.parent
VIEW = "widget: Container\nstyle: {width: 10, height: 10}\n"


def problem(text):
    return marker.scan(text).problem


def test_the_line_is_the_first_two_parts_of_the_package_version():
    """A new line is the user's to start: this fails when the version moves up a line, and then the files and `marker.LINE` move together."""
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert marker.LINE == ".".join(version.split(".")[:2])


@pytest.mark.parametrize("text", [
    f"tesserae: {marker.LINE}\n{VIEW}", f"tesserae: {marker.LINE}   # the line\n{VIEW}", f"tesserae:\t{marker.LINE}\n{VIEW}",
    f"tesserae: {marker.LINE}\r\n{VIEW}", f"\ufefftesserae: {marker.LINE}\n{VIEW}", f"tesserae: {marker.LINE}", f"tesserae:{marker.LINE}\n{VIEW}",
])
def test_a_marker_on_the_first_line_is_found_and_is_fine(text):
    scanned = marker.scan(text)
    assert scanned.found and scanned.value == marker.LINE and scanned.problem is None


def test_no_marker_is_not_a_problem_in_this_line():
    scanned = marker.scan(VIEW)
    assert not scanned.found and scanned.problem is None


@pytest.mark.parametrize("text, line", [
    (f"# a header\ntesserae: {marker.LINE}\n{VIEW}", 2), (f"\ntesserae: {marker.LINE}\n{VIEW}", 2), (f"---\ntesserae: {marker.LINE}\n{VIEW}", 2),
    (f"{VIEW}tesserae: {marker.LINE}\n", 3),
])
def test_a_marker_that_is_not_the_first_line_is_an_error_naming_where_it_is(text, line):
    scanned = marker.scan(text)
    assert scanned.line == line and "first line" in scanned.problem and f"tesserae: {marker.LINE}" in scanned.problem


@pytest.mark.parametrize("value", ["", "abc", "0.5.1", "0", "05", "'0.5'", '"0.5"'])
def test_a_value_that_is_not_a_line_says_what_to_write(value):
    assert f"write `tesserae: {marker.LINE}`" in problem(f"tesserae: {value}\n{VIEW}")


def test_a_newer_line_says_to_upgrade_and_an_older_one_to_migrate():
    newer = problem("tesserae: 0.99\n" + VIEW)
    assert "written for Tesserae 0.99" in newer and "this is" in newer and "upgrade" in newer
    older = problem("tesserae: 0.4\n" + VIEW)
    assert "written for Tesserae 0.4" in older and "tesserae migrate-yaml" in older
    assert "upgrade" in problem("tesserae: 1.0\n" + VIEW)


def test_a_key_further_down_a_mapping_is_not_the_marker():
    assert not marker.scan("widget: Container\nchildren:\n  - widget: Text\n    tesserae: 0.5\n").found
    assert problem("widget: Container\nchildren:\n  - widget: Text\n    tesserae: 0.5\n") is None


# -- the loaders

def test_a_view_with_the_marker_loads_as_one_without(tmp_path):
    with_key = load_marked(f"tesserae: {marker.LINE}\n{VIEW}", "A_View.yaml")
    without = load_marked(VIEW, "A_View.yaml")
    assert dict(with_key) == dict(without) and "tesserae" not in with_key and "tesserae" not in with_key.key_at and "tesserae" not in with_key.val_at


def test_the_positions_of_everything_else_are_the_same_with_the_marker():
    """The key is the first line and the rest is where it was written, so an error's line is the file's line."""
    body = "widget: Container\nchildren:\n  - widget: Text\n    colour: red\n"
    lines = []
    for text in (f"tesserae: {marker.LINE}\n" + body, body):
        with pytest.raises(LoadError) as caught:
            parse_view(text, "A_View.yaml")
        lines.append((caught.value.line, "colour" in str(caught.value)))
    assert lines[0] == (lines[1][0] + 1, True) and lines[1][1], "each file's own line: the marker is line 1 and shifts nothing but its own position"


def test_a_view_with_a_misplaced_marker_is_a_load_error_at_the_marker():
    with pytest.raises(LoadError) as caught:
        parse_view(f"# header\ntesserae: {marker.LINE}\n{VIEW}", "A_View.yaml")
    error = caught.value
    assert "A_View.yaml:2" in str(error) and "first line" in str(error)


def test_a_view_of_another_line_is_a_load_error_at_line_one():
    with pytest.raises(LoadError) as caught:
        parse_view("tesserae: 0.99\n" + VIEW, "A_View.yaml")
    assert "A_View.yaml:1" in str(caught.value) and "upgrade" in str(caught.value)


def test_a_view_root_with_the_marker_has_no_unknown_property():
    doc = parse_view(f"tesserae: {marker.LINE}\n{VIEW}", "A_View.yaml")
    assert doc.root.widget == "Container"


def test_a_rule_sheet_file_with_the_marker_loads(tmp_path):
    path = tmp_path / "A_Stylesheet.yaml"
    path.write_text(f"tesserae: {marker.LINE}\nstyles:\n  - widget: Text\n    style: {{opacity: 1}}\n", encoding="utf-8")
    assert len(load_rule_sheet(path).rules) == 1


def test_a_theme_and_a_stylesheet_file_with_the_marker_load_without_it(tmp_path):
    theme = tmp_path / "A_Theme.yaml"
    theme.write_text(f"tesserae: {marker.LINE}\nseed: '#6750A4'\n", encoding="utf-8")
    assert load_theme(theme) == {"seed": "#6750A4"}
    sheet = tmp_path / "A_Stylesheet.yaml"
    sheet.write_text(f"tesserae: {marker.LINE}\nstyles:\n  - widget: Text\n    style: {{opacity: 1}}\n", encoding="utf-8")
    assert list(load_stylesheet(sheet)) == ["styles"]


def test_a_theme_file_with_a_misplaced_marker_is_an_error_naming_the_file(tmp_path):
    theme = tmp_path / "A_Theme.yaml"
    theme.write_text(f"seed: '#6750A4'\ntesserae: {marker.LINE}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"A_Theme\.yaml.*first line"):
        load_theme(theme)


def test_the_shipped_default_theme_loads_with_its_marker():
    from tess_ui.spec.build import shipped_default_theme

    path = ROOT / "src" / "tess_ui" / "spec" / "default_theme.yaml"
    assert path.read_text(encoding="utf-8").startswith(f"tesserae: {marker.LINE}\n")
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
    plain = tmp_path / "A_Theme.yaml"
    plain.write_text("seed: '#6750A4'\n", encoding="utf-8")
    keyed = tmp_path / "B_Theme.yaml"
    keyed.write_text(f"tesserae: {marker.LINE}\nseed: '#6750A4'\n", encoding="utf-8")
    load_theme(plain)
    load_theme(plain)
    load_theme(keyed)
    mine = [n for n in notes if "A_Theme.yaml" in n or "B_Theme.yaml" in n]
    assert len(mine) == 1 and "A_Theme.yaml" in mine[0] and f"tesserae: {marker.LINE}" in mine[0] and "first line" in mine[0]


def test_text_given_straight_to_the_parser_is_not_noted(notes):
    parse_view(VIEW, "A_View.yaml")
    assert not [n for n in notes if "A_View.yaml" in n]


def test_the_note_is_for_a_view_read_from_disk_too(tmp_path, notes):
    from tess_ui.shipped import ViewLibrary

    (tmp_path / "Z_View.yaml").write_text("name: Z\n" + VIEW, encoding="utf-8")
    ViewLibrary({"Z": tmp_path / "Z_View.yaml"}).doc("Z")
    assert [n for n in notes if "Z_View.yaml" in n and "first line" in n]


# -- migrate-yaml writes the marker on what it translates

def test_migrate_yaml_writes_the_marker_first_in_a_translated_view_and_stylesheet(tmp_path):
    from tess_ui.migrate import migrate_project

    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.yaml").write_text("# The screen.\nid: root\nkind: Container\nstyle: {width: 100, height: 40}\n", encoding="utf-8")
    (tmp_path / "Styles").mkdir()
    (tmp_path / "Styles" / "Look_Stylesheet.yaml").write_text(
        "# Looks.\nstyles:\n  - kind: Container\n    style: {corner_radius: 4}\n", encoding="utf-8")
    report = migrate_project(tmp_path, write=True)
    assert not report.failed
    view = (tmp_path / "Views" / "Main_View.yaml").read_text(encoding="utf-8")
    sheet = (tmp_path / "Styles" / "Look_Stylesheet.yaml").read_text(encoding="utf-8")
    for text in (view, sheet):
        assert text.startswith(f"tesserae: {marker.LINE}\n# "), text  # the key, then the comments it had
    parse_view(view, "Main_View.yaml")  # it loads: the key is first
    assert marker.scan(sheet).found and marker.scan(sheet).problem is None


def test_migrate_yaml_leaves_a_current_file_alone_marker_or_not(tmp_path):
    from tess_ui.migrate import migrate_project

    (tmp_path / "Views").mkdir()
    keyed = f"tesserae: {marker.LINE}\n{VIEW}"
    (tmp_path / "Views" / "A_View.yaml").write_text(keyed, encoding="utf-8")
    (tmp_path / "Views" / "B_View.yaml").write_text(VIEW, encoding="utf-8")
    report = migrate_project(tmp_path, write=True)
    assert {r.path.name: r.status for r in report.results} == {"A_View.yaml": "current", "B_View.yaml": "current"}
    assert (tmp_path / "Views" / "A_View.yaml").read_text(encoding="utf-8") == keyed
    assert (tmp_path / "Views" / "B_View.yaml").read_text(encoding="utf-8") == VIEW


# -- a file of an older line: the loaders refuse it and say `migrate-yaml`, so `migrate-yaml` has to be what fixes it

PREVIOUS = f"{marker.LINE.split('.')[0]}.{int(marker.LINE.split('.')[1]) - 1}"  # the line before this one
SHEET = "styles:\n  - {widget: Text, style: {opacity: 1}}\n"
THEME = "seed: '#6750A4'\n"
KINDS = [("view", "Views/A_View.yaml", VIEW), ("stylesheet", "Styles/A_Stylesheet.yaml", SHEET), ("theme", "Themes/A_Theme.yaml", THEME)]


def load_as(kind, path):
    """Loads `path` the way the app does; an older line is a `ValueError` (a `LoadError` is one) for each of the three."""
    if kind == "view":
        return parse_view(path.read_text(encoding="utf-8"), path.name)
    return load_rule_sheet(path) if kind == "stylesheet" else load_theme(path)


@pytest.mark.parametrize("line", [PREVIOUS, "0.1"])
@pytest.mark.parametrize("kind, relative, body", KINDS)
def test_a_file_of_an_older_line_is_refused_and_migrate_yaml_brings_it_forward(tmp_path, kind, relative, body, line):
    from tess_ui.migrate import migrate_project

    path = tmp_path / relative
    path.parent.mkdir()
    old = f"tesserae: {line}\n# kept\n{body}"
    path.write_text(old, encoding="utf-8")
    with pytest.raises(ValueError, match="tesserae migrate-yaml"):
        load_as(kind, path)
    dry = migrate_project(tmp_path)
    assert {r.path.name: r.status for r in dry.results} == {path.name: "migrated"}
    assert path.read_text(encoding="utf-8") == old  # a report writes nothing
    report = migrate_project(tmp_path, write=True)
    assert report.written and not report.failed
    assert path.read_text(encoding="utf-8") == f"tesserae: {marker.LINE}\n# kept\n{body}"  # the first line moved and nothing else
    load_as(kind, path)  # and the file loads


def test_only_the_value_on_the_first_line_changes_a_bom_a_comment_and_windows_line_ends_stay(tmp_path):
    from tess_ui.migrate import migrate_project

    (tmp_path / "Views").mkdir()
    path = tmp_path / "Views" / "A_View.yaml"
    raw = "\ufefftesserae: 0.1  # the line\r\n# header\r\nwidget: Container\r\nstyle: {width: 10, height: 10}\r\n"
    path.write_bytes(raw.encode("utf-8"))
    assert migrate_project(tmp_path, write=True).written
    assert path.read_bytes() == raw.replace("0.1", marker.LINE, 1).encode("utf-8")


def test_migrate_yaml_leaves_a_file_of_this_line_a_newer_line_or_no_line_alone(tmp_path):
    from tess_ui.migrate import migrate_project

    files = {"Views/A_View.yaml": f"tesserae: {marker.LINE}\n{VIEW}", "Views/B_View.yaml": VIEW, "Views/C_View.yaml": f"tesserae: 9.9\n{VIEW}",
             "Themes/Plain_Theme.yaml": THEME, "Themes/Same_Theme.yaml": f"tesserae: {marker.LINE}\n{THEME}", "Themes/Newer_Theme.yaml": f"tesserae: 9.9\n{THEME}"}
    for relative, text in files.items():
        (tmp_path / relative).parent.mkdir(exist_ok=True)
        (tmp_path / relative).write_text(text, encoding="utf-8")
    report = migrate_project(tmp_path, write=True)
    assert [r.path.name for r in report.results if r.status == "migrated"] == []
    assert {relative: (tmp_path / relative).read_text(encoding="utf-8") for relative in files} == files


def test_a_view_that_only_has_its_first_line_moved_gets_no_viewmodel_advice(tmp_path):
    """The advice is for a view that was translated (`views = ...`, no `view` argument): this one is already in the current language."""
    from tess_ui.migrate import migrate_project

    (tmp_path / "Views").mkdir()
    (tmp_path / "ViewModels").mkdir()
    (tmp_path / "Views" / "Main_View.yaml").write_text(f"tesserae: 0.1\nname: Main\n{VIEW}", encoding="utf-8")
    (tmp_path / "ViewModels" / "Main_ViewModel.py").write_text("class MainViewModel:\n    views = 'Main'\n", encoding="utf-8")
    report = migrate_project(tmp_path)
    assert [r.status for r in report.results] == ["migrated"] and report.python == []


def test_a_file_with_a_problem_of_its_own_still_gets_its_first_line_moved_and_blocks_nothing(tmp_path):
    """Only the first line is this command's to change: an unrelated mistake in the file is for the loader to report when the app opens it, and no reason to leave the
    whole project on the old line."""
    from tess_ui.migrate import migrate_project

    (tmp_path / "Views").mkdir()
    broken = tmp_path / "Views" / "Broken_View.yaml"
    good = tmp_path / "Views" / "Good_View.yaml"
    broken.write_text("tesserae: 0.1\nwidget: NoSuchWidget\n", encoding="utf-8")
    good.write_text(f"tesserae: 0.1\n{VIEW}", encoding="utf-8")
    report = migrate_project(tmp_path, write=True)
    assert report.written and not report.failed
    for path in (broken, good):
        assert path.read_text(encoding="utf-8").startswith(f"tesserae: {marker.LINE}\n")


def test_the_command_brings_a_project_of_an_older_line_forward(tmp_path, capsys):
    from tess_ui import cli

    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.yaml").write_text(f"tesserae: 0.1\n{VIEW}", encoding="utf-8")
    assert cli.main(["migrate-yaml", str(tmp_path), "--write"]) == 0
    out = capsys.readouterr().out
    assert "migrated" in out and "Main_View.yaml" in out and f"tesserae: {marker.LINE}" in out and "written" in out
    assert (tmp_path / "Views" / "Main_View.yaml").read_text(encoding="utf-8").startswith(f"tesserae: {marker.LINE}\n")


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

def stamp_tool():
    import importlib.util

    spec = importlib.util.spec_from_file_location("stamp_language", ROOT / "tools" / "stamp_language.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_yaml_file_tesserae_ships_starts_with_the_marker():
    """The shipped views and stylesheets, the default theme, the project templates and the examples: `python3 tools/stamp_language.py --write` fixes it."""
    tool = stamp_tool()
    files = tool.files()
    assert len(files) >= 150, len(files)
    missing = [str(p.relative_to(ROOT)) for p in files if not p.read_bytes().decode("utf-8").startswith(f"{marker.KEY}: {marker.LINE}")]
    assert not missing, f"{len(missing)} file(s) lack `tesserae: {marker.LINE}` on line 1: {missing[:5]}"
    assert all(tool.stamped(p) is None for p in files)


def test_the_older_syntax_fragments_have_no_marker_it_is_what_marks_them_as_older():
    for folder in (ROOT / "src" / "tess_ui" / "spec" / "components", ROOT / "tests" / "older_syntax"):
        for path in folder.rglob("*.yaml"):
            assert not marker.scan(path.read_text(encoding="utf-8")).found, path


def test_the_stamp_tool_prepends_replaces_and_leaves_alone(tmp_path):
    tool = stamp_tool()
    def stamp(text):
        path = tmp_path / "A_View.yaml"
        path.write_bytes(text.encode("utf-8"))
        return tool.stamped(path)

    assert stamp("# header\nwidget: Container\n") == f"tesserae: {marker.LINE}\n# header\nwidget: Container\n"
    assert stamp("# header\r\nwidget: Container\r\n") == f"tesserae: {marker.LINE}\r\n# header\r\nwidget: Container\r\n"
    assert stamp("tesserae: 0.4\nwidget: Container\n") == f"tesserae: {marker.LINE}\nwidget: Container\n"
    assert stamp(f"tesserae: {marker.LINE}  # ok\nwidget: Container\n") is None
    assert stamp(f"tesserae: {marker.LINE}\nwidget: Container\n") is None


def test_a_new_app_and_a_new_screen_are_written_with_the_marker(tmp_path):
    from tess_ui import cli

    for flags in ([], ["--window"], ["--window", "--custom-title-bar"]):
        name = "app" + "".join(f.strip("-") for f in flags).replace("window", "w").replace("custom", "c").replace("title-bar", "t")
        assert cli.main(["new", name, "--no-venv", "--dir", str(tmp_path), *flags]) == 0
        written = [p for p in (tmp_path / name).rglob("*_View.yaml")]
        assert written, name
        for path in written:
            text = path.read_text(encoding="utf-8")
            assert text.startswith(f"tesserae: {marker.LINE}\n"), f"{path.relative_to(tmp_path)}: {text[:40]!r}"
            assert marker.scan(text).problem is None
    assert cli.main(["add", "screen", "Settings", "--dir", str(tmp_path / "app")]) == 0
    assert (tmp_path / "app" / "Views" / "Settings_View.yaml").read_text(encoding="utf-8").startswith(f"tesserae: {marker.LINE}\n")


def test_an_example_loads_with_no_note_about_the_marker(tmp_path):
    """The shipped views and stylesheets an app reads, and the example's own, have the marker: opening one says nothing about it."""
    import subprocess
    import sys

    done = subprocess.run([sys.executable, "app.py"], cwd=ROOT / "examples" / "counter", capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr[-800:]
    assert "no `tesserae:" not in done.stderr, done.stderr[-800:]


def test_every_docs_block_that_shows_a_whole_file_starts_with_the_marker():
    tool = stamp_tool()
    assert len(tool.pages()) > 50
    assert all(tool.stamped_page(p) is None for p in tool.pages()), "run `python3 tools/stamp_language.py --write`"
