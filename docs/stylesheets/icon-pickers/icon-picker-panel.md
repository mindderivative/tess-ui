# IconPickerPanel_Stylesheet.tdl

The look of the icon picker's grid: a cell is 48 pixels square with 12 pixel corners (the one holding `Value` in `secondary_container`, the one the keyboard is on in `surface_container_highest`), its icon 24 pixels in `on_surface` (a file's preview 32); the empty note in `on_surface_variant` and a message in `Error`.

The look of [`IconPickerPanel`](../../components/icon-pickers.md) (in [Icon picker](../../components/icon-pickers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: IconPickerPanel
Tesserae: "0.6"
---
# The look of the icon picker's grid: a cell is 48 pixels square with 12 pixel corners (the one holding `value` in `secondary_container`, the one the keyboard is on in
# `surface_container_highest`), its icon 24 pixels in `on_surface` (a file's preview 32); the empty note in `on_surface_variant` and a message in `error`.
Styles {
  Rule { Widget: IconPickerPanel, Part: cell, Style { Corner_Radius: 12 } }
  Rule { Widget: IconPickerPanel, Part: empty, Style { Foreground: on_surface_variant } }
  Rule { Widget: IconPickerPanel, Part: message_text, Style { Foreground: error } }
}
```

## How it reaches the view

Each rule names `Widget: IconPickerPanel` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `cell` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

### `empty` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `message_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: IconPickerPanel
    Part: empty
    Style { Foreground: tertiary }
  }
}
```
