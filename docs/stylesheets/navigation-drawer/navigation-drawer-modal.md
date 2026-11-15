# NavigationDrawerModal_Stylesheet.tdl

The look of the modal navigation drawer: surface_container_low at level 1, 16 pixel corners on the right (the side that opens onto the content).

The look of [`NavigationDrawerModal`](../../components/navigation-drawer.md) (in [Navigation drawer](../../components/navigation-drawer.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: NavigationDrawerModal
Tesserae: "0.6"
---
# The look of the modal navigation drawer: surface_container_low at level 1, 16 pixel corners on the right (the side that opens onto the content).
Styles {
  Rule {
    Widget: NavigationDrawerModal
    Part: sheet
    Style {
      Background: <| 'surface_container_low@72%' if frosted else 'surface_container_low' |>
      Backdrop_Blur: <| 20 if frosted else 0 |>
      Elevation: 1
      Corner_Radius { Top_Right: 16, Bottom_Right: 16 }
    }
  }
}
```

## How it reaches the view

Each rule names `Widget: NavigationDrawerModal` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `sheet` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'surface_container_low@72%' if frosted else 'surface_container_low' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Backdrop_Blur` | `<\| 20 if frosted else 0 \|>` | Blurs what is behind it, by this many pixels: with a translucent `Background`, a frosted surface. |
| always | `Elevation` | `1` | A shadow level, 0 to 5. |
| always | `Corner_Radius` | `{ Top_Right: 16, Bottom_Right: 16 }` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: NavigationDrawerModal
    Part: sheet
    Style { Background: tertiary }
  }
}
```
