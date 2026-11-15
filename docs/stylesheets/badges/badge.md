# Badge_Stylesheet.tdl

The look of Badge (Material 3): an error-coloured dot or pill, with the label in on_error. Anchored, the mark is placed over the host's top right corner: a dot overlaps it by 4, a pill starts 12 in from the corner and sits 4 above it.

The look of [`Badge`](../../components/badges.md) (in [Badges](../../components/badges.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Badge
Tesserae: "0.6"
---
# The look of Badge (Material 3): an error-coloured dot or pill, with the label in on_error. Anchored, the mark is placed over the host's top right
# corner: a dot overlaps it by 4, a pill starts 12 in from the corner and sits 4 above it.
Styles {
  Rule {
    Widget: Badge
    Style {
      Background: <| 'error' if flat else 'transparent' |>
      Width: <| (6 if value == '' else (16 if len(str(value)) < 2 else 8 + 6 * len(str(value)))) if flat else 'auto' |>
      Height: <| (6 if value == '' else 16) if flat else 'auto' |>
      Corner_Radius: <| (3 if value == '' else 8) if flat else 0 |>
      Align_Content: <| 'center' if flat else 'top_left' |>
    }
  }
  Rule {
    Widget: Badge
    Part: flat_label
    Style { Foreground: on_error }
  }
  Rule {
    Widget: Badge
    Part: mark
    Style {
      Background: error
      Width: <| 6 if value == '' else (16 if len(str(value)) < 2 else 8 + 6 * len(str(value))) |>
      Height: <| 6 if value == '' else 16 |>
      Corner_Radius: <| 3 if value == '' else 8 |>
      Align_Content: center
      Position: <| 'absolute' if anchored else 'relative' |>
      X: <| '100%' if anchored else 'auto' |>
      Y: <| (0 if value == '' else -4) if anchored else 'auto' |>
      Translate_X: <| (-4 if value == '' else -12) if anchored else 0 |>
    }
  }
  Rule {
    Widget: Badge
    Part: label
    Style { Foreground: on_error }
  }
}
```

## How it reaches the view

Each rule names `Widget: Badge` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Badge` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'error' if flat else 'transparent' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Width` | `<\| (6 if value == '' else (16 if len(str(value)) < 2 else 8 + 6 * len(str(value)))) if flat else 'auto' \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| (6 if value == '' else 16) if flat else 'auto' \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `<\| (3 if value == '' else 8) if flat else 0 \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Align_Content` | `<\| 'center' if flat else 'top_left' \|>` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `flat_label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `mark` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `error` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Width` | `<\| 6 if value == '' else (16 if len(str(value)) < 2 else 8 + 6 * len(str(value))) \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| 6 if value == '' else 16 \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `<\| 3 if value == '' else 8 \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |
| always | `Position` | `<\| 'absolute' if anchored else 'relative' \|>` | `absolute` takes it out of the flow and places it at `X` and `Y`. |
| always | `X` | `<\| '100%' if anchored else 'auto' \|>` | Where an `absolute` node sits from the left; the same as `Left` (say one of them). |
| always | `Y` | `<\| (0 if value == '' else -4) if anchored else 'auto' \|>` | Where an `absolute` node sits from the top; the same as `Top` (say one of them). |
| always | `Translate_X` | `<\| (-4 if value == '' else -12) if anchored else 0 \|>` | Draws the node this many pixels to the right of where it is laid out. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Badge
    Style { Background: tertiary }
  }
}
```
