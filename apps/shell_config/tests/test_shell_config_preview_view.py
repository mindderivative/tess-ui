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
