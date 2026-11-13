"""T-034 (1): the icon picker -- `IconBrowser` (the model), the `IconBrowser` control, and the `IconPicker` view inline and in a popup, over `tmp_path` folders and a fake file system.
Nothing here reads outside `tmp_path`."""

import struct
import zlib

import pytest

from tess_ui import App, Signal, ViewModel, filesystem, icons, reactive
from tess_ui.filesystem import Entry, FileSystemError, LocalFileSystem
from tess_ui.icon_controls import IconBrowser, clean_svg, decode_png
from tess_ui.shipped import shipped_views
from tess_ui.spec.nodes import LoadError
from tess_ui.spec.widgets import lookup

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="currentColor"/></svg>'


def png_bytes(width=4, height=4, rgba=(200, 30, 30, 255)):
    """A real PNG, made by hand (the file a user would drop in an icons folder)."""
    raw = b"".join(b"\x00" + bytes(rgba) * width for _ in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def folder(tmp_path, names=("logo.svg", "badge.png", "zeta.SVG", "notes.txt", ".hidden.svg")):
    base = tmp_path / "icons"
    base.mkdir()
    for name in names:
        suffix = name.rsplit(".", 1)[-1].lower()
        (base / name).write_bytes(png_bytes() if suffix == "png" else SVG.encode() if suffix == "svg" else b"text")
    (base / "sub.svg").mkdir()  # a folder named like a file is no icon
    return base


class Counting(LocalFileSystem):
    def __init__(self):
        self.listed, self.read = [], []

    def list_dir(self, path):
        self.listed.append(path)
        return super().list_dir(path)

    def read_bytes(self, path, limit):
        self.read.append(path.rsplit("/", 1)[-1])
        return super().read_bytes(path, limit)


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.icon = Signal("home")
        self.pop = Signal(False)
        self.log = []

    def changed(self):
        self.log.append(self.icon.get())


CALL = '{widget: IconPicker, name: ip, value: "{{ icon }}", on_change: changed%s}'
POPUP = '{widget: IconPicker, name: ip, popup: true, open: "{{ pop }}", value: "{{ icon }}", on_change: changed%s}'


def opened(tmp_path, call=CALL, options="", dark=False, size=(460, 600), sheet=None):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.yaml").write_text(f"""tesserae: 0.6
name: main
widget: Container
style: {{flex_direction: vertical, gap: 16, padding: 16, width: {size[0]}, height: {size[1]}}}
children:
  - {call % options}
  - {{widget: Rect, name: elsewhere, style: {{width: 80, height: 80, background: surface_variant}}}}
""")
    if sheet:
        (tmp_path / "Views" / "Main_Stylesheet.yaml").write_text(sheet)
    app = App(root=tmp_path, width=size[0], height=size[1], theme_seed=(0x67, 0x50, 0xA4, 0xFF), dark=dark)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 4)
    return view, app.bindings.viewmodel_for("main")


def settle(view, n=6):
    for _ in range(n):
        view.window.advance(16)


def panel_of(view, popup=False):
    return "root.ip.layer.surface.popup_panel" if popup else "root.ip.panel"


def ctl(view, popup=False):
    return view._built.controls[f"{panel_of(view, popup)}.browser"]


def node(view, name, popup=False):
    return view._built.nodes[f"{panel_of(view, popup)}.{name}"]


def search(view, popup=False):
    return node(view, "search.box.body.input", popup)


def typed(view, text, popup=False):
    field = search(view, popup)
    field.focus()
    field.set(text=text[:-1])
    view.window.simulate("key_down", key="end")
    view.window.simulate("input", text=text[-1])
    settle(view, 3)


def key(view, name, popup=False, n=3, **mods):
    box = node(view, "list_group.list_box", popup)
    if not box.get("focused"):
        box.focus()
    view.window.simulate("key_down", key=name, **mods)
    settle(view, n)


def field_key(view, name, popup=False):
    search(view, popup).focus()
    view.window.simulate("key_down", key=name)
    settle(view, 3)


def shown(view, popup=False):
    """The names of the cells built, in grid order."""
    prefix = f"{panel_of(view, popup)}.list_group.list_box.list.row["
    found = []
    for k in view._built.nodes:
        if k.startswith(prefix) and ".cell[" in k and k.endswith("]"):
            n = view._built.nodes[k]
            found.append((n.get("layout_y"), n.get("layout_x"), k[k.rindex(".cell[") + 6:-1]))
    return [index for _, _, index in sorted(found)]


def cell(view, index, popup=False):
    prefix = f"{panel_of(view, popup)}.list_group.list_box.list.row["
    for k in view._built.nodes:
        if k.startswith(prefix) and k.endswith(f".cell[{index}]"):
            return view._built.nodes[k]
    raise KeyError(index)


def press(view, target, n=4):
    view.window.simulate("pointer_down", node=target)
    view.window.simulate("pointer_up", node=target)
    settle(view, n)


@pytest.fixture(autouse=True)
def disk(monkeypatch):
    """Each test has its own file system (the default is the disk)."""
    fs = Counting()
    monkeypatch.setattr(filesystem, "_default", fs)
    return fs


# -- the model --------------------------------------------------------------------------------------------------------------------------

def test_it_lists_the_files_of_the_folder_first_then_the_built_in_icons(tmp_path):
    browser = IconBrowser(filesystem.default(), str(folder(tmp_path)))
    names = [e.name for e in browser.results]
    assert names[:3] == ["badge.png", "logo.svg", "zeta.SVG"]  # by name without regard to case; .txt, a hidden file and a folder are no icons
    assert names[3:] == sorted(icons.ICONS, key=str.lower)
    assert [e.kind for e in browser.results[:3]] == ["png", "svg", "svg"]
    assert browser.message == ""


def test_with_no_folder_it_lists_only_the_built_in_set():
    browser = IconBrowser(filesystem.default())
    assert len(browser.results) == len(icons.ICONS) and {e.kind for e in browser.results} == {"glyph"}


def test_a_folder_that_cannot_be_read_is_a_message_and_the_built_in_set_stays(tmp_path):
    browser = IconBrowser(filesystem.default(), str(tmp_path / "nowhere"))
    assert "nowhere" in browser.message and len(browser.results) == len(icons.ICONS)


def test_search_takes_every_word_in_any_order_and_ignores_case_and_separators():
    browser = IconBrowser(filesystem.default(), builtin=["arrow_back", "arrow_forward", "back_hand", "home", "Home_Work"])
    browser.set_query("back arrow")
    assert [e.name for e in browser.results] == ["arrow_back"]
    browser.set_query("HOME")
    assert [e.name for e in browser.results] == ["home", "Home_Work"]
    browser.set_query("arrow-back")
    assert [e.name for e in browser.results] == ["arrow_back"]
    browser.set_query("back")
    assert [e.name for e in browser.results] == ["back_hand", "arrow_back"]  # a name that starts with it comes first
    browser.set_query("nothing like this")
    assert browser.results == [] and browser.cursor == -1
    browser.set_query("")
    assert len(browser.results) == 5 and browser.cursor == 0


def test_a_search_finds_a_file_by_its_name_and_its_extension(tmp_path):
    browser = IconBrowser(filesystem.default(), str(folder(tmp_path)), builtin=["home"])
    browser.set_query("svg")
    assert [e.name for e in browser.results] == ["logo.svg", "zeta.SVG"]


def test_the_keys_move_the_cursor_by_one_by_a_row_by_a_page_and_stop_at_the_ends():
    browser = IconBrowser(filesystem.default(), columns=4, page_rows=2, builtin=[f"i{n:02d}" for n in range(30)])
    assert browser.cursor == 0
    browser.press("arrow_right")
    browser.press("arrow_down")
    assert browser.cursor == 5
    browser.press("end")
    assert browser.cursor == 7
    browser.press("home")
    assert browser.cursor == 4
    browser.press("page_down")
    assert browser.cursor == 12
    browser.press("end", ctrl=True)
    assert browser.cursor == 29
    browser.press("arrow_right")
    browser.press("arrow_down")
    assert browser.cursor == 29
    browser.press("home", ctrl=True)
    assert browser.cursor == 0
    browser.press("arrow_up")
    browser.press("arrow_left")
    assert browser.cursor == 0
    browser.press("page_up")
    assert browser.cursor == 0
    assert browser.press("enter") == "pick" and browser.press(" ") == "pick" and browser.press("a") is None


def test_in_the_search_field_the_left_and_right_keys_and_space_are_the_texts():
    browser = IconBrowser(filesystem.default(), columns=4, builtin=[f"i{n:02d}" for n in range(30)])
    browser.cursor = 5
    for name in ("arrow_left", "arrow_right", "home", "end", " "):
        assert browser.press(name, in_field=True) is None
        assert browser.cursor == 5
    browser.press("arrow_down", in_field=True)
    assert browser.cursor == 9
    assert browser.press("enter", in_field=True) == "pick"


def test_the_keys_do_nothing_with_no_results_and_a_click_outside_them_picks_nothing():
    browser = IconBrowser(filesystem.default(), builtin=["a"])
    browser.set_query("zzz")
    assert browser.press("arrow_down") is None and browser.press("enter") is None and browser.click(0) is None
    assert browser.picked is None


def test_reveal_keeps_the_cursor_row_in_the_window():
    browser = IconBrowser(filesystem.default(), columns=4, page_rows=3, builtin=[f"i{n:02d}" for n in range(60)])
    browser.cursor = 0
    assert browser.reveal(0.0, 48.0) == 0.0
    browser.cursor = 4 * 5 + 1  # row 5
    assert browser.reveal(0.0, 48.0) == 3 * 48.0  # rows 3, 4, 5 show
    assert browser.reveal(3 * 48.0, 48.0) == 3 * 48.0
    browser.cursor = 4  # row 1
    assert browser.reveal(3 * 48.0, 48.0) == 48.0


def test_svg_and_png_are_checked_before_the_engine_sees_them():
    assert clean_svg(SVG.encode()) == SVG
    assert clean_svg(b"\xef\xbb\xbf" + SVG.encode()) == SVG  # a byte order mark is fine
    assert clean_svg(b"not an svg") is None and clean_svg(b"\xff\xfe\x00") is None
    assert clean_svg(b'<!DOCTYPE svg [<!ENTITY a "aaa">]>' + SVG.encode()) is None
    frame = decode_png(png_bytes(200, 100))
    assert frame is not None and frame[1:] == (96, 48) and len(frame[0]) == 96 * 48 * 4  # drawn small
    assert decode_png(b"nope") is None


# -- the control and the view, inline --------------------------------------------------------------------------------------------------------

def test_the_picker_and_its_parts_are_shipped_and_declared():
    assert {"IconPicker", "IconPickerPanel"} <= set(shipped_views())
    declared = lookup("IconBrowser")
    assert declared is not None and declared.properties["value"].model and declared.properties["scroll"].model


def test_inline_it_shows_the_grid_at_the_value_and_the_view_matches_its_viewmodel(tmp_path):
    view, vm = opened(tmp_path)
    assert view.handle.viewmodel is vm
    control = ctl(view)
    assert control.count.get() == len(icons.ICONS)
    assert control.value.get() == "home" and control.current.get()["name"] == "home" and control.current.get()["kind"] == "glyph"
    assert control.browser.results[control.cursor.get()].name == "home"  # the cursor starts on the value
    assert control.scroll.get() > 0  # and the grid is scrolled so that it shows
    built = shown(view)
    assert 0 < len(built) <= (6 + 2 * 3 + 1) * 8  # a virtual grid builds the rows in view and three past each edge, not all 164


def test_a_press_picks_an_icon_writes_value_and_calls_on_change(tmp_path):
    view, vm = opened(tmp_path)
    control = ctl(view)
    index = control.browser.index_of("search")
    assert index >= 0
    press(view, cell(view, index))
    assert vm.icon.get() == "search" and vm.log == ["search"]
    assert control.value.get() == "search" and control.cursor.get() == index


def test_a_value_set_from_the_viewmodel_moves_the_selection_and_the_cursor(tmp_path):
    view, vm = opened(tmp_path)
    vm.icon.set("close")
    settle(view, 6)
    control = ctl(view)
    assert control.value.get() == "close"
    assert control.browser.results[control.cursor.get()].name == "close"
    assert vm.log == []  # a change the app made is not on_change


def test_a_value_that_is_not_an_icon_is_kept_as_it_is_and_nothing_is_selected(tmp_path):
    view, vm = opened(tmp_path)
    vm.icon.set("no_such_icon")
    settle(view, 6)
    control = ctl(view)
    assert control.value.get() == "no_such_icon" and vm.icon.get() == "no_such_icon"
    assert control.current.get()["kind"] == "none"


def test_typing_in_the_search_field_narrows_the_grid(tmp_path):
    view, vm = opened(tmp_path)
    control = ctl(view)
    typed(view, "arrow")
    names = [e.name for e in control.browser.results]
    assert names and all("arrow" in n for n in names) and control.count.get() == len(names)
    assert control.cursor.get() == 0 and control.scroll.get() == 0
    typed(view, "zzzz")
    assert control.count.get() == 0
    assert "root.ip.panel.empty" in view._built.nodes
    typed(view, "a")  # the text is replaced, so the grid fills again
    assert control.count.get() > 0 and all("a" in e.name for e in control.browser.results)


def test_from_the_search_field_down_moves_the_cursor_and_enter_picks(tmp_path):
    view, vm = opened(tmp_path)
    typed(view, "e")
    control = ctl(view)
    field_key(view, "arrow_down")
    assert control.cursor.get() == 8
    field_key(view, "arrow_up")
    assert control.cursor.get() == 0
    field_key(view, "arrow_down")
    search(view).focus()
    view.window.simulate("key_down", key="Enter")  # the name a text field's Enter has
    settle(view, 4)
    assert vm.icon.get() == control.browser.results[8].name and vm.log == [vm.icon.get()]


def test_the_left_and_right_keys_in_the_search_field_do_not_move_the_cursor(tmp_path):
    view, vm = opened(tmp_path)
    typed(view, "arrow")
    control = ctl(view)
    field_key(view, "arrow_right")
    field_key(view, "end")
    assert control.cursor.get() == 0


def test_the_grid_has_the_keys_and_scrolls_to_keep_the_cursor_in_view(tmp_path):
    view, vm = opened(tmp_path)
    control = ctl(view)
    start = control.cursor.get()
    key(view, "arrow_right")
    assert control.cursor.get() == start + 1
    key(view, "arrow_down")
    assert control.cursor.get() == start + 9
    key(view, "arrow_left")
    key(view, "arrow_up")
    assert control.cursor.get() == start
    key(view, "end", ctrl=True)
    last = control.count.get() - 1
    assert control.cursor.get() == last
    assert control.scroll.get() == pytest.approx(((last // 8) + 1 - 6) * 48.0)
    assert any(i == str(last) for i in shown(view))  # the last row has been built
    key(view, "home", ctrl=True)
    assert control.cursor.get() == 0 and control.scroll.get() == 0
    key(view, "page_down")
    assert control.cursor.get() == 6 * 8
    assert vm.log == []  # moving is not picking


def test_enter_and_space_pick_the_cursor_icon_in_the_grid(tmp_path):
    view, vm = opened(tmp_path)
    control = ctl(view)
    key(view, "home", ctrl=True)
    key(view, "enter")
    first = control.browser.results[0].name
    assert vm.icon.get() == first and vm.log == [first]
    key(view, "arrow_right")
    key(view, " ")
    assert vm.icon.get() == control.browser.results[1].name and len(vm.log) == 2


def test_the_grid_is_in_the_tab_order_after_the_search_field(tmp_path):
    view, vm = opened(tmp_path)
    assert node(view, "list_group.list_box").get("focusable")
    assert search(view).get("focusable")


def test_the_names_a_screen_reader_hears(tmp_path):
    view, vm = opened(tmp_path, options=", label: Pick one")
    box = node(view, "list_group.list_box")
    assert box.get("role") == "list" and box.get("label") == "Pick one icons"
    index = ctl(view).browser.index_of("home")
    item = cell(view, index)
    assert item.get("role") == "listitem" and item.get("label") == "home" and item.get("selected") is True
    other = cell(view, index + 1)
    assert other.get("selected") is False
    assert view._built.nodes["root.ip.panel.search.box.body.input"].get("label") == "Search icons"


def test_disabled_it_changes_nothing(tmp_path):
    view, vm = opened(tmp_path, options=", disabled: true")
    control = ctl(view)
    assert control.disabled.get()
    press(view, cell(view, int(shown(view)[0])))
    key(view, "end", ctrl=True)
    key(view, "enter")
    assert vm.icon.get() == "home" and vm.log == [] and control.value.get() == "home"


# -- the folder ------------------------------------------------------------------------------------------------------------------------

def test_the_folder_is_read_when_the_grid_is_listed_and_a_file_is_read_only_when_its_row_is_in_view(tmp_path, disk):
    base = folder(tmp_path, names=[f"i{n:03d}.svg" for n in range(120)])
    view, vm = opened(tmp_path, options=f', icons_folder: "{base}"')
    assert disk.listed == [str(base)]
    control = ctl(view)
    assert control.count.get() == 120 + len(icons.ICONS)
    assert disk.read == []  # the grid opened scrolled to `home`, below the files: none of them is in view
    key(view, "home", ctrl=True)
    first_rows = len(disk.read)
    assert 0 < first_rows <= (6 + 2) * 8 + 8  # the rows in view, and two past them; not all 120
    assert sorted(set(disk.read)) == sorted(disk.read)  # none twice
    key(view, "end", ctrl=True)
    key(view, "home", ctrl=True)
    assert len(disk.read) == first_rows  # and a file that was read is not read again
    for _ in range(4):
        key(view, "page_down")
    assert first_rows < len(disk.read) <= 120


# -- a file system that is not the disk -------------------------------------------------------------------------------------------------------

class Fake:
    """A file system of one folder of many files, which cannot read any (a preview that fails leaves the file glyph)."""

    def __init__(self, count):
        self.count = count
        self.listed = 0

    def list_dir(self, path):
        self.listed += 1
        return [Entry(f"f{n:04d}.svg", f"{path}/f{n:04d}.svg", False, 10, 1.0, False) for n in range(self.count)]

    def read_bytes(self, path, limit):
        raise FileSystemError("Cannot read", path)

    def is_dir(self, path):
        return True

    def exists(self, path):
        return True


def test_a_thousand_files_build_only_the_rows_in_view_and_one_that_cannot_be_read_is_a_file_glyph(tmp_path, monkeypatch):
    fake = Fake(1000)
    monkeypatch.setattr(filesystem, "_default", fake)
    view, vm = opened(tmp_path, options=', icons_folder: "/elsewhere"')
    control = ctl(view)
    assert control.count.get() == 1000 + len(icons.ICONS) and fake.listed == 1
    assert len(shown(view)) <= 104
    assert {c["kind"] for row in control.grid.get()[:3] for c in row["cells"]} == {"file"}
    key(view, "end", ctrl=True)
    assert len(shown(view)) <= 104 and control.cursor.get() == control.count.get() - 1
    assert fake.listed == 1  # one listing, however far it scrolls


# -- the popup --------------------------------------------------------------------------------------------------------------------------

def test_a_popup_reads_nothing_until_it_opens(tmp_path, disk):
    base = folder(tmp_path)
    view, vm = opened(tmp_path, POPUP, options=f', icons_folder: "{base}"')
    assert disk.listed == [] and not view._shown_layers
    assert view._built.controls["root.ip.swatch"].current.get()["name"] == "home"
    press(view, view.node("root.ip.field.trigger"))
    assert vm.pop.get() is True and view._shown_layers
    assert disk.listed == [str(base)]


def test_the_button_shows_the_icon_and_its_name_and_says_so_to_a_screen_reader(tmp_path):
    view, vm = opened(tmp_path, POPUP, options=", label: Symbol")
    trigger = view.node("root.ip.field.trigger")
    assert trigger.get("role") == "button" and trigger.get("label") == "Symbol: home" and trigger.get("expanded") is False
    assert view.node("root.ip.field.trigger_text").get("text") == "home"
    assert "root.ip.field.trigger_icon" in view._built.nodes
    vm.icon.set("")
    settle(view, 6)
    assert view.node("root.ip.field.trigger_text").get("text") == "Choose an icon" and trigger.get("label") == "Symbol"
    assert "root.ip.field.trigger_icon" not in view._built.nodes


def test_the_button_of_a_file_icon_shows_the_file(tmp_path):
    base = folder(tmp_path, names=("logo.svg", "badge.png"))
    view, vm = opened(tmp_path, POPUP, options=f', icons_folder: "{base}"')
    vm.icon.set("logo.svg")
    settle(view, 6)
    assert "root.ip.field.trigger_svg" in view._built.nodes and "root.ip.field.trigger_icon" not in view._built.nodes
    vm.icon.set("badge.png")
    settle(view, 6)
    assert "root.ip.field.trigger_image" in view._built.nodes and "root.ip.field.trigger_svg" not in view._built.nodes


def test_pressing_the_button_opens_the_grid_with_the_search_field_focused(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.ip.field.trigger"))
    assert vm.pop.get() is True and view._shown_layers
    assert view.node("root.ip.field.trigger").get("expanded") is True
    assert search(view, True).get("focused")
    surface = view.node("root.ip.layer.surface")
    assert surface.get("corner_radius") == 12.0
    assert ctl(view, True).count.get() == len(icons.ICONS)


def test_a_pick_closes_the_popup_and_writes_the_value(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.ip.field.trigger"))
    index = ctl(view, True).browser.index_of("cog")
    press(view, cell(view, index, True))
    assert vm.icon.get() == "cog" and vm.log == ["cog"] and vm.pop.get() is False and not view._shown_layers
    assert view.node("root.ip.field.trigger_text").get("text") == "cog"
    press(view, view.node("root.ip.field.trigger"))  # and it opens again, on the new value
    assert vm.pop.get() is True
    control = ctl(view, True)
    assert control.browser.results[control.cursor.get()].name == "cog"


def test_a_pick_leaves_the_popup_open_when_it_says_not_to_close(tmp_path):
    view, vm = opened(tmp_path, POPUP, options=", close_on_pick: false")
    press(view, view.node("root.ip.field.trigger"))
    press(view, cell(view, ctl(view, True).browser.index_of("cog"), True))
    assert vm.icon.get() == "cog" and vm.pop.get() is True and view._shown_layers


def test_enter_in_the_search_field_picks_and_closes(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.ip.field.trigger"))
    typed(view, "cog", popup=True)
    search(view, True).focus()
    view.window.simulate("key_down", key="Enter")
    settle(view, 6)
    first = ctl(view, True).browser.results[0].name
    assert vm.icon.get() == first and vm.pop.get() is False


def test_escape_closes_the_popup_and_writes_false_back_and_the_focus_returns_to_the_button(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.ip.field.trigger"))
    assert vm.pop.get() is True
    view.window.simulate("key_down", key="escape")
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers
    assert vm.icon.get() == "home" and vm.log == []
    press(view, view.node("root.ip.field.trigger"))
    assert vm.pop.get() is True and view._shown_layers  # it opens again


def test_the_popup_opens_from_the_keyboard_and_escape_gives_the_focus_back_to_the_button(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    trigger = view.node("root.ip.field.trigger")
    trigger.focus()
    view.window.simulate("key_down", key="enter")
    settle(view, 6)
    assert vm.pop.get() is True and search(view, True).get("focused")
    view.window.simulate("key_down", key="escape")
    settle(view, 8)
    assert vm.pop.get() is False and trigger.get("focused")


def test_escape_from_the_grid_closes_the_popup_too(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.ip.field.trigger"))
    node(view, "list_group.list_box", True).focus()
    view.window.simulate("key_down", key="escape")
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers


def test_a_press_outside_closes_the_popup(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.ip.field.trigger"))
    view.window.simulate("pointer_down", x=430, y=580)
    view.window.simulate("pointer_up", x=430, y=580)
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers


def test_pressing_the_button_again_closes_it(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    trigger = view.node("root.ip.field.trigger")
    press(view, trigger)
    assert vm.pop.get() is True
    view.window.advance(1000)  # two presses in one place within the double click time are one double click
    x, y = trigger.get("layout_x") + 30, trigger.get("layout_y") + 24
    view.window.simulate("pointer_down", x=x, y=y)  # at the button's own place, as a pointer arrives (a press sent to the node itself skips the layer's own check)
    view.window.simulate("pointer_up", x=x, y=y)
    settle(view, 4)
    assert vm.pop.get() is False and not view._shown_layers


def test_a_disabled_popup_does_not_open(tmp_path):
    view, vm = opened(tmp_path, POPUP, options=", disabled: true")
    press(view, view.node("root.ip.field.trigger"))
    assert vm.pop.get() is False and not view._shown_layers


def test_a_popup_can_be_opened_and_closed_from_the_viewmodel(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    vm.pop.set(True)
    settle(view, 6)
    assert view._shown_layers
    vm.pop.set(False)
    settle(view, 6)
    assert not view._shown_layers


def _collect_reentrant(monkeypatch):
    """Errors a Signal raises for a write made while it is notifying: the engine logs and swallows them, so they are caught where they are raised."""
    errors = []
    original = reactive._Notifiable._notify

    def watching(self, *args, **kwargs):
        try:
            return original(self, *args, **kwargs)
        except RuntimeError as error:
            errors.append(error)
            raise

    monkeypatch.setattr(reactive._Notifiable, "_notify", watching)
    return errors


STATE_RULES = """tesserae: 0.6
styles:
  - {widget: IconPicker, state: focused, style: {opacity: 0.99}}
  - {widget: IconPicker, state: hovered, style: {opacity: 0.98}}
  - {widget: IconPicker, state: pressed, style: {opacity: 0.97}}
"""


def test_escape_with_a_state_rule_on_the_popup_root_raises_no_reentrant_write_and_closes(tmp_path, monkeypatch):
    errors = _collect_reentrant(monkeypatch)
    view, vm = opened(tmp_path, POPUP, sheet=STATE_RULES)
    press(view, view.node("root.ip.field.trigger"))
    assert vm.pop.get() is True
    view.window.simulate("key_down", key="escape")
    settle(view, 8)
    assert vm.pop.get() is False and not view._shown_layers
    press(view, view.node("root.ip.field.trigger"))
    view.window.simulate("key_down", key="escape")
    settle(view, 8)
    assert vm.pop.get() is False and errors == []


def test_a_pick_with_a_state_rule_on_the_root_raises_no_reentrant_write(tmp_path, monkeypatch):
    errors = _collect_reentrant(monkeypatch)
    view, vm = opened(tmp_path, POPUP, sheet=STATE_RULES)
    press(view, view.node("root.ip.field.trigger"))
    press(view, cell(view, ctl(view, True).browser.index_of("cog"), True))
    assert vm.icon.get() == "cog" and vm.pop.get() is False and errors == []


def test_an_unknown_property_of_the_picker_is_named(tmp_path):
    with pytest.raises(LoadError, match="colour"):
        opened(tmp_path, call="{widget: IconPicker, name: ip, colour: red%s}")


def test_the_picked_cell_and_the_cursor_cell_are_drawn_in_the_themes_colours_in_light_and_dark(tmp_path):
    from tess_ui import tokens

    for dark in (False, True):
        view, vm = opened(tmp_path / str(dark), dark=dark)
        scheme = view._scheme or tokens.BASELINE
        control = ctl(view)
        picked = cell(view, control.browser.index_of("home"))
        assert picked.get("fill") == scheme["secondary_container"]
        other = cell(view, control.browser.index_of("home") + 1)
        assert other.get("fill") != scheme["secondary_container"]
        key(view, "arrow_right")  # the cursor moved off the picked icon: it is `surface_container_highest`
        assert cell(view, control.cursor.get()).get("fill") == scheme["surface_container_highest"]
        assert picked.get("fill") == scheme["secondary_container"]
