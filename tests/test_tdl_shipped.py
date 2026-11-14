"""Piece 3 of the TDL switch: every shipped `*_View.yaml` has its `*_View.tdl` beside it, current, and loading to the same mapping.

The YAML files are still what tess-ui loads; the `.tdl` files are the converter's output, kept in step until the cutover (piece 10)."""

from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front end needs tess_dl (Python 3.14)")

from tess_ui.migrate_tdl import convert_view  # noqa: E402
from tests.test_migrate_tdl import reads_equal  # noqa: E402

VIEWS = Path(__file__).parent.parent / "src" / "tess_ui" / "views"
SHIPPED = sorted(VIEWS.glob("*_View.yaml"))


def test_every_shipped_view_has_a_tdl_file_and_no_tdl_file_is_left_without_its_yaml():
    yaml_names = {p.name.removesuffix(".yaml") for p in SHIPPED}
    tdl_names = {p.name.removesuffix(".tdl") for p in VIEWS.glob("*_View.tdl")}
    assert len(SHIPPED) == 61
    assert yaml_names == tdl_names


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.name)
def test_the_tdl_file_is_what_the_converter_writes_now_and_loads_to_the_yaml_mapping(path):
    text = path.read_text(encoding="utf-8")
    tdl = path.with_suffix(".tdl")
    written = tdl.read_bytes().decode("utf-8")
    assert written == convert_view(text, path.name.removesuffix("_View.yaml"), path.name).text, f"{tdl.name} is stale: run `tesserae migrate-tdl --write`"
    assert reads_equal(text, written), path.name
