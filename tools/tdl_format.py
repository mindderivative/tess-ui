"""TDL text for the generators: a value or a small block shown on a docs page, in the spelling a `.tdl` file uses.

The generators read the shipped `.tdl` files through the front ends, which hand back plain dicts (lower snake_case keys, `{{ expr }}` for a slot). A docs page
shows them as an author writes them: `Title_Case` keys, `<| expr |>` slots. This is the one place that spelling is made.
"""

from __future__ import annotations

import json
import re
from typing import Any

from tess_ui.spec.tdl import title_case

_SLOT = re.compile(r"\{\{\s*(.*?)\s*\}\}", re.S)
_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*$")
_PERCENT = re.compile(r"^[0-9]+%$")


def key(name: str) -> str:
    """`corner_radius` is `Corner_Radius`."""
    return title_case(name)


def slots(text: str) -> str:
    """A `{{ expr }}` template as TDL spells it, `<| expr |>`."""
    return _SLOT.sub(lambda m: f"<| {m.group(1)} |>", text)


def value(item: Any) -> str:
    """One value on one line: a word bare, other text quoted, a slot as a slot, a list `[a, b]`, a mapping `{ Key: v }`."""
    if item is None:
        return "null"
    if isinstance(item, bool):
        return "true" if item else "false"
    if isinstance(item, (int, float)):
        return repr(item)
    if isinstance(item, str):
        text = slots(item)
        if text.startswith("<|") and text.endswith("|>") and text.count("<|") == 1:
            return text
        if (_WORD.match(text) and text not in ("true", "false", "null")) or _PERCENT.match(text):
            return text
        return json.dumps(text, ensure_ascii=False)
    if isinstance(item, (list, tuple)):
        return "[" + ", ".join(value(entry) for entry in item) + "]"
    if isinstance(item, dict):
        if not item:
            return "{ }"
        return "{ " + ", ".join(f"{key(str(k))}: {value(v)}" for k, v in item.items()) + " }"
    return json.dumps(str(item))


def rule(selectors: dict[str, Any], style: dict[str, Any], indent: str = "") -> list[str]:
    """The lines of one stylesheet `Rule` block: the selectors, then a `Style` block on one line."""
    lines = [f"{indent}Rule {{"]
    lines += [f"{indent}  {key(k)}: {value(v)}" for k, v in selectors.items()]
    body = ", ".join(f"{key(k)}: {value(v)}" for k, v in style.items())
    lines.append(f"{indent}  Style {{ {body} }}")
    lines.append(f"{indent}}}")
    return lines


def stylesheet(rules: list[tuple[dict[str, Any], dict[str, Any]]]) -> str:
    """A stylesheet body (no metadata block) for `(selectors, style)` pairs."""
    lines = ["Styles {"]
    for selectors, style in rules:
        lines += rule(selectors, style, "  ")
    lines.append("}")
    return "\n".join(lines)


_NAMES: dict[bool, set[str]] = {}


def _names(widget_properties: bool) -> set[str]:
    """Every key a TDL file can carry that is spelled in lower snake_case in the code: a node's universal keys, style fields, handler events and
    accessibility keys, and (when `widget_properties`) the properties of the widgets and shipped views. What a docs sentence means by one of them in
    backticks is the `Title_Case` key. The widget properties are left out for the schemas' own descriptions, where a word such as `transparent` or `page` is a value."""
    if widget_properties not in _NAMES:
        import importlib.util
        from pathlib import Path

        from tess_ui.shipped import ViewLibrary, shipped_views
        from tess_ui.spec import cascade
        from tess_ui.spec import widgets as registry

        names: set[str] = set(registry._UNIVERSAL) | set(cascade.STYLE_FIELDS)
        here = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location("generate_schema", here / "generate_schema.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        defs = module._definitions(fragment=False)
        names |= set(defs["handlers"]["properties"]) | set(defs["a11y"]["properties"])
        if widget_properties:
            for name in registry.names():
                decl = registry.lookup(name)
                names |= set(decl.properties if decl else ())
            library = ViewLibrary()
            for name in shipped_views():
                decl = library.decl(name)
                names |= set(decl.properties if decl else ())
        _NAMES[widget_properties] = names
    return _NAMES[widget_properties]


_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
_SNAKE = re.compile(r"[a-z][a-z0-9_]*")
_LIST = re.compile(r"[\[{]\s*[a-z][a-z0-9_]*(?:,\s*[a-z][a-z0-9_]*)*\s*[\]}]")


def prose(text: str, *, widget_properties: bool = True) -> str:
    """A sentence with its code spans in TDL spelling: a span that is one key (`flex_direction`, `on_link`), a path of them (`style.width`), a list of them
    (`{left, right}`) is `Title_Case`, `{{ expr }}` is `<| expr |>`, and the keys in `key: value` are `Title_Case`."""
    names = _names(widget_properties)

    def known(word: str) -> str:
        return key(word) if word in names else word

    def span(match: re.Match[str]) -> str:
        body = match.group(1)
        if _SNAKE.fullmatch(body):
            return f"`{known(body)}`"
        if re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", body) and all(part in names for part in body.split(".")):
            return "`" + ".".join(key(part) for part in body.split(".")) + "`"
        if _LIST.fullmatch(body):
            return "`" + re.sub(r"[a-z][a-z0-9_]*", lambda m: known(m.group(0)), body) + "`"
        keyed = re.sub(r"(?<![\w.'\"])([a-z][a-z0-9_]*)(?=:(?:\s|$))", lambda m: known(m.group(1)), body)
        return f"`{slots(keyed)}`"

    return _CODE.sub(span, text)
