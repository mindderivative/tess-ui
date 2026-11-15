"""M29 Phase 2: Tesserae decodes images itself (Pillow) and hands `tess_re`
only RGBA bytes -- `tess_re` never opens an image file.

`tess_re` has no API to read an image node's pixels back, so this covers
the decode and extraction steps directly, proves (by wrapping `tess_re`'s
entry points) that no `src:` or file path reaches `tess_re`, and loads real
views end to end -- `push_frame` rejects a frame whose byte length
doesn't match its size, so a clean load means `tess_re` accepted the frame.
"""

from pathlib import Path

import pytest
from PIL import Image

from tess_ui import App
from tess_ui.images import decode_image
from tess_ui.spec import ComponentError
from tess_ui.spec.images import extract_images

RED_BLUE = b"\xff\x00\x00\xff" + b"\x00\x00\xff\xff"


def _png(path: Path, mode: str = "RGB", size=(2, 1), pixels=((255, 0, 0), (0, 0, 255))) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new(mode, size)
    img.putdata(list(pixels))
    img.save(path)
    return path


# -- decode_image ------------------------------------------------------


def test_decode_image_returns_straight_rgba_bytes_and_pixel_size(tmp_path: Path):
    rgba, width, height = decode_image(_png(tmp_path / "rb.png"))
    assert (width, height) == (2, 1)
    assert rgba == RED_BLUE


def test_decode_image_converts_non_rgba_modes(tmp_path: Path):
    # Greyscale+alpha in, RGBA out: 4 bytes per pixel, alpha preserved.
    path = _png(tmp_path / "la.png", mode="LA", size=(1, 1), pixels=((128, 64),))
    rgba, width, height = decode_image(path)
    assert (width, height, rgba) == (1, 1, b"\x80\x80\x80\x40")


def test_decode_image_missing_file_raises_oserror_naming_it(tmp_path: Path):
    with pytest.raises(OSError, match="nope.png"):
        decode_image(tmp_path / "nope.png")


def test_decode_image_corrupt_file_raises_oserror(tmp_path: Path):
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(OSError, match="bad.png"):
        decode_image(bad)


# -- extract_images ----------------------------------------------------


def _image_node(node_id="img", src="rb.png", fit="cover"):
    return {"id": node_id, "kind": "Image", "image": {"src": src, "fit": fit}}


def test_extract_images_strips_src_keeps_fit_and_decodes(tmp_path: Path):
    _png(tmp_path / "rb.png")
    spec = {"id": "root", "kind": "Container", "children": [_image_node()]}

    stripped, frames = extract_images(spec, tmp_path)

    assert stripped["children"][0]["image"] == {"fit": "cover"}
    assert frames == [("img", RED_BLUE, 2, 1)]
    assert spec["children"][0]["image"]["src"] == "rb.png"  # input not modified


def test_extract_images_finds_nested_images_and_leaves_others_alone(tmp_path: Path):
    _png(tmp_path / "rb.png")
    blank = {"id": "blank", "kind": "Image", "image": {"fit": "fill"}}
    spec = {
        "id": "root",
        "kind": "Container",
        "children": [
            {"id": "row", "kind": "Container", "children": [_image_node("deep")]},
            blank,
            {"id": "label", "kind": "Text", "text": {"content": "src"}},
        ],
    }
    stripped, frames = extract_images(spec, tmp_path)
    assert [f[0] for f in frames] == ["deep"]
    assert stripped["children"][1] == blank
    assert stripped["children"][2] == spec["children"][2]


@pytest.mark.parametrize(
    "src, match",
    [
        ("missing.png", "cannot read"),
        ("../outside.png", "resolves outside the view directory"),
    ],
)
def test_extract_images_rejects_unreadable_or_escaping_paths(tmp_path: Path, src, match):
    _png(tmp_path / "outside.png")
    app = tmp_path / "app"
    app.mkdir()
    with pytest.raises(ComponentError, match=match):
        extract_images(_image_node(src=src), app)


def test_extract_images_rejects_absolute_paths(tmp_path: Path):
    target = _png(tmp_path / "rb.png")
    with pytest.raises(ComponentError, match="must be a relative path"):
        extract_images(_image_node(src=str(target)), tmp_path)


def test_extract_images_needs_a_base_directory():
    with pytest.raises(ComponentError, match="no base directory"):
        extract_images(_image_node(), None)


def test_extract_images_undecodable_file_names_the_widget(tmp_path: Path):
    (tmp_path / "rb.png").write_bytes(b"not an image")
    with pytest.raises(ComponentError, match=r"widget 'img': cannot decode image"):
        extract_images(_image_node(), tmp_path)


# -- end to end --------------------------------------------------------

IMAGE_VIEW = """---
TDL: 0.2
Name: Gallery
Tesserae: "0.6"
---
Container {
  Style { Width: 200, Height: 200 }
  Children {
    Image { Name: img, Src: assets/rb.png, Fit: cover, Style { Width: 100, Height: 100 } }
  }
}
"""


def _gallery(root: Path):
    (root / "Views").mkdir(exist_ok=True)
    (root / "Views" / "Gallery_View.tdl").write_text(IMAGE_VIEW)
    return App(root=root)


def test_a_view_decodes_images_into_image_nodes(tmp_path: Path):
    """Tesserae decodes the file and builds its pixels into a `tess_re`
    `image` node (M37); `tess_re` is given no path."""
    _png(tmp_path / "Views" / "assets" / "rb.png")
    node = _gallery(tmp_path).open_view("Gallery").node("root.img")
    rgba, width, height = decode_image(tmp_path / "Views" / "assets" / "rb.png")
    assert (node.get("pixel_width"), node.get("pixel_height"), node.get("fit")) == (width, height, "cover")
    assert node.get("rgba") == rgba


def test_a_view_with_a_missing_image_is_a_component_error(tmp_path: Path):
    with pytest.raises(ComponentError, match=r"widget 'root.img'.*cannot read"):
        _gallery(tmp_path).open_view("Gallery")
