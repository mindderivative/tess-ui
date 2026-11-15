#!/usr/bin/env python3
"""Writes the TDL reference page, `docs/api/tdl.md` (0.3.4, #83; for TDL since the YAML loaders went).

One page for every key of every kind of file Tesserae reads: a view's node (and its `Style`, `Handlers`, `A11y`), the widgets, a stylesheet and a theme.
Each block stub lists all of its properties with the values they take and what they do. It is written from the same schemas the editor tools use
(`tools/generate_schema.py`: the data a `.tdl` file loads to), so the page, the schemas and the code can't disagree; the only prose of its own is
`NODE_KEYS` and the sections about the file and the wrappers. Keys are shown as an author writes them in TDL (`Title_Case`; a value `<| expr |>`).

    python tools/generate_tdl_docs.py          # write docs/api/tdl.md
    python tools/generate_tdl_docs.py --check  # exit 1 if it is out of date
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import tdl_format  # noqa: E402  (tools/tdl_format.py: the TDL spelling of a value and of the prose)

OUTPUT = ROOT / "docs" / "api" / "tdl.md"
DATA = ROOT / "tools" / "component_docs.yaml"

#: What every node has beyond its widget's own properties: (key, the values it takes, what it does). Checked against `widgets._UNIVERSAL`, so a new one cannot go
#: undocumented. `widget` is the block head, `if`, `for` and `key` are the wrappers (below), `children` is the `Children` block.
NODE_KEYS = (
    ("name", "text", "An optional handle, unique in the view: a letter or `_`, then letters, digits and `_`. A ViewModel, a rule's `Name` or `Part`, a test and a hot reload that keeps state find the node by it."),
    ("slot", "text", "Which slot of the view being called this child goes into."),
    ("state", "a block", "Local state: a name and a starting value for each, as a Signal for this node and everything under it."),
    ("style", "a `Style` block", "How the node looks and lays out its children: the [style fields](#the-style), and any extra the widget declares."),
    ("classes", "a list of names", "Extra names a stylesheet rule's `Classes` can select."),
    ("handlers", "a `Handlers` block", "What each event calls: see [Handlers](#handlers)."),
    ("a11y", "an `A11y` block", "What assistive technology is told: see [Accessibility](#accessibility)."),
    ("interaction", "`true` or `false`, or text", "The hover, press and focus feedback of the node: `true`, `false`, a colour role, or an expression."),
    ("visible", "`true` or `false`, or text", "`false` hides a built node: it takes no room and no pointer, but stays in the tree with its state. An expression is allowed."),
    ("window_region", "`drag` or `none`", "`drag`: a press here moves the window (a title bar); `none`: it does not."),
    ("route", "text", "On a view call inside the window view: makes it a screen of the app; its route, such as `\"\"`, `settings` or `notes/{id}`."),
    ("focus_group", "`horizontal`, `vertical` or `both`", "The focusable nodes under it share one Tab stop, and the arrow keys move among them."),
    ("tooltip", "text or a block", "A tooltip: plain text, or a block with a title, text, delay and up to two actions."),
    ("params", "a `Params` block", "On the root of a view file: the parameters the view takes, each with a `Type`, a `Default`, `Choices`, `Min`, `Max`, `Required`, `Model` and `Doc`."),
    ("expects", "a block", "On the root of a view file: the names, actions and types the view expects of its ViewModel (checked by `app.check()`)."),
)
#: Keys of a node a block head or a wrapper stands for, not a property.
NOT_KEYS = frozenset({"widget", "if", "for", "key", "tesserae"})

#: The widgets a page can show are all of them; this is the width a description is cut to in the table.
CUT = 150


def _schemas() -> dict[str, dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("generate_schema", ROOT / "tools" / "generate_schema.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.schemas()


def _definitions() -> dict[str, Any]:
    """The shared definitions (the style, colour, handlers and accessibility schemas), from the schema generator."""
    spec = importlib.util.spec_from_file_location("generate_schema", ROOT / "tools" / "generate_schema.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._definitions(fragment=False)


class Reader:
    """Resolves `$ref`s and says in words what a schema accepts."""

    def __init__(self, schema: dict[str, Any]) -> None:
        self.defs = schema.get("definitions", {})

    def resolve(self, schema: dict[str, Any]) -> dict[str, Any]:
        while "$ref" in schema:
            schema = {**self.defs[schema["$ref"].rsplit("/", 1)[1]], **{k: v for k, v in schema.items() if k != "$ref"}}
        return schema

    def values(self, schema: dict[str, Any]) -> str:
        if "$ref" in schema:
            name = schema["$ref"].rsplit("/", 1)[1]
            if name in ("color", "fill", "style", "zone_style"):
                return {"color": "a color", "fill": "a color or a gradient", "style": "a `Style` block",
                        "zone_style": "a `Style` block"}[name]
        schema = self.resolve(schema)
        if "enum" in schema:
            if len(schema["enum"]) > 14:
                return f"one of {len(schema['enum'])} names"
            return " \\| ".join(f"`{v}`" for v in schema["enum"])
        if "const" in schema:
            return f"`{schema['const']}`"
        for key in ("anyOf", "oneOf"):
            if key in schema:
                parts = [self.values(s) for s in schema[key] if "$ref" not in s or "parameter" not in s["$ref"] and "conditional" not in s["$ref"]]
                out: list[str] = []
                for part in parts:
                    if part not in out:
                        out.append(part)
                return " or ".join(out)
        kind = schema.get("type")
        if isinstance(kind, list):
            return " or ".join(dict.fromkeys(self.values({**schema, "type": one}) for one in kind))
        if kind == "string" and "pattern" in schema and "%" in schema["pattern"]:
            return "a percentage such as `50%`"
        return {"number": "a number", "integer": "an integer", "string": "text", "boolean": "`true` or `false`", "null": "`null`",
                "object": "a block", "array": "a list"}.get(str(kind), "any value")


#: A mapping with more properties than this, all of one kind (colour roles, type roles), is one row, not one each.
GROUP = 8
SIDES = {"top": "the top", "right": "the right", "bottom": "the bottom", "left": "the left"}

LEAF_REFS = ("style", "zone_style", "handlers", "a11y")


def _is_leaf(sub: dict[str, Any]) -> bool:
    """A property whose mapping has a section of its own (the style, the handlers, ...): not spelled out inline."""
    refs = [sub.get("$ref", ""), *(member.get("$ref", "") for member in sub.get("anyOf", []))]
    return any(ref.rsplit("/", 1)[-1] in LEAF_REFS for ref in refs if ref)


def _item_properties(reader: Reader, schema: dict[str, Any]) -> dict[str, Any]:
    """The properties of a list's entries, when they are a small mapping of their own (not a whole node)."""
    resolved = reader.resolve(schema)
    items = resolved.get("items", {})
    if resolved.get("type") != "array" or items.get("$ref", "").rsplit("/", 1)[-1] in ("node", "widget"):
        return {}
    return reader.resolve(items).get("properties", {})


def _grouped(reader: Reader, schema: dict[str, Any]) -> bool:
    props = list(reader.resolve(schema).get("properties", {}).values())
    return len(props) > GROUP and len({reader.values(p) + str(sorted(reader.resolve(p).get("properties", {}))) for p in props}) == 1


def _rows(reader: Reader, schema: dict[str, Any], prefix: str = "", depth: int = 3) -> list[tuple[str, str, str, bool]]:
    """(dotted key, values, what it does, required) for each property, nested ones after their parent."""
    schema = reader.resolve(schema)
    required = set(schema.get("required", []))
    rows = []
    if _grouped(reader, schema):
        first = next(iter(schema["properties"].values()))
        names = ", ".join(f"`{tdl_format.key(n)}`" for n in list(schema["properties"])[:4])
        text = f"One for each of {len(schema['properties'])} names, such as {names}."
        rows.append((f"{prefix}<Name>", reader.values(first), text, False))
        inner = reader.resolve(first)
        if depth > 1 and inner.get("properties"):
            rows += _rows(reader, inner, f"{prefix}<Name>.", depth - 1)
        return rows
    for name, sub in schema.get("properties", {}).items():
        resolved = reader.resolve(sub)
        if "anyOf" in resolved and not resolved.get("description"):
            described = next((s for s in resolved["anyOf"] if reader.resolve(s).get("description")), None)
            if described:
                resolved = {**resolved, "description": reader.resolve(described)["description"]}
        text = " ".join(resolved.get("description", "").split())
        if not text and name in SIDES:
            text = f"Space on {SIDES[name]} side."
        if sub.get("$ref", "").endswith("/color") and "description" not in sub:
            text = "A color."
        rows.append((prefix + tdl_format.key(name), reader.values(sub), tdl_format.prose(text, widget_properties=False), name in required))
        if _item_properties(reader, sub) and depth > 1:
            rows += _rows(reader, resolved["items"], f"{prefix}{tdl_format.key(name)}[].", depth - 1)
        if depth > 1 and not _is_leaf(sub):
            inner = resolved
            if "anyOf" in inner:  # a number or a `{size, style}`: show the mapping's keys
                inner = next((reader.resolve(s) for s in inner["anyOf"] if reader.resolve(s).get("properties")), inner)
            if inner.get("properties"):
                rows += _rows(reader, inner, f"{prefix}{tdl_format.key(name)}.", depth - 1)
    return rows


def _table(rows: list[tuple[str, str, str, bool]], first: str = "Key") -> list[str]:
    out = [f"| {first} | Values | What it does |", "| --- | --- | --- |"]
    for key, values, text, required in rows:
        mark = " *(required)*" if required else ""
        out.append(f"| `{key}`{mark} | {values} | {text.replace('|', chr(92) + '|')} |")
    return out + [""]


def _stub(reader: Reader, schema: dict[str, Any], indent: int = 0, depth: int = 2) -> list[str]:
    """The block as TDL: `Key: <values>` for a property, `Key { ... }` for a mapping, `Key { Item { ... } }` for a list of small mappings."""
    schema = reader.resolve(schema)
    lines = []
    pad = "  " * indent
    if _grouped(reader, schema):
        first = next(iter(schema["properties"].values()))
        inner = reader.resolve(first)
        if inner.get("properties") and depth > 1:
            return [f"{pad}<Name> {{"] + _stub(reader, inner, indent + 1, depth - 1) + [f"{pad}}}"]
        return [f"{pad}<Name>: <{reader.values(first).replace('`', '')}>"]
    for name, sub in schema.get("properties", {}).items():
        key = tdl_format.key(name)
        if _item_properties(reader, sub) and depth > 1:
            lines.append(f"{pad}{key} {{")
            lines.append(f"{pad}  Item {{ " + ", ".join(f"{tdl_format.key(k)}: ..." for k in _item_properties(reader, sub)) + " }")
            lines.append(f"{pad}}}")
            continue
        resolved = reader.resolve(sub)
        inner = resolved
        if "anyOf" in inner:
            inner = next((reader.resolve(s) for s in inner["anyOf"] if reader.resolve(s).get("properties")), inner)
        nested = inner.get("properties") if depth > 1 and not _is_leaf(sub) else None
        if nested:
            lines.append(f"{pad}{key} {{")
            lines += _stub(reader, inner, indent + 1, depth - 1)
            lines.append(f"{pad}}}")
        else:
            hint = reader.values(sub).replace(" \\| ", " | ").replace("`", "")
            if len(hint) > 60:
                hint = hint[:57] + "..."
            lines.append(f"{pad}{key}: <{hint}>")
    return lines


def _style_tables(reader: Reader) -> list[str]:
    """The style fields in the sections `tess_ui.spec.cascade.STYLE_GROUPS` makes, each its own table."""
    from tess_ui.spec import cascade

    style = reader.defs["style"]
    rows = _rows(reader, style)
    by_group: dict[str, list[tuple[str, str, str, bool]]] = {}
    for row in rows:
        top = tdl_format_snake(row[0].split(".")[0])  # a field's own keys (`Filter.Sepia`) go with it
        group = style["properties"][top]["x-group"]
        by_group.setdefault(group, []).append((row[0], row[1], row[2].removesuffix(f" ({group}.)"), row[3]))
    out: list[str] = []
    for group in cascade.STYLE_GROUPS:
        out += [f"### {group}", ""] + _table(by_group.pop(group), "Field")
    if by_group:
        raise SystemExit(f"style fields in no known group: {sorted(by_group)}")
    return out


def tdl_format_snake(key: str) -> str:
    from tess_ui.spec.tdl import snake_case

    return snake_case(key) or key


def _block(reader: Reader, schema: dict[str, Any], first: str = "Key", head: str | None = None) -> list[str]:
    """A stub (a fragment of TDL showing the shape, not a document: `text`, so it is not run as a view) and the table of its keys."""
    lines = _stub(reader, schema)
    if head:
        lines = [f"{head} {{", *("  " + line for line in lines), "}"]
    return ["```text", *lines, "```", "", *_table(_rows(reader, schema), first)]


def _widget_docs() -> dict[str, str]:
    """Each built-in widget and each shipped view: the page that describes it, from the component data."""
    import yaml

    data = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    pages: dict[str, str] = {}
    for entry in data["components"]:
        for name in [*(entry.get("views") or []), *(entry.get("widgets") or [])]:
            pages[name] = f"../components/{entry['slug']}.md"
    return pages


def _first_sentence(text: str) -> str:
    text = " ".join(text.split())
    out = text.split(". ")[0].rstrip(".")
    return out + "." if len(out) <= CUT else out[:CUT - 1].rstrip() + "…"


def _view_summary(name: str) -> str:
    """The first sentence of a shipped view's header comment."""
    from generate_component_docs import _header  # noqa: PLC0415

    return _first_sentence(_header((ROOT / "src" / "tess_ui" / "views" / f"{name}_View.tdl").read_text(encoding="utf-8")))


def _widgets_section() -> list[str]:
    from tess_ui.shipped import shipped_views
    from tess_ui.spec import widgets

    pages = _widget_docs()
    rows = []
    for name in widgets.names():
        decl = widgets.lookup(name)
        rows.append((name, _first_sentence(decl.doc) if decl and decl.doc else "A built-in widget."))
    for name in sorted(shipped_views()):
        rows.append((name, _view_summary(name)))
    out = ["| Widget | What it is |", "| --- | --- |"]
    for name, text in sorted(rows, key=lambda r: r[0]):
        link = f"[`{name}`]({pages[name]})" if name in pages else f"`{name}`"
        out.append(f"| {link} | {tdl_format.prose(text).replace('|', chr(92) + '|')} |")
    return out + [""]


def render() -> str:
    from tess_ui import view as view_module
    from tess_ui.spec import widgets

    schemas = _schemas()
    undocumented = sorted(set(widgets._UNIVERSAL) - NOT_KEYS - {key for key, _, _ in NODE_KEYS})
    if undocumented:
        raise SystemExit(f"tools/generate_tdl_docs.py: document the node keys {undocumented} in NODE_KEYS")
    view = Reader({"definitions": _definitions()})
    sheet = Reader(schemas["tess-ui-stylesheet-schema.json"])
    theme = Reader(schemas["tess-ui-theme-schema.json"])
    out = ["# TDL Reference", "",
           "Every key Tesserae's TDL files take, with the values it accepts and what it does. "
           "This page is written from the same schemas the editor tools use (`tesserae schema`), "
           "so it can't fall behind the code. For how the pieces fit, see the [guide](../guide/layout.md).", "",
           "## The files", "",
           "| File | What it is | Reference |", "| --- | --- | --- |",
           "| `<Name>_View.tdl` | A screen or a widget: one root block, with its children. | [The node](#the-node) |",
           "| `<Name>_Stylesheet.tdl` | Style rules for a view or an app: a `Styles` block of `Rule`s. | [The stylesheet](#the-stylesheet) |",
           "| `<Name>_Theme.tdl` | A theme: colours, type, shapes and style rules. | [The theme](#the-theme) |", "",
           "## The file", "",
           "A file starts with a metadata block, then holds one root block. `TDL` is the language version, `Name` the file's name "
           "and `Tesserae` the release series of the language it is written for. A `#` starts a comment. "
           "Every key is `Title_Case` (`Corner_Radius`, `On_Click`); a value that is a word is bare, other text is quoted, and an expression "
           "is a slot, `<| expr |>`.", "",
           "```tdl",
           "---", "TDL: 0.2", "Name: Counter", 'Tesserae: "0.6"', "---",
           "Container {",
           "  Name: counter",
           "  Style { Flex_Direction: vertical, Gap: 8, Padding: 16 }",
           "  Children {",
           "    Text { Text: <| 'Clicked ' + str(count) |> }",
           "    If <| count > 0 |> {",
           "      Button {",
           "        Label: Reset",
           "        Handlers { On_Click { Set { Target: count, Value: <| 0 |> } } }",
           "      }",
           "    }",
           "  }",
           "}",
           "```", ""]

    out += ["## The node", "",
            "A view is one block headed by a widget, with its children inside it. A node is a block headed by its widget (`Button { ... }`); a scalar "
            "key is a property (`Label: Save`); a mapping is a block headed by its key (`Style { ... }`); the child nodes are in `Children { ... }`. "
            "Which blocks are nodes is told by where they are: a block directly in `Children`, `If` or `For` is a node, any other block in a node is a mapping.", "",
            "| Key | Values | What it does |", "| --- | --- | --- |"]
    out += [f"| `{tdl_format.key(key)}` | {values} | {text} |" for key, values, text in NODE_KEYS]
    out += ["| `Children` | a block of nodes | The child nodes, in order. |",
            "| anything else | | A property of the widget: see [the widgets](#the-widgets). |", "",
            "### Choosing and repeating", "",
            "`If` and `For` wrap the one node they apply to; the node inside is built while the condition holds or once for each item:", "",
            "```text",
            "If <| loading |> {",
            "  Circular_Progress { Name: spinner }",
            "}",
            "For item In <| items |> Key <| item['id'] |> {",
            "  Chip { Label: <| item['name'] |> }",
            "}",
            "```", "",
            "`For` takes one or several names (`For i, row In <| enumerate(rows) |> Key <| row['id'] |>`) and needs a `Key` (`Key <| None |>` for none). "
            "A node with both has the `For` outside and the `If` inside it. An `If` or `For` holds exactly one node.", ""]

    out += ["## The widgets", "",
            "A node's widget is a built-in one, one the app registered, or a view found by name (a file Tesserae ships, or `<Name>_View.tdl` of your own). "
            "Each takes its own properties, with a type, a default and the values it allows; the page of a component lists them.", ""]
    out += _widgets_section()

    out += ["## The style", "", "A node's `Style` block is a mapping of these fields, or the name of a `*_Style.yaml` file. "
            "The same fields go in a stylesheet's or theme's rules.", ""]
    out += _style_tables(view)
    out += ["## Colors", "", "Any field that takes a color takes " + tdl_format.prose(view.defs["color"]["description"][0].lower()
            + view.defs["color"]["description"][1:].replace("A theme role (", "a theme role (", 1), widget_properties=False), ""]
    out += ["## Gradients", "",
            "`Background`, `Foreground` and `Border_Color` take a gradient where they take a color: a CSS-like string "
            "(`linear-gradient(90deg, primary, tertiary)`, `radial-gradient(at 30% 30%, primary_container, surface)`, "
            "`conic-gradient(from 90deg, primary, secondary, primary)`; `to right` and the like name a direction; a stop "
            "may have a place, `primary 40%`). Stops are theme roles or colors. "
            "A control's color (a `Switch`, a `Slider`) takes a plain color only.", ""]

    actions = ", ".join([*(f"`window.{action}`" for action in view_module.WINDOW_ACTIONS),
                         *(f"`surface.{action}`" for action in view_module.SURFACE_ACTIONS),
                         "`navigate.<Screen>`", *(f"`navigate.{t}`" for t in view_module.NAVIGATE_TARGETS)])
    out += ["## Handlers", "",
            f"`Handlers` names what an event calls. An event is a property with a bare action name (`On_Click: save`), or a block of steps that run in "
            f"order, each seeing the writes of the earlier ones: `Set {{ Target: name, Value: <| expr |> }}` writes a name, `Call {{ Action: \"name\", Args: [<| expr |>] }}` "
            f"calls a ViewModel method or one of {actions}.", "",
            "```text", "Handlers {", "  On_Click {", "    Set { Target: open, Value: <| not open |> }",
            "    Call { Action: \"on_toggle\" }", "  }", "}", "```", ""]
    handler_rows = [(tdl_format.key(name), "an action name or a block of steps", f"Runs on the `{event}` event.", False) for name, event in view_module._EVENTS.items()]
    out += _table(handler_rows, "Event")
    out += ["## Accessibility", "", "`A11y` on any node.", ""]
    out += _table(_rows(view, view.defs["a11y"]), "Key")

    out += ["## The stylesheet", "",
            "A stylesheet is a `Styles` block of `Rule` blocks, in order (a later rule wins a tie). A rule says which widgets it is for and the style it sets. "
            "See [Component stylesheets](../stylesheets/index.md).", ""]
    rule = schemas["tess-ui-stylesheet-schema.json"]["properties"]["styles"]["items"]
    out += ["```text", "Styles {", "  Rule {", *("    " + line for line in _stub(sheet, rule)), "  }", "}", "```", ""]
    out += _table(_rows(sheet, rule), "Key")

    out += ["## The theme", "",
            "A theme is one `Theme` block. See [Themes](../themes/index.md).", ""]
    out += _block(theme, schemas["tess-ui-theme-schema.json"], "Key", "Theme")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the page is out of date")
    args = parser.parse_args()
    text = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
            print(f"{OUTPUT.relative_to(ROOT)} is out of date: run `python tools/generate_tdl_docs.py`")
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}: {len(text.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
