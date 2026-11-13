# FontListPanel_Stylesheet.yaml

The look of the font list: a row is 40 pixels tall with 12 pixel corners (the one holding `value` in `secondary_container`, the one the keyboard is on in `surface_container_highest`), its name in `on_surface` (in `on_secondary_container` when picked); the empty note in `on_surface_variant`.

The look of [`FontListPanel`](../../components/font-lists.md) (in [Font list](../../components/font-lists.md)). [How component stylesheets work](../index.md).

## The stylesheet

```yaml
tesserae: 0.6
# The look of the font list: a row is 40 pixels tall with 12 pixel corners (the one holding `value` in `secondary_container`, the one the keyboard is on in `surface_container_highest`),
# its name in `on_surface` (in `on_secondary_container` when picked); the empty note in `on_surface_variant`.
styles:
  - {widget: FontListPanel, part: row, style: {corner_radius: 12}}
  - {widget: FontListPanel, part: empty, style: {foreground: on_surface_variant}}
```

## How it reaches the view

Each rule names `widget: FontListPanel` and may add the properties the view declares (a `variant`, a `size`, a `shape`), `classes`, a node `name`, a `part` (one of the view's named nodes) and a `state` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `name`, then the number of properties matched (all the `classes` count as one more), then a `state`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `style:` beats every rule for the fields it sets.

## The rules

### `row` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `corner_radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |

### `empty` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```yaml
styles:
  - widget: FontListPanel
    part: empty
    style: {foreground: tertiary}
```
