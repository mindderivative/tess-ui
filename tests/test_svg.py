"""0.4.2 (#88): `kind: Svg`, the engine's `svg` node, and the pictures an SVG refers to.

The engine draws the document itself but decodes no image format, so Tesserae decodes each `<image href>`
(PNG, JPEG, GIF, WebP; also a `data:` URL, whose `href` it rewrites) and passes `svg_images`, keyed by the
`href` as written. `style.foreground` is `svg_color` (what `currentColor` is).
"""

import base64
import gzip
import io
import json

import pytest
from PIL import Image

from tess_ui import App, View
from tess_ui.spec import ComponentError
from tess_ui.spec.images import extract_images
from tess_ui.widgets import svg as svg_widget

SEED = (0x67, 0x50, 0xA4, 0xFF)
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="40" height="20">'


def _document(*inner):
    return HEAD + '<rect width="40" height="20" fill="currentColor"/>' + "".join(inner) + "</svg>"


def _png(tmp_path, name="p.png", size=(4, 2), color=(255, 0, 0, 255)):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, color).save(path)
    return path


def _data_png(color=(0, 255, 0, 255)):
    buffer = io.BytesIO()
    Image.new("RGBA", (2, 2), color).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _view(tmp_path, svg=None, style=None):
    """Writes the spec of a view with one `Svg` node, as a JSON file in `tmp_path` (what `_spec` reads: the `svg:` mapping and `style:` are what the tests vary)."""
    spec = {"id": "root", "kind": "Container", "style": {"width": 300, "height": 200}, "children": [
        {"id": "logo", "kind": "Svg", "svg": {"src": "logo.svg"} if svg is None else svg,
         "style": {"width": 80, "foreground": "primary"} if style is None else style}]}
    (tmp_path / "S_spec.json").write_text(json.dumps(spec), encoding="utf-8")


def _spec(folder):
    """The spec written by `_view` (one is made when the test has not), with its images decoded: `(spec, frames)`."""
    if not (folder / "S_spec.json").exists():
        _view(folder)
    return extract_images(json.loads((folder / "S_spec.json").read_text(encoding="utf-8")), folder)


def _build(tmp_path, **kwargs):
    app = App(width=400, height=300, theme_seed=SEED, **kwargs)
    spec, frames = _spec(tmp_path)
    view = View(spec, window=app.window, frames={node_id: (rgba, w, h) for node_id, rgba, w, h in frames})
    app.window.root.add_child(view.root)
    app.window.advance(16)
    return app, view


def test_an_svg_file_is_drawn_by_the_engine_with_its_pictures_decoded(tmp_path):
    (tmp_path / "logo.svg").write_text(_document('<image xlink:href="p.png" width="10" height="5"/>'), encoding="utf-8")
    _png(tmp_path)
    app, view = _build(tmp_path)
    node = view.node("logo")
    assert node.get("svg_size") == (40.0, 20.0)
    images = node.get("svg_images")
    assert list(images) == ["p.png"] and images["p.png"][1:] == (4, 2) and images["p.png"][0][:4] == bytes([255, 0, 0, 255])
    assert "<rect" in node.get("svg") and node.get("layout_width") == 80.0


def test_foreground_is_what_current_color_means_and_follows_the_theme(tmp_path):
    (tmp_path / "logo.svg").write_text(_document(), encoding="utf-8")
    app, view = _build(tmp_path)
    light = app.theme.role("primary")
    assert view.node("logo").get("svg_color") == app.theme.role("primary")
    before = view.node("logo").get("svg_color")
    app.set_dark(not app.dark)
    app.window.advance(16)
    assert view.node("logo").get("svg_color") != before and view.node("logo").get("svg_color") == app.theme.role("primary")
    assert light is not None


def test_an_svg_with_no_foreground_leaves_current_color_alone(tmp_path):
    (tmp_path / "logo.svg").write_text(_document(), encoding="utf-8")
    _view(tmp_path, style={"width": 80})
    app, view = _build(tmp_path)
    assert view.node("logo").get("svg_color") is None


def test_a_document_in_the_view_finds_its_pictures_beside_the_view(tmp_path):
    _png(tmp_path)
    doc = _document('<image href="p.png" width="4" height="2"/>').replace("\n", " ")
    spec = {"id": "r", "kind": "Container", "children": [{"id": "s", "kind": "Svg", "svg": {"content": doc}}]}
    out, _ = extract_images(spec, tmp_path)
    assert list(out["children"][0]["svg"]["images"]) == ["p.png"]


def test_a_data_url_picture_is_decoded_and_its_href_rewritten(tmp_path):
    url = _data_png()
    (tmp_path / "logo.svg").write_text(_document(f'<image href="{url}" width="4" height="4"/>'), encoding="utf-8")
    app, view = _build(tmp_path)
    node = view.node("logo")
    (key,) = node.get("svg_images")
    assert key.startswith("tesserae-picture-") and f'href="{key}"' in node.get("svg") and "data:image/png" not in node.get("svg")


def test_a_nested_svg_and_an_address_are_left_alone(tmp_path):
    nested = "data:image/svg+xml;base64," + base64.b64encode(b"<svg xmlns='http://www.w3.org/2000/svg' width='4' height='4'/>").decode()
    (tmp_path / "logo.svg").write_text(
        _document(f'<image href="{nested}"/>', '<image href="https://example.com/p.png"/>', '<image href="#local"/>'), encoding="utf-8")
    app, view = _build(tmp_path)
    assert view.node("logo").get("svg_images") == {} and nested in view.node("logo").get("svg")


def test_a_gzip_compressed_svg_works(tmp_path):
    (tmp_path / "logo.svg").write_bytes(gzip.compress(_document().encode()))
    app, view = _build(tmp_path)
    assert view.node("logo").get("svg_size") == (40.0, 20.0)


def test_a_picture_named_twice_is_decoded_once(tmp_path):
    (tmp_path / "logo.svg").write_text(_document('<image href="p.png"/><image href="p.png"/>'), encoding="utf-8")
    _png(tmp_path)
    app, view = _build(tmp_path)
    assert list(view.node("logo").get("svg_images")) == ["p.png"]


def test_a_picture_in_a_folder_is_found_relative_to_the_svg_file(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.svg").write_text(_document('<image href="img/p.png"/>'), encoding="utf-8")
    _png(tmp_path / "assets", "img/p.png")
    _view(tmp_path, svg={"src": "assets/logo.svg"})
    app, view = _build(tmp_path)
    assert list(view.node("logo").get("svg_images")) == ["img/p.png"]


@pytest.mark.parametrize("href, message", [
    ("missing.png", "cannot read"),
    ("/etc/passwd", "must be a relative path"),
    ("../outside.png", "is outside the view's folder"),
])
def test_a_picture_that_cant_be_used_is_an_error_naming_it(tmp_path, href, message):
    folder = tmp_path / "v"
    folder.mkdir()
    _png(tmp_path, "outside.png")
    (folder / "logo.svg").write_text(_document(f'<image href="{href}"/>'), encoding="utf-8")
    _view(folder)
    with pytest.raises(ComponentError, match=rf"widget 'logo': svg <image href='{href}'>: .*{message}"):
        _spec(folder)


def test_a_picture_that_is_not_a_picture_is_an_error(tmp_path):
    (tmp_path / "logo.svg").write_text(_document('<image href="p.png"/>'), encoding="utf-8")
    (tmp_path / "p.png").write_text("not a picture")
    _view(tmp_path)
    with pytest.raises(ComponentError, match="cannot decode"):
        _spec(tmp_path)


def test_a_picture_longer_than_8192_pixels_is_refused(tmp_path):
    (tmp_path / "logo.svg").write_text(_document('<image href="wide.png"/>'), encoding="utf-8")
    _png(tmp_path, "wide.png", size=(8193, 1))
    _view(tmp_path)
    with pytest.raises(ComponentError, match="at most 8192 pixels on a side, got 8193x1"):
        _spec(tmp_path)


@pytest.mark.parametrize("svg, message", [
    ({}, "takes `src:`"), ({"src": "a.svg", "content": "x"}, "takes `src:`"), ({"src": 3}, "svg.src must be a string"),
    ({"src": "/abs.svg"}, "must be a relative path"), ({"src": "gone.svg"}, "cannot read"),
])
def test_an_svg_node_says_what_is_wrong_with_it(tmp_path, svg, message):
    _view(tmp_path, svg=svg)
    with pytest.raises(ComponentError, match=message):
        _spec(tmp_path)


def test_a_malformed_document_is_an_error_naming_the_widget(tmp_path):
    (tmp_path / "logo.svg").write_text("<svg><rect></svg>", encoding="utf-8")
    _view(tmp_path)
    with pytest.raises(ValueError, match='widget "logo"'):
        _build(tmp_path)


def test_the_svg_widget_from_a_file_and_from_text(tmp_path):
    (tmp_path / "icon.svg").write_text(_document('<image href="p.png"/>'), encoding="utf-8")
    _png(tmp_path)
    app = App(width=300, height=200, theme_seed=SEED)
    from_file = svg_widget(app.window, tmp_path / "icon.svg", width=60, color="on_surface", label="A logo")
    assert from_file.node.get("svg_size") == (40.0, 20.0) and list(from_file.node.get("svg_images")) == ["p.png"]
    assert from_file.node.get("svg_color") == app.theme.role("on_surface") and from_file.node.get("role") == "img"
    from_text = svg_widget(app.window, _document(), height=30)
    assert from_text.node.get("svg_size") == (40.0, 20.0) and from_text.node.get("a11y_hidden") is True
    with pytest.raises(ValueError, match="cannot read"):
        svg_widget(app.window, _document('<image href="nope.png"/>'), base=tmp_path)


def test_changing_the_documents_text_reconciles_in_place(tmp_path):
    (tmp_path / "logo.svg").write_text(_document(), encoding="utf-8")
    app, view = _build(tmp_path)
    node = view.node("logo")
    (tmp_path / "logo.svg").write_text(HEAD.replace('width="40" height="20"', 'width="10" height="10"') + "</svg>", encoding="utf-8")
    spec, _ = _spec(tmp_path)
    view.reconcile(spec)
    assert node.get("svg_size") == (10.0, 10.0)
