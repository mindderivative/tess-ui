# IconPickerPanel_Stylesheet.yaml

The look of the icon picker's grid: a cell is 48 pixels square with 12 pixel corners (the one holding `value` in `secondary_container`, the one the keyboard is on in `surface_container_highest`), its icon 24 pixels in `on_surface` (a file's preview 32); the empty note in `on_surface_variant` and a message in `error`.

The look of [`IconPickerPanel`](../../components/icon-pickers.md) (in [Icon picker](../../components/icon-pickers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```yaml
tesserae: 0.6
# The look of the icon picker's grid: a cell is 48 pixels square with 12 pixel corners (the one holding `value` in `secondary_container`, the one the keyboard is on in
# `surface_container_highest`), its icon 24 pixels in `on_surface` (a file's preview 32); the empty note in `on_surface_variant` and a message in `error`.
styles:
  - {widget: IconPickerPanel, part: cell, style: {corner_radius: 12}}
  - {widget: IconPickerPanel, part: empty, style: {foreground: on_surface_variant}}
  - {widget: IconPickerPanel, part: message_text, style: {foreground: error}}
```

## How it reaches the view

Each rule names `widget: IconPickerPanel` and may add the properties the view declares (a `variant`, a `size`, a `shape`), `classes`, a node `name`, a `part` (one of the view's named nodes) and a `state` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `name`, then the number of properties matched (all the `classes` count as one more), then a `state`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `style:` beats every rule for the fields it sets.

## The rules

### `cell` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `corner_radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |

### `empty` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `message_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```yaml
styles:
  - widget: IconPickerPanel
    part: empty
    style: {foreground: tertiary}
```
