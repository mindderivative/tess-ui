# ChoicePicker_Stylesheet.tdl

The look of ChoicePicker (ux spec Choice Picker): the button is an outlined control as high as a control of the density (40, 32, 28) with a 1 pixel `outline` border, corners of half its height, padding 16 / 12 / 8 at the start and 12 / 8 / 8 beside the chevron (24, 16, 12 on the label side), the label in `on_surface` and the chevron in `on_surface_variant`.

The look of [`ChoicePicker`](../../components/choice-pickers.md) (in [Choice pickers](../../components/choice-pickers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: ChoicePicker
Tesserae: "0.6"
---
# The look of ChoicePicker (ux spec Choice Picker): the button is an outlined control as high as a control of the density (40, 32, 28) with a 1 pixel `outline` border, corners of half its height, padding
# 16 / 12 / 8 at the start and 12 / 8 / 8 beside the chevron (24, 16, 12 on the label side), the label in `on_surface` and the chevron in `on_surface_variant`.
Styles {
  Rule {
    Widget: ChoicePicker
    Part: button
    Style {
      Height: <| 40 if density == '' else density_token(density, 'control_height') |>
      Flex_Direction: horizontal
      Align_Content: left
      Border_Width: 1
      Border_Color: outline
      Corner_Radius: <| 20 if density == '' else density_token(density, 'control_height') / 2 |>
      Padding: <| {'left': 16 if density in ('', 'default') else (12 if density == 'compact' else 8), 'right': 12 if density in ('', 'default') else 8, 'top': 0, 'bottom': 0} |>
      Gap: <| 8 if density in ('', 'default', 'compact') else 4 |>
    }
  }
  Rule { Widget: ChoicePicker, Part: chevron, Style { Width: 20, Height: 20, Foreground: on_surface_variant } }
}
```

## How it reaches the view

Each rule names `Widget: ChoicePicker` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `button` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Height` | `<\| 40 if density == '' else density_token(density, 'control_height') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Flex_Direction` | `horizontal` | How its children are laid out: `horizontal` (the default) or `Vertical`. |
| always | `Align_Content` | `left` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |
| always | `Border_Width` | `1` | The width of its border, in pixels. |
| always | `Border_Color` | `outline` | The colour of its border: a colour or a gradient. |
| always | `Corner_Radius` | `<\| 20 if density == '' else density_token(density, 'control_height') / 2 \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `<\| {'left': 16 if density in ('', 'default') else (12 if density == 'compact' else 8), 'right': 12 if density…` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `<\| 8 if density in ('', 'default', 'compact') else 4 \|>` | Space between its children. |

### `chevron` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `20` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `20` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: ChoicePicker
    Part: chevron
    Style { Foreground: tertiary }
  }
}
```
