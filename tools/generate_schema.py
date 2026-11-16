#!/usr/bin/env python3
"""Writes Tesserae's JSON schemas of the data the TDL front ends read (0.3.2, #79; for TDL since the YAML loaders went).

Three JSON Schema draft-07 files, each for one kind of file Tesserae reads. They describe the *data* a `.tdl` file loads to (the front ends in
`tess_ui.spec.tdl*` return plain dicts with lower snake_case keys, which is what the loaders and `tests/test_widget_schema.py` validate):

- `tess-ui-widget-schema.json`      a view, `*_View.tdl`: a tree of `widget` nodes, with a branch for each built-in widget and each shipped view
- `tess-ui-stylesheet-schema.json`  a stylesheet of rules, `*_Stylesheet.tdl`
- `tess-ui-theme-schema.json`       a theme, `*_Theme.tdl`

They are built from Tesserae's own code, so a new widget, style field or token can't be left out by accident: the widgets and their properties, style
fields, the colour, type and shape tokens, the icons, the accessibility roles and the handlers. The layout enums (`flex_direction`, `align_items`, ...)
are asked of `tess_re`, whose error for a bad value lists the good ones. `tests/test_schema.py` and `tests/test_widget_schema.py` check every `.tdl`
file of the repository against them and that the committed files match what this writes. `tools/generate_tdl_docs.py` writes the reference page from them.

    python tools/generate_schema.py          # write src/tess_ui/schema and docs/schema
    python tools/generate_schema.py --check  # exit 1 if they are out of date
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRS = (ROOT / "src" / "tess_ui" / "schema", ROOT / "docs" / "schema")
SITE = "https://mindderivative.github.io/tess-ui/schema/"
DRAFT = "http://json-schema.org/draft-07/schema#"

#: The style fields whose valid values `tess_re` lists in its errors.
TESS_RE_ENUMS = ("flex_direction", "flex_wrap", "position", "display", "grid_auto_flow")


# -- what Tesserae and tess_re say ---------------------------------------------------------------

def _tre_values(prop: str) -> list[str]:
    """The values `tess_re` accepts for a node property, from the error it gives for a bad one."""
    from tess_ui import App

    window = App(width=10, height=10).window
    try:
        window.create("box", **{prop: "__no_such_value__"})
    except Exception as exc:  # noqa: BLE001 -- the message is what we want
        found = re.search(r"must be one of: (.+)$", str(exc))
        if found:
            return [value.strip() for value in found.group(1).split(",")]
    raise SystemExit(f"tess_re did not list the values of `{prop}`: has its error message changed?")


# -- the building blocks ---------------------------------------------------------------------

def _definitions(fragment: bool) -> dict[str, Any]:
    """The shared definitions. A fragment's numbers and names can be `{{ parameter }}`s, filled in
    when the fragment is used, so there they may also be that."""
    from tess_ui import a11y, tokens
    from tess_ui import view as view_module
    from tess_ui.spec import cascade, layout, placement

    roles = sorted(tokens.color_scheme((0x67, 0x50, 0xA4, 0xFF)))
    param = {"type": "string", "pattern": r"^\s*\{\{.*\}\}\s*$",
             "description": "A fragment parameter: filled in where the fragment is used."}

    conditional = {"type": "object", "required": ["if", "then"], "additionalProperties": False,
                   "properties": {"if": {}, "then": {}, "else": {}},
                   "description": "A value chosen by a parameter: `{if: \"{{ flag }}\", then: a, else: b}`."}

    def loose(schema: dict[str, Any]) -> dict[str, Any]:
        """In a fragment a value may also be a `{{ parameter }}`, or chosen by one."""
        if not fragment:
            return schema
        return {"anyOf": [schema, {"$ref": "#/definitions/parameter"}, {"$ref": "#/definitions/conditional"}]}

    number = {"type": "number"}
    radius = {"anyOf": [number, {"enum": [*sorted(tokens.SHAPES), "full"]}]}
    percent = {"type": "string", "pattern": r"^\d+(\.\d+)?%$"}
    term = r"\d+(?:\.\d+)?(?:%|px)?"
    # as `tess_ui.spec.sizes` takes them (tre 0.5.7): a size is not negative; a sum has a space each side of `+` and `-`
    dimension = {"anyOf": [{"type": "number", "minimum": 0}, {"enum": ["auto"]}, percent]}
    size = {"anyOf": [{"type": "number", "minimum": 0}, {"enum": ["auto", "fit-content"]}, percent,
                      {"type": "string", "pattern": rf"^(?:calc\(\s*{term}(?: [+-] {term})*\s*\)|{term}(?: [+-] {term})+)$"}]}
    inset = {"anyOf": [number, {"enum": ["auto"]}, percent]}
    sides = ("top", "right", "bottom", "left")
    spacing = {"anyOf": [loose(number), {"type": "object", "properties": {side: loose(number) for side in sides},
                                         "additionalProperties": False}]}
    enums = {name: {"enum": _tre_values(name)} for name in TESS_RE_ENUMS}
    size_text = ("Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as "
                 "`calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum).")
    style_fields: dict[str, tuple[dict[str, Any], str]] = {
        "width": (size, size_text), "height": (size, size_text),
        "min_width": (dimension, "The least width it can take."), "max_width": (dimension, "The most width it can take."),
        "min_height": (dimension, "The least height it can take."), "max_height": (dimension, "The most height it can take."),
        "flex_direction": (enums["flex_direction"], "How its children are laid out: `horizontal` (the default) or `vertical`."),
        "padding": (spacing, "Space inside it: one number, or `{left, right, top, bottom}`."),
        "margin": (spacing, "Space outside it: one number, or `{left, right, top, bottom}`."),
        "gap": ({"type": "number", "minimum": 0}, "Space between its children."),
        "row_gap": ({"type": "number", "minimum": 0}, "Space between rows (defaults to `gap`)."),
        "column_gap": ({"type": "number", "minimum": 0}, "Space between columns (defaults to `gap`)."),
        "align_content": ({"enum": list(layout.POSITIONS)},
                          "Where its children sit: `top_left`, `top`, `top_right`, `left`, `center`, `right`, `bottom_left`, "
                          "`bottom` or `bottom_right`. Not set, they fill the space across the layout."),
        "spread": ({"enum": list(layout.SPREADS)},
                   "Spreads its children along the layout: `between` (the space goes between them), `around` or `evenly`."),
        "flex": ({"enum": list(layout.FLEXES)},
                 "How it takes room in its parent: `none` (the default) is as big as its content and never squeezed, "
                 "`expand_horizontal` and `expand_vertical` take the room left over in that direction, `fill` both."),
        "align_self": ({"enum": list(layout.POSITIONS)}, "Its own place in its parent, over the parent's `align_content`."),
        "align_wrapped": ({"enum": list(layout.ALIGN_TRACKS)},
                          "With `flex_wrap: wrap`: how the lines share the room left over."),
        "align_tracks": ({"enum": list(layout.ALIGN_TRACKS)}, "In a grid: how the tracks share the room left over."),
        "align_cells": ({"enum": list(layout.POSITIONS)}, "In a grid: where each item sits in its cell."),
        "flex_wrap": (enums["flex_wrap"], "`wrap` lets children flow onto more lines; `no_wrap` keeps one."),
        "position": (enums["position"], "`absolute` takes it out of the flow and places it at `x` and `y`."),
        "display": (enums["display"], "`flex` (the default) or `grid`."),
        "grid_auto_flow": (enums["grid_auto_flow"], "How grid children fill the cells."),
        "background": ({"$ref": "#/definitions/fill"},
                       "Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as "
                       "`linear-gradient(90deg, primary, tertiary)`."),
        "foreground": ({"$ref": "#/definitions/fill"},
                       "Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient."),
        "border_color": ({"$ref": "#/definitions/fill"}, "The colour of its border: a colour or a gradient."),
        "blur": ({"type": "number", "minimum": 0}, "Blurs the node and what it draws, by this many pixels."),
        "backdrop_blur": ({"type": "number", "minimum": 0},
                          "Blurs what is behind it, by this many pixels: with a translucent `background`, a frosted surface."),
        "blend_mode": ({"enum": ["normal", "multiply", "screen", "overlay", "darken", "lighten", "color_dodge", "color_burn",
                                 "hard_light", "soft_light", "difference", "exclusion", "hue", "saturation", "color",
                                 "luminosity"]},
                       "How it is drawn over what is behind it, as CSS `mix-blend-mode`."),
        "filter": ({"type": "object", "additionalProperties": False,
                    "properties": {name: {"type": "number", "description": text} for name, text in (
                        ("saturate", "1 is unchanged, 0 grey, above 1 more vivid."),
                        ("brightness", "1 is unchanged, 0 black, above 1 brighter."),
                        ("contrast", "1 is unchanged, 0 flat grey, above 1 harder."),
                        ("grayscale", "0 is unchanged, 1 fully grey."),
                        ("hue_rotate", "Turns the hues, in degrees."),
                        ("invert", "0 is unchanged, 1 inverted."),
                        ("sepia", "0 is unchanged, 1 fully sepia."))}},
                   "Colour filters over it and its children, as in CSS: `{grayscale: 1}`, `{saturate: 0.4, brightness: 0.9}` "
                   "(`hue_rotate` is in degrees)."),
        "sticky": ({"type": "number"}, "In a scroll view, it sticks this many pixels from the top edge as its siblings scroll past."),
        "snap_align": ({"enum": ["none", "start", "center", "end"]}, "In a scroll view that has `snap`, this node is a place it settles on, with this edge of the node at the same edge of the view."),
        "overflow": ({"enum": ["hidden", "visible"]}, "`hidden` cuts what is inside to the node's own box, `visible` lets it spill out: the same as `clip_children: true` and `false`, "
                      "which it is another way to write (a node that says both must agree). It does not scroll: use a ScrollView for that."),
        "pointer_events": ({"enum": ["auto", "none"]}, "`none` lets the pointer through the node itself: a click on it goes to whatever is under it, and it "
                            "is not hovered or pressed. What is inside it keeps its own (a child with `auto` is still hit). `auto`, the default, is the usual."),
        "scale": ({"type": "number", "minimum": 0}, "Draws the node and what is in it at this multiple of its size (1 is unchanged), about its centre."),
        "translate_x": ({"type": "number"}, "Draws the node this many pixels to the right of where it is laid out."),
        "translate_y": ({"type": "number"}, "Draws the node this many pixels lower than where it is laid out."),
        "rotation_deg": ({"type": "number"}, "Turns the node by this many degrees, clockwise, about its centre."),
        "transition": ({"type": "object",
                        "description": "Which changes ease instead of jumping.",
                        "properties": {name: {"anyOf": [{"type": "number", "minimum": 0},
                                                         {"type": "object", "additionalProperties": False,
                                                          "properties": {"duration": {"type": "number", "minimum": 0},
                                                                         "easing": {"anyOf": [{"enum": ["linear", "standard", "standard_accelerate", "standard_decelerate",
                                                                                                        "emphasized", "emphasized_accelerate", "emphasized_decelerate", "spring"]},
                                                                                              {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}]},
                                                                         "bounce": {"type": "number", "exclusiveMinimum": -1, "exclusiveMaximum": 1}}}]}
                                       for name in ("all", "background", "foreground", "border_color", "border_width", "corner_radius", "elevation",
                                                    "opacity", "blur", "backdrop_blur", "scale", "translate_x", "translate_y", "rotation_deg",
                                                    "width", "height", "x", "y", "gap", "padding", "margin")},
                        "additionalProperties": False},
                       "Which style changes ease to their new value: a duration in milliseconds, or `{duration, easing, bounce}`. "
                       "`all` covers every one that can. A node is where it says when first drawn; only a change eases."),
        "zone": ({"enum": ["left", "right", "top", "bottom", "center"]},
                 "A DockPanel's zone in its Dock: where it docks. Only a DockPanel directly in a Dock has one; anywhere else it is an error."),
        "cursor": ({"anyOf": [{"enum": ["default", "pointer", "text", "grab", "grabbing", "move", "not_allowed", "wait",
                                        "progress", "crosshair", "help", "col_resize", "row_resize", "ew_resize", "ns_resize",
                                        "nesw_resize", "nwse_resize", "copy", "cell", "context_menu", "zoom_in", "zoom_out",
                                        "all_scroll"]},
                              {"type": "object", "additionalProperties": False, "required": ["src"],
                               "properties": {"src": {"type": "string", "description": "A PNG, JPEG, GIF or WebP picture next to the view."},
                                              "hotspot": {"type": "array", "items": {"type": "integer"},
                                                          "description": "`[x, y]`: the pixel that is the pointer's place."}}}]},
                   "The pointer over it: a name, or `{src: cursor.png, hotspot: [x, y]}` (a picture next to the view, at most "
                   "256 pixels a side; only in a node's own `style:`)."),
        "border_width": ({"type": "number", "minimum": 0}, "The width of its border, in pixels."),
        "corner_radius": ({"anyOf": [radius, {"type": "array", "items": radius, "minItems": 4, "maxItems": 4},
                                     {"type": "object", "additionalProperties": False,
                                      "properties": {key: {**radius, "description": f"The radius of {what}."} for key, what in (
                                          ("top_left", "the top left corner"), ("top_right", "the top right corner"),
                                          ("bottom_right", "the bottom right corner"), ("bottom_left", "the bottom left corner"),
                                          ("top", "both top corners"), ("right", "both right corners"),
                                          ("bottom", "both bottom corners"), ("left", "both left corners"))}}]},
                          "Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, "
                          "bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square."),
        "opacity": ({"type": "number", "minimum": 0, "maximum": 1}, "From 0 (clear) to 1 (opaque)."),
        "elevation": ({"anyOf": [number, {"enum": sorted(tokens.ELEVATION_LEVELS)}]}, "A shadow level, 0 to 5."),
        "aspect_ratio": ({"type": "number", "exclusiveMinimum": 0}, "Width over height: gives the missing side from the one set."),
        "x": (inset, "Where an `absolute` node sits from the left; the same as `left` (say one of them)."),
        "y": (inset, "Where an `absolute` node sits from the top; the same as `top` (say one of them)."),
        "left": (inset, "How far an `absolute` node is from its parent's left edge; with `right` it is stretched between the two. A node in the flow is moved by it."),
        "top": (inset, "How far an `absolute` node is from its parent's top edge; with `bottom` it is stretched between the two. A node in the flow is moved by it."),
        "right": (inset, "How far an `absolute` node is from its parent's right edge; with `left` it is stretched between the two."),
        "bottom": (inset, "How far an `absolute` node is from its parent's bottom edge; with `top` it is stretched between the two."),
        "inset": (inset, "All four insets at once: an `absolute` node with `inset: 8` fills its parent less 8 pixels each side."),
        "anchor": ({"type": "string", "minLength": 1},
                   "The name of another node in this view to sit against, or `parent` for the node it is inside. The node leaves the flow and follows the anchor with no lag; "
                   "it stays in the tree, clipped and ordered as a child of its parent is."),
        "placement": ({"enum": list(placement.PLACEMENTS)},
                      "With `anchor`: which side of the anchor (`below`, `above`, `start`, `end`) or which of its corners, or its centre, the node's centre sits on."),
        "offset": ({"type": "array", "items": number, "minItems": 2, "maxItems": 2}, "With `anchor`: `[dx, dy]` pixels added to the point it sits on."),
        "z_index": ({"type": "integer"}, "Stacking order: higher is in front."),
        "clip_children": ({"type": "boolean"}, "Whether children are cut off at its edge."),
        "grid_template_columns": ({"type": "string"}, "The grid's columns, as in CSS: `1fr 2fr 100px`."),
        "grid_template_rows": ({"type": "string"}, "The grid's rows, as in CSS."),
        "grid_auto_columns": ({"type": "string"}, "The size of columns the template doesn't name."),
        "grid_auto_rows": ({"type": "string"}, "The size of rows the template doesn't name."),
        "grid_column": ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, "Which grid column it takes: `2`, or `1 / 3`."),
        "grid_row": ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, "Which grid row it takes: `2`, or `1 / 3`."),
    }
    missing = cascade.STYLE_FIELDS - set(style_fields)
    extra = set(style_fields) - cascade.STYLE_FIELDS
    if missing or extra:
        raise SystemExit(f"the style fields changed: add {sorted(missing)}, drop {sorted(extra)} in {__file__}")
    style = {"type": "object", "description": "How a node looks and lays out its children.",
             "properties": {name: {**loose(schema), "description": f"{text} ({cascade.STYLE_GROUP_OF[name]}.)",
                                  "x-group": cascade.STYLE_GROUP_OF[name]}
                            for name, (schema, text) in sorted(style_fields.items())},
             "additionalProperties": False}

    window_actions = ", ".join("`window." + action + "`" for action in view_module.WINDOW_ACTIONS)
    window_actions += ", " + ", ".join("`surface." + action + "`" for action in view_module.SURFACE_ACTIONS)
    window_actions += ", `navigate.<Screen>`, " + ", ".join("`navigate." + t + "`" for t in view_module.NAVIGATE_TARGETS)
    handlers = {"type": "object", "description": "What a user's action calls: the name of a ViewModel method, or `window.<action>`.",
                "properties": {name: {"type": "string",
                                      "description": f"Runs on `{event}`: a ViewModel method name, or one of {window_actions}."}
                               for name, event in view_module._EVENTS.items()},
                "additionalProperties": False}
    a11y_schema = {"type": "object", "description": "What assistive technology is told about this node.",
                   "properties": {"label": {"type": "string", "description": "The name a screen reader says."},
                                  "role": {"enum": sorted(a11y.ROLES), "description": "What kind of thing it is."},
                                  "hidden": {"type": "boolean", "description": "Hide it from assistive technology."},
                                  "live": {"enum": sorted(a11y.LIVE), "description": "How changes to it are announced."},
                                  "level": {"type": "integer", "minimum": 1, "description": "A heading's level."},
                                  "expanded": {"anyOf": [{"type": "boolean"}, {"type": "null"}, {"type": "string"}],
                                               "description": "Open or closed, on something that opens and closes."},
                                  "selected": {"anyOf": [{"type": "boolean"}, {"type": "null"}, {"type": "string"}], "description": "One of a set, chosen."},
                                  "checked": {"anyOf": [{"type": "boolean"}, {"type": "null"}, {"type": "string"}], "description": "On or off."},
                                  "value": {"anyOf": [{"type": "number"}, {"type": "null"}, {"type": "string"}], "description": "A number the node holds."},
                                  "value_min": {"anyOf": [{"type": "number"}, {"type": "null"}, {"type": "string"}], "description": "Its least."},
                                  "value_max": {"anyOf": [{"type": "number"}, {"type": "null"}, {"type": "string"}], "description": "Its most."},
                                  "value_step": {"anyOf": [{"type": "number"}, {"type": "null"}, {"type": "string"}], "description": "One step."},
                                  "pressed": {"anyOf": [{"type": "boolean"}, {"const": "mixed"}, {"type": "null"}, {"type": "string"}],
                                              "description": "A toggle button's state: true, false or `mixed`."},
                                  "invalid": {"anyOf": [{"type": "boolean"}, {"type": "null"}, {"type": "string"}], "description": "The value is not acceptable."},
                                  "description": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "A longer description than the label."},
                                  "describedby": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                                                  "description": "The `name:` of a node in this view that describes this one, or a list."},
                                  "controls": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                                               "description": "The `name:` of a node in this view that this one controls, or a list."},
                                  "current": {"anyOf": [{"type": "boolean"}, {"enum": sorted(a11y.CURRENT)}, {"type": "null"}, {"type": "string"}],
                                              "description": "The current item of a set: `page`, `step`, `location`, `date`, `time` or true."},
                                  "value_now": {"anyOf": [{"type": "number"}, {"type": "null"}, {"type": "string"}], "description": "The value of a range."},
                                  "value_text": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "How a range's value is said."},
                                  "busy": {"anyOf": [{"type": "boolean"}, {"type": "null"}, {"type": "string"}], "description": "The node is updating."}},
                   "additionalProperties": False}
    color = {"anyOf": [{"enum": roles}, {"type": "string"}],
             "description": "A theme role (such as `surface` or `on_primary`), `#RGB`, `#RRGGBB`, `#RRGGBBAA`, `transparent`, "
                            "a CSS colour name, or a CSS function such as `rgb(...)` or `oklch(...)`. End any of them with `@N%` to scale its alpha: "
                            "`primary@12%`."}
    gradient = {"anyOf": [{"type": "string", "pattern": r"^\s*(linear|radial|conic)-gradient\("},
                          {"type": "object", "required": ["gradient", "stops"], "additionalProperties": False,
                           "properties": {"gradient": {"enum": ["linear", "radial", "sweep"]},
                                          "stops": {"type": "array", "minItems": 2,
                                                    "description": "Colours, or `[place, colour]` pairs with places from 0 to 1."},
                                          "angle": {"type": "number", "description": "Degrees: 0 up, 90 right, 180 down."},
                                          "center": {"type": "array", "items": {"type": "number"},
                                                     "description": "`[x, y]`, as fractions of the box."},
                                          "radius": {"type": "number"}, "start": {"type": "number"}}}],
                "description": "A CSS-like `linear-gradient(...)`, `radial-gradient(...)` or `conic-gradient(...)` whose stops are "
                               "theme roles or colours, or a mapping with `gradient: linear|radial|sweep` and `stops`."}
    fill = {"anyOf": [{"$ref": "#/definitions/color"}, gradient],
            "description": "A colour (a theme role, a hex or a CSS colour) or a gradient."}
    extra = {"parameter": param, "conditional": conditional} if fragment else {}
    return {**extra, "color": color, "fill": fill, "style": style, "handlers": handlers, "a11y": a11y_schema}


def _only(definitions: dict[str, Any], *names: str) -> dict[str, Any]:
    """The named definitions and everything they refer to."""
    wanted: set[str] = set()
    pending = list(names)
    while pending:
        name = pending.pop()
        if name in wanted:
            continue
        wanted.add(name)
        pending += re.findall(r"#/definitions/(\w+)", json.dumps(definitions[name]))
    return {name: definitions[name] for name in definitions if name in wanted}


def _root(filename: str, title: str, description: str, definitions: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    return {"$schema": DRAFT, "$id": SITE + filename, "title": title, "description": description,
            "definitions": definitions, **body}


# -- the files --------------------------------------------------------------------------


def _theme() -> dict[str, Any]:
    from tess_ui import tokens
    from tess_ui.spec import build

    # The rules of a theme's own `Styles` (and of a built-in fragment's stylesheet, which may use the fragment's `{{ parameters }}`) are as loose as a
    # fragment's styles.
    defs = _only(_definitions(fragment=True), "style", "color", "fill")
    defs["rule"] = {
        "type": "object",
        "description": "Styles for the nodes it matches: by `kind`, by `classes`, or by `id`. With none of the three, for every node.",
        "properties": {"kind": {"enum": sorted(build._KINDS), "description": "Every node of this kind."},
                       "classes": {"type": "array", "items": {"type": "string"}, "description": "Nodes with all of these classes."},
                       "id": {"type": "string", "description": "The node with this id."},
                       "style": {"$ref": "#/definitions/style", "description": "How the matching nodes look."}},
        "additionalProperties": False}
    typography = {
        "type": "object", "description": "Changes to Material 3's type styles, by role.",
        "properties": {role: {"type": "object",
                              "properties": {"font_family": {"type": "string", "description": "A font family."},
                                             "font_size": {"type": "number", "description": "Pixels."},
                                             "font_weight": {"type": "number", "description": "1 to 1000."},
                                             "line_height": {"type": "number", "description": "A multiple of the size."},
                                             "tracking": {"type": "number", "description": "Extra space between letters, in pixels (Material 3's tracking: `tokens.MD3_TRACKING`)."}},
                              "additionalProperties": False}
                       for role in sorted(tokens.TYPE_SCALE)},
        "additionalProperties": False}
    colors = {"type": "object", "description": "Colour roles to replace: a role name and a colour.",
              "properties": {role: {"$ref": "#/definitions/color", "description": f"The `{role}` colour."}
                             for role in sorted(tokens.color_scheme((0x67, 0x50, 0xA4, 0xFF)))},
              "additionalProperties": False}
    return _root("tess-ui-theme-schema.json", "Tesserae theme or stylesheet",
                 "A theme file as the TDL front end reads it (`<Name>_Theme.tdl`): `styles` rules, a `seed`, `dark`, `colors`, `typography` and `components`.",
                 defs, {"type": "object", "additionalProperties": False, "properties": {
                     "seed": {"$ref": "#/definitions/color", "description": "The colour the theme's palette is made from."},
                     "dark": {"type": "boolean", "description": "Whether it is the dark scheme."},
                     "colors": colors, "typography": typography,
                     "components": {"type": "object", "description": "Per-component shape and elevation."},
                     "styles": {"type": "array", "items": {"$ref": "#/definitions/rule"}, "description": "Style rules, in order."}}})


def _style_definitions() -> dict[str, Any]:
    """The style fields of a 0.5.0 node, as the editor should offer them: each with its type or choices, and anything that is an expression
    (`Height: <| height / 2 |>`) accepted where a value is."""
    defs = _only(_definitions(fragment=False), "style", "color", "fill")
    expression = {"type": "string", "pattern": r"<\|"}
    style = defs["style"]
    wrapped = {}
    for key, spec in style["properties"].items():
        meta = {k: spec[k] for k in ("description", "x-group") if k in spec}
        body = {k: v for k, v in spec.items() if k not in meta}
        wrapped[key] = {**meta, "anyOf": [body, expression]}
    from tess_ui.spec.transition import LAYOUT_TRANSITIONABLE, TRANSITIONABLE

    for option in wrapped["transition"]["anyOf"]:  # the fields that can ease are the ones the engine's planner takes
        if option.get("type") == "object" and "all" in option.get("properties", {}):
            one = option["properties"]["all"]
            option["properties"] = {name: one for name in ["all", *TRANSITIONABLE, *LAYOUT_TRANSITIONABLE]}
    defs["style"] = {**style, "properties": wrapped}
    return defs


def _widget() -> dict[str, Any]:
    """A node of the current language: a branch for each built-in widget and each view Tesserae ships. A project's own views are added by
    `tesserae schema --project`."""
    from tess_ui.shipped import ViewLibrary, shipped_views
    from tess_ui.spec.widgets import json_schema

    library = ViewLibrary()
    views = {name: library.decl(name) for name in shipped_views()}
    out = json_schema(views, _style_definitions())
    return {"$schema": DRAFT, "$id": SITE + "tess-ui-widget-schema.json",
            "description": "A view of the current language, as the TDL front end reads it from `*_View.tdl`: a tree of `widget` nodes, with a branch for each "
                           "built-in widget and each view Tesserae ships; `tesserae schema --project` adds the project's own.",
            **{k: v for k, v in out.items() if k != "$schema"}}


def _stylesheet() -> dict[str, Any]:
    """A stylesheet of rules (`*_Stylesheet.tdl`), as the front end reads it: `widget`, `variant`, `part`, `state` and a `style` of fields."""
    from tess_ui.spec.rules import STATES

    defs = _style_definitions()
    rule = {
        "type": "object", "title": "Rule",
        "description": "Styles for the nodes it matches: a widget (a built-in, or a view called by its name), narrowed by variant, size, shape, classes, name, part and state.",
        "required": ["style"],
        "properties": {
            "widget": {"type": "string", "description": "The widget the rule is for: a built-in, or a view (`Button`)."},
            "variant": {"type": "string", "description": "Only widgets with this variant."},
            "size": {"type": "string", "description": "Only widgets of this size."},
            "shape": {"type": "string", "description": "Only widgets of this shape."},
            "classes": {"type": "array", "items": {"type": "string"}, "description": "Only nodes with all of these classes."},
            "name": {"type": "string", "description": "Only the node with this name."},
            "part": {"type": "string", "description": "A named node inside the widget's view (the widget's root when left out)."},
            "state": {"enum": list(STATES), "description": "Only while the widget is in this state."},
            "style": {"$ref": "#/definitions/style", "description": "The style fields the rule sets."}},
        "additionalProperties": False}
    return _root("tess-ui-stylesheet-schema.json", "Tesserae stylesheet of rules",
                 "A stylesheet of rules: `<Name>_Stylesheet.tdl`, or the file `App(stylesheet=)` names, as the TDL front end reads it. Each rule says which "
                 "widgets it is for and the style it sets.",
                 defs, {"type": "object", "required": ["styles"], "additionalProperties": False, "properties": {
                     "styles": {"type": "array", "items": rule, "description": "The rules, in order: a later rule wins a tie."}}})


def schemas() -> dict[str, dict[str, Any]]:
    return {"tess-ui-widget-schema.json": _widget(), "tess-ui-stylesheet-schema.json": _stylesheet(), "tess-ui-theme-schema.json": _theme()}


def render(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the committed files are out of date")
    args = parser.parse_args(argv)
    stale = []
    for name, schema in schemas().items():
        text = render(schema)
        for folder in OUTPUT_DIRS:
            path = folder / name
            if args.check:
                if not path.exists() or path.read_text(encoding="utf-8") != text:
                    stale.append(path.relative_to(ROOT).as_posix())
            else:
                folder.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
    if args.check and stale:
        print("out of date: " + ", ".join(stale) + " -- run tools/generate_schema.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
