# NavigationDrawer_Stylesheet.tdl

The look of the standard navigation drawer: a `surface` column.

The look of [`NavigationDrawer`](../../components/navigation-drawer.md) (in [Navigation drawer](../../components/navigation-drawer.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: NavigationDrawer
Tesserae: "0.6"
---
# The look of the standard navigation drawer: a `surface` column.
Styles {
  Rule {
    Widget: NavigationDrawer
    Style {
      Background: <| 'surface@72%' if frosted else 'surface' |>
      Backdrop_Blur: <| 20 if frosted else 0 |>
    }
  }
}
```

## How it reaches the view

Each rule names `Widget: NavigationDrawer` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `NavigationDrawer` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'surface@72%' if frosted else 'surface' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Backdrop_Blur` | `<\| 20 if frosted else 0 \|>` | Blurs what is behind it, by this many pixels: with a translucent `Background`, a frosted surface. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: NavigationDrawer
    Style { Background: tertiary }
  }
}
```
