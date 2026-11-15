"""0.3.2 (#79): the JSON schemas of the data the TDL front ends read.

`src/tess_ui/schema/*.json` (and their copies on the docs site) are written by `tools/generate_schema.py` from Tesserae's own code: a view (`widget`), a stylesheet
of rules (`stylesheet`) and a theme (`theme`). Every `.tdl` theme in the repository must validate against its schema, the mistakes a tool should flag must not,
the committed files must be what the generator writes (apart from the layout enums, which are `tess_re`'s and may grow without Tesserae changing), and the layout
enums they list must be ones `tess_re` accepts. The views and stylesheets are checked against theirs in `tests/test_widget_schema.py`.
"""

import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

pytest.importorskip("tess_dl", reason="the themes are TDL, which needs tess_dl (Python 3.14)")

from tess_ui.spec import cascade  # noqa: E402
from tess_ui.spec.tdl_theme import load_theme_tdl  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "src" / "tess_ui" / "schema"
SITE = ROOT / "docs" / "schema"
NAMES = {"widget": "tess-ui-widget-schema.json", "stylesheet": "tess-ui-stylesheet-schema.json", "theme": "tess-ui-theme-schema.json"}


def _schema(kind: str) -> dict:
    return json.loads((SCHEMAS / NAMES[kind]).read_text(encoding="utf-8"))


def _validator(kind: str) -> jsonschema.Draft7Validator:
    return jsonschema.Draft7Validator(_schema(kind))


def _generator():
    spec = importlib.util.spec_from_file_location("generate_schema", ROOT / "tools" / "generate_schema.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _theme_files():
    for path in sorted([*(ROOT / "src").rglob("*_Theme.tdl"), *(ROOT / "src").rglob("default_theme.tdl"), *(ROOT / "examples").rglob("*_Theme.tdl")]):
        yield pytest.param(path, id=path.relative_to(ROOT).as_posix())


@pytest.mark.parametrize("kind", sorted(NAMES))
def test_each_schema_is_valid_draft_07_and_says_what_it_is(kind):
    schema = _schema(kind)
    jsonschema.Draft7Validator.check_schema(schema)
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["$id"] == "https://mindderivative.github.io/tess-ui/schema/" + NAMES[kind]
    assert schema["description"] and ".tdl" in schema["description"]
    assert "yaml" not in schema["description"].lower()


def test_only_the_schemas_of_the_tdl_files_are_shipped():
    """The older syntax's schemas (a `kind:` view, a `*_Style.yaml` file) were for a YAML language server and are gone."""
    assert sorted(p.name for p in SCHEMAS.glob("*.json")) == sorted(NAMES.values())
    assert sorted(p.name for p in SITE.glob("*.json")) == sorted(NAMES.values())


def test_there_are_themes_to_check():
    assert len(list(_theme_files())) >= 9  # the default theme and the examples' `Brand_Theme.tdl`


@pytest.mark.parametrize("path", list(_theme_files()))
def test_every_theme_validates(path):
    data = load_theme_tdl(path.read_text(encoding="utf-8"), path.name)
    errors = sorted(_validator("theme").iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    assert not errors, "; ".join(f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message[:120]}" for e in errors[:3])


def test_theme_files_reject_a_misspelt_key():
    assert not list(_validator("theme").iter_errors({"seed": "#6750A4", "styles": [{"kind": "Rect", "style": {"corner_radius": 4}}]}))
    assert list(_validator("theme").iter_errors({"styles": [{"kind": "Rect", "style": {"corner_radious": 4}}]}))
    assert list(_validator("theme").iter_errors({"colours": {}}))


def test_a_theme_written_in_tdl_loads_to_what_the_schema_describes():
    theme = load_theme_tdl('---\nTDL: 0.2\nName: Mine\n---\nTheme {\n  Seed: "#6750A4"\n  Dark: true\n  Colors { Tertiary: "#C2410C" }\n'
                           '  Typography { Body_Large { Font_Size: 17 } }\n}\n', "Mine_Theme.tdl")
    assert theme == {"seed": "#6750A4", "dark": True, "colors": {"tertiary": "#C2410C"}, "typography": {"body_large": {"font_size": 17}}}
    assert not list(_validator("theme").iter_errors(theme))


TESS_RE_ENUMS = _generator().TESS_RE_ENUMS


def _enum_values(node, found: list) -> list:
    if isinstance(node, dict):
        if "enum" in node:
            found.extend(node["enum"])
        for value in node.values():
            _enum_values(value, found)
    elif isinstance(node, list):
        for item in node:
            _enum_values(item, found)
    return found


def _without_tre_enums(schema: dict) -> dict:
    """The schema with the layout enums, which are `tess_re`'s, taken out."""
    schema = json.loads(json.dumps(schema))
    properties = schema.get("definitions", {}).get("style", {}).get("properties", {})
    for name in TESS_RE_ENUMS:
        if name in properties:
            properties[name] = {"description": properties[name].get("description"), "<tess_re's values>": True}
    return schema


def test_the_committed_files_are_what_the_generator_writes():
    """Everything Tesserae owns must match; `tess_re`'s layout enums may be newer in `tess_re` than in the file."""
    generator = _generator()
    written = generator.schemas()
    assert sorted(written) == sorted(NAMES.values())
    for kind, name in NAMES.items():
        regenerated = json.loads(generator.render(written[name]))
        assert _without_tre_enums(regenerated) == _without_tre_enums(_schema(kind)), \
            f"{name} is out of date: run `python tools/generate_schema.py`"


def test_the_layout_enums_in_the_schema_are_ones_tre_accepts():
    generator = _generator()
    for kind in ("widget", "theme"):
        properties = _schema(kind)["definitions"]["style"]["properties"]
        for name in TESS_RE_ENUMS:
            listed = [v for v in _enum_values(properties[name], []) if not str(v).startswith("{{")]
            assert listed and set(listed) <= set(generator._tre_values(name)), f"{kind}: {name}: {listed}"


def test_the_site_copies_are_the_shipped_ones():
    for name in NAMES.values():
        assert (SITE / name).read_text(encoding="utf-8") == (SCHEMAS / name).read_text(encoding="utf-8"), name


def test_every_style_field_is_in_exactly_one_group():
    """0.4.4 (#101): the reference and the schema show style fields in sections; a new field can't go ungrouped."""
    listed = [name for names in cascade.STYLE_GROUPS.values() for name in names]
    assert len(listed) == len(set(listed)), "a style field is in two groups"
    assert set(listed) == cascade.STYLE_FIELDS, (
        f"ungrouped: {sorted(cascade.STYLE_FIELDS - set(listed))}, not a field: {sorted(set(listed) - cascade.STYLE_FIELDS)}")
    properties = _schema("widget")["definitions"]["style"]["properties"]
    assert {name: p["x-group"] for name, p in properties.items()} == cascade.STYLE_GROUP_OF
    assert all(f"({p['x-group']}.)" in p["description"] for p in properties.values())
