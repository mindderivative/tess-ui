# Dialog_Stylesheet.tdl

The look of Dialog (Material 3): a raised panel with 28 pixel corners, 24 pixels of padding, an icon in `secondary`, the supporting text in `on_surface_variant`. The scrim is the modal Overlay's.

The look of [`Dialog`](../../components/dialogs.md) (in [Dialogs](../../components/dialogs.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Dialog
Tesserae: "0.6"
---
# The look of Dialog (Material 3): a raised panel with 28 pixel corners, 24 pixels of padding, an icon in `secondary`, the supporting text in
# `on_surface_variant`. The scrim is the modal Overlay's.
Styles {
  Rule {
    Widget: Dialog
    Part: panel
    Style {
      Background: <| 'surface' if fullscreen else 'surface_container_high' |>
      Corner_Radius: <| 0 if fullscreen else 28 |>
      Padding: <| 0 if fullscreen else 24 |>
      Gap: <| 0 if fullscreen else 16 |>
      Elevation: <| 0 if fullscreen else 3 |>
    }
  }
  Rule { Widget: Dialog, Part: icon, Style { Foreground: secondary, Width: 24, Height: 24 } }
  Rule { Widget: Dialog, Part: headline, Style { Foreground: on_surface } }
  Rule { Widget: Dialog, Part: body, Style { Foreground: on_surface_variant } }
  Rule { Widget: Dialog, Part: bar, Style { Padding { Left: 4, Right: 16, Top: 0, Bottom: 0 }, Gap: 8 } }
  Rule { Widget: Dialog, Part: bar_title, Style { Foreground: on_surface } }
  Rule { Widget: Dialog, Part: content, Style { Padding: <| {'left': 24, 'right': 24, 'top': 16, 'bottom': 16} if fullscreen else 0 |> } }
}
```

## How it reaches the view

Each rule names `Widget: Dialog` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `panel` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'surface' if fullscreen else 'surface_container_high' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Corner_Radius` | `<\| 0 if fullscreen else 28 \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `<\| 0 if fullscreen else 24 \|>` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `<\| 0 if fullscreen else 16 \|>` | Space between its children. |
| always | `Elevation` | `<\| 0 if fullscreen else 3 \|>` | A shadow level, 0 to 5. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `secondary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `headline` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `body` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `bar` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `{ Left: 4, Right: 16, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `8` | Space between its children. |

### `bar_title` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `content` (ScrollView)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `<\| {'left': 24, 'right': 24, 'top': 16, 'bottom': 16} if fullscreen else 0 \|>` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Dialog
    Part: panel
    Style { Background: tertiary }
  }
}
```
