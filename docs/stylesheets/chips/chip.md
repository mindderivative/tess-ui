# Chip_Stylesheet.tdl

The look of Chip (Material 3): 8 pixel corners, 8 pixels between parts, 16 pixels of padding (8 beside an icon or the close button). Assist, suggestion, filter and input chips are outlined in `outline_variant`; elevated ones are `surface_container_low` at level 1 with no outline; a selected filter or input chip is `secondary_container` with no outline.

The look of [`Chip`](../../components/chips.md) (in [Chips](../../components/chips.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Chip
Tesserae: "0.6"
---
# The look of Chip (Material 3): 8 pixel corners, 8 pixels between parts, 16 pixels of padding (8 beside an icon or the close button). Assist, suggestion,
# filter and input chips are outlined in `outline_variant`; elevated ones are `surface_container_low` at level 1 with no outline; a selected filter or input chip
# is `secondary_container` with no outline.
Styles {
  Rule {
    Widget: Chip
    Style {
      Corner_Radius: 8
      Gap: 8
      Padding: <| {'left': 8 if (avatar_text != '' or icon != '' or (variant == 'filter' and selected)) else 16, 'right': 8 if removable else 16, 'top': 0, 'bottom': 0} |>
      Transition { Background: 150 }
      Border_Width: <| 0 if (elevated or (selected and variant in ('filter', 'input'))) else 1 |>
      Border_Color: outline_variant
      Background: <| 'secondary_container' if (selected and variant in ('filter', 'input')) else ('surface_container_low' if elevated else 'transparent') |>
      Elevation: <| 1 if (elevated and not (selected and variant in ('filter', 'input'))) else 0 |>
    }
  }
  Rule {
    Widget: Chip
    Part: label
    Style {
      Foreground: <| 'on_secondary_container' if (selected and variant in ('filter', 'input')) else ('on_surface_variant' if variant in ('filter', 'input') else 'on_surface') |>
    }
  }
  Rule {
    Widget: Chip
    Part: icon
    Style {
      Width: 18
      Height: 18
      Foreground: <| 'on_secondary_container' if (selected and variant in ('filter', 'input')) else ('primary' if variant in ('assist', 'suggestion') else 'on_surface_variant') |>
    }
  }
  Rule {
    Widget: Chip
    Part: avatar
    Style { Width: 24, Height: 24, Corner_Radius: full, Background: primary_container, Align_Content: center }
  }
  Rule { Widget: Chip, Part: avatar_text, Style { Foreground: on_primary_container } }
  Rule {
    Widget: Chip
    Part: close
    Style { Width: 18, Height: 18, Corner_Radius: 9, Align_Content: center }
  }
  Rule {
    Widget: Chip
    Part: close_icon
    Style { Width: 18, Height: 18, Foreground: <| 'on_secondary_container' if selected else 'on_surface_variant' |> }
  }
}
```

## How it reaches the view

Each rule names `Widget: Chip` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Chip` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `8` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Gap` | `8` | Space between its children. |
| always | `Padding` | `<\| {'left': 8 if (avatar_text != '' or icon != '' or (variant == 'filter' and selected)) else 16, 'right': 8 …` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Transition` | `{ Background: 150 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |
| always | `Border_Width` | `<\| 0 if (elevated or (selected and variant in ('filter', 'input'))) else 1 \|>` | The width of its border, in pixels. |
| always | `Border_Color` | `outline_variant` | The colour of its border: a colour or a gradient. |
| always | `Background` | `<\| 'secondary_container' if (selected and variant in ('filter', 'input')) else ('surface_container_low' if el…` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Elevation` | `<\| 1 if (elevated and not (selected and variant in ('filter', 'input'))) else 0 \|>` | A shadow level, 0 to 5. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `<\| 'on_secondary_container' if (selected and variant in ('filter', 'input')) else ('on_surface_variant' if va…` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `18` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `18` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `<\| 'on_secondary_container' if (selected and variant in ('filter', 'input')) else ('primary' if variant in ('…` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `avatar` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Background` | `primary_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `avatar_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_primary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `close` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `18` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `18` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `9` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `close_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `18` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `18` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Chip
    Style { Background: tertiary }
  }
}
```
