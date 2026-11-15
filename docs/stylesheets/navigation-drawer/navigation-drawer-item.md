# NavigationDrawerItem_Stylesheet.tdl

The look of NavigationDrawerItem (Material 3): a pill (28 pixel corners) that is secondary_container when selected, 16 pixels in on the left and 24 on the right, the icon, label and badge in on_secondary_container when selected and on_surface_variant otherwise.

The look of [`NavigationDrawerItem`](../../components/navigation-drawer.md) (in [Navigation drawer](../../components/navigation-drawer.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: NavigationDrawerItem
Tesserae: "0.6"
---
# The look of NavigationDrawerItem (Material 3): a pill (28 pixel corners) that is secondary_container when selected, 16 pixels in on the left and 24 on the right, the
# icon, label and badge in on_secondary_container when selected and on_surface_variant otherwise.
Styles {
  Rule {
    Widget: NavigationDrawerItem
    Style {
      Corner_Radius: 28
      Padding { Left: 16, Right: 24, Top: 0, Bottom: 0 }
      Gap: 12
      Background: <| 'secondary_container' if selected else 'transparent' |>
      Transition { Background: 150 }
    }
  }
  Rule {
    Widget: NavigationDrawerItem
    Part: icon
    Style { Width: 24, Height: 24, Foreground: <| 'on_secondary_container' if selected else 'on_surface_variant' |> }
  }
  Rule { Widget: NavigationDrawerItem, Part: label, Style { Foreground: <| 'on_secondary_container' if selected else 'on_surface_variant' |> } }
  Rule { Widget: NavigationDrawerItem, Part: badge, Style { Foreground: <| 'on_secondary_container' if selected else 'on_surface_variant' |> } }
}
```

## How it reaches the view

Each rule names `Widget: NavigationDrawerItem` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `NavigationDrawerItem` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `28` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `{ Left: 16, Right: 24, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `12` | Space between its children. |
| always | `Background` | `<\| 'secondary_container' if selected else 'transparent' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Transition` | `{ Background: 150 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `badge` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: NavigationDrawerItem
    Style { Background: tertiary }
  }
}
```
