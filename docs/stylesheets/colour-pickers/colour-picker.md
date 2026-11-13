# ColourPicker_Stylesheet.yaml

The look of ColourPicker: the swatch that opens a popup is a 40 pixel square with 8 pixel corners and a 1 pixel `outline` border, and the layer is a `surface_container` surface with 12 pixel corners and 16 pixels of padding at level 2. The swatch has the state layer, ripple and focus ring of any pressable node (hovered, focused, pressed), and a disabled one fades to 38%. A state rule of a stylesheet is the state of the whole picker, popup included, so the swatch's own feedback is not written as one here.

The look of [`ColourPicker`](../../components/colour-pickers.md) (in [Colour picker](../../components/colour-pickers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```yaml
tesserae: 0.6
# The look of ColourPicker: the swatch that opens a popup is a 40 pixel square with 8 pixel corners and a 1 pixel `outline` border, and the layer is a `surface_container`
# surface with 12 pixel corners and 16 pixels of padding at level 2. The swatch has the state layer, ripple and focus ring of any pressable node (hovered, focused, pressed), and a
# disabled one fades to 38%. A state rule of a stylesheet is the state of the whole picker, popup included, so the swatch's own feedback is not written as one here.
styles:
  - widget: ColourPicker
    part: trigger
    style: {width: 40, height: 40, corner_radius: 8, border_width: 1, border_color: outline}
  - widget: ColourPicker
    part: surface
    style: {background: surface_container, corner_radius: 12, padding: 16, elevation: 2}
```

## How it reaches the view

Each rule names `widget: ColourPicker` and may add the properties the view declares (a `variant`, a `size`, a `shape`), `classes`, a node `name`, a `part` (one of the view's named nodes) and a `state` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `name`, then the number of properties matched (all the `classes` count as one more), then a `state`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `style:` beats every rule for the fields it sets.

## The rules

### `trigger` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `width` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `height` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `corner_radius` | `8` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |
| always | `border_width` | `1` | The width of its border, in pixels. |
| always | `border_color` | `outline` | The colour of its border: a colour or a gradient. |

### `surface` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `background` | `surface_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `corner_radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |
| always | `padding` | `16` | Space inside it: one number, or `{left, right, top, bottom}`. |
| always | `elevation` | `2` | A shadow level, 0 to 5. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```yaml
styles:
  - widget: ColourPicker
    part: surface
    style: {background: tertiary}
```
