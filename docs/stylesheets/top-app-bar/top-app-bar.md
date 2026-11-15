# TopAppBar_Stylesheet.tdl

The look of TopAppBar (Material 3): a `surface` bar that becomes `surface_container` once content has scrolled under it; 4 pixels in from the edge for the icons, the title in on_surface (16 pixels from the left of a medium or large bar's title), 16 pixels of room at each end.

The look of [`TopAppBar`](../../components/top-app-bar.md) (in [Top app bar](../../components/top-app-bar.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: TopAppBar
Tesserae: "0.6"
---
# The look of TopAppBar (Material 3): a `surface` bar that becomes `surface_container` once content has scrolled under it; 4 pixels in from the edge for the icons, the
# title in on_surface (16 pixels from the left of a medium or large bar's title), 16 pixels of room at each end.
Styles {
  Rule {
    Widget: TopAppBar
    Style {
      Background: <| ('surface_container' if scrolled else 'surface') + ('@72%' if frosted else '') |>
      Backdrop_Blur: <| 20 if frosted else 0 |>
      Padding { Left: 4, Right: 4, Top: 0, Bottom: 0 }
      Clip_Children: true
    }
  }
  Rule { Widget: TopAppBar, Part: title, Style { Foreground: on_surface } }
  Rule { Widget: TopAppBar, Part: big_title, Style { Foreground: on_surface, Padding { Left: 12, Right: 12, Top: 0, Bottom: 0 } } }
}
```

## How it reaches the view

Each rule names `Widget: TopAppBar` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `TopAppBar` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| ('surface_container' if scrolled else 'surface') + ('@72%' if frosted else '') \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Backdrop_Blur` | `<\| 20 if frosted else 0 \|>` | Blurs what is behind it, by this many pixels: with a translucent `Background`, a frosted surface. |
| always | `Padding` | `{ Left: 4, Right: 4, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Clip_Children` | `true` | Whether children are cut off at its edge. |

### `title` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `big_title` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Padding` | `{ Left: 12, Right: 12, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: TopAppBar
    Style { Background: tertiary }
  }
}
```
