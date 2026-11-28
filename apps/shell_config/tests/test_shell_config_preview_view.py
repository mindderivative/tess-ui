"""The View tab's drawing against recorded preview models (fixtures/preview_*.json, made by tess_shell.preview on a small config): the geometry the picture draws, the colours it takes
from the model's tokens, the dimmed last good picture when the model has errors, and golden screenshots (a pixel difference under a small tolerance: the renderer's antialiasing differs between GPUs).
Regenerate the goldens with `TESS_UPDATE_GOLDEN=1 pytest apps/shell_config/tests/test_shell_config_preview_view.py`."""

import json
import os
from pathlib import Path

import pytest
import tess_re

from tess_shell_config.preview_view import DIM, PreviewPane, chips, rgba, sides

FIXTURES = Path(__file__).resolve().parent / "fixtures"
W, H = 640, 400


def model(name):
    return json.loads((FIXTURES / f"preview_{name}.json").read_text())


def drawn(data, *, bad=None, width=W, height=H):
    window = tess_re.Window(width=width, height=height)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, fill=(30, 30, 36, 255))
    stage = window.create("box", width=float(width), height=float(height), flex_shrink=0.0)
    window.root.add_child(stage)
    for _ in range(3):
        window.advance(16)
    pane = PreviewPane(window, stage)
    pane.show(data)
    if bad is not None:
        pane.show(bad)
    for _ in range(4):
        window.advance(16)
    return window, pane


def texts(node):
    found = []
    for child in node.children():
        if child.get("kind") == "text":
            found.append(child.get("text"))
        found += texts(child)
    return found


def test_colours_sides_and_chips_read_the_models_shapes():
    assert rgba("#12171D") == (0x12, 0x17, 0x1D, 255) and rgba("#abc") == (0xAA, 0xBB, 0xCC, 255) and rgba("#11223380", 0.5) == (0x11, 0x22, 0x33, 64)
    assert sides(4) == (4.0,) * 4 and sides([1, 2, 3, 4]) == (1.0, 2.0, 3.0, 4.0) and sides({"left": 4, "top": 1, "right": 2, "bottom": 3}) == (1.0, 2.0, 3.0, 4.0)
    bar = next(s for s in model("panels")["surfaces"] if s["name"] == "Top_Bar")
    assert chips(bar["blocks"]) == ["Notes"]


def test_the_picture_draws_the_surfaces_at_their_real_proportions_in_the_pane():
    window, pane = drawn(model("panels"))
    screen = max((n for n in pane.stage.children() if n.get("kind") == "box"), key=lambda n: n.get("layout_height"))
    scale = screen.get("layout_width") / 1920
    assert screen.get("layout_height") == pytest.approx(1080 * scale, abs=1.0)
    bar = next(n for n in pane.stage.children() if n.get("kind") == "box" and n.get("layout_width") == pytest.approx(1920 * scale, abs=1.0) and n is not screen
               and n.get("layout_height") == pytest.approx(36 * scale, abs=1.0))
    assert bar.get("layout_y") == pytest.approx(screen.get("layout_y"), abs=1.0)
    notes = next(n for n in pane.stage.children() if n.get("kind") == "box" and n.get("layout_width") == pytest.approx(280 * scale, abs=1.0))
    assert notes.get("layout_x") == pytest.approx(screen.get("layout_x") + 12 * scale, abs=1.0) and notes.get("layout_y") == pytest.approx(screen.get("layout_y") + 44 * scale, abs=1.0)
    names = texts(pane.stage)
    assert "Top_Bar" in names and "Notes" in names and any("DP-1" in t for t in names)


def test_the_colours_are_the_models_not_the_windows():
    data = model("panels")
    data["tokens"]["color.surface"] = "#ff0000"
    data["surfaces"][0]["style"] = {"Background": {"token": "color.surface", "value": "#ff0000"}}
    window, pane = drawn(data)
    bar = next(n for n in pane.stage.children() if n.get("kind") == "box" and n.get("layout_height") < 20 and n.get("layout_width") > 300)
    assert bar.get("fill")[:3] == (255, 0, 0)


def test_a_model_with_a_syntax_error_keeps_the_last_good_picture_dimmed_under_a_message():
    window, pane = drawn(model("panels"), bad={"findings": [{"severity": "error", "message": "x"}], "surfaces": []})
    assert pane.unavailable and "Preview unavailable: see Problems" in texts(pane.stage)
    assert "Top_Bar" in texts(pane.stage), "the last good picture is still there"
    screen = max((n for n in pane.stage.children() if n.get("kind") == "box"), key=lambda n: n.get("layout_height"))
    assert screen.get("fill")[3] == round(255 * DIM)
    pane.show(model("panels"))
    assert not pane.unavailable and "Preview unavailable: see Problems" not in texts(pane.stage)


def test_the_unavailable_message_is_readable_over_the_dimmed_picture_not_lost_in_it():
    good = drawn(model("panels"))[0].snapshot()
    bad = drawn(model("panels"), bad={"findings": [{"severity": "error"}], "surfaces": []})[0].snapshot()
    ink, plate = (230, 230, 235), (32, 32, 40)
    pixels, width, _ = bad
    corner = [tuple(pixels[(y * width + x) * 4 : (y * width + x) * 4 + 3]) for y in range(H - 32, H - 8) for x in range(8, 200)]
    assert any(max(abs(a - b) for a, b in zip(px, ink)) < 30 for px in corner), "light text pixels over the plate"
    assert sum(1 for px in corner if max(abs(a - b) for a, b in zip(px, plate)) < 12) > 500, "the plate under the message"
    assert bad[0] != good[0]


def test_the_desktop_work_area_is_drawn_and_named():
    window, pane = drawn(model("panels"))
    assert "Desktop" in texts(pane.stage)
    area = next(n for n in pane.stage.children() if n.get("kind") == "box" and n.get("layout_y") > 10 and n.get("fill")[3] < 60 and n.get("layout_height") > 200)
    assert area.get("stroke_width") == 1.0


def test_a_pane_that_is_too_small_says_so():
    window, pane = drawn(model("panels"), width=120, height=80)
    assert texts(pane.stage) == ["Make the pane larger to see the preview"]


def test_the_text_alternative_names_the_surfaces_and_says_when_the_picture_is_old():
    window, pane = drawn(model("panels"))
    alternative = pane.alternative()
    assert alternative.startswith("Shell preview:") and "bar Top_Bar, 1920 by 36 at 0, 0" in alternative and "panel Notes" in alternative
    pane.show({"findings": [{"severity": "error"}], "surfaces": []})
    assert "last good picture" in pane.alternative()


@pytest.mark.parametrize("name", ["panels", "frame"])
def test_the_picture_matches_its_golden_screenshot(name):
    window, _ = drawn(model(name))
    try:
        pixels, width, height = window.snapshot()
    except RuntimeError as error:
        pytest.skip(f"no GPU to render with: {error}")
    golden = FIXTURES / "golden" / f"preview_{name}.png"
    if os.environ.get("TESS_UPDATE_GOLDEN") or not golden.exists():
        tess_re.write_png(str(golden), pixels, width, height)
    pil = pytest.importorskip("PIL.Image", reason="reading the golden back needs Pillow")
    image = pil.open(golden).convert("RGBA")
    data, (gw, gh) = image.tobytes(), image.size
    assert (gw, gh) == (width, height)
    total = sum(abs(a - b) for a, b in zip(pixels, data, strict=True))
    assert total / len(pixels) < 2.0, f"the picture differs from {golden.name}: mean channel difference {total / len(pixels):.2f}"


# -- the live preview: what the editor holds, a worker thread, 300 ms -------------------------------------------------------------------

def test_overrides_are_the_text_of_the_files_with_unsaved_changes_only():
    from tess_shell_config.preview_source import overrides_of

    class Held:
        def __init__(self, text, dirty):
            self.text, self.dirty = text, dirty

    got = overrides_of(Path("/cfg"), {"Shells/Main_Shell.tdl": Held("new", True), "settings.tdl": Held("same", False)})
    assert got == {Path("/cfg/Shells/Main_Shell.tdl"): "new"}


@pytest.fixture
def live(tmp_path, schema):
    import shutil

    from test_shell_config_form_window import FormWindow
    from test_shell_config_window import CONFIG

    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    w = FormWindow(folder, tmp_path, schema)
    heard = []
    services = w.vm.services
    services.preview_sink = lambda model, reason: heard.append((model, reason))
    services.timer = lambda ms, fn: w.window.after(ms, fn)
    services.offload = __import__("tess_shell_config.shell", fromlist=["InlineOffload"]).InlineOffload()
    return w, heard


def test_an_edit_draws_the_view_once_after_300_ms_of_rest_from_the_editors_text(live, monkeypatch):
    w, heard = live
    seen = []
    monkeypatch.setattr("tess_shell_config.services.build_preview", lambda folder, overrides: seen.append(dict(overrides)) or {"surfaces": [], "findings": [], "outputs": [], "tokens": {}, "desktop": []})
    w.open()
    assert len(seen) == 1 and seen[0] == {}, "opening a file draws at once, from the disk"
    w.vm.services.edited(typing=True)
    w.vm.services.edited(typing=True)
    w.vm.services.edited(typing=True)
    w.settle(10)  # 160 ms: still resting
    assert len(seen) == 1
    w.settle(12)  # past 300 ms
    assert len(seen) == 2, "three edits in a burst are one drawing"


def test_unsaved_text_stands_in_for_the_file_in_the_overrides(live, monkeypatch):
    w, heard = live
    seen = []
    monkeypatch.setattr("tess_shell_config.services.build_preview", lambda folder, overrides: seen.append(dict(overrides)) or {"surfaces": [], "findings": [], "outputs": [], "tokens": {}, "desktop": []})
    w.open()
    w.session.model.set_text(w.session.model.text + "\n# typed\n")
    assert w.session.model.dirty
    w.vm.services.request_preview(soon=True)
    assert list(seen[-1].values()) == [w.session.model.text] and list(seen[-1])[0].name == "Main_Shell.tdl"


def test_a_shell_without_the_preview_model_says_so_instead_of_failing(live, monkeypatch):
    from tess_shell_config.preview_source import PreviewMissing

    w, heard = live

    def missing(folder, overrides):
        raise PreviewMissing("The View needs a newer tesserae-shell (one with the preview model).")

    monkeypatch.setattr("tess_shell_config.services.build_preview", missing)
    w.vm.services.request_preview(soon=True)
    assert heard[-1] == (None, "The View needs a newer tesserae-shell (one with the preview model).")


def test_the_real_preview_of_the_recorded_config_is_a_model_the_view_draws(tmp_path):
    pytest.importorskip("tess_shell.preview", reason="the shell's preview model needs a newer tesserae-shell")
    from tess_shell_config.preview_source import build_preview

    folder = tmp_path / "cfg"
    (folder / "Shells").mkdir(parents=True)
    (folder / "Shells" / "Main_Shell.tdl").write_text('---\nTDL: 0.2\nName: Main_Shell\n---\nShell { Monitor { Name: Main\n Index: default\n Children { Bar { Name: Top_Bar\n Edge: TOP\n Width: EXPAND\n Height: 32 } } } }\n')
    (folder / "settings.tdl").write_text('---\nTDL: 0.2\nName: Settings\n---\nSettings { Main_Shell: "Main_Shell.tdl" }\n')
    data = build_preview(folder, {})
    assert [s["name"] for s in data["surfaces"]] == ["Top_Bar"]
    over = build_preview(folder, {folder / "Shells" / "Main_Shell.tdl": "{"})
    assert not over["surfaces"] and any(f["severity"] == "error" for f in over["findings"]), "unsaved text that does not parse is an error with no surface"


def test_a_module_slot_says_the_words_the_file_gives_it_else_its_name():
    from tess_shell_config.preview_view import module_label

    assert module_label({"type": "module", "module": "Button", "label": "x", "params": {"Label": "", "Text": "Notes"}}) == "Notes"
    assert module_label({"type": "module", "module": "Clock", "label": "Clock", "params": {}}) == "Clock"
    assert module_label({"type": "module", "module": "Slider", "name": "Volume", "label": "Slider", "params": {"Value": 3}}) == "Volume"
    assert module_label({"type": "module", "module": "Text", "label": "Text", "params": {"Text": {"slot": "battery.level"}}}) == "Text"


def test_a_pane_does_not_repeat_its_tab_title_as_a_heading(tmp_path, schema):
    import shutil

    from test_shell_config_form_window import FormWindow
    from test_shell_config_window import CONFIG

    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    w = FormWindow(folder, tmp_path, schema)
    names = {inst.name for inst in w.built.view.handle.composition.walk()}
    assert not names & {"files_heading", "structure_heading", "form_heading", "text_heading"}
