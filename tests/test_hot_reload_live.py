"""End to end: `App.run(hot_reload=True)` reloads a screen while the
app is running -- `watchfiles` notices the edit on the watcher thread,
and the reload reaches the live tree through `tess_re`'s `LoopHandle`.

Runs in a fresh subprocess: a second real `App.run()` in one pytest
process can break unrelated tests (found by `tre`'s own M87 testing).
Skips when no frame renders (no display), since `App.run()` then returns
at once and there is nothing to test.

Timing is deterministic rather than raced: idle frames take
microseconds, so a background edit could land after `max_frames` ran
out. Instead a callable queued before `run()` makes the edit on the
first frame and re-queues itself (20 ms per frame) until the new text
shows up, re-applying the same edit every half second in case the watcher
wasn't listening yet (not every frame: a file rewritten that often never
settles, so the watcher keeps waiting for the save to finish, #39).
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT = textwrap.dedent(
    '''
    import sys, time

    # An editor saves once. A watcher waits for a save to settle (two
    # readings 50 ms apart that agree, #39), so a file rewritten on every
    # frame never settles: save again only if the reload hasn't shown up
    # after half a second.
    _saved = [0.0]

    def save_due():
        now = time.monotonic()
        if now - _saved[0] < 0.5:
            return False
        _saved[0] = now
        return True
    from pathlib import Path

    work = Path(sys.argv[1])
    sys.path.insert(0, str(work))
    from Home_ViewModel import HomeViewModel
    from tess_ui import App

    def view_text(content):
        return (
            "---\\nTDL: 0.2\\nName: home\\n---\\nContainer {\\n  Name: home\\n  Children {\\n"
            "    Text { Name: label, Text: " + content + ", Typography_Role: body_large,"
            ' Style { Width: 100, Height: 20, Foreground: "#000000" } }\\n  }\\n}\\n'
        )

    (work / "Views").mkdir()
    view_path = work / "Views" / "Home_View.tdl"
    view_path.write_text(view_text("Hello"))

    app = App(root=work, width=200, height=80, title="hot_reload_live")
    app.bind(HomeViewModel)
    view = app.open_view("Home")
    app.show("home")
    handle = app.thread_handle()
    state = {"frames": 0, "seen": None}
    deadline = time.monotonic() + 10

    def check():
        state["frames"] += 1
        if view.node("root.label").get("text") == "Goodbye":
            state["seen"] = "Goodbye"
            return
        if time.monotonic() < deadline:
            if save_due():
                view_path.write_text(view_text("Goodbye"))  # the "editor save"
            time.sleep(0.02)
            handle.call_soon(check)

    handle.call_soon(check)
    app.run(max_frames=2000, hot_reload=True)
    print("FRAMES", state["frames"], "SEEN", state["seen"])
    '''
)


def test_app_run_hot_reload_updates_the_live_view(tmp_path: Path):
    """A view opened with `open_view` reloads while `run(hot_reload=True)` runs."""
    (tmp_path / "Home_ViewModel.py").write_text(
        "from tess_ui import ViewModel\n\n\nclass HomeViewModel(ViewModel):\n    views = \"home\"\n"
    )
    script = tmp_path / "run_app.py"
    script.write_text(SCRIPT)

    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path)], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    frames, seen = result.stdout.split()[1], result.stdout.split()[3]
    if frames == "0":
        pytest.skip("no display reachable -- App.run() rendered no frames")
    assert seen == "Goodbye", result.stdout + result.stderr


STYLE_SCRIPT = textwrap.dedent(
    '''
    import sys, time

    # An editor saves once. A watcher waits for a save to settle (two
    # readings 50 ms apart that agree, #39), so a file rewritten on every
    # frame never settles: save again only if the reload hasn't shown up
    # after half a second.
    _saved = [0.0]

    def save_due():
        now = time.monotonic()
        if now - _saved[0] < 0.5:
            return False
        _saved[0] = now
        return True
    from pathlib import Path

    work = Path(sys.argv[1])
    sys.path.insert(0, str(work))
    from Home_ViewModel import HomeViewModel
    from tess_ui import App
    from tess_ui.tokens import elevation_shadows

    HEADER = "---\\nTDL: 0.2\\nName: %s\\n---\\n"

    def theme_text(elevation, colours=""):
        return HEADER % "brand" + "Theme {\\n  Styles { Item { Kind: Rect, Style { Elevation: " + str(elevation) + " } } }\\n" + colours + "}\\n"

    def sheet_text(radius):
        return HEADER % "default" + "Styles { Rule { Widget: Rect, Style { Corner_Radius: " + str(radius) + " } } }\\n"

    theme = work / "brand_Theme.tdl"
    sheet = work / "default_Stylesheet.tdl"
    theme.write_text(theme_text(1))
    sheet.write_text(sheet_text(2))
    (work / "Views").mkdir()
    view_path = work / "Views" / "Home_View.tdl"
    view_path.write_text(HEADER % "home" + 'Rect { Name: home, Style { Width: 10, Height: 10, Background: "#112233" } }\\n')

    app = App(root=work, width=200, height=80, title="style_reload_live",
              theme_seed=(0x67, 0x50, 0xA4, 0xFF), custom_theme=theme, stylesheet=sheet)
    app.bind(HomeViewModel)
    view = app.open_view("Home")
    app.show("home")
    handle = app.thread_handle()
    state = {"frames": 0, "seen": None}
    deadline = time.monotonic() + 10
    new_theme = theme_text(5, '  Colors { Primary: "#0000FF" }\\n')

    def check():
        state["frames"] += 1
        box = view.node("root")
        got = (box.get("shadows"), box.get("corner_radius"), app.theme.role("primary"))
        if got == (elevation_shadows(5), 9.0, (0, 0, 255, 255)):
            state["seen"] = "restyled"
            return
        if time.monotonic() < deadline:
            if save_due():
                theme.write_text(new_theme)  # the "editor saves"
                sheet.write_text(sheet_text(9))
            time.sleep(0.02)
            handle.call_soon(check)
        else:
            state["seen"] = "stuck:" + repr(got).replace(" ", "")

    handle.call_soon(check)
    app.run(max_frames=2000, hot_reload=True)
    print("FRAMES", state["frames"], "SEEN", state["seen"])
    '''
)


def test_app_run_hot_reload_restyles_on_theme_and_stylesheet_edits(tmp_path: Path):
    """M31: editing the theme file and the default stylesheet file while
    the app runs re-styles the live screen and re-themes the app."""
    (tmp_path / "Home_ViewModel.py").write_text(
        "from tess_ui import ViewModel\n\n\nclass HomeViewModel(ViewModel):\n    views = \"home\"\n"
    )
    script = tmp_path / "run_app.py"
    script.write_text(STYLE_SCRIPT)

    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path)], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    frames, seen = result.stdout.split()[1], result.stdout.split()[3]
    if frames == "0":
        pytest.skip("no display reachable -- App.run() rendered no frames")
    assert seen == "restyled", result.stdout + result.stderr


COMPONENT_SCRIPT = textwrap.dedent(
    '''
    import sys, time

    # An editor saves once. A watcher waits for a save to settle (two
    # readings 50 ms apart that agree, #39), so a file rewritten on every
    # frame never settles: save again only if the reload hasn't shown up
    # after half a second.
    _saved = [0.0]

    def save_due():
        now = time.monotonic()
        if now - _saved[0] < 0.5:
            return False
        _saved[0] = now
        return True
    from pathlib import Path

    work = Path(sys.argv[1])
    sys.path.insert(0, str(work))
    from Home_ViewModel import HomeViewModel
    from tess_ui import App

    def row_text(content):
        return ("---\\nTDL: 0.2\\nName: Row\\n---\\nText { Typography_Role: body_large, Text: " + content + ","
                ' Style { Width: 100, Height: 20, Foreground: "#000000" } }\\n')

    (work / "Views").mkdir()
    row_path = work / "Views" / "Row_View.tdl"
    row_path.write_text(row_text("Hello"))
    view_path = work / "Views" / "Home_View.tdl"
    view_path.write_text("---\\nTDL: 0.2\\nName: home\\n---\\nContainer {\\n  Name: home\\n  Style { Flex_Direction: vertical }\\n"
                         "  Children {\\n    Row { Name: one }\\n    Row { Name: two }\\n  }\\n}\\n")

    app = App(root=work, width=200, height=80, title="component_reload_live")
    app.bind(HomeViewModel)
    view = app.open_view("Home")
    app.show("home")
    handle = app.thread_handle()
    state = {"frames": 0, "seen": None}
    deadline = time.monotonic() + 10

    def check():
        state["frames"] += 1
        texts = [view.node(f"root.{n}").get("text") for n in ("one", "two")]
        if texts == ["Goodbye", "Goodbye"]:
            state["seen"] = "Goodbye"
            return
        if time.monotonic() < deadline:
            if save_due():
                row_path.write_text(row_text("Goodbye"))  # the "editor save"
            time.sleep(0.02)
            handle.call_soon(check)
        else:
            state["seen"] = "stuck:" + ",".join(map(str, texts))

    handle.call_soon(check)
    app.run(max_frames=2000, hot_reload=True)
    stopped = not app._watchers  # run() stopped them
    print("FRAMES", state["frames"], "SEEN", state["seen"], "STOPPED", stopped)
    '''
)


def test_app_run_hot_reload_updates_every_use_of_a_view_it_calls(tmp_path: Path):
    """M51: a view the screen calls is watched, and every live use of it reloads."""
    (tmp_path / "Home_ViewModel.py").write_text(
        "from tess_ui import ViewModel\n\n\nclass HomeViewModel(ViewModel):\n    views = \"home\"\n"
    )
    script = tmp_path / "run_app.py"
    script.write_text(COMPONENT_SCRIPT)
    result = subprocess.run([sys.executable, str(script), str(tmp_path)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    words = result.stdout.split()
    frames, seen, stopped = words[1], words[3], words[5]
    if frames == "0":
        pytest.skip("no display reachable -- App.run() rendered no frames")
    assert seen == "Goodbye" and stopped == "True", result.stdout + result.stderr
