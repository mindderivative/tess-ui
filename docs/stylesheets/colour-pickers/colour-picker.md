# ColourPicker_Stylesheet.tdl

The look of ColourPicker: the swatch that opens a popup is a 40 pixel square with 8 pixel corners and a 1 pixel `outline` border, and the layer is a `surface_container` surface with 12 pixel corners and 16 pixels of padding at level 2. The swatch has the state layer, ripple and focus ring of any pressable node (hovered, focused, pressed), and a disabled one fades to 38%. A state rule of a stylesheet is the state of the whole picker, popup included, so the swatch's own feedback is not written as one here.

The look of [`ColourPicker`](../../components/colour-pickers.md) (in [Colour picker](../../components/colour-pickers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: ColourPicker
Tesserae: "0.6"
---
# The look of ColourPicker: the swatch that opens a popup is a 40 pixel square with 8 pixel corners and a 1 pixel `outline` border, and the layer is a `surface_container`
# surface with 12 pixel corners and 16 pixels of padding at level 2. The swatch has the state layer, ripple and focus ring of any pressable node (hovered, focused, pressed), and a
# disabled one fades to 38%. A state rule of a stylesheet is the state of the whole picker, popup included, so the swatch's own feedback is not written as one here.
Styles {
  Rule {
    Widget: ColourPicker
    Part: trigger
    Style { Width: 40, Height: 40, Corner_Radius: 8, Border_Width: 1, Border_Color: outline }
  }
  Rule {
    Widget: ColourPicker
    Part: surface
    Style { Background: surface_container, Corner_Radius: 12, Padding: 16, Elevation: 2 }
  }
}
```

## How it reaches the view

Each rule names `Widget: ColourPicker` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `trigger` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `8` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Border_Width` | `1` | The width of its border, in pixels. |
| always | `Border_Color` | `outline` | The colour of its border: a colour or a gradient. |

### `surface` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `16` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Elevation` | `2` | A shadow level, 0 to 5. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: ColourPicker
    Part: surface
    Style { Background: tertiary }
  }
}
```
