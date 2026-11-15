# Menu_Stylesheet.tdl

The look of Menu (Material 3): a surface_container surface with 4 pixel corners at level 2, 8 pixels above and below its items; headings in on_surface_variant.

The look of [`Menu`](../../components/menus.md) (in [Menus](../../components/menus.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Menu
Tesserae: "0.6"
---
# The look of Menu (Material 3): a surface_container surface with 4 pixel corners at level 2, 8 pixels above and below its items; headings in on_surface_variant.
Styles {
  Rule {
    Widget: Menu
    Part: surface
    Style {
      Background: <| 'surface_container@72%' if frosted else 'surface_container' |>
      Backdrop_Blur: <| 20 if frosted else 0 |>
      Corner_Radius: 4
      Elevation: 2
      Padding { Left: 0, Right: 0, Top: 8, Bottom: 8 }
    }
  }
  Rule { Widget: Menu, Part: heading, Style { Foreground: on_surface_variant, Padding { Left: 12, Right: 12, Top: 8, Bottom: 8 } } }
}
```

## How it reaches the view

Each rule names `Widget: Menu` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `surface` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'surface_container@72%' if frosted else 'surface_container' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Backdrop_Blur` | `<\| 20 if frosted else 0 \|>` | Blurs what is behind it, by this many pixels: with a translucent `Background`, a frosted surface. |
| always | `Corner_Radius` | `4` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Elevation` | `2` | A shadow level, 0 to 5. |
| always | `Padding` | `{ Left: 0, Right: 0, Top: 8, Bottom: 8 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `heading` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Padding` | `{ Left: 12, Right: 12, Top: 8, Bottom: 8 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Menu
    Part: surface
    Style { Background: tertiary }
  }
}
```
