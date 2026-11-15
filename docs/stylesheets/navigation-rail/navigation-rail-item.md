# NavigationRailItem_Stylesheet.tdl

The look of NavigationRailItem (Material 3): a 56 by 32 pill that is secondary_container when selected, with a 24 pixel icon in on_secondary_container (on_surface_variant otherwise) and the label in on_surface (on_surface_variant otherwise). In an expanded rail the pill is 56 high and as wide as the item, with the label inside it.

The look of [`NavigationRailItem`](../../components/navigation-rail.md) (in [Navigation rail](../../components/navigation-rail.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: NavigationRailItem
Tesserae: "0.6"
---
# The look of NavigationRailItem (Material 3): a 56 by 32 pill that is secondary_container when selected, with a 24 pixel icon in on_secondary_container
# (on_surface_variant otherwise) and the label in on_surface (on_surface_variant otherwise). In an expanded rail the pill is 56 high and as wide as the
# item, with the label inside it.
Styles {
  Rule {
    Widget: NavigationRailItem
    Style {
      Corner_Radius: 16
      Transition { Background: 150 }
    }
  }
  Rule {
    Widget: NavigationRailItem
    Part: pill
    Style {
      Width: <| 'auto' if expanded else 56 |>
      Height: <| 56 if expanded else 32 |>
      Corner_Radius: <| 28 if expanded else 16 |>
      Padding: <| {'left': 16, 'right': 24, 'top': 0, 'bottom': 0} if expanded else 0 |>
      Background: <| 'secondary_container' if selected else 'transparent' |>
      Transition { Background: 150 }
    }
  }
  Rule {
    Widget: NavigationRailItem
    Part: icon
    Style { Width: 24, Height: 24, Foreground: <| 'on_secondary_container' if selected else 'on_surface_variant' |> }
  }
  Rule {
    Widget: NavigationRailItem
    Part: badged_icon
    Style { Width: 24, Height: 24, Foreground: <| 'on_secondary_container' if selected else 'on_surface_variant' |> }
  }
  Rule { Widget: NavigationRailItem, Part: label, Style { Foreground: <| 'on_surface' if selected else 'on_surface_variant' |> } }
  Rule { Widget: NavigationRailItem, Part: inline_label, Style { Foreground: <| 'on_secondary_container' if selected else 'on_surface_variant' |> } }
}
```

## How it reaches the view

Each rule names `Widget: NavigationRailItem` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `NavigationRailItem` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `16` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Transition` | `{ Background: 150 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |

### `pill` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `<\| 'auto' if expanded else 56 \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| 56 if expanded else 32 \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `<\| 28 if expanded else 16 \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `<\| {'left': 16, 'right': 24, 'top': 0, 'bottom': 0} if expanded else 0 \|>` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Background` | `<\| 'secondary_container' if selected else 'transparent' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Transition` | `{ Background: 150 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `badged_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `<\| 'on_surface' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `inline_label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: NavigationRailItem
    Part: pill
    Style { Background: tertiary }
  }
}
```
