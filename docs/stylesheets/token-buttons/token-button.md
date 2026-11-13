# TokenButton_Stylesheet.yaml

The look of TokenButton: the button (`field`, with `trigger` pressable over it) is 48 pixels tall with 12 pixel corners, 12 pixels of padding and a 1 pixel `outline` border, and the layer is a `surface_container` surface with 12 pixel corners and 8 pixels of padding at level 2; a row has 12 pixel corners (the token held in `secondary_container`, the one the keyboard is on in `surface_container_highest`) and the empty note is in `on_surface_variant`. The button has the state layer, ripple and focus ring of any pressable node, and a disabled one fades to 38%.

The look of [`TokenButton`](../../components/token-buttons.md) (in [Token button](../../components/token-buttons.md)). [How component stylesheets work](../index.md).

## The stylesheet

```yaml
tesserae: 0.6
# The look of TokenButton: the button (`field`, with `trigger` pressable over it) is 48 pixels tall with 12 pixel corners, 12 pixels of padding and a 1 pixel `outline` border, and the layer is a
# `surface_container` surface with 12 pixel corners and 8 pixels of padding at level 2; a row has 12 pixel corners (the token held in `secondary_container`, the one the keyboard is on in
# `surface_container_highest`) and the empty note is in `on_surface_variant`. The button has the state layer, ripple and focus ring of any pressable node, and a disabled one fades to 38%.
styles:
  - widget: TokenButton
    part: field
    style: {min_height: 48, corner_radius: 12, border_width: 1, border_color: outline, padding: {left: 12, right: 12, top: 0, bottom: 0}}
  - {widget: TokenButton, part: trigger, style: {corner_radius: 12}}
  - widget: TokenButton
    part: surface
    style: {background: surface_container, corner_radius: 12, padding: 8, elevation: 2}
  - {widget: TokenButton, part: row, style: {corner_radius: 12}}
  - {widget: TokenButton, part: empty, style: {foreground: on_surface_variant}}
```

## How it reaches the view

Each rule names `widget: TokenButton` and may add the properties the view declares (a `variant`, a `size`, a `shape`), `classes`, a node `name`, a `part` (one of the view's named nodes) and a `state` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `name`, then the number of properties matched (all the `classes` count as one more), then a `state`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `style:` beats every rule for the fields it sets.

## The rules

### `field` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `min_height` | `48` | The least height it can take. |
| always | `corner_radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |
| always | `border_width` | `1` | The width of its border, in pixels. |
| always | `border_color` | `outline` | The colour of its border: a colour or a gradient. |
| always | `padding` | `{bottom: 0, left: 12, right: 12, top: 0}` | Space inside it: one number, or `{left, right, top, bottom}`. |

### `trigger` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `corner_radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |

### `surface` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `background` | `surface_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `corner_radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |
| always | `padding` | `8` | Space inside it: one number, or `{left, right, top, bottom}`. |
| always | `elevation` | `2` | A shadow level, 0 to 5. |

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
  - widget: TokenButton
    part: surface
    style: {background: tertiary}
```
