"""The specification's acceptance criteria that only a whole-application test can show: the shell's shipped default configuration opens with no finding, one key-only pass through every action, a value outside a key's range
is refused for every key of the schema, a token chosen for a colour key, the accessible names and descriptions, the Tab order, and nothing outside the temporary folders.

Every test here works in `tmp_path` under the real-session guard; the shell is the fake command of `conftest.FakeShell`, never the real one.
"""

import json
import os
import re
import shutil
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from test_shell_config_form_window import FormWindow
from test_shell_config_services import MAIN, RECORDED, check_answer, finding
from test_shell_config_structure_window import pick, value_of
from test_shell_config_window import CONFIG

from tess_shell_config import cli
from tess_shell_config.app import build
from tess_shell_config.files import state_dir
from tess_shell_config.form import Form, coverage
from tess_shell_config.model import DocumentModel
from tess_shell_config.session import ConfigSession
from tess_shell_config.shell import ShellCommand
from tess_shell_config.tdl import walk
from tess_shell_config.widgets import LengthWidget, NumberWidget, Refused

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[2] / "tests"))
import real_session  # noqa: E402
TESS_SHELL = Path("/home/phil/Projects/pyDev/projects/tess-shell/src/tess_shell/shipped")


# -- (c) the shipped default configuration opens and shows no finding -----------------------------------------------------------------

def test_the_application_starts_opens_the_shells_default_configuration_and_shows_no_finding(tmp_path, fake_shell):
    folder = tmp_path / "config_clean"
    shutil.copytree(RECORDED / "config_clean", folder)
    fake_shell.answer("check", (RECORDED / "check_clean.json").read_text())
    session = cli.start(str(folder), str(fake_shell.path), str(tmp_path / "state"), shell=ShellCommand(str(fake_shell.path)))  # the command found, the schema read through the (fake) shell
    built = build(session, reduced_motion=True)
    vm = built.viewmodel
    for _ in range(8):
        built.window.advance(16)
    assert sorted(f.rel for f in session.files) == ["Shells/Main_Shell.tdl", "Themes/Dark_Theme.tdl"] and all(f.parses for f in session.files)
    built.shortcuts.handle("F5")  # the keyboard asks for the check
    for _ in range(6):
        built.window.advance(16)
    assert any(c.startswith("check") and str(folder) in c for c in fake_shell.calls())
    assert vm.problems.get() == [] and not vm.has_problems.get() and vm.problems_title.get() == "Problems: none (2 files checked)"
    vm.open_file("Shells/Main_Shell.tdl")
    assert vm.has_tree.get() and not vm.status_is_error.get()


# -- (b) open and save unchanged, byte for byte, for the shell's shipped default configuration ---------------------------------------

RECORDED_FILES = sorted((RECORDED / "config_clean").rglob("*.tdl")) + sorted((RECORDED / "config_findings").rglob("*.tdl"))
LIVE_FILES = sorted(TESS_SHELL.rglob("*.tdl")) if TESS_SHELL.is_dir() else []


@pytest.mark.parametrize("source", RECORDED_FILES + LIVE_FILES, ids=lambda p: "/".join(p.parts[-3:]))
def test_every_file_of_the_shells_shipped_configuration_opens_and_saves_byte_for_byte(source, tmp_path):
    folder = tmp_path / "cfg"
    target = folder / "Shells" / "X_Shell.tdl"
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    before = source.read_bytes()
    session = ConfigSession(folder, state_dir=tmp_path / "state")
    model = session.open("Shells/X_Shell.tdl")
    assert model.data == before and (model.valid or "config_findings" in source.parts)  # the findings fixture is the one file with a fault in it
    session.save()
    assert target.read_bytes() == before and source.read_bytes() == before


def test_the_shipped_files_are_there_to_be_tested():
    assert len(RECORDED_FILES) == 3 and (not TESS_SHELL.is_dir() or len(LIVE_FILES) >= 30)


# -- (a) the whole-schema coverage test lists what fell back, each with its reason ---------------------------------------------------

def test_every_key_that_got_the_generic_field_has_a_stated_reason(schema):
    report = coverage(schema)
    assert report.fallbacks and all(f.reason.strip() and len(f.reason) > 20 for f in report.fallbacks)
    assert {f.kind for f in report.fallbacks} == {"", "shadows", "tooltip"}
    assert {f.kind for f in report.fallbacks if f.kind} == {"shadows", "tooltip"}
    assert all(f.where.startswith("tokens") for f in report.fallbacks if f.kind == "shadows")  # a token whose value is a list of Shadow blocks: a block key has its button, a token has no block to add to


# -- (d) a value outside a key's range cannot be written from its widget ------------------------------------------------------------

def ranged(schema):
    found = []
    for where, key, widget in coverage(schema).entries:
        if isinstance(widget, (NumberWidget, LengthWidget)) and (key.minimum is not None or key.maximum is not None):
            found.append((where, key, widget))
    return found


def test_a_value_outside_the_range_of_any_key_is_refused_by_its_widget_with_the_range(schema):
    entries = ranged(schema)
    assert len(entries) >= 40
    for where, key, widget in entries:
        for bad in ((Decimal(str(key.minimum)) - 1,) if key.minimum is not None else ()) + ((Decimal(str(key.maximum)) + 1,) if key.maximum is not None else ()):
            if isinstance(widget, LengthWidget):
                edit = {"text": str(bad), "unit": "px" if "px" in widget.key.units or not widget.key.units else widget.key.units[0]}
            else:
                edit = {"text": str(bad)}
            with pytest.raises(Refused) as caught:
                widget.write(edit)
            assert re.search(r"\d", str(caught.value)), (where, key.name, str(caught.value))


def test_a_refused_value_writes_nothing_in_the_form_for_every_ranged_block_key(schema):
    """Through the form's commit, not only the widget: the document is unchanged and the cell says why."""
    done = 0
    for where, key, widget in ranged(schema):
        if where.startswith(("tokens", "module")) or isinstance(widget, LengthWidget) or key.maximum is None:
            continue
        text = f"---\nTDL: 0.1\nName: R\n---\nShell {{ Monitor {{ Name: M, Index: default, {where} {{ Name: B }} }} }}\n"
        model = DocumentModel.from_bytes(text.encode())
        node = next((n for n in walk(model.document.root) if getattr(n, "type", "") == where), None)
        if node is None:
            continue
        model.select(tuple(node.index_path))
        form = Form(schema)
        form.build(model)
        if f"k:{key.name}|" not in form._cells:
            continue
        before = model.text
        outcome = form.commit(f"k:{key.name}|", {"text": str(Decimal(str(key.maximum)) + 1)})
        assert not outcome.ok and not outcome.changed and model.text == before and form.errors.get(f"k:{key.name}|"), (where, key.name)
        done += 1
    assert done >= 5


# -- (e) a token chosen for a colour key ---------------------------------------------------------------------------------------------

def test_a_token_for_a_colour_key_writes_color_dot_name_and_the_list_has_only_the_accepted_groups_preferred_first(schema):
    keys = [(where, key) for where, key in schema.walk_keys() if key.kind == "color" and key.tokens]
    assert len(keys) >= 10
    for where, key in keys:
        groups = [g for g in key.tokens if g in schema.tokens]
        found = schema.tokens_for(key)
        assert {t.group for t in found} == set(groups) and {t.group for t in found} <= set(key.tokens)
        preferred = schema.preferred_refs(key)
        assert [t.ref for t in found][: len(preferred)] == preferred, (where, key.name)
    where, key = next((w, k) for w, k in keys if k.preferred_tokens)
    text = f"---\nTDL: 0.1\nName: T\n---\nShell {{ Monitor {{ Name: M, Index: default, {where} {{ Name: B }} }} }}\n"
    model = DocumentModel.from_bytes(text.encode())
    node = next(n for n in walk(model.document.root) if getattr(n, "type", "") == where)
    model.select(tuple(node.index_path))
    form = Form(schema)
    form.build(model)
    cell = f"k:{key.name}|"
    listed = form.tokens_for(cell)
    assert {t["group"] for t in listed} <= set(key.tokens) and [t["ref"] for t in listed][:1] == schema.preferred_refs(key)[:1]
    token = next(t for t in listed if t["group"] == "color")
    assert form.use_token(cell, token["ref"]).changed and f"{key.name}: $color.{token['name']}" in model.text


# -- (f) every action works from the keyboard alone: one pass, check included ---------------------------------------------------------

def test_one_pass_from_the_keyboard_alone_open_select_change_add_move_duplicate_undo_redo_save_and_check(folder_copy, tmp_path, schema, fake_shell):
    folder = folder_copy
    fake_shell.answer("check", check_answer(finding(17, 13, "Width is wrong.")), fails=True)
    session = ConfigSession(folder, schema, ShellCommand(str(fake_shell.path)), state_dir=tmp_path / "state")
    built = build(session, reduced_motion=True)
    w = FormWindow.__new__(FormWindow)
    w.session, w.built, w.vm, w.window = session, built, built.viewmodel, built.window
    w.settle(8)
    main = folder / "Shells" / "Main_Shell.tdl"
    original = main.read_bytes()
    w.row("f:Shells/Main_Shell.tdl")
    w.key("enter")  # open
    w.key("F6")
    w.row(value_of(w, "Bar  Top_Bar"))
    w.key("enter")  # select
    w.key("F6")
    w.tab(4)
    w.key("enter")
    w.tab(3)
    assert w.where() == "k:Height.field"
    w.type_over("48")
    w.key("Enter")  # change a value
    changed = w.session.model.text
    assert w.diff(original.decode()) == ["-Height: 32", "+Height: 48"]
    w.key("F6")
    w.key("F6", shift=True)
    w.key("F6", shift=True)
    assert w.region() == 1
    w.key("n", ctrl=True, shift=True)
    pick(w, "Box")  # add a block
    added = w.session.model.text
    w.key("arrow_down", alt=True)  # move
    moved = w.session.model.text
    assert moved.index("Popup {") < moved.index("Bar {")
    w.key("d", ctrl=True, shift=True)  # duplicate
    assert w.session.model.text.count("Name: Top_Bar_Copy") == 1
    for earlier in (moved, added, changed):
        w.key("z", ctrl=True)  # undo
        assert w.session.model.text == earlier
    w.key("y", ctrl=True)  # redo
    w.key("y", ctrl=True)
    assert w.session.model.text == moved and main.read_bytes() == original
    w.key("s", ctrl=True)  # save
    assert main.read_bytes() == moved.encode() and not w.vm.dirty.get()
    assert [c for c in fake_shell.calls() if c.startswith("check")], "a save runs check"
    w.key("F5")  # check
    assert w.vm.problems.get() and w.vm.has_problems.get() and "Width is wrong." in w.vm.problems.get()[0]["message"]


@pytest.fixture
def folder_copy(tmp_path):
    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    return target


# -- (g) no test reads or writes outside its folder ---------------------------------------------------------------------------------------

def test_the_guard_makes_the_xdg_folders_private_so_the_app_never_reaches_the_real_session(tmp_path):
    """The guard of the repository's tests (`tests/real_session.py`, applied by this package's conftest) applied to a stand-in for a desktop environment: no display, no bus, every XDG folder private, and the
    application's own state folder inside them."""
    desktop = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus", "HOME": "/home/someone", "XDG_STATE_HOME": "/home/someone/.local/state",
               "XDG_CONFIG_HOME": "/home/someone/.config", "XDG_RUNTIME_DIR": "/run/user/1000"}
    removed = real_session.keep_off_the_real_session(desktop)
    assert set(removed) == {"DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"} and not {"DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"} & set(desktop)
    for name in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR"):
        assert Path(desktop[name]).is_absolute() and not desktop[name].startswith("/home/someone") and desktop[name] != "/run/user/1000" and Path(desktop[name]).is_dir(), name
    assert state_dir(desktop) == Path(desktop["XDG_STATE_HOME"]) / "tesserae-shell-config" and not str(state_dir(desktop)).startswith("/home/someone")
    # and in this run, unless the environment allows the real session on purpose (CI, or TESS_UI_ALLOW_REAL_SESSION), the same holds for the real environment
    if not (os.environ.get("CI") or os.environ.get("TESS_UI_ALLOW_REAL_SESSION") == "1"):
        assert not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")
        assert state_dir().is_relative_to(Path(os.environ["XDG_STATE_HOME"])) and not state_dir().is_relative_to(Path.home() / ".local")


def test_no_window_test_builds_a_session_on_the_default_state_folder():
    """A session made with no `state_dir` would write backups and settings under the real `$XDG_STATE_HOME`: every test of this package gives one (the conftest's fixtures are built on tmp_path)."""
    offenders = []
    for path in HERE.glob("test_*.py"):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if "ConfigSession(" in line and "state_dir" not in line and not line.lstrip().startswith(("#", "class ")) and "def " not in line:
                offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert offenders == [], offenders


# -- the user guide: every shortcut of the code is in one table of the README and of the guide ------------------------------------------------

def table_keys(text):
    """The first cells of the rows of every markdown table in `text`."""
    return {line.split("|")[1].strip() for line in text.splitlines() if line.startswith("| ") and line.count("|") >= 3 and not line.startswith("| ---")}


def test_every_shortcut_of_the_code_is_in_the_readmes_and_the_guides_keyboard_tables():
    from tess_shell_config import shortcuts

    wanted = {k for k in table_keys(shortcuts.__doc__) if k != "Keys"}
    assert len(wanted) >= 15
    readme = table_keys((HERE.parent / "README.md").read_text())
    guide = table_keys((HERE.parents[2] / "docs" / "guide" / "shell-config.md").read_text())
    assert wanted <= readme, sorted(wanted - readme)
    assert wanted <= guide, sorted(wanted - guide)
    for common in ("Tab, Shift+Tab", "Arrow keys, Enter", "Space, Enter", "Escape"):
        assert common in readme and common in guide


def test_every_screenshot_of_the_guide_is_a_file():
    guide = HERE.parents[2] / "docs" / "guide"
    pictures = re.findall(r"!\[[^\]]*\]\((img/[^)]+)\)", (guide / "shell-config.md").read_text())
    assert len(pictures) == 3 and all((guide / p).stat().st_size > 20000 for p in pictures)
