"""#299: the file dialog's rules, with no window: `FileBrowser` over `tmp_path` trees and a fake file system for the errors."""

import os
import time

import pytest

from tess_ui import filesystem
from tess_ui.file_browser import FileBrowser, Filter, read_filters, size_text, time_text
from tess_ui.filesystem import Entry, FileSystemError, LocalFileSystem


def tree(base):
    """A small tree: folders `beta`, `Alpha` and `.hidden_dir`; files `b.txt`, `A.TDL`, `c.tdl`, `.secret`, `notes.md`."""
    for name in ("beta", "Alpha", ".hidden_dir"):
        (base / name).mkdir()
    for name, text in (("b.txt", "b"), ("A.TDL", "aa"), ("c.tdl", "ccc"), (".secret", "s"), ("notes.md", "n" * 2000)):
        (base / name).write_text(text)
    (base / "Alpha" / "inner.txt").write_text("i")
    (base / "Alpha" / "deeper").mkdir()
    return base


def names(browser):
    return [r["name"] for r in browser.rows]


class Fake:
    """A file system in a dict, for what a disk will not do on request: errors, vanishing folders, a huge listing."""

    def __init__(self, folders):
        self.folders = {k: list(v) for k, v in folders.items()}
        self.denied = set()
        self.made = []

    def list_dir(self, path):
        if path in self.denied:
            raise FileSystemError(f"Cannot open {path}: permission denied", path)
        if path not in self.folders:
            raise FileSystemError(f"Cannot open {path}: it is not there any more", path)
        return list(self.folders[path])

    def is_dir(self, path):
        return path in self.folders

    def exists(self, path):
        return path in self.folders or any(e.path == path for v in self.folders.values() for e in v)

    def make_dir(self, path):
        if os.path.dirname(path) in self.denied:
            raise FileSystemError(f"Cannot create {path}: permission denied", path)
        self.folders[path] = []
        self.folders[os.path.dirname(path)].append(Entry(os.path.basename(path), path, True, None, 0.0, False))
        self.made.append(path)

    def real_path(self, path):
        return path

    def home(self):
        return "/home/u"

    def cwd(self):
        return "/home/u"


def entry(folder, name, is_dir=False):
    return Entry(name, f"{folder}/{name}", is_dir, None if is_dir else 5, 86400.0 * 400, name.startswith("."))


# -- the listing ----------------------------------------------------------------------------------------------------------------------

def test_a_folder_lists_folders_first_then_files_each_sorted_without_regard_to_case(tmp_path):
    browser = FileBrowser(start=str(tree(tmp_path)))
    assert names(browser) == ["Alpha", "beta", "A.TDL", "b.txt", "c.tdl", "notes.md"]
    assert [r["dir"] for r in browser.rows] == [True, True, False, False, False, False]
    assert browser.path == str(tmp_path)
    assert browser.message == ""


def test_a_row_has_the_columns_a_list_shows(tmp_path):
    base = tree(tmp_path)
    os.utime(base / "notes.md", (1_700_000_000, 1_700_000_000))
    rows = {r["name"]: r for r in FileBrowser(start=str(base)).rows}
    assert rows["notes.md"]["size"] == "2.0 KB"
    assert rows["b.txt"]["size"] == "1 B"
    assert rows["Alpha"]["size"] == ""
    assert rows["notes.md"]["modified"] == time.strftime("%Y-%m-%d %H:%M", time.localtime(1_700_000_000))
    assert rows["Alpha"]["icon"] == "folder" and rows["notes.md"]["icon"] == "file"
    assert rows["notes.md"]["path"] == str(base / "notes.md")


def test_size_and_time_texts():
    assert [size_text(n) for n in (None, 0, 1023, 1024, 15 * 1024, 5 * 1024 * 1024, 3 * 1024**3, 9 * 1024**4)] == ["", "0 B", "1023 B", "1.0 KB", "15 KB", "5.0 MB", "3.0 GB", "9.0 TB"]
    assert time_text(None) == "" and time_text(1e30) == ""


def test_hidden_entries_are_off_until_the_toggle_turns_them_on(tmp_path):
    browser = FileBrowser(start=str(tree(tmp_path)))
    assert ".hidden_dir" not in names(browser) and ".secret" not in names(browser)
    browser.set_show_hidden(True)
    assert names(browser) == [".hidden_dir", "Alpha", "beta", ".secret", "A.TDL", "b.txt", "c.tdl", "notes.md"]
    browser.set_show_hidden(False)
    assert ".secret" not in names(browser)
    assert FileBrowser(start=str(tmp_path), show_hidden=True).show_hidden


def test_a_filter_hides_files_that_do_not_match_and_never_a_folder(tmp_path):
    browser = FileBrowser(start=str(tree(tmp_path)), filters=[{"label": "TDL files", "patterns": ["*.tdl"]}, {"label": "Text", "patterns": ["*.txt", "*.md"]}])
    assert [f.label for f in browser.filters] == ["TDL files", "Text", "All files"]
    assert names(browser) == ["Alpha", "beta", "A.TDL", "c.tdl"]  # case does not count
    browser.set_filter(1)
    assert names(browser) == ["Alpha", "beta", "b.txt", "notes.md"]
    browser.set_filter(2)
    assert names(browser) == ["Alpha", "beta", "A.TDL", "b.txt", "c.tdl", "notes.md"]
    browser.set_filter(99)
    assert browser.filter_index == 2


def test_the_filters_are_read_in_each_shape_and_a_bad_one_is_named():
    assert read_filters(None) == [Filter("All files", ("*",))]
    assert read_filters([("A", "*.a"), Filter("B", ("*.b",)), {"label": "C", "patterns": ["*.c"]}])[:3] == [Filter("A", ("*.a",)), Filter("B", ("*.b",)), Filter("C", ("*.c",))]
    assert len(read_filters([{"label": "Everything", "patterns": ["*"]}])) == 1  # one that shows all is not followed by another
    for bad in ({"label": "x"}, {"patterns": ["*.a"]}, {"label": "", "patterns": ["*.a"]}, {"label": "x", "patterns": []}, 5, {"label": "x", "patterns": [3]}):
        with pytest.raises(ValueError, match="filter"):
            read_filters([bad])


def test_a_selected_file_that_a_filter_hides_is_no_longer_selected(tmp_path):
    browser = FileBrowser(start=str(tree(tmp_path)), filters=[("TDL", ["*.tdl"])], filter_index=2)
    browser.click(names(browser).index("b.txt"))
    assert browser.selection == [str(tmp_path / "b.txt")]
    browser.set_filter(0)
    assert browser.selection == [] and browser.cursor == -1


def test_a_big_folder_is_one_listing_and_every_row_is_there(tmp_path):
    for i in range(10_000):
        (tmp_path / f"file{i:05d}.dat").write_text("")
    started = time.perf_counter()
    browser = FileBrowser(start=str(tmp_path))
    took = time.perf_counter() - started
    assert len(browser.rows) == 10_000 and browser.rows[0]["name"] == "file00000.dat" and browser.rows[-1]["name"] == "file09999.dat"
    assert took < 5  # a generous bound: one scandir and a stat each, not a freeze
    browser.press("end")
    assert browser.cursor == 9_999
    assert browser.reveal(0.0) == 9_999 * 40 + 40 - 8 * 40


# -- moving about ---------------------------------------------------------------------------------------------------------------------

def test_navigate_up_back_forward_and_home(tmp_path):
    base = tree(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    browser = FileBrowser(LocalFileSystem(), start=str(base))
    assert not browser.can_back and not browser.can_forward
    assert browser.navigate("Alpha") and browser.path == str(base / "Alpha")  # relative to where it is
    assert browser.navigate("deeper") and browser.path == str(base / "Alpha" / "deeper")
    assert browser.can_back and not browser.can_forward
    assert browser.up() and browser.path == str(base / "Alpha")
    assert browser.back() and browser.path == str(base / "Alpha" / "deeper")
    assert browser.back() and browser.path == str(base / "Alpha")
    assert browser.back() and browser.path == str(base) and not browser.can_back
    assert not browser.back()
    assert browser.forward() and browser.path == str(base / "Alpha")
    assert browser.navigate(str(base / "beta")) and not browser.can_forward  # a new place drops what Forward held

    class Homed(LocalFileSystem):
        def home(self):
            return str(home)

    homed = FileBrowser(Homed(), start=str(base))
    assert homed.home() and homed.path == str(home)


def test_up_stops_at_the_top_of_the_file_system():
    fs = Fake({"/": [entry("", "a", True)], "/a": []})
    browser = FileBrowser(fs, start="/a")
    assert browser.can_up and browser.up() and browser.path == "/"
    assert not browser.can_up and not browser.up() and browser.path == "/"


def test_the_start_is_the_start_then_the_root_then_the_working_folder(tmp_path):
    base = tree(tmp_path)

    class Here(LocalFileSystem):
        def cwd(self):
            return str(base / "beta")

    assert FileBrowser(Here()).path == str(base / "beta")
    assert FileBrowser(Here(), root=str(base)).path == str(base)
    assert FileBrowser(Here(), root=str(base), start=str(base / "Alpha")).path == str(base / "Alpha")
    assert FileBrowser(Here(), root=str(base / "beta"), start=str(base / "Alpha")).path == str(base / "beta")  # a start outside the root gives way to it


def test_an_unreadable_start_falls_back_to_the_folder_above_and_says_why(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base / "gone" / "deeper"))
    assert browser.path == str(base) and "There is no folder" in browser.message and "gone" in browser.message
    fs = Fake({"/": [], "/a": [entry("/a", "x")]})
    fs.denied.add("/a")
    shown = FileBrowser(fs, start="/a")
    assert shown.path == "/" and "permission denied" in shown.message


def test_the_path_bar_enters_a_folder_selects_a_file_and_complains_about_the_rest(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base))
    assert browser.submit_path("Alpha") and browser.path == str(base / "Alpha")
    assert browser.submit_path("  " + str(base) + "  ") and browser.path == str(base)
    assert browser.submit_path(str(base / "Alpha" / "inner.txt"))
    assert browser.path == str(base / "Alpha") and browser.selection == [str(base / "Alpha" / "inner.txt")] and browser.valid
    assert not browser.submit_path(str(base / "nope"))
    assert browser.path == str(base / "Alpha") and "There is no folder" in browser.message and "nope" in browser.message
    assert not browser.submit_path("")
    assert FileBrowser(start=str(base), mode="folder").submit_path(str(base / "b.txt")) is False


def test_a_tilde_in_the_path_bar_and_in_the_start_and_root_is_the_file_systems_home(tmp_path):
    base = tree(tmp_path)

    class Homed(LocalFileSystem):
        def home(self):
            return str(base / "Alpha")

    browser = FileBrowser(Homed(), start=str(base))
    assert browser.navigate("~") and browser.path == str(base / "Alpha")
    assert browser.navigate(str(base)) and browser.navigate("~/deeper") and browser.path == str(base / "Alpha" / "deeper")
    assert FileBrowser(Homed(), start="~").path == str(base / "Alpha")
    assert FileBrowser(Homed(), root="~").root == str(base / "Alpha")


def test_the_crumbs_run_from_the_top_to_the_folder_and_from_the_root_when_there_is_one(tmp_path):
    base = tree(tmp_path)
    inner = base / "Alpha" / "deeper"
    plain = FileBrowser(start=str(inner))
    trail = plain.crumbs
    assert trail[0] == {"name": os.path.splitroot(str(inner))[0] + os.sep, "path": os.sep} or trail[0]["path"] == os.path.splitroot(str(inner))[1]
    assert [c["name"] for c in trail][-3:] == [base.name, "Alpha", "deeper"] and trail[-1]["path"] == str(inner)
    confined = FileBrowser(start=str(inner), root=str(base))
    assert [c["name"] for c in confined.crumbs] == [base.name, "Alpha", "deeper"]
    assert confined.crumbs[0]["path"] == str(base) and confined.crumbs[-1]["path"] == str(inner)
    assert [c["name"] for c in FileBrowser(start=str(base), root=str(base)).crumbs] == [base.name]


# -- the root -----------------------------------------------------------------------------------------------------------------------

def test_the_root_confines_every_way_out(tmp_path):
    base = tree(tmp_path)
    inside = base / "Alpha"
    browser = FileBrowser(start=str(inside), root=str(inside))
    assert not browser.can_up and not browser.up()
    assert not browser.navigate(str(base)) and "outside" in browser.message and browser.path == str(inside)
    assert not browser.navigate("..") and browser.path == str(inside)
    assert not browser.submit_path(str(base / "b.txt")) and "outside" in browser.message
    assert not browser.navigate(str(inside) + "/../beta")
    assert browser.navigate("deeper") and browser.can_up and browser.up() and browser.path == str(inside)
    assert not browser.can_up


def test_home_outside_the_root_goes_to_the_root(tmp_path):
    base = tree(tmp_path)

    class Homed(LocalFileSystem):
        def home(self):
            return str(tmp_path.parent)

    browser = FileBrowser(Homed(), start=str(base / "Alpha"), root=str(base))
    assert browser.home() and browser.path == str(base)


def test_a_symlink_inside_the_root_that_leads_out_is_not_followed_out(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "private.txt").write_text("x")
    os.symlink(outside, root / "escape")
    browser = FileBrowser(start=str(root), root=str(root))
    assert "escape" in names(browser)  # it is there to see
    assert not browser.navigate("escape") and "outside" in browser.message
    assert browser.path == str(root)


# -- errors ----------------------------------------------------------------------------------------------------------------------------

def test_a_folder_that_cannot_be_read_is_a_message_and_the_dialog_stays_put():
    fs = Fake({"/h": [entry("/h", "locked", True), entry("/h", "f.txt")], "/h/locked": [], "/h/gone": []})
    fs.denied.add("/h/locked")
    browser = FileBrowser(fs, start="/h")
    assert not browser.navigate("/h/locked")
    assert browser.path == "/h" and names(browser) == ["locked", "f.txt"] and "permission denied" in browser.message
    assert browser.navigate("/h") and browser.message == ""  # the next good move clears it
    assert not browser.navigate("/h/missing") and "There is no folder" in browser.message
    assert not browser.navigate("/h/f.txt")  # a file is not a folder (the fake knows only folders, so it is "not there")


def test_a_folder_that_vanishes_under_the_dialog_is_shown_empty_with_the_reason():
    fs = Fake({"/h": [entry("/h", "x.txt")], "/h/sub": [entry("/h/sub", "y.txt")]})
    browser = FileBrowser(fs, start="/h/sub")
    del fs.folders["/h/sub"]
    assert not browser.refresh()
    assert browser.rows == [] and "There is no folder" in browser.message and browser.selection == []
    assert browser.target == []
    assert browser.up() and names(browser) == ["x.txt"] and browser.message == ""


def test_the_local_file_system_explains_a_failure_in_words(tmp_path):
    fs = LocalFileSystem()
    with pytest.raises(FileSystemError, match="not there any more"):
        fs.list_dir(str(tmp_path / "nope"))
    (tmp_path / "f").write_text("")
    with pytest.raises(FileSystemError, match="not a folder"):
        fs.list_dir(str(tmp_path / "f"))
    with pytest.raises(FileSystemError, match="name is taken"):
        fs.make_dir(str(tmp_path))
    if os.geteuid() != 0:
        locked = tmp_path / "locked"
        locked.mkdir()
        locked.chmod(0)
        try:
            with pytest.raises(FileSystemError, match="permission denied"):
                fs.list_dir(str(locked))
            with pytest.raises(FileSystemError, match="permission denied"):
                fs.make_dir(str(locked / "inside"))
        finally:
            locked.chmod(0o700)


def test_the_default_file_system_can_be_swapped_and_put_back():
    fake = Fake({"/z": [entry("/z", "only.txt")]})
    previous = filesystem.use(fake)
    try:
        assert names(FileBrowser(start="/z")) == ["only.txt"]
    finally:
        assert filesystem.use(previous) is fake
    assert isinstance(filesystem.default(), LocalFileSystem)
    assert isinstance(filesystem.use(None), LocalFileSystem)


# -- picking: open ---------------------------------------------------------------------------------------------------------------------

def test_open_mode_wants_one_file(tmp_path):
    browser = FileBrowser(start=str(tree(tmp_path)))
    assert not browser.valid and browser.target == [] and browser.result() is None
    browser.click(names(browser).index("b.txt"))
    assert browser.valid and browser.result() == [str(tmp_path / "b.txt")]
    browser.click(0)  # a folder is not a file: the cursor goes to it and nothing is picked
    assert browser.selection == [] and browser.cursor == 0 and not browser.valid and browser.result() is None


def test_open_mode_with_multiple_takes_several_files_by_ctrl_and_shift(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base), multiple=True)
    index = {n: i for i, n in enumerate(names(browser))}
    browser.click(index["A.TDL"])
    browser.click(index["c.tdl"], ctrl=True)
    assert browser.selection == [str(base / "A.TDL"), str(base / "c.tdl")] and browser.valid
    browser.click(index["A.TDL"], ctrl=True)
    assert browser.selection == [str(base / "c.tdl")]
    browser.click(index["A.TDL"])
    browser.click(index["notes.md"], shift=True)
    assert [os.path.basename(p) for p in browser.selection] == ["A.TDL", "b.txt", "c.tdl", "notes.md"]
    browser.press("a", ctrl=True)
    assert [os.path.basename(p) for p in browser.selection] == ["A.TDL", "b.txt", "c.tdl", "notes.md"]
    browser.click(0, ctrl=True)  # a folder joins nothing
    assert len(browser.selection) == 4
    single = FileBrowser(start=str(base))
    single.click(index["A.TDL"])
    single.click(index["c.tdl"], ctrl=True)  # Ctrl means nothing when only one may be chosen
    assert single.selection == [str(base / "c.tdl")]
    single.press("a", ctrl=True)
    assert single.selection == [str(base / "c.tdl")]


def test_a_double_click_opens_a_folder_or_accepts_a_file(tmp_path):
    base = tree(tmp_path)
    now = [100.0]
    browser = FileBrowser(start=str(base), clock=lambda: now[0])
    assert browser.click(0) == "" and browser.path == str(base)
    now[0] += 0.2
    assert browser.click(0) == "entered" and browser.path == str(base / "Alpha")
    now[0] += 5
    browser = FileBrowser(start=str(base), clock=lambda: now[0])
    i = names(browser).index("b.txt")
    assert browser.click(i) == ""
    now[0] += 0.2
    assert browser.click(i) == "accept" and browser.result() == [str(base / "b.txt")]
    now[0] += 0.2
    assert browser.click(i) == ""  # a double click is used up
    now[0] += 1.0
    assert browser.click(i) == ""  # slow clicks are two clicks
    assert browser.click(i + 1) == ""  # another row is not a double


def test_activate_by_index(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base))
    assert browser.activate(99) == "" and browser.activate(-1) == ""
    assert browser.activate(names(browser).index("c.tdl")) == "accept" and browser.selection == [str(base / "c.tdl")]
    assert browser.activate(0) == "entered" and browser.path == str(base / "Alpha")


# -- picking: folder ------------------------------------------------------------------------------------------------------------------

def test_folder_mode_lists_only_folders_and_gives_the_one_picked_or_the_one_it_is_in(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base), mode="folder")
    assert names(browser) == ["Alpha", "beta"]
    assert browser.valid and browser.result() == [str(base)]  # nothing picked: this folder
    browser.click(1)
    assert browser.result() == [str(base / "beta")]
    browser.activate(1)
    assert browser.path == str(base / "beta") and browser.result() == [str(base / "beta")]
    many = FileBrowser(start=str(base), mode="folder", multiple=True)
    many.click(0)
    many.click(1, ctrl=True)
    assert many.result() == [str(base / "Alpha"), str(base / "beta")]


def test_folder_mode_with_nothing_readable_has_nothing_to_give():
    fs = Fake({})
    fs.denied.add("/x")
    assert FileBrowser(fs, mode="folder", start="/x").result() is None


# -- picking: save --------------------------------------------------------------------------------------------------------------------

def test_save_mode_gives_the_folder_and_the_typed_name_and_adds_the_filter_extension(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base), mode="save", filters=[("TDL files", ["*.tdl"])])
    assert not browser.valid and browser.result() is None and browser.problem == ""
    browser.name = "plan"
    assert browser.filename() == "plan.tdl" and browser.result() == [str(base / "plan.tdl")] and not browser.exists
    browser.name = "plan.md"  # an extension typed is kept
    assert browser.result() == [str(base / "plan.md")]
    browser.name = "  plan  "
    assert browser.filename() == "plan.tdl"
    browser.name = "trailing."
    assert browser.filename() == "trailing."
    browser.set_filter(1)  # All files adds nothing
    browser.name = "plan"
    assert browser.filename() == "plan"
    assert FileBrowser(start=str(base), mode="save", filters=[("Pictures", ["*.png", "*.jpg"])], name="a").filename() == "a.png"
    assert FileBrowser(start=str(base), mode="save", filters=[("Odd", ["data*", "*.t?t"])], name="a").filename() == "a"


def test_save_mode_knows_when_the_file_is_there_and_when_the_name_is_wrong(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base), mode="save")
    browser.name = "b.txt"
    assert browser.valid and browser.exists  # the dialog asks before writing over it
    browser.name = "fresh.txt"
    assert browser.valid and not browser.exists
    for bad in ("a/b", "..", ".", "x\\y"):
        browser.name = bad
        assert not browser.valid and browser.problem and browser.result() is None
    browser.name = "Alpha"  # a folder of that name
    assert not browser.valid and browser.problem == "Alpha is a folder"
    browser.name = ""
    assert not browser.valid and browser.problem == ""


def test_picking_a_file_in_save_mode_names_the_save_after_it_but_a_folder_does_not(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base), mode="save")
    browser.name = "mine.txt"
    browser.click(0)
    assert browser.name == "mine.txt" and browser.selection == []  # a folder is entered, not chosen, in a save
    browser.click(names(browser).index("c.tdl"))
    assert browser.name == "c.tdl" and browser.exists


def test_a_name_that_is_set_is_kept_across_folders(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base), mode="save", name="keep.txt")
    browser.navigate("beta")
    assert browser.result() == [str(base / "beta" / "keep.txt")]


# -- new folder ----------------------------------------------------------------------------------------------------------------------

def test_new_folder_makes_it_and_selects_it(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base), mode="folder")
    assert browser.make_folder("  zeta  ")
    assert (base / "zeta").is_dir() and browser.selection == [str(base / "zeta")] and browser.rows[browser.cursor]["name"] == "zeta"
    assert browser.result() == [str(base / "zeta")]


def test_new_folder_refuses_a_bad_name_and_a_taken_one_and_a_place_that_will_not(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base), mode="save")
    for bad, why in (("", "Type a name"), ("  ", "Type a name"), ("a/b", "not a name"), ("..", "not a name")):
        assert not browser.make_folder(bad) and why in browser.message
    assert not browser.make_folder("beta") and browser.message == "beta already exists"
    assert not browser.make_folder("b.txt") and "already exists" in browser.message
    assert sorted(p.name for p in base.iterdir()) == sorted(["beta", "Alpha", ".hidden_dir", "b.txt", "A.TDL", "c.tdl", ".secret", "notes.md"])
    fs = Fake({"/h": []})
    denied = FileBrowser(fs, start="/h", mode="save")
    fs.denied.add("/h")
    assert not denied.make_folder("new") and "permission denied" in denied.message and fs.made == []


# -- the keyboard --------------------------------------------------------------------------------------------------------------------

def test_the_arrows_page_keys_home_and_end_move_and_select_one_row(tmp_path):
    for i in range(30):
        (tmp_path / f"f{i:02d}").write_text("")
    browser = FileBrowser(start=str(tmp_path))
    browser.page_rows = 8
    browser.press("arrow_down")
    assert browser.cursor == 0 and browser.selection == [str(tmp_path / "f00")]
    browser.press("arrow_down")
    browser.press("arrow_down")
    assert browser.cursor == 2
    browser.press("arrow_up")
    assert browser.cursor == 1
    browser.press("page_down")
    assert browser.cursor == 8
    browser.press("page_up")
    assert browser.cursor == 1
    browser.press("end")
    assert browser.cursor == 29 and browser.selection == [str(tmp_path / "f29")]
    browser.press("arrow_down")
    assert browser.cursor == 29  # held to the last
    browser.press("home")
    assert browser.cursor == 0
    browser.press("arrow_up")
    assert browser.cursor == 0
    browser.press("page_up")
    assert browser.cursor == 0
    assert browser.press("f13") == "" and browser.cursor == 0


def test_shift_with_the_arrows_extends_the_selection_when_several_are_allowed(tmp_path):
    for i in range(6):
        (tmp_path / f"f{i}").write_text("")
    browser = FileBrowser(start=str(tmp_path), multiple=True)
    browser.press("home")
    browser.press("arrow_down", shift=True)
    browser.press("arrow_down", shift=True)
    assert [os.path.basename(p) for p in browser.selection] == ["f0", "f1", "f2"] and browser.cursor == 2
    browser.press("arrow_up", shift=True)
    assert [os.path.basename(p) for p in browser.selection] == ["f0", "f1"]
    one = FileBrowser(start=str(tmp_path))
    one.press("home")
    one.press("arrow_down", shift=True)
    assert [os.path.basename(p) for p in one.selection] == ["f1"]  # shift does nothing extra for one


def test_enter_opens_the_row_the_cursor_is_on_or_accepts_with_none(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base))
    assert browser.press("enter") == ""  # nothing to accept yet
    browser.press("home")
    assert browser.press("enter") == "entered"
    assert browser.path == str(base / "Alpha")
    browser.press("backspace")
    assert browser.path == str(base)
    browser.click(names(browser).index("b.txt"))
    browser.cursor = -1
    assert browser.press("enter") == "accept"
    browser.press("end")
    assert browser.press("enter") == "accept" and browser.result() == [str(base / "notes.md")]


def test_alt_arrows_and_backspace_walk_the_history(tmp_path):
    base = tree(tmp_path)
    browser = FileBrowser(start=str(base))
    browser.navigate("Alpha")
    browser.press("arrow_left", alt=True)
    assert browser.path == str(base)
    browser.press("arrow_right", alt=True)
    assert browser.path == str(base / "Alpha")
    browser.press("arrow_up", alt=True)
    assert browser.path == str(base)
    browser.navigate("Alpha")
    browser.press("backspace")
    assert browser.path == str(base)


def test_typing_jumps_to_the_next_name_that_starts_with_it(tmp_path):
    for name in ("apple", "apricot", "banana", "avocado", "Berry"):
        (tmp_path / name).write_text("")
    now = [10.0]
    browser = FileBrowser(start=str(tmp_path), clock=lambda: now[0])
    browser.press("b")
    assert browser.rows[browser.cursor]["name"] == "banana"
    browser.press("e")
    assert browser.rows[browser.cursor]["name"] == "Berry"  # `be`
    now[0] += 5
    browser.press("a")
    assert browser.rows[browser.cursor]["name"] == "apple"
    browser.press("a")  # `aa` steps through the a's
    assert browser.rows[browser.cursor]["name"] == "apricot"
    now[0] += 5
    browser.press("q")
    assert browser.rows[browser.cursor]["name"] == "apricot"  # no match: stays


def test_reveal_scrolls_just_far_enough(tmp_path):
    for i in range(30):
        (tmp_path / f"f{i:02d}").write_text("")
    browser = FileBrowser(start=str(tmp_path))
    browser.page_rows, browser.row_height = 5, 40.0
    assert browser.reveal(0.0) == 0.0  # no cursor
    browser.move(2)
    assert browser.reveal(0.0) == 0.0
    browser.move(7)
    assert browser.reveal(0.0) == 7 * 40 + 40 - 200
    browser.move(1)
    assert browser.reveal(160.0) == 40.0
    browser.move(6)
    assert browser.reveal(160.0) == 160.0  # in view already


def test_listeners_hear_each_operation(tmp_path):
    browser = FileBrowser(start=str(tree(tmp_path)))
    heard = []
    stop = browser.on_change(lambda: heard.append(browser.path))
    browser.navigate("Alpha")
    browser.click(0)
    browser.set_show_hidden(True)
    assert len(heard) == 3
    stop()
    browser.up()
    assert len(heard) == 3


def test_the_mode_is_checked():
    with pytest.raises(ValueError, match="mode is one of"):
        FileBrowser(Fake({"/": []}), mode="pick")
