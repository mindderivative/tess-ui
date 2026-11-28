"""The menu bar and the toolbar of the window (the vault's Config App Layout, AC-CFG-9 to AC-CFG-13): one table of commands feeds both, so a toolbar button and the menu entry of the same name are enabled together."""

from __future__ import annotations

import pytest

from test_shell_config_window import CONFIG, Window, folder  # noqa: F401


def entries(menus):
    """Every command entry of the menus, with the submenus walked: (value, row)."""
    yield from rows_of([row for m in menus for row in m["items"]])


def rows_of(items):
    for row in items:
        if row.get("divider"):
            continue
        if "submenu" in row:
            yield from rows_of(row["submenu"])
        else:
            yield row["value"], row


@pytest.fixture
def w(folder, tmp_path):  # noqa: F811
    window = Window(folder, tmp_path)
    window.vm.open_file("Shells/Main_Shell.tdl")
    window.settle(6)
    return window


def titles(w):
    return [w.built.view.node(f"root.menu_row.menubar.strip.title[{i}]") for i in range(4)]


def menu(w):
    return {m["label"]: m["items"] for m in w.vm.menu_bar.get()}


def tool(w, value):
    return w.built.view.node(f"root.toolbar.group.entry[{value}].item")


def open_menus(w):
    return sorted(w.built.view._shown_layers)


def test_the_window_has_a_menu_bar_with_file_edit_view_shell_and_their_mnemonics_AC_CFG_9(w):
    bar = w.built.view.node("root.menu_row.menubar")
    assert bar.get("label") == "Menu bar"
    assert [t.get("label") for t in titles(w)] == ["File", "Edit", "View", "Shell"]
    assert [m["label"] for m in w.vm.menu_bar.get()] == ["&File", "&Edit", "&View", "&Shell"]
    file_menu, edit, view, shell = (menu(w)[k] for k in ("&File", "&Edit", "&View", "&Shell"))
    assert [r.get("label") for r in file_menu if not r.get("divider")] == ["New file...", "Save", "Rename file...", "Duplicate file", "Delete file", "Reload from disk", "Keep my version", "Quit"]
    assert [r.get("label") for r in edit if not r.get("divider")] == ["Undo", "Redo", "Format file", "Structure"]
    assert [r["label"] for r in edit[-1]["submenu"]] == ["Add child block...", "Duplicate block", "Move block into...", "Move up", "Move down", "Remove block"]
    assert [r.get("label") for r in view if not r.get("divider")] == ["Theme", "Go to", "Reset layout"]
    assert [r["label"] for r in view[1]["submenu"]] == ["Files", "Structure", "Editor", "View", "Properties", "Problems"]
    assert [r.get("label") for r in shell if not r.get("divider")] == ["Check", "Reload shell", "Apply as I edit"]
    shortcuts = {value: row.get("shortcut") for value, row in entries(w.vm.menu_bar.get())}
    assert shortcuts["save"] == "Ctrl+S" and shortcuts["quit"] == "Ctrl+Q" and shortcuts["check"] == "F5" and shortcuts["structure_remove"] == "Ctrl+Shift+Delete" and shortcuts["format"] is None


def test_alt_and_a_letter_open_the_menu_from_the_editor_and_a_shortcut_works_with_the_menu_closed_AC_CFG_10(w):
    w.built.view.node("root.dock.text_panel.text_pane.editor").focus() if False else w.built.shortcuts._focus("editor")
    w.settle(2)
    w.key("f", alt=True)
    assert open_menus(w) == ["root.menu_row.menubar.strip.title[0].menu"]
    w.key("escape")
    w.session.model.set_value((0,), "Index", "7")
    w.vm.sync()
    w.key("s", ctrl=True)
    assert b"Index: 7" in (w.session.folder / "Shells" / "Main_Shell.tdl").read_bytes() and open_menus(w) == []


def test_choosing_view_theme_dark_sets_the_theme_and_exactly_one_radio_entry_is_checked_AC_CFG_10(w):
    w.vm.run_command("theme_dark")
    w.settle(4)
    theme = menu(w)["&View"][0]["submenu"]
    assert [(r["label"], r["checked"]) for r in theme] == [("System", False), ("Light", False), ("Dark", True)]
    assert w.vm.services.theme_mode.get() == "dark"
    w.vm.run_command("theme_system")
    assert [r["checked"] for r in menu(w)["&View"][0]["submenu"]] == [True, False, False]


def test_the_apply_toggle_the_check_entry_and_the_signal_are_one_state_AC_CFG_10(w):
    assert tool(w, "apply").get("pressed") is False and menu(w)["&Shell"][-1]["checked"] is False
    w.vm.run_command("apply")
    w.settle(4)
    assert w.vm.apply_on_edit.get() is True and tool(w, "apply").get("pressed") is True and menu(w)["&Shell"][-1]["checked"] is True
    w.window.simulate("click", node=tool(w, "apply"))
    w.settle(4)
    assert w.vm.apply_on_edit.get() is False and tool(w, "apply").get("pressed") is False


def test_a_menu_entry_runs_its_command_by_the_pointer_and_closes_the_menu_AC_CFG_10(w):
    w.session.model.set_value((0,), "Index", "7")
    w.vm.sync()
    w.window.simulate("click", node=titles(w)[0])
    w.settle(6)
    save = w.built.view.node("root.menu_row.menubar.strip.title[0].menu.surface.row[1].item")
    assert save.get("label") == "Save"
    w.window.simulate("click", node=save)
    w.settle(6)
    assert open_menus(w) == [] and not w.vm.dirty.get() and b"Index: 7" in (w.session.folder / "Shells" / "Main_Shell.tdl").read_bytes()


def test_quit_closes_the_window_and_ctrl_q_is_quit_and_reset_layout_puts_the_zones_back(w):
    calls = []
    w.vm.commands.hooks["quit"] = lambda: calls.append("quit")
    w.vm.run_command("quit")
    w.key("q", ctrl=True)
    assert calls == ["quit", "quit"]
    dock = w.built.view.dock_host("root.dock")
    before = dock.layout()
    dock.set_size("left", dock.size("left") + 60)
    assert dock.layout() != before
    w.vm.run_command("reset_layout")
    w.settle(4)
    assert dock.layout() == before


def test_go_to_shows_the_panel_and_moves_the_focus_there_and_a_panel_with_nothing_is_disabled(w):
    rows = {value: row for value, row in entries(w.vm.menu_bar.get())}
    assert rows["go_files"]["disabled"] is False and rows["go_problems"]["disabled"] is True
    w.vm.run_command("go_editor")
    w.settle(4)
    assert w.region() == 2
    w.vm.run_command("go_files")
    w.settle(4)
    assert w.region() == 0
    w.vm.run_command("go_view")
    w.settle(4)
    shown = w.built.view.dock_host("root.dock").dock
    assert shown.shown(shown.side_of(shown.panel("View"))) is shown.panel("View")


def test_every_toolbar_item_has_a_menu_entry_with_the_same_name_shortcut_and_enabled_state_at_every_step_AC_CFG_11(w):
    def parity():
        menu_rows = dict(entries(w.vm.menu_bar.get()))
        for item in w.vm.tool_items.get():
            if item.get("divider"):
                continue
            row = menu_rows[item["value"]]
            assert (row["label"], row.get("shortcut"), row["disabled"]) == (item["label"], item.get("shortcut"), item["disabled"]), item["value"]

    parity()
    w.session.model.set_value((0,), "Index", "7")  # an edit: Save and Undo turn on
    w.vm.sync()
    parity()
    assert not dict(entries(w.vm.menu_bar.get()))["save"]["disabled"] and not dict(entries(w.vm.menu_bar.get()))["undo"]["disabled"]
    w.vm.save()
    parity()
    assert dict(entries(w.vm.menu_bar.get()))["save"]["disabled"]
    w.vm.undo()
    w.vm.redo()
    parity()
    w.vm.services.shell_running.set(True)
    parity()
    assert not dict(entries(w.vm.menu_bar.get()))["reload_shell"]["disabled"]
    w.vm.services.checking.set(True)
    parity()
    assert dict(entries(w.vm.menu_bar.get()))["check"]["disabled"]


def test_the_menu_bar_is_32_and_the_toolbar_40_dp_high_with_32_dp_buttons_at_compact_AC_CFG_12(w):
    assert titles(w)[0].get("layout_height") == 32.0 and w.built.view.node("root.toolbar").get("layout_height") == 40.0
    assert {tool(w, v).get("layout_height") for v in ("save", "undo", "redo", "format", "check", "reload_shell", "apply")} == {32.0}


def test_the_toolbar_is_one_tab_stop_arrows_skip_the_dividers_and_disabled_items_and_the_tooltip_names_the_shortcut_AC_CFG_13(w):
    w.session.model.set_value((0,), "Index", "7")  # Save and Undo turn on, Redo stays off
    w.vm.sync()
    w.settle(4)
    tool(w, "undo").focus()
    w.settle(3)
    w.key("arrow_right")  # Redo is off and a divider follows: the next stop is Format file
    assert w.focused() == ["root.toolbar.group.entry[format].item"]
    assert [t.get("text") for layer in w.built.view._tips.values() for t in layer[0].children()] == ["Format file"]
    w.key("arrow_left")
    assert w.focused() == ["root.toolbar.group.entry[undo].item"]
    assert [t.get("text") for layer in w.built.view._tips.values() for t in layer[0].children()] == ["Undo (Ctrl+Z)"]
