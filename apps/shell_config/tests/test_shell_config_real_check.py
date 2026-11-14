"""Against the REAL checker: what the application writes is run through `tesserae-shell check --json` and `tesserae-shell schema --json` of the shell itself (tess-shell at a3083ca), not the recorded fixtures.

The module is on only when the shell's checkout (`/home/phil/Projects/pyDev/projects/tess-shell`, or `TESS_SHELL_CHECKOUT`) is there AND a virtual environment of its own with `tesserae-shell` installed from that commit
(`TESS_SHELL_VERIFY_VENV`, default `tesserae-shell-verify-venv` beside the repository); otherwise it is skipped with that reason. The commands are the two that only read files and start no shell: each runs with an
environment built from scratch (PATH, HOME and XDG_* in a temporary folder, no DISPLAY, WAYLAND_DISPLAY or DBUS), on a temporary configuration folder given with `--config-dir`. Nothing here starts, reloads or asks a shell.

What is written: a new file of every type by the application's own new-file code, every block a structure edit can add (to every block that may hold it, down from each file's root), every selector the builder makes, a
theme's modes and shadows, the For/If edits, the calls of every module (a user module named like a shipped one among them), and one sample edit of every key of every block, setting, module param and token through the form.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

import tess_dl
from tess_shell_config import fileops
from tess_shell_config.blocks import HOLDER, add_child, children_of, has_layout, holder_of, is_layout, mode_names, module_layout
from tess_shell_config.folder import FileType
from tess_shell_config.form import Form, coverage
from tess_shell_config.model import DocumentModel
from tess_shell_config.schema import Schema
from tess_shell_config.selector import BASES, STATES, Selector, SelectorStore
from tess_shell_config.tdl import walk

REPO = Path(__file__).resolve().parents[3]
SHELL_CHECKOUT = Path(os.environ.get("TESS_SHELL_CHECKOUT", "/home/phil/Projects/pyDev/projects/tess-shell"))
VENV = Path(os.environ.get("TESS_SHELL_VERIFY_VENV", REPO.parent / "tesserae-shell-verify-venv"))
SHELL = VENV / "bin" / "tesserae-shell"

REASON = f"needs the shell's checkout ({SHELL_CHECKOUT}) and a venv with tesserae-shell installed from commit a3083ca ({SHELL}): set TESS_SHELL_CHECKOUT / TESS_SHELL_VERIFY_VENV"
pytestmark = [pytest.mark.real_shell_check, pytest.mark.skipif(not (SHELL_CHECKOUT.is_dir() and SHELL.is_file()), reason=REASON)]

BATCH = 40  # files per check run: the shell prints at most 50 findings


def shell(args: list[str], scratch: Path) -> subprocess.CompletedProcess[str]:
    """Run the real `tesserae-shell` with an environment built from scratch, so that it cannot reach a session, a bus or the real configuration."""
    home = scratch / "home"
    home.mkdir(parents=True, exist_ok=True)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "XDG_CONFIG_HOME": str(home / "c"), "XDG_CACHE_HOME": str(home / "k"), "XDG_DATA_HOME": str(home / "d"), "XDG_RUNTIME_DIR": str(home / "r"), "XDG_STATE_HOME": str(home / "s")}
    return subprocess.run([str(SHELL), *args], env=env, cwd=scratch, capture_output=True, text=True, timeout=300, check=False)


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    severity: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity} {self.file}:{self.line} [{self.rule}] {self.message}"


def check(files: dict[str, str], scratch: Path, support: dict[str, str] | None = None) -> list[Finding]:
    """Every finding of the real `check` on `files` (a path from the configuration folder -> text), in batches of `BATCH` files; `support` files go into every batch (a module the shells call)."""
    found: list[Finding] = []
    items = sorted(files.items())
    for number, start in enumerate(range(0, len(items), BATCH)):
        folder = scratch / f"cfg_{number}"
        for rel, text in {**(support or {}), **dict(items[start:start + BATCH])}.items():
            target = folder / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        done = shell(["check", "--json", "--config-dir", str(folder)], scratch)
        report = json.loads(done.stdout)
        assert report["omitted"] == 0, f"more findings than the shell prints in batch {number}: split the batch"
        found += [Finding(e["file"], e["line"], e["severity"], e["rule"], e["message"]) for e in report["errors"]]
    return found


#: The one warning the real checker gives for a thing the application writes correctly: a `Bitmap` needs a `Source`, an image file the person has not chosen yet. It is the key's own warning, not "not built".
KNOWN_WARNINGS = {"image-not-found"}


def assert_clean(findings: list[Finding], schema: Schema | None = None) -> list[Finding]:
    """No error; a warning only when it is a known one (`KNOWN_WARNINGS`) or says the key is not built. Returns the warnings, for the report."""
    errors = [f for f in findings if f.severity == "error"]
    assert errors == [], "\n".join(str(f) for f in errors[:30])
    unexpected = [f for f in findings if f.severity != "error" and f.rule not in KNOWN_WARNINGS and "not built" not in f.message.lower()]
    assert unexpected == [], "\n".join(str(f) for f in unexpected[:30])
    return [f for f in findings if f.severity != "error"]


# -- the shell's own schema -------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_schema_text(tmp_path_factory):
    done = shell(["schema", "--json"], tmp_path_factory.mktemp("schema"))
    assert done.returncode == 0, done.stderr[-500:]
    return done.stdout


@pytest.fixture(scope="module")
def real_schema(real_schema_text):
    return Schema.from_json(real_schema_text)


def test_the_real_schema_is_read_by_the_applications_reader_and_its_coverage_report_lists_what_has_no_kind(real_schema, real_schema_text, schema):
    data = json.loads(real_schema_text)
    assert real_schema.version >= (1, 3) and list(real_schema.roots) == list(data["roots"]) and list(real_schema.modules) == list(data["modules"])
    assert not (set(real_schema.extra) - {"shortcuts"}), "a table the reader does not know yet: " + ", ".join(sorted(real_schema.extra))
    report = coverage(real_schema)
    assert {f.kind for f in report.fallbacks} == {"", "shadows", "tooltip"}
    no_kind = [(w, k.name) for w, k, widget in report.entries if widget.reason and not k.kind]
    recorded = [(w, k.name) for w, k, widget in coverage(schema).entries if widget.reason and not k.kind]
    # the real schema 1.3 gives `Bar.Reveal_Key` a kind (key_chord) and it is built: 12 entries without a kind against the recorded 1.2's 13
    assert len(recorded) - len(no_kind) == 1 and set(recorded) - set(no_kind) == {("Bar", "Reveal_Key")}
    assert len(report.entries) == len(list(real_schema.walk_keys())) + sum(len(m.params) for m in real_schema.modules.values()) + sum(len(t) for t in real_schema.tokens.values())


# -- files -------------------------------------------------------------------------------------------------------------------------

def test_a_new_file_of_every_type_is_accepted(tmp_path, real_schema):
    folder = tmp_path / "new"
    folder.mkdir()
    files = {}
    for file_type in (FileType.SHELL, FileType.MODULE, FileType.STYLE, FileType.STYLESHEET, FileType.THEME, FileType.SETTINGS):
        rel = fileops.create(folder, [], file_type, "Mine", module_layout(real_schema))
        files[rel] = (folder / rel).read_text()
    assert len(files) == 6
    assert_clean(check(files, tmp_path))


# -- structure edits: every block the Add menu offers, to every block that may hold it ---------------------------------------------

ROOTS = {FileType.SHELL: "Shell", FileType.MODULE: "Module", FileType.STYLE: "Style", FileType.STYLESHEET: "Stylesheet", FileType.THEME: "Theme", FileType.SETTINGS: "Settings"}
REL = {FileType.SHELL: "Shells/{n}_Shell.tdl", FileType.MODULE: "Modules/{n}/{n}_Module.tdl", FileType.STYLE: "Styles/{n}_Style.tdl", FileType.STYLESHEET: "Stylesheets/{n}_Stylesheet.tdl", FileType.THEME: "Themes/{n}_Theme.tdl",
       FileType.SETTINGS: "settings.tdl"}


def new_model(file_type: FileType, schema: Schema, name: str, layout: bool = True) -> DocumentModel:
    return DocumentModel(fileops.minimal_text(file_type, name, module_layout(schema) if layout and file_type is FileType.MODULE else ""))


def chain_to(schema: Schema, root: str, target: str, parent_of: str = "") -> list[str] | None:
    """The block types from `root` down to a block of type `target` (the first way the Add menus reach it), or `None`."""
    queue, seen = [[root]], {root}
    while queue:
        path = queue.pop(0)
        if path[-1] == target:
            return path
        for child in children_of(schema, path[-1], path[-2] if len(path) > 1 else ""):
            if child.module or child.type in seen or child.type == HOLDER:
                continue
            seen.add(child.type)
            queue.append([*path, child.type])
    return None


def structure_files(schema: Schema) -> tuple[dict[str, str], int]:
    """One file for every (block, block it may hold) pair reachable from a file's root: the holder is made the way the application makes it (add_child), the child last. Settings: one file, every section."""
    files: dict[str, str] = {}
    pairs = 0
    for file_type, root in ROOTS.items():
        if file_type is FileType.SETTINGS:
            model = new_model(file_type, schema, "Settings")
            for child in children_of(schema, root):
                add_child(model, schema, (), child.type)
                pairs += 1
            files[REL[file_type].format(n="Settings")] = model.text
            continue
        holders = {root}
        queue = [root]
        while queue:  # every block type that can be reached, as a holder
            for child in children_of(schema, queue.pop(0)):
                if child.type != HOLDER and not child.module and child.type not in holders:
                    holders.add(child.type)
                    queue.append(child.type)
        for holder in sorted(holders):
            way = chain_to(schema, root, holder)
            if way is None:
                continue
            for child in children_of(schema, holder, way[-2] if len(way) > 1 else ""):
                if child.type == HOLDER:
                    continue
                # a name no other file of the folder has; a module that gets its layout from the edit does not start with one
                model = new_model(file_type, schema, f"P{pairs + 1}", layout=not is_layout(schema, root, way[1] if len(way) > 1 else child.type))
                path: tuple[int, ...] = ()
                for step in way[1:]:
                    path = add_child(model, schema, path, step)
                add_child(model, schema, path, child.type)
                pairs += 1
                files[REL[file_type].format(n=f"P{pairs}_{holder}_{child.type}")] = model.text
    return files, pairs


def test_every_block_the_add_menu_offers_is_accepted_where_it_is_added(tmp_path, real_schema):
    files, pairs = structure_files(real_schema)
    assert pairs > 250, pairs
    warnings = assert_clean(check(files, tmp_path))
    print(f"{pairs} (holder, child) pairs written; warnings: {sorted({(w.rule, w.message.split(' at ')[0]) for w in warnings})}")


# -- form edits: one sample edit of every key, through the form --------------------------------------------------------------------

def make_model(schema: Schema, file_type: FileType, way: list[str], name: str) -> tuple[DocumentModel, tuple[int, ...]]:
    """A new file of `file_type` with the blocks of `way` (from its root down) added the way the application adds them; the path of the last one."""
    model = new_model(file_type, schema, name, layout=len(way) <= 1 or not is_layout(schema, way[0], way[1]))
    path: tuple[int, ...] = ()
    for step in way[1:]:
        path = add_child(model, schema, path, step)
    return model, path


def form_targets(schema: Schema) -> list[tuple[FileType, list[str]]]:
    """Every kind of block a form is shown for: each block type reachable from a file's root, and a call of every module in a Bar."""
    found: list[tuple[FileType, list[str]]] = []
    for file_type, root in ROOTS.items():
        seen, queue = {root}, [root]
        while queue:
            for child in children_of(schema, queue.pop(0)):
                if child.type != HOLDER and not child.module and child.type not in seen:
                    seen.add(child.type)
                    queue.append(child.type)
        found += [(file_type, way) for t in sorted(seen) if (way := chain_to(schema, root, t)) is not None]
    bar = chain_to(schema, "Shell", "Bar")
    assert bar is not None
    found += [(FileType.SHELL, [*bar, module]) for module in schema.modules]
    return found


def form_files(schema: Schema, scratch: Path) -> tuple[dict[str, str], dict[str, str], int]:
    """One file per key and block type: the new file, and the form's sample edit of that one key. Settings: one file per section with all its keys (the folder has one `settings.tdl`).
    Returns the files, the key each file edits (`rel -> key name`; a settings file: `""`) and the number of edits."""
    files: dict[str, str] = {}
    keys: dict[str, str] = {}
    edits = 0
    for file_type, way in form_targets(schema):
        base, path = make_model(schema, file_type, way, "Base")
        base_text = base.text
        base.select(path)
        form = Form(schema)
        view = form.build(base, scratch)
        cells = [c.id for row in view.rows if not row.id.startswith("s:") for c in row.cells if c.widget is not None and not c.readonly]
        target = " ".join(way[-2:]) if len(way) > 1 else way[0]
        if file_type is FileType.SETTINGS:
            model = DocumentModel(base_text)
            model.select(path)
            form = Form(schema)
            for cell_id in cells:
                form.build(model, scratch)
                assert form.commit(cell_id, form.cell(cell_id).widget.sample_edit()).ok, (target, cell_id)
                edits += 1
            rel = f"settings_{'_'.join(way)}.tdl"  # moved to the folder's one settings.tdl by the caller
            files[rel], keys[rel] = model.text, ""
            continue
        for cell_id in cells:
            model = DocumentModel(base_text)
            model.select(path)
            form = Form(schema)
            form.build(model, scratch)
            outcome = form.commit(cell_id, form.cell(cell_id).widget.sample_edit())
            assert outcome.ok, f"{target} {cell_id}: {outcome.message}"
            edits += 1
            model.set_metadata("Name", f"K{edits}")
            rel = REL[file_type].format(n=re.sub(r"[^A-Za-z0-9_]", "_", f"K{edits}_{target}_{cell_id}"))
            files[rel], keys[rel] = model.text, cell_id.removeprefix("k:").rstrip("|").split("|")[0]
    return files, keys, edits


#: What the real checker still says about ONE sample edit of ONE key, and why it is not the application's fault: the sample is a value that does not stand alone. By key name -> rules.
#: (a) a name that must refer to something the file does not have: `Class` (a class of the module's style), `Selector` (a block name), `Attach_To`; (b) a file that is not there: `Source` of an SVG (and `Bitmap`: `image-not-found`);
#: (c) a key that needs another or is refused without it (Panel's placement keys, a Frame's `Border_Width` and `Border_Color`); (d) the checker's own disagreement with its schema: `Part` is only valid in a module's file but the
#: schema does not say so (`part-outside-module`), a stylesheet Rule's `Text_Align` has no allowed values (`bad-value`, "is not one of "), `Wrap` and `Lines` on a single-line TextField (`key-not-applied`, warning).
STANDS_ALONE = {
    "Class": {"class-not-found"}, "Selector": {"unknown-key"}, "Attach_To": {"missing-key", "attach-unknown"}, "Part": {"part-outside-module"}, "Source": {"bad-key", "bad-value", "image-not-found"},
    "Attach": {"attach-orphan"}, "Gap": {"attach-orphan"}, "Alignment": {"attach-orphan"}, "Meld": {"missing-key", "meld-size", "meld-target"}, "Depth": {"meld-size-orphan"}, "Length": {"meld-size-orphan"},
    "Peek": {"peek-window"}, "Border_Width": {"missing-key"}, "Border_Color": {"missing-key"}, "Text_Align": {"bad-value"}, "Wrap": {"key-not-applied"}, "Lines": {"key-not-applied"},
}
#: The same for a settings section (all its keys written in one file): the sample paths and names refer to files and themes the folder does not have, and the sample shortcuts are all the same chord.
SETTINGS_STAND_ALONE = {"relative-path", "main-shell-not-found", "theme-not-found", "stylesheet-not-found", "shortcut-conflict"}


def test_one_sample_edit_of_every_key_of_every_block_is_accepted(tmp_path, real_schema):
    files, keys, edits = form_files(real_schema, tmp_path)
    settings = {rel: text for rel, text in files.items() if rel.startswith("settings_")}
    others = {rel: text for rel, text in files.items() if rel not in settings}
    assert edits > 2500, edits
    found = check(others, tmp_path)
    for number, (rel, text) in enumerate(sorted(settings.items())):  # one settings.tdl for each folder
        alone = tmp_path / f"settings_{number}"
        alone.mkdir()
        found += [Finding(rel, f.line, f.severity, f.rule, f.message) for f in check({"settings.tdl": text}, alone)]
    by_number = {int(m.group(1)): key for rel, key in keys.items() if (m := re.search(r"/K(\d+)_", rel))}
    unexplained, explained = [], 0
    for f in found:
        number = re.search(r"/K(\d+)_", f.file)
        key = by_number.get(int(number.group(1)), "") if number else ""
        in_settings = f.file in settings
        allowed = STANDS_ALONE.get(key, set()) | (SETTINGS_STAND_ALONE if in_settings else set()) | KNOWN_WARNINGS  # a Bitmap always lacks the image file it needs
        if f.rule in allowed or (f.severity == "warning" and (f.rule == "not-built" or "not built" in f.message.lower())):
            explained += 1
        else:
            unexplained.append(f"{f} (edit of {key or 'a section'})")
    assert unexplained == [], "\n".join(unexplained[:40])
    print(f"{edits} edits in {len(files)} files; {len(found)} findings, all explained ({explained}): not built or a sample that cannot stand alone")


# -- stylesheet selectors --------------------------------------------------------------------------------------------------------

def selector_forms() -> list[Selector]:
    """Every form the builder makes: a block or module name, a class, a name; each with every state; a module name also with a part."""
    forms = []
    for base, targets in {BASES[0]: ("Text", "Clock", "Slider"), BASES[1]: ("warn",), BASES[2]: ("clock_label",)}.items():
        for target in targets:
            for part in ("", "track") if base == BASES[0] and target != "Text" else ("",):  # the real checker: "::track is a part of a module and Text is no module"
                forms += [Selector(base, target, part, state) for state in ("", *STATES)]
    return forms


def test_every_selector_the_builder_makes_is_accepted(tmp_path, real_schema):
    model = new_model(FileType.STYLESHEET, real_schema, "Sel")
    expected = []
    for selector in selector_forms():
        path = add_child(model, real_schema, (), "Rule")
        for part in ("target", "base", "part", "state"):  # the builder's rows, in the order a person fills them
            value = {"target": selector.target, "base": selector.base, "part": selector.part, "state": selector.state}[part]
            if value:
                SelectorStore(path, part).write(model, value)
        expected.append(selector.text())
    written = re.findall(r'Selector: "([^"]*)"', model.text)
    assert written == expected and len(expected) == len(set(expected)) > 30
    warnings = assert_clean(check({"Stylesheets/Sel_Stylesheet.tdl": model.text}, tmp_path))
    assert {w.rule for w in warnings} <= {"not-built"}, warnings  # :focused ("no block can take focus yet"), the real shell's own words


# -- a theme's modes and shadows ---------------------------------------------------------------------------------------------------

def test_a_theme_with_every_mode_every_token_group_and_the_shadows_of_a_token_is_accepted(tmp_path, real_schema):
    model = new_model(FileType.THEME, real_schema, "Full")
    path_of_group = {}
    for child in children_of(real_schema, "Theme"):
        path_of_group[child.type] = add_child(model, real_schema, (), child.type)
    modes = next(p for t, p in path_of_group.items() if t == "Modes")
    for mode in mode_names(real_schema):
        mode_path = add_child(model, real_schema, modes, mode)
        for group in children_of(real_schema, mode):
            add_child(model, real_schema, mode_path, group.type)
    # a token in the base and in every mode column, through the form, for every group
    form = Form(real_schema)
    cells = 0
    for group, group_path in sorted(path_of_group.items()):
        if group == "Modes":
            continue
        model.select(next(n.index_path for n in walk(model.document.root) if getattr(n, "type", "") == group and tuple(n.index_path) == tuple(model.node_at(group_path).index_path)))
        view = form.build(model, tmp_path)
        for row in view.rows:
            if row.id.startswith("t:") and len(row.cells) > 1 and all(c.widget is not None and not c.readonly for c in row.cells):
                for cell in row.cells:
                    if form.commit(cell.id, cell.widget.sample_edit()).ok:
                        cells += 1
                break
    assert cells >= 5 * len(mode_names(real_schema)), cells
    warnings = assert_clean(check({"Themes/Full_Theme.tdl": model.text}, tmp_path))
    print(f"theme: {cells} token cells over {len(mode_names(real_schema))} modes + base; warnings {[w.rule for w in warnings]}")


def test_a_shadows_block_of_a_surface_and_of_a_drawn_block_is_accepted(tmp_path, real_schema):
    files = {}
    for number, way in enumerate((["Shell", "Monitor", "Bar"], ["Shell", "Monitor", "Bar", "Box"], ["Shell", "Monitor", "Panel", "FlexBox"])):
        model, path = make_model(real_schema, FileType.SHELL, way, f"Sh{number}")
        model.select(path)
        form = Form(real_schema)
        form.build(model, tmp_path)
        outcome = form.commit("k:Shadows|", form.cell("k:Shadows|").widget.sample_edit())
        assert outcome.ok and "Shadows" in model.text, outcome.message
        files[f"Shells/Sh{number}_Shell.tdl"] = model.text
    assert_clean(check(files, tmp_path))


# -- For and If ------------------------------------------------------------------------------------------------------------------------

FLOW = """---
TDL: 0.1
Name: Flow
---
Shell {
  Monitor {
    Name: Main
    Children {
      Bar {
        Name: Top_Bar
        Edge: TOP
        Width: EXPAND
        Height: 32
        Children {
          If {{ true }} {
            Text { Text: "yes" }
          } Else {
            Text { Text: "no" }
          }
          For tile In {{ [1, 2, 3] }} Key {{ tile }} {
            Text { Text: {{ tile }} }
          }
        }
      }
    }
  }
}
"""


def test_a_for_and_an_if_after_every_edit_of_their_parts_are_accepted(tmp_path, real_schema):
    before = check({"Shells/Flow_Shell.tdl": FLOW}, tmp_path / "before")
    assert [f for f in before if f.severity == "error"] == [], before
    model = DocumentModel(FLOW)
    node = {type(n).__name__: n for n in walk(model.document.root) if type(n).__name__ in ("If", "For")}
    model.set_flow(node["If"].index_path, "condition", "{{ false }}")
    model.set_flow(next(n for n in walk(model.document.root) if type(n).__name__ == "For").index_path, "items", "{{ [4, 5] }}")
    model.set_flow(next(n for n in walk(model.document.root) if type(n).__name__ == "For").index_path, "key", "{{ tile }}")
    model.set_flow(next(n for n in walk(model.document.root) if type(n).__name__ == "For").index_path, "variable", "entry")
    text = model.text.replace("Text: {{ tile }}", "Text: {{ entry }}").replace("Key {{ tile }}", "Key {{ entry }}")
    assert "For entry In {{ [4, 5] }}" in text and "If {{ false }}" in text
    after = check({"Shells/Flow_Shell.tdl": text}, tmp_path / "after")
    assert [f for f in after if f.severity == "error"] == [], after
    print("For/If warnings:", sorted({(f.rule, f.message[:60]) for f in before + after}))


# -- module calls and user modules -----------------------------------------------------------------------------------------------

USER_CLOCK = """---
TDL: 0.1
Name: Clock
---
Module {
    Params { who { Type: string, Default: "world" } }
    Text { Text: {{ params.who }} }
}
"""

USER_HELLO = USER_CLOCK.replace("Name: Clock", "Name: Hello")


def test_calls_of_a_user_module_named_like_a_shipped_one_and_of_one_of_its_own_are_accepted(tmp_path, real_schema):
    """A user module `Clock` beside the shipped `Clock`: the shell takes the user's (its own params), and the application's Add menu offers the name once."""
    from tess_shell_config.usermodules import read_module, user_modules

    found = user_modules([("Modules/Clock/Clock_Module.tdl", USER_CLOCK, "Clock_Module"), ("Modules/Hello/Hello_Module.tdl", USER_HELLO, "Hello_Module")], real_schema)
    schema = real_schema.with_modules(found)
    assert read_module("Modules/Clock/Clock_Module.tdl", USER_CLOCK, "Clock_Module") is not None and [c.type for c in children_of(schema, "Bar")].count("Clock") == 1
    model, bar = make_model(schema, FileType.SHELL, ["Shell", "Monitor", "Bar"], "Calls")
    for module in ("Clock", "Hello"):
        add_child(model, schema, bar, module)
    form = Form(schema)
    for module in ("Clock", "Hello"):
        node = next(n for n in walk(model.document.root) if getattr(n, "type", "") == module)
        model.select(node.index_path)
        view = form.build(model, tmp_path)
        if "k:who|" in [c.id for row in view.rows for c in row.cells]:
            assert form.commit("k:who|", form.cell("k:who|").widget.sample_edit()).ok
    support = {"Modules/Clock/Clock_Module.tdl": USER_CLOCK, "Modules/Hello/Hello_Module.tdl": USER_HELLO}
    findings = check({"Shells/Calls_Shell.tdl": model.text}, tmp_path, support)
    assert_clean(findings)
