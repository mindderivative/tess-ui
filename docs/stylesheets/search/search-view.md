# SearchView_Stylesheet.tdl

The look of SearchView (Material 3): a surface_container_high panel with 28 pixel corners, 8 pixels above and below the rows.

The look of [`SearchView`](../../components/search.md) (in [Search](../../components/search.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: SearchView
Tesserae: "0.6"
---
# The look of SearchView (Material 3): a surface_container_high panel with 28 pixel corners, 8 pixels above and below the rows.
Styles {
  Rule {
    Widget: SearchView
    Part: panel
    Style {
      Background: <| 'surface_container_high@72%' if frosted else 'surface_container_high' |>
      Backdrop_Blur: <| 20 if frosted else 0 |>
      Corner_Radius: 28
      Padding { Left: 0, Right: 0, Top: 8, Bottom: 8 }
    }
  }
  Rule { Widget: SearchView, Part: none, Style { Foreground: on_surface_variant, Padding { Left: 16, Right: 16, Top: 12, Bottom: 12 } } }
  Rule { Widget: SearchView, Part: count, Style { Foreground: on_surface_variant } }
}
```

## How it reaches the view

Each rule names `Widget: SearchView` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `panel` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'surface_container_high@72%' if frosted else 'surface_container_high' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Backdrop_Blur` | `<\| 20 if frosted else 0 \|>` | Blurs what is behind it, by this many pixels: with a translucent `Background`, a frosted surface. |
| always | `Corner_Radius` | `28` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `{ Left: 0, Right: 0, Top: 8, Bottom: 8 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `none` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Padding` | `{ Left: 16, Right: 16, Top: 12, Bottom: 12 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `count` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: SearchView
    Part: panel
    Style { Background: tertiary }
  }
}
```
