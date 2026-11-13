"""The schema reader: the recorded schema 1.1 reads into typed classes, an unknown major version is refused, a higher minor is tolerated, no key name is in the code."""

import copy
import json
from pathlib import Path

import pytest

import tess_shell_config
from tess_shell_config.schema import SUPPORTED_MAJOR, KeyInfo, Schema, SchemaError, UnsupportedSchemaVersion, parse_version

SOURCE = Path(tess_shell_config.__file__).parent


def test_the_recorded_schema_reads_into_every_table(schema, schema_data):
    assert schema.version == (1, 1) and schema.version_text == "1.1"
    assert list(schema.kinds) == list(schema_data["kinds"])
    assert list(schema.roots) == list(schema_data["roots"])
    assert list(schema.blocks) == list(schema_data["blocks"])
    assert list(schema.modules) == list(schema_data["modules"])
    assert set(schema.settings) == set(schema_data["settings"])
    assert {g: len(t) for g, t in schema.tokens.items()} == {g: len(t) for g, t in schema_data["tokens"].items()}
    assert len(schema.events) == len(schema_data["events"]) and len(schema.actions) == len(schema_data["actions"])
    assert schema.enums["Edge"] == tuple(schema_data["enums"]["Edge"])


def test_a_key_carries_its_kind_default_doc_and_hints(schema, schema_data):
    width = schema.roots["Bar"].keys["Width"]
    raw = schema_data["roots"]["Bar"]["keys"]["Width"]
    assert isinstance(width, KeyInfo)
    assert (width.kind, width.default, width.doc, width.required, width.group) == (raw["kind"], raw["default"], raw["doc"], raw["required"], raw["group"])
    assert width.units == tuple(raw["units"])
    assert schema.roots["Bar"].required == tuple(tuple(g) for g in schema_data["roots"]["Bar"]["required"])


def test_every_key_of_the_schema_reads_with_its_range_hints(schema, schema_data):
    seen = 0
    for table in ("roots", "blocks"):
        for name, raw_block in schema_data[table].items():
            block = getattr(schema, table)[name]
            for part in ("keys", "style"):
                for key, raw in raw_block[part].items():
                    info = getattr(block, part)[key]
                    seen += 1
                    assert info.minimum == raw.get("min") and info.maximum == raw.get("max") and info.step == raw.get("step") and info.unit == raw.get("unit")
                    assert info.tokens == tuple(raw["tokens"]) and info.preferred_tokens == tuple(raw["preferred_tokens"])
                    assert set(info.extra) == set(raw) - {"kind", "choices", "enum", "default", "doc", "slot", "required", "built", "group", "tokens", "preferred_tokens"}
    assert seen == 1017


def test_a_module_has_params_events_and_common_keys(schema, schema_data):
    button = schema.modules["Button"]
    assert button.root_block == schema_data["modules"]["Button"]["root_block"]
    assert list(button.params) == list(schema_data["modules"]["Button"]["params"])
    assert button.params["Text"].kind == "string" and button.common_keys[0] == "Key"
    assert sum(len(m.params) for m in schema.modules.values()) == 80


def test_the_tokens_a_key_accepts_are_its_groups_with_the_preferred_ones_first(schema):
    colour = next(k for _, k in schema.walk_keys() if k.tokens == ("color",))
    offered = schema.tokens_for(colour)
    assert offered and {t.group for t in offered} == {"color"}
    # a preferred entry can name one token: that one comes before the rest of its group
    shadow = next(k for _, k in schema.walk_keys() if "elevation" in k.tokens and any("." in p for p in k.preferred_tokens))
    offered = schema.tokens_for(shadow)
    first = shadow.preferred_tokens[0]
    assert f"{offered[0].group}.{offered[0].name}" == first and {t.group for t in offered} <= set(shadow.tokens)
    # with no preference the order is the groups' own
    plain = next(k for _, k in schema.walk_keys() if len(k.tokens) > 4 and not k.preferred_tokens)
    assert [t.group for t in schema.tokens_for(plain)] == [t.group for g in plain.tokens for t in schema.tokens[g].values()]


def test_an_unknown_major_version_is_refused_naming_both_versions(schema_data):
    data = copy.deepcopy(schema_data)
    data["schema_version"] = "2.0"
    with pytest.raises(UnsupportedSchemaVersion) as raised:
        Schema.from_data(data)
    message = str(raised.value)
    assert "2.0" in message and f"{SUPPORTED_MAJOR}.x" in message and isinstance(raised.value, SchemaError)


def test_a_higher_minor_version_is_read_and_keeps_what_it_adds(schema_data):
    data = copy.deepcopy(schema_data)
    data["schema_version"] = "1.9"
    data["future_table"] = {"x": 1}
    data["kinds"]["hologram"] = {"ui": "hologram", "note": "new", "model_kinds": [], "palette": 3}
    data["roots"]["Bar"]["keys"]["Width"]["fancy"] = True
    data["roots"]["Bar"]["new_part"] = [1]
    schema = Schema.from_data(data)
    assert schema.version == (1, 9) and schema.extra == {"future_table": {"x": 1}}
    assert schema.kinds["hologram"].extra == {"palette": 3}
    assert schema.roots["Bar"].keys["Width"].extra["fancy"] is True and schema.roots["Bar"].extra == {"new_part": [1]}


def test_a_kind_the_table_lacks_reads_as_the_generic_text_kind(schema):
    assert schema.kind("not_a_kind_yet").ui == "text"


@pytest.mark.parametrize("data, words", [
    ("not json", "not JSON"),
    ("[]", "not a table"),
    ('{"kinds": {}}', "no schema_version"),
    ('{"schema_version": "1.0"}', "lacks"),
    ('{"schema_version": "x"}', "not major.minor"),
])
def test_a_schema_that_is_not_one_is_refused_with_a_message(data, words):
    with pytest.raises(SchemaError, match=words):
        Schema.from_json(data)


def test_versions_parse_as_major_and_minor():
    assert parse_version("1.1") == (1, 1) and parse_version("2") == (2, 0) and parse_version(" 1.12 ") == (1, 12)


def test_the_code_writes_no_key_name_or_enum_value_of_the_schema(schema):
    """No key name, enum value or default is written in the application's code: every name in the schema's keys and enums, as a quoted word, is absent from the source."""
    names = {key.name for _, key in schema.walk_keys()} | {v for values in schema.enums.values() for v in values}
    names |= {p for m in schema.modules.values() for p in m.params} | {t.name for g in schema.tokens.values() for t in g.values()}
    words = {n for n in names if len(n) > 4 and n[0].isupper()}  # the shell's own words: Capitalised, not an English word the code needs
    text = "\n".join(p.read_text(encoding="utf-8") for p in SOURCE.rglob("*") if p.suffix in (".py", ".yaml"))
    quoted = {w for w in words if f'"{w}"' in text or f"'{w}'" in text}
    # the file types' root words and the configuration folder's own folder names are the application's vocabulary (what a file and a folder are called), not keys; nothing else may appear
    assert quoted <= {"Shell", "Module", "Style", "Stylesheet", "Theme", "Settings", "Shells", "Modules", "Styles", "Stylesheets", "Themes", "Icons"}, quoted


def test_the_recorded_file_is_the_schema_the_shell_exports(schema_text):
    assert json.loads(schema_text)["schema_version"] == "1.1"
