# TokenButton_Stylesheet.tdl

The look of TokenButton: the button (`field`, with `trigger` pressable over it) is 48 pixels tall with no density (40, 32, 28 at default, compact, dense: a text field's height) with 12 pixel corners, 12 pixels of padding (8 at compact and dense) and a 1 pixel `outline` border, and the layer is a `surface_container` surface with 12 pixel corners and 8 pixels of padding at level 2; a row has 12 pixel corners (the token held in `secondary_container`, the one the keyboard is on in `surface_container_highest`) and the empty note is in `on_surface_variant`. The button has the state layer, ripple and focus ring of any pressable node, and a disabled one fades to 38%.

The look of [`TokenButton`](../../components/token-buttons.md) (in [Token button](../../components/token-buttons.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: TokenButton
Tesserae: "0.6"
---
# The look of TokenButton: the button (`field`, with `trigger` pressable over it) is 48 pixels tall with no density (40, 32, 28 at default, compact, dense: a text field's height) with 12 pixel corners, 12 pixels of padding (8 at compact and dense) and a 1 pixel `outline` border, and the layer is a
# `surface_container` surface with 12 pixel corners and 8 pixels of padding at level 2; a row has 12 pixel corners (the token held in `secondary_container`, the one the keyboard is on in
# `surface_container_highest`) and the empty note is in `on_surface_variant`. The button has the state layer, ripple and focus ring of any pressable node, and a disabled one fades to 38%.
Styles {
  Rule {
    Widget: TokenButton
    Part: field
    Style {
      Min_Height: <| 48 if density == '' else density_token(density, 'control_height') |>
      Corner_Radius: 12
      Border_Width: 1
      Border_Color: outline
      Padding: <| {'left': 12 if density == '' else density_token(density, 'field_padding_x'), 'right': 12 if density == '' else density_token(density, 'field_padding_x'), 'top': 0, 'bottom': 0} |>
      Gap: <| 12 if density == '' else density_token(density, 'icon_label_gap') |>
    }
  }
  Rule { Widget: TokenButton, Part: trigger, Style { Corner_Radius: 12 } }
  Rule {
    Widget: TokenButton
    Part: surface
    Style { Background: surface_container, Corner_Radius: 12, Padding: 8, Elevation: 2 }
  }
  Rule { Widget: TokenButton, Part: row, Style { Corner_Radius: 12 } }
  Rule { Widget: TokenButton, Part: empty, Style { Foreground: on_surface_variant } }
}
```

## How it reaches the view

Each rule names `Widget: TokenButton` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `field` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Min_Height` | `<\| 48 if density == '' else density_token(density, 'control_height') \|>` | The least height it can take. |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Border_Width` | `1` | The width of its border, in pixels. |
| always | `Border_Color` | `outline` | The colour of its border: a colour or a gradient. |
| always | `Padding` | `<\| {'left': 12 if density == '' else density_token(density, 'field_padding_x'), 'right': 12 if density == '' …` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `<\| 12 if density == '' else density_token(density, 'icon_label_gap') \|>` | Space between its children. |

### `trigger` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

### `surface` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `8` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Elevation` | `2` | A shadow level, 0 to 5. |

### `row` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

### `empty` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: TokenButton
    Part: surface
    Style { Background: tertiary }
  }
}
```
