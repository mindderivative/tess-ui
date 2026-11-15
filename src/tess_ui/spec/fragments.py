"""The built-in component fragments the Python widget factories (`widgets/*.py`, `overlays.py`) are built from, as plain data.

`FRAGMENTS[name]` has three parts:

* `params`: the names a call must give (`label`) or may give (`{"corner_radius": 20}` is a name with its default);
* `tree`: the fragment's structure, a kind-tree node (`id`, `kind`, `text`, `children`, ...) whose `{{ param }}` placeholders `spec/expand.py` fills in. A node
  `{"component": Other, "id": ..., "with": {...}}` calls another fragment; `{"if": c, "then": a, "else": b}` picks a value, a child with `"when": c` is kept
  only when `c` holds, `"repeat": "{{ items }}"` makes one child per entry;
* `sheet`: the look of each part, `{part id: style}`, put under the `style` the tree gives the part itself (its `{{ }}` are filled in the same way).

An app's own views, themes and stylesheets are TDL and never come through here.
"""

from __future__ import annotations

from typing import Any

FRAGMENTS: dict[str, dict[str, Any]] = {
    # A section header that expands and collapses its content: a title and a chevron.
    "AccordionHeader": {
        "params": ["title", "width"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "title",
                    "kind": "Text",
                    "text": {"content": "{{ title }}", "typography_role": "label_large", "wrap": "none", "overflow": "ellipsis"},
                },
                {"id": "chevron", "kind": "Icon", "icon": {"name": "expand_more"}},
            ],
        },
        "sheet": {
            "root": {"width": "{{ width }}", "height": 56, "align_content": "left", "padding": 16, "gap": 12},
            "title": {"foreground": "on_surface", "flex": "expand_horizontal", "min_width": 0},
            "chevron": {"width": 24, "height": 24, "foreground": "on_surface_variant"},
        },
    },
    # A small dot that marks something as having news, with no number.
    "BadgeDot": {
        "params": [],
        "tree": {"id": "root", "kind": "Rect"},
        "sheet": {"root": {"width": 6, "height": 6, "background": "error", "corner_radius": 3}},
    },
    # A small pill carrying a short count or label.
    "BadgeLabeled": {
        "params": ["label", "width"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_small", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {"width": "{{ width }}", "height": 16, "background": "error", "corner_radius": "small", "align_content": "center"},
            "label": {"foreground": "on_error"},
        },
    },
    # An elevated button: a tinted surface with a shadow, for emphasis on a busy background.
    "ButtonElevated": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "surface_container_low",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_1",
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "primary"},
        },
    },
    # A filled button: the highest-emphasis button, for a screen's main action.
    "ButtonFilled": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "primary",
                "corner_radius": "{{ corner_radius }}",
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "on_primary"},
        },
    },
    # A filled tonal button: a medium-emphasis button in the secondary container colour.
    "ButtonFilledTonal": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "secondary_container",
                "corner_radius": "{{ corner_radius }}",
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "on_secondary_container"},
        },
    },
    # An outlined button: a medium-emphasis button with a border and no fill.
    "ButtonOutlined": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "transparent",
                "corner_radius": "{{ corner_radius }}",
                "border_color": "outline",
                "border_width": 1.0,
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "primary"},
        },
    },
    # A text button: the lowest-emphasis button, for dialogs and cards.
    "ButtonText": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "transparent",
                "corner_radius": "{{ corner_radius }}",
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "primary"},
        },
    },
    # An elevated card: a container on a tinted surface with a shadow.
    "CardElevated": {
        "params": ["width", "height"],
        "tree": {"id": "root", "kind": "Rect"},
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "background": "surface_container_low",
                "corner_radius": "medium",
                "elevation": "level_1",
            }
        },
    },
    # A filled card: a container on a higher surface, with no shadow or border.
    "CardFilled": {
        "params": ["width", "height"],
        "tree": {"id": "root", "kind": "Rect"},
        "sheet": {"root": {"width": "{{ width }}", "height": "{{ height }}", "background": "surface_container_highest", "corner_radius": "medium"}},
    },
    # An outlined card: a container with a border and no fill.
    "CardOutlined": {
        "params": ["width", "height"],
        "tree": {"id": "root", "kind": "Rect"},
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "background": "surface",
                "corner_radius": "medium",
                "border_color": "outline_variant",
                "border_width": 1.0,
            }
        },
    },
    # An assist chip: a smart or automated action, such as adding to a calendar.
    "ChipAssist": {
        "params": ["label", "width"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 32,
                "align_content": "left",
                "padding": {"left": 16, "right": 16, "top": 0, "bottom": 0},
                "gap": 8,
                "background": "transparent",
                "corner_radius": "small",
                "border_color": "outline",
                "border_width": 1.0,
            },
            "label": {"foreground": "on_surface"},
        },
    },
    # A filter chip, not selected: narrows a set of results.
    "ChipFilter": {
        "params": ["label", "width"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 32,
                "align_content": "left",
                "padding": {"left": 16, "right": 16, "top": 0, "bottom": 0},
                "gap": 8,
                "background": "transparent",
                "corner_radius": "small",
                "border_color": "outline",
                "border_width": 1.0,
            },
            "label": {"foreground": "on_surface_variant"},
        },
    },
    # An input chip: a piece of information the user entered, such as a tag.
    "ChipInput": {
        "params": ["label", "width"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 32,
                "align_content": "left",
                "padding": {"left": 16, "right": 16, "top": 0, "bottom": 0},
                "gap": 8,
                "background": "transparent",
                "corner_radius": "small",
                "border_color": "outline",
                "border_width": 1.0,
            },
            "label": {"foreground": "on_surface_variant"},
        },
    },
    # A suggestion chip: a dynamic suggestion, such as a smart reply.
    "ChipSuggestion": {
        "params": ["label", "width"],
        "tree": {
            "id": "root",
            "kind": "Rect",
            "children": [
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 32,
                "align_content": "left",
                "padding": {"left": 16, "right": 16, "top": 0, "bottom": 0},
                "gap": 8,
                "background": "transparent",
                "corner_radius": "small",
                "border_color": "outline",
                "border_width": 1.0,
            },
            "label": {"foreground": "on_surface_variant"},
        },
    },
    # One day in a date picker's month grid.
    "DatePickerDay": {
        "params": ["day"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [{"id": "label", "kind": "Text", "text": {"content": "{{ day }}", "typography_role": "body_large", "text_align": "center"}}],
        },
        "sheet": {
            "root": {"width": 48, "height": 48, "background": "transparent", "corner_radius": 24, "align_content": "center"},
            "label": {"foreground": "on_surface"},
        },
    },
    # A dialog: a headline and text on a raised panel, over a scrim.
    "Dialog": {
        "params": ["headline", "text", "width", "height", "scrim_width", "scrim_height"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "panel",
                    "kind": "Container",
                    "children": [
                        {"id": "headline", "kind": "Text", "text": {"content": "{{ headline }}", "typography_role": "headline_small"}},
                        {"id": "body", "kind": "Text", "text": {"content": "{{ text }}", "typography_role": "body_medium"}},
                    ],
                }
            ],
        },
        "sheet": {
            "root": {"width": "{{ scrim_width }}", "height": "{{ scrim_height }}", "background": "#00000052", "align_content": "center"},
            "panel": {
                "flex_direction": "vertical",
                "width": "{{ width }}",
                "height": "{{ height }}",
                "background": "surface_container_high",
                "corner_radius": "extra_large",
                "elevation": "level_3",
                "padding": 24,
                "gap": 16,
            },
            "headline": {"foreground": "on_surface"},
            "body": {"foreground": "on_surface_variant", "flex": "expand_vertical"},
        },
    },
    # A thin line that separates content.
    "Divider": {
        "params": ["width", "height"],
        "tree": {"id": "root", "kind": "Rect"},
        "sheet": {"root": {"width": "{{ width }}", "height": "{{ height }}", "background": "outline_variant"}},
    },
    # An extended floating action button in the primary colour: an icon and a label.
    "ExtendedFabPrimary": {
        "params": ["label", "width", {"icon": None}],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {"id": "icon", "when": "{{ icon }}", "kind": "Icon", "icon": {"name": "{{ icon }}"}},
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "wrap": "none"}},
            ],
        },
        "sheet": {
            "root": {
                "flex_direction": "horizontal",
                "width": "{{ width }}",
                "height": 56,
                "background": "primary_container",
                "corner_radius": "large",
                "elevation": "level_3",
                "padding": {
                    "if": "{{ icon }}",
                    "then": {"left": 16, "right": 20, "top": 0, "bottom": 0},
                    "else": {"left": 20, "right": 20, "top": 0, "bottom": 0},
                },
                "align_content": {"if": "{{ icon }}", "then": "left", "else": "center"},
                "gap": 8,
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_primary_container"},
            "label": {"foreground": "on_primary_container"},
        },
    },
    # An extended floating action button in the secondary colour.
    "ExtendedFabSecondary": {
        "params": ["label", "width", {"icon": None}],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {"id": "icon", "when": "{{ icon }}", "kind": "Icon", "icon": {"name": "{{ icon }}"}},
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "wrap": "none"}},
            ],
        },
        "sheet": {
            "root": {
                "flex_direction": "horizontal",
                "width": "{{ width }}",
                "height": 56,
                "background": "secondary_container",
                "corner_radius": "large",
                "elevation": "level_3",
                "padding": {
                    "if": "{{ icon }}",
                    "then": {"left": 16, "right": 20, "top": 0, "bottom": 0},
                    "else": {"left": 20, "right": 20, "top": 0, "bottom": 0},
                },
                "align_content": {"if": "{{ icon }}", "then": "left", "else": "center"},
                "gap": 8,
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_secondary_container"},
            "label": {"foreground": "on_secondary_container"},
        },
    },
    # An extended floating action button on the surface colour.
    "ExtendedFabSurface": {
        "params": ["label", "width", {"icon": None}],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {"id": "icon", "when": "{{ icon }}", "kind": "Icon", "icon": {"name": "{{ icon }}"}},
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "wrap": "none"}},
            ],
        },
        "sheet": {
            "root": {
                "flex_direction": "horizontal",
                "width": "{{ width }}",
                "height": 56,
                "background": "surface_container_high",
                "corner_radius": "large",
                "elevation": "level_3",
                "padding": {
                    "if": "{{ icon }}",
                    "then": {"left": 16, "right": 20, "top": 0, "bottom": 0},
                    "else": {"left": 20, "right": 20, "top": 0, "bottom": 0},
                },
                "align_content": {"if": "{{ icon }}", "then": "left", "else": "center"},
                "gap": 8,
            },
            "icon": {"width": 24, "height": 24, "foreground": "primary"},
            "label": {"foreground": "primary"},
        },
    },
    # An extended floating action button in the tertiary colour.
    "ExtendedFabTertiary": {
        "params": ["label", "width", {"icon": None}],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {"id": "icon", "when": "{{ icon }}", "kind": "Icon", "icon": {"name": "{{ icon }}"}},
                {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "wrap": "none"}},
            ],
        },
        "sheet": {
            "root": {
                "flex_direction": "horizontal",
                "width": "{{ width }}",
                "height": 56,
                "background": "tertiary_container",
                "corner_radius": "large",
                "elevation": "level_3",
                "padding": {
                    "if": "{{ icon }}",
                    "then": {"left": 16, "right": 20, "top": 0, "bottom": 0},
                    "else": {"left": 20, "right": 20, "top": 0, "bottom": 0},
                },
                "align_content": {"if": "{{ icon }}", "then": "left", "else": "center"},
                "gap": 8,
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_tertiary_container"},
            "label": {"foreground": "on_tertiary_container"},
        },
    },
    # A floating action button in the primary colour: the screen's main action.
    "FabPrimary": {
        "params": ["icon", "size", "corner_radius", {"fab_size": "default"}],
        "tree": {
            "id": "root",
            "component_of": "fab.{{ fab_size }}",
            "kind": "Rect",
            "children": [{"id": "icon", "kind": "Icon", "icon": {"name": "{{ icon }}"}}],
        },
        "sheet": {
            "root": {
                "width": "{{ size }}",
                "height": "{{ size }}",
                "align_content": "center",
                "background": "primary_container",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_3",
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_primary_container"},
        },
    },
    # A floating action button in the secondary colour.
    "FabSecondary": {
        "params": ["icon", "size", "corner_radius", {"fab_size": "default"}],
        "tree": {
            "id": "root",
            "component_of": "fab.{{ fab_size }}",
            "kind": "Rect",
            "children": [{"id": "icon", "kind": "Icon", "icon": {"name": "{{ icon }}"}}],
        },
        "sheet": {
            "root": {
                "width": "{{ size }}",
                "height": "{{ size }}",
                "align_content": "center",
                "background": "secondary_container",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_3",
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_secondary_container"},
        },
    },
    # A floating action button on the surface colour.
    "FabSurface": {
        "params": ["icon", "size", "corner_radius", {"fab_size": "default"}],
        "tree": {
            "id": "root",
            "component_of": "fab.{{ fab_size }}",
            "kind": "Rect",
            "children": [{"id": "icon", "kind": "Icon", "icon": {"name": "{{ icon }}"}}],
        },
        "sheet": {
            "root": {
                "width": "{{ size }}",
                "height": "{{ size }}",
                "align_content": "center",
                "background": "surface_container_high",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_3",
            },
            "icon": {"width": 24, "height": 24, "foreground": "primary"},
        },
    },
    # A floating action button in the tertiary colour.
    "FabTertiary": {
        "params": ["icon", "size", "corner_radius", {"fab_size": "default"}],
        "tree": {
            "id": "root",
            "component_of": "fab.{{ fab_size }}",
            "kind": "Rect",
            "children": [{"id": "icon", "kind": "Icon", "icon": {"name": "{{ icon }}"}}],
        },
        "sheet": {
            "root": {
                "width": "{{ size }}",
                "height": "{{ size }}",
                "align_content": "center",
                "background": "tertiary_container",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_3",
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_tertiary_container"},
        },
    },
    # A filled icon button: a high-emphasis action shown as an icon.
    "IconButtonFilled": {
        "params": ["icon", "size", "corner_radius"],
        "tree": {"id": "root", "kind": "Rect", "children": [{"id": "icon", "kind": "Icon", "icon": {"name": "{{ icon }}"}}]},
        "sheet": {
            "root": {
                "width": "{{ size }}",
                "height": "{{ size }}",
                "align_content": "center",
                "background": "primary",
                "corner_radius": "{{ corner_radius }}",
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_primary"},
        },
    },
    # A filled tonal icon button: a medium-emphasis action shown as an icon.
    "IconButtonFilledTonal": {
        "params": ["icon", "size", "corner_radius"],
        "tree": {"id": "root", "kind": "Rect", "children": [{"id": "icon", "kind": "Icon", "icon": {"name": "{{ icon }}"}}]},
        "sheet": {
            "root": {
                "width": "{{ size }}",
                "height": "{{ size }}",
                "align_content": "center",
                "background": "secondary_container",
                "corner_radius": "{{ corner_radius }}",
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_secondary_container"},
        },
    },
    # An outlined icon button: a medium-emphasis action shown as an icon with a border.
    "IconButtonOutlined": {
        "params": ["icon", "size", "corner_radius"],
        "tree": {"id": "root", "kind": "Rect", "children": [{"id": "icon", "kind": "Icon", "icon": {"name": "{{ icon }}"}}]},
        "sheet": {
            "root": {
                "width": "{{ size }}",
                "height": "{{ size }}",
                "align_content": "center",
                "background": "transparent",
                "corner_radius": "{{ corner_radius }}",
                "border_color": "outline",
                "border_width": 1.0,
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_surface_variant"},
        },
    },
    # A standard icon button: a low-emphasis action shown as an icon alone.
    "IconButtonStandard": {
        "params": ["icon", "size", "corner_radius"],
        "tree": {"id": "root", "kind": "Rect", "children": [{"id": "icon", "kind": "Icon", "icon": {"name": "{{ icon }}"}}]},
        "sheet": {
            "root": {
                "width": "{{ size }}",
                "height": "{{ size }}",
                "align_content": "center",
                "background": "transparent",
                "corner_radius": "{{ corner_radius }}",
            },
            "icon": {"width": 24, "height": 24, "foreground": "on_surface_variant"},
        },
    },
    # Text that opens something when it is clicked.
    "Link": {
        "params": ["text", "width", "height", {"wrap": "none"}, {"overflow": "ellipsis"}],
        "tree": {
            "id": "root",
            "kind": "Link",
            "text": {"content": "{{ text }}", "typography_role": "body_large", "wrap": "{{ wrap }}", "overflow": "{{ overflow }}"},
        },
        "sheet": {"root": {"width": "{{ width }}", "height": "{{ height }}", "foreground": "primary"}},
    },
    # A list row: a headline, and room for more.
    "ListItem": {
        "params": ["headline", "width"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "headline",
                    "kind": "Text",
                    "text": {"content": "{{ headline }}", "typography_role": "body_large", "wrap": "none", "overflow": "ellipsis"},
                }
            ],
        },
        "sheet": {
            "root": {"width": "{{ width }}", "height": 56, "align_content": "left", "padding": 16},
            "headline": {"foreground": "on_surface", "flex": "expand_horizontal", "min_width": 0},
        },
    },
    # One choice in a menu.
    "MenuItem": {
        "params": ["label", "width", {"height": 56}, {"padding": 16}],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "label",
                    "kind": "Text",
                    "text": {"content": "{{ label }}", "typography_role": "label_large", "wrap": "none", "overflow": "ellipsis"},
                }
            ],
        },
        "sheet": {
            "root": {"width": "{{ width }}", "height": "{{ height }}", "align_content": "left", "padding": "{{ padding }}"},
            "label": {"foreground": "on_surface", "flex": "expand_horizontal", "min_width": 0},
        },
    },
    # A pannable canvas for a node graph: its GraphNodes and the edges between them.
    "NodeGraph": {
        "params": ["width", "height"],
        "tree": {"id": "root", "kind": "Rect"},
        "sheet": {"root": {"width": "{{ width }}", "height": "{{ height }}", "background": "surface_container_low"}},
    },
    # A time picker's AM / PM selector, with AM selected.
    "PeriodSelectorAM": {
        "params": [],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "am",
                    "kind": "Container",
                    "children": [
                        {"id": "am_label", "kind": "Text", "text": {"content": "AM", "typography_role": "label_large", "text_align": "center"}}
                    ],
                },
                {
                    "id": "pm",
                    "kind": "Container",
                    "children": [
                        {"id": "pm_label", "kind": "Text", "text": {"content": "PM", "typography_role": "label_large", "text_align": "center"}}
                    ],
                },
            ],
        },
        "sheet": {
            "root": {"flex_direction": "vertical", "width": 52, "height": 72},
            "am": {"width": 52, "height": 36, "background": "tertiary_container", "corner_radius": "small", "align_content": "center"},
            "am_label": {"foreground": "on_tertiary_container"},
            "pm": {"width": 52, "height": 36, "background": "transparent", "corner_radius": "small", "align_content": "center"},
            "pm_label": {"foreground": "on_surface"},
        },
    },
    # A search bar: a rounded field with a placeholder.
    "SearchBar": {
        "params": ["placeholder", "width", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "field",
                    "kind": "TextField",
                    "text": {"content": "{{ placeholder }}", "font_family": "Roboto", "font_weight": 400, "font_size": 16},
                }
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 56,
                "background": "surface_container_high",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_3",
                "align_content": "left",
                "padding": {"left": 4, "right": 4, "top": 0, "bottom": 0},
            },
            "field": {"background": "transparent", "flex": "expand_horizontal"},
        },
    },
    # A modal side sheet: a panel at the side of the window, over a scrim.
    "SideSheetModal": {
        "params": ["width", "height", "scrim_width", "scrim_height"],
        "tree": {"id": "root", "kind": "Container", "children": [{"id": "panel", "kind": "Rect"}]},
        "sheet": {
            "root": {"width": "{{ scrim_width }}", "height": "{{ scrim_height }}", "background": "#00000052", "align_content": "top_right"},
            "panel": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "background": "surface_container_low",
                "corner_radius": "large",
                "elevation": "level_1",
            },
        },
    },
    # A standard side sheet: a panel at the side that shares the window with the content.
    "SideSheetStandard": {
        "params": ["width", "height"],
        "tree": {"id": "root", "kind": "Rect"},
        "sheet": {"root": {"width": "{{ width }}", "height": "{{ height }}", "background": "surface", "corner_radius": "large"}},
    },
    # A snackbar: a short message about a process, at the bottom of the window.
    "Snackbar": {
        "params": ["text", "width"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [{"id": "text", "kind": "Text", "text": {"content": "{{ text }}", "typography_role": "body_medium"}}],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 48,
                "background": "inverse_surface",
                "corner_radius": "extra_small",
                "elevation": "level_3",
                "align_content": "left",
                "padding": {"left": 16, "right": 16, "top": 0, "bottom": 0},
            },
            "text": {"foreground": "inverse_on_surface", "flex": "expand_horizontal"},
        },
    },
    # An elevated split button: an action, and a menu of related ones.
    "SplitButtonElevated": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "leading",
                    "kind": "Rect",
                    "children": [
                        {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
                    ],
                },
                {"id": "trailing", "kind": "Rect", "children": [{"id": "chevron", "kind": "Icon", "icon": {"name": "expand_more"}}]},
            ],
        },
        "sheet": {
            "root": {"flex_direction": "horizontal", "gap": 2},
            "leading": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "surface_container_low",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_1",
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "primary"},
            "trailing": {
                "width": "{{ height }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "surface_container_low",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_1",
            },
            "chevron": {"width": 22, "height": 22, "foreground": "primary"},
        },
    },
    # A filled split button: an action, and a menu of related ones.
    "SplitButtonFilled": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "leading",
                    "kind": "Rect",
                    "children": [
                        {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
                    ],
                },
                {"id": "trailing", "kind": "Rect", "children": [{"id": "chevron", "kind": "Icon", "icon": {"name": "expand_more"}}]},
            ],
        },
        "sheet": {
            "root": {"flex_direction": "horizontal", "gap": 2},
            "leading": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "primary",
                "corner_radius": "{{ corner_radius }}",
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "on_primary"},
            "trailing": {
                "width": "{{ height }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "primary",
                "corner_radius": "{{ corner_radius }}",
            },
            "chevron": {"width": 22, "height": 22, "foreground": "on_primary"},
        },
    },
    # A filled tonal split button: an action, and a menu of related ones.
    "SplitButtonFilledTonal": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "leading",
                    "kind": "Rect",
                    "children": [
                        {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
                    ],
                },
                {"id": "trailing", "kind": "Rect", "children": [{"id": "chevron", "kind": "Icon", "icon": {"name": "expand_more"}}]},
            ],
        },
        "sheet": {
            "root": {"flex_direction": "horizontal", "gap": 2},
            "leading": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "secondary_container",
                "corner_radius": "{{ corner_radius }}",
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "on_secondary_container"},
            "trailing": {
                "width": "{{ height }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "secondary_container",
                "corner_radius": "{{ corner_radius }}",
            },
            "chevron": {"width": 22, "height": 22, "foreground": "on_secondary_container"},
        },
    },
    # An outlined split button: an action, and a menu of related ones.
    "SplitButtonOutlined": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "leading",
                    "kind": "Rect",
                    "children": [
                        {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
                    ],
                },
                {"id": "trailing", "kind": "Rect", "children": [{"id": "chevron", "kind": "Icon", "icon": {"name": "expand_more"}}]},
            ],
        },
        "sheet": {
            "root": {"flex_direction": "horizontal", "gap": 2},
            "leading": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "transparent",
                "corner_radius": "{{ corner_radius }}",
                "border_color": "outline",
                "border_width": 1.0,
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "primary"},
            "trailing": {
                "width": "{{ height }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "transparent",
                "corner_radius": "{{ corner_radius }}",
                "border_color": "outline",
                "border_width": 1.0,
            },
            "chevron": {"width": 22, "height": 22, "foreground": "primary"},
        },
    },
    # A text split button: an action, and a menu of related ones.
    "SplitButtonText": {
        "params": ["label", "width", "height", "corner_radius"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "leading",
                    "kind": "Rect",
                    "children": [
                        {"id": "label", "kind": "Text", "text": {"content": "{{ label }}", "typography_role": "label_large", "text_align": "center"}}
                    ],
                },
                {"id": "trailing", "kind": "Rect", "children": [{"id": "chevron", "kind": "Icon", "icon": {"name": "expand_more"}}]},
            ],
        },
        "sheet": {
            "root": {"flex_direction": "horizontal", "gap": 2},
            "leading": {
                "width": "{{ width }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "transparent",
                "corner_radius": "{{ corner_radius }}",
                "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0},
            },
            "label": {"foreground": "primary"},
            "trailing": {
                "width": "{{ height }}",
                "height": "{{ height }}",
                "align_content": "center",
                "background": "transparent",
                "corner_radius": "{{ corner_radius }}",
            },
            "chevron": {"width": 22, "height": 22, "foreground": "primary"},
        },
    },
    # A status bar: a thin strip of text along the bottom of the window.
    "StatusBar": {
        "params": ["text", "width"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "text",
                    "kind": "Text",
                    "text": {"content": "{{ text }}", "typography_role": "label_small", "wrap": "none", "overflow": "ellipsis"},
                }
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 24,
                "background": "surface_container",
                "align_content": "left",
                "padding": {"left": 8, "right": 8, "top": 0, "bottom": 0},
            },
            "text": {"foreground": "on_surface_variant", "flex": "expand_horizontal", "min_width": 0},
        },
    },
    # Text in one of MD3's type styles and a colour.
    "Text": {
        "params": ["text", {"typography_role": "body_medium"}, {"color": "on_surface"}, {"wrap": "word"}, {"overflow": "clip"}],
        "tree": {
            "id": "root",
            "kind": "Text",
            "text": {"content": "{{ text }}", "typography_role": "{{ typography_role }}", "wrap": "{{ wrap }}", "overflow": "{{ overflow }}"},
        },
        "sheet": {"root": {"foreground": "{{ color }}"}},
    },
    # A docked toolbar: a bar of actions fixed to an edge of the window.
    "ToolbarDocked": {
        "params": ["background", "width"],
        "tree": {"id": "root", "kind": "Container", "children": []},
        "sheet": {
            "root": {
                "flex_direction": "horizontal",
                "width": "{{ width }}",
                "height": 64,
                "background": "{{ background }}",
                "align_content": "center",
                "padding": 16,
                "gap": 32,
            }
        },
    },
    # A floating toolbar: a rounded bar of actions over the content.
    "ToolbarFloating": {
        "params": ["background", "width", "corner_radius"],
        "tree": {"id": "root", "kind": "Container", "children": []},
        "sheet": {
            "root": {
                "flex_direction": "horizontal",
                "width": "{{ width }}",
                "height": 64,
                "background": "{{ background }}",
                "corner_radius": "{{ corner_radius }}",
                "elevation": "level_3",
                "align_content": "center",
                "padding": 16,
                "gap": 32,
            }
        },
    },
    # A tooltip: a short label that appears beside what the pointer rests on.
    "Tooltip": {
        "params": ["text", "width"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "text",
                    "kind": "Text",
                    "text": {"content": "{{ text }}", "typography_role": "body_small", "wrap": "none", "overflow": "ellipsis"},
                }
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 24,
                "background": "inverse_surface",
                "corner_radius": "extra_small",
                "align_content": "center",
                "padding": {"left": 8, "right": 8, "top": 0, "bottom": 0},
            },
            "text": {"foreground": "inverse_on_surface", "flex": "expand_horizontal", "min_width": 0},
        },
    },
    # A top app bar: the window's title and actions, along the top.
    "TopAppBar": {
        "params": ["title", "width"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "title",
                    "kind": "Text",
                    "text": {"content": "{{ title }}", "typography_role": "title_large", "wrap": "none", "overflow": "ellipsis"},
                }
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 64,
                "background": "surface",
                "align_content": "left",
                "padding": {"left": 4, "right": 4, "top": 0, "bottom": 0},
            },
            "title": {
                "foreground": "on_surface",
                "flex": "expand_horizontal",
                "margin": {"left": 16, "right": 0, "top": 0, "bottom": 0},
                "min_width": 0,
            },
        },
    },
    # A tree row that can be expanded: a title and a chevron, indented by its depth.
    "TreeNodeBranch": {
        "params": ["title", "width", "left_padding"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "title",
                    "kind": "Text",
                    "text": {"content": "{{ title }}", "typography_role": "label_large", "wrap": "none", "overflow": "ellipsis"},
                },
                {"id": "chevron", "kind": "Icon", "icon": {"name": "expand_more"}},
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 56,
                "align_content": "left",
                "padding": {"left": "{{ left_padding }}", "right": 16, "top": 0, "bottom": 0},
                "gap": 12,
            },
            "title": {"foreground": "on_surface", "flex": "expand_horizontal", "min_width": 0},
            "chevron": {"width": 24, "height": 24, "foreground": "on_surface_variant"},
        },
    },
    # A tree row with nothing under it: a title, indented by its depth.
    "TreeNodeLeaf": {
        "params": ["title", "width", "left_padding"],
        "tree": {
            "id": "root",
            "kind": "Container",
            "children": [
                {
                    "id": "title",
                    "kind": "Text",
                    "text": {"content": "{{ title }}", "typography_role": "label_large", "wrap": "none", "overflow": "ellipsis"},
                }
            ],
        },
        "sheet": {
            "root": {
                "width": "{{ width }}",
                "height": 56,
                "align_content": "left",
                "padding": {"left": "{{ left_padding }}", "right": 16, "top": 0, "bottom": 0},
            },
            "title": {"foreground": "on_surface", "flex": "expand_horizontal", "min_width": 0},
        },
    },
}
