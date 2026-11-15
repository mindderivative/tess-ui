# NavigationRail_Stylesheet.tdl

The look of NavigationRail (Material 3): a surface column 80 pixels wide, with 44 pixels above the first destination (less when there is a header), 12 between destinations. An expanded rail has 20 pixels of padding each side.

The look of [`NavigationRail`](../../components/navigation-rail.md) (in [Navigation rail](../../components/navigation-rail.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: NavigationRail
Tesserae: "0.6"
---
# The look of NavigationRail (Material 3): a surface column 80 pixels wide, with 44 pixels above the first destination (less when there is a header),
# 12 between destinations. An expanded rail has 20 pixels of padding each side.
Styles {
  Rule {
    Widget: NavigationRail
    Style {
      Background: <| 'surface@72%' if frosted else 'surface' |>
      Backdrop_Blur: <| 20 if frosted else 0 |>
      Padding: <| {'left': 20, 'right': 20, 'top': 44, 'bottom': 56} if expanded else {'left': 0, 'right': 0, 'top': 44, 'bottom': 56} |>
      Gap: 12
    }
  }
}
```

## How it reaches the view

Each rule names `Widget: NavigationRail` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `NavigationRail` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'surface@72%' if frosted else 'surface' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Backdrop_Blur` | `<\| 20 if frosted else 0 \|>` | Blurs what is behind it, by this many pixels: with a translucent `Background`, a frosted surface. |
| always | `Padding` | `<\| {'left': 20, 'right': 20, 'top': 44, 'bottom': 56} if expanded else {'left': 0, 'right': 0, 'top': 44, 'bo…` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `12` | Space between its children. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: NavigationRail
    Style { Background: tertiary }
  }
}
```
