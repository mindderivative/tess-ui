"""The window's two budgeted actions, as counts (not clock time, which varies by machine): selecting a block and one committed edit each compose the window ONCE.

Before the fix a selection set off about ten whole-window syncs (every changed `Signal`, and every region whose children changed, ran the window's effect at once); the cost of one sync is
what is left. The times measured on the development machine are in LOG.md; `tools/perf.py` measures them again.
"""

import shutil
from pathlib import Path

import pytest

from tess_ui import composed

from tess_shell_config.app import build
from tess_shell_config.session import ConfigSession

CONFIG = Path(__file__).parent / "fixtures" / "config"


@pytest.fixture
def window(tmp_path, schema):
    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    built = build(ConfigSession(folder, schema, None, state_dir=tmp_path / "state"), reduced_motion=True)
    for _ in range(8):
        built.window.advance(16)
    built.viewmodel.open_file("Shells/Main_Shell.tdl")
    for _ in range(4):
        built.window.advance(16)
    return built


def rows(nodes):
    for row in nodes:
        yield row
        yield from rows(row.get("children", []))


@pytest.fixture
def syncs(monkeypatch):
    """How many times the window was brought in line with its composition."""
    count = []
    original = composed.ComposedView.reconcile

    def counted(self, *args, **kwargs):
        count.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(composed.ComposedView, "reconcile", counted)
    return count


def test_selecting_a_block_composes_the_window_once(window, syncs):
    vm = window.viewmodel
    targets = {r["label"]: r["value"] for r in rows(vm.structure_nodes.get())}
    for label in ("Bar  Top_Bar", "Monitor  Primary", "Bar  Top_Bar", "Popup  Calendar_Popup"):
        syncs.clear()
        vm.structure_selected.set(targets[label])
        assert len(syncs) == 1, (label, len(syncs))
        assert vm.form_items.get()


def test_one_committed_edit_composes_the_window_once_and_an_unchanged_value_not_at_all(window, syncs):
    vm = window.viewmodel
    vm.structure_selected.set(next(r["value"] for r in rows(vm.structure_nodes.get()) if r["label"] == "Bar  Top_Bar"))
    for value in ("40", "41", "42"):
        syncs.clear()
        vm.form_commit("k:Height|", {"text": value})
        assert len(syncs) == 1, (value, len(syncs))
        assert f"Height: {value}" in window.viewmodel.session.model.text
    syncs.clear()
    vm.form_commit("k:Height|", {"text": "42"})  # the same value: nothing is written, nothing is composed
    assert syncs == []


def test_a_group_opening_composes_the_window_once(window, syncs):
    vm = window.viewmodel
    vm.structure_selected.set(next(r["value"] for r in rows(vm.structure_nodes.get()) if r["label"] == "Bar  Top_Bar"))
    syncs.clear()
    vm.form_group("Size")
    assert len(syncs) == 1


def test_a_closed_structure_menu_is_not_part_of_the_window(window):
    names = {inst.name for inst in window.view.handle.composition.walk() if inst.name}
    assert "structure_menu" not in names
    window.viewmodel.structure_actions.open_menu()
    for _ in range(4):
        window.window.advance(16)
    assert "structure_menu" in {inst.name for inst in window.view.handle.composition.walk() if inst.name}
